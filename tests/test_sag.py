import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from sag.evidence import (load_evidence, validate, MissingFieldError,
                          InvalidMeasurementError, EmptyEvidenceError)
from sag.findings import analyze
from sag.fixtures import generate
from sag.questions import checklist
from sag.report import BANNER, render


@pytest.fixture
def evidence(tmp_path):
    return load_evidence(generate(tmp_path))


def single(evidence, **changes):
    result = copy.deepcopy(evidence)
    result["processes"] = [dict(result["processes"][0], **changes)]
    return result


def cli(*args):
    return subprocess.run([sys.executable, "-m", "sag", *map(str, args)],
                          capture_output=True, text=True)


def test_valid_observation_loads(evidence):
    assert evidence["business"]["fictional"] is True


@pytest.mark.parametrize("field,value,error", [
    ("name", None, MissingFieldError),
    ("measured_minutes_per_run", -1, InvalidMeasurementError),
    ("runs_per_week", -1, InvalidMeasurementError),
    ("processes", [], EmptyEvidenceError),
])
def test_malformed_evidence_raises_named_errors(evidence, field, value, error):
    if field == "processes":
        evidence[field] = value
    else:
        evidence["processes"][0][field] = value
    with pytest.raises(error):
        validate(evidence)


def test_waste_computed_only_from_fully_measured_processes(evidence):
    result = analyze(single(evidence))
    assert result["waste"][0]["weekly_waste_minutes"] == "120"
    assert {r["field"] for r in result["waste"][0]["evidence_refs"]} == {"measured_minutes_per_run", "runs_per_week"}


def test_partially_measured_process_has_no_waste(evidence):
    evidence = single(evidence)
    del evidence["processes"][0]["runs_per_week"]
    result = analyze(evidence)
    assert not result["waste"]
    assert result["not_observed"][0]["field"] == "runs_per_week"


def test_unmeasured_process_produces_no_numbers(evidence):
    evidence = single(evidence, pain_notes=["slow"])
    for field in ("measured_minutes_per_run", "runs_per_week"):
        del evidence["processes"][0][field]
    result = analyze(evidence)
    assert not result["waste"]
    assert all(not any(c.isdigit() for c in f["text"]) for f in result["findings"])


def test_every_finding_cites_evidence(evidence):
    for finding in analyze(evidence)["findings"]:
        assert finding["evidence_refs"]
        for ref in finding["evidence_refs"]:
            assert any(p["name"] == ref["process"] and ref["field"] in p for p in evidence["processes"])


def test_conflicting_entries_flagged_no_waste(evidence):
    result = analyze(evidence)
    assert any(f["rule"] == "conflicting_evidence" for f in result["findings"])
    assert all(w["process"] != "approval routing" for w in result["waste"])
    assert any(q["process"] == "approval routing" for q in result["not_observed"])


@pytest.mark.parametrize("format", ["md", "json"])
def test_honesty_banner_in_md_and_json(evidence, format):
    output = render(evidence, analyze(evidence), format)
    assert BANNER in output
    if format == "md":
        assert output.startswith(BANNER)
    else:
        assert next(iter(json.loads(output))) == "honesty_note"


def test_fixture_labelled_synthetic(tmp_path):
    text = generate(tmp_path).read_text()
    assert text.startswith("# SYNTHETIC FIXTURE - not a real business")
    assert "fictional: true" in text


def test_fixture_determinism(tmp_path):
    assert generate(tmp_path / "a").read_bytes() == generate(tmp_path / "b").read_bytes()


@pytest.mark.parametrize("format", ["md", "json"])
def test_determinism(tmp_path, format):
    path = generate(tmp_path)
    first = cli("audit", "--evidence", path, "--report", format)
    second = cli("audit", "--evidence", path, "--report", format)
    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout


def test_cli_smoke(tmp_path):
    assert cli("fixtures", "--out", tmp_path).returncode == 0
    path = tmp_path / "observation.yaml"
    for command in ("validate", "questions"):
        assert cli(command, "--evidence", path).returncode == 0
    for format in ("md", "json"):
        out = tmp_path / f"audit.{format}"
        run = cli("audit", "--evidence", path, "--report", format, "--out", out)
        assert run.returncode == 0, run.stderr
        assert BANNER in out.read_text()


def test_no_inference_from_pain_notes(evidence):
    evidence = single(evidence, pain_notes=["takes forever", "wastes 999 hours"])
    for field in ("measured_minutes_per_run", "runs_per_week"):
        del evidence["processes"][0][field]
    assert not analyze(evidence)["waste"]


def test_absurd_values_preserved(evidence):
    evidence = single(evidence, measured_minutes_per_run=100000)
    validate(evidence)
    result = analyze(evidence)
    assert result["waste"][0]["weekly_waste_minutes"] == "400000"
    assert any("100000" in f["text"] and f["evidence_refs"] for f in result["findings"])


def test_markdown_injection(evidence):
    baseline = render(evidence, analyze(evidence))
    evidence = single(evidence, name="## Pwned\n<script>alert(1)</script>|[bad](url)")
    output = render(evidence, analyze(evidence))
    assert sum(line.startswith("#") for line in output.splitlines()) == sum(line.startswith("#") for line in baseline.splitlines())
    assert "<script>" not in output
    assert "&lt;script&gt;" in output
    assert "## Pwned" not in output


def test_empty_process_report(evidence):
    evidence["processes"] = []
    validated = validate(evidence, allow_empty=True)
    result = analyze(validated)
    assert not result["findings"]
    for format in ("md", "json"):
        output = render(validated, result, format)
        assert BANNER in output and "No processes observed" in output


@pytest.mark.parametrize("content", ["[]", "hello", "null", "[one, two]", "!!python/object/apply:os.system ['echo bad']"])
def test_non_observation_yaml(tmp_path, content):
    path = tmp_path / "bad.yaml"
    path.write_text(content)
    with pytest.raises(MissingFieldError):
        load_evidence(path)
    run = cli("validate", "--evidence", path)
    assert run.returncode == 1
    assert "MissingFieldError" in run.stderr and "Traceback" not in run.stderr


@pytest.mark.parametrize("value", [True, "30", None, float("nan"), float("inf")])
def test_invalid_measurement_types(evidence, value):
    with pytest.raises(InvalidMeasurementError):
        validate(single(evidence, measured_minutes_per_run=value))


def test_rules_and_threshold(evidence):
    evidence = single(evidence)
    assert any(f["rule"] == "tool_switching" for f in analyze(evidence)["findings"])
    assert any(f["rule"] == "high_manual_load" for f in analyze(evidence)["findings"])
    assert not any(f["rule"] == "high_manual_load" for f in analyze(evidence, 30)["findings"])
    assert not any(f["rule"] == "tool_switching" for f in analyze(single(evidence, pain_notes=["slow"]))["findings"])


def test_questions(evidence):
    output = checklist(analyze(evidence))
    assert "- [ ]" in output and "approval routing" in output
    assert "runs per week" in output and "customer filing" in output


def test_duplicate_does_not_double_count_or_merge_partial(evidence):
    evidence = single(evidence)
    evidence["processes"].append(copy.deepcopy(evidence["processes"][0]))
    assert len(analyze(evidence)["waste"]) == 1
    del evidence["processes"][0]["runs_per_week"]
    del evidence["processes"][1]["measured_minutes_per_run"]
    assert not analyze(evidence)["waste"]


def test_fractional_and_zero_measurements(evidence):
    result = analyze(single(evidence, measured_minutes_per_run=0.1, runs_per_week=3))
    assert result["waste"][0]["weekly_waste_minutes"] == "0.3"
    assert analyze(single(evidence, measured_minutes_per_run=0))["waste"][0]["weekly_waste_minutes"] == "0"


def test_findings_sorted(evidence):
    findings = analyze(evidence)["findings"]
    keys = [(f["process"], f["rule"], f["text"]) for f in findings]
    assert keys == sorted(keys)


def test_cli_invalid_threshold_and_missing_file(tmp_path):
    path = generate(tmp_path)
    for threshold in ("bad", "-1", "NaN", "Infinity"):
        run = cli("audit", "--evidence", path, "--manual-threshold", threshold)
        assert run.returncode == 1 and "Traceback" not in run.stderr
    assert cli("validate", "--evidence", tmp_path / "absent").returncode == 1


def test_missing_process_name(evidence):
    del evidence["processes"][0]["name"]
    with pytest.raises(MissingFieldError):
        validate(evidence)


def test_end_to_end_traceability(tmp_path):
    from decimal import Decimal
    path = generate(tmp_path)
    evidence = load_evidence(path)
    run = cli("audit", "--evidence", path, "--report", "json")
    assert run.returncode == 0
    report = json.loads(run.stdout)
    for row in report["quantified_waste"]:
        entries = [p for p in evidence["processes"] if p["name"] == row["process"]]
        assert any(Decimal(str(p.get("measured_minutes_per_run", -1))) * Decimal(str(p.get("runs_per_week", -1))) == Decimal(row["weekly_waste_minutes"]) for p in entries)
        assert row["evidence_refs"]
    assert report["not_observed"] and report["evidence_appendix"] == evidence


def test_empty_cli_report(tmp_path, evidence):
    import yaml
    evidence["processes"] = []
    path = tmp_path / "empty.yaml"
    path.write_text(yaml.safe_dump(evidence))
    assert cli("validate", "--evidence", path).returncode == 1
    result = cli("audit", "--evidence", path)
    assert result.returncode == 0
    assert result.stdout.startswith(BANNER) and "No processes observed" in result.stdout
