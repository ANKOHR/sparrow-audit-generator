"""Mandatory-banner Markdown and JSON reports."""
import html
import json

BANNER = "HONESTY NOTE: every number in this audit is computed from the supplied observation file. This tool measured nothing and inferred nothing. Items that were not observed are listed under Not observed."


def escape(value):
    text = html.escape(str(value), quote=True)
    for char in "\\`*_{}[]()#+-.!|":
        text = text.replace(char, "\\" + char)
    return text.replace("\r", "&#13;").replace("\n", "&#10;")


def citation(refs):
    return "; ".join(f"{r['process']}.{r['field']}" for r in refs)


def render(evidence, result, format="md"):
    summary = "No processes observed" if not evidence["processes"] else "Findings reflect supplied observations. Waste figures are measured process time, not a claim that all recorded time is avoidable."
    if format == "json":
        return json.dumps(dict(honesty_note=BANNER, executive_summary=summary,
                               findings=result["findings"], quantified_waste=result["waste"],
                               friction_points=[f for f in result["findings"] if f["rule"] in ("pain_note", "tool_switching", "high_manual_load")],
                               not_observed=result["not_observed"], evidence_appendix=evidence),
                          ensure_ascii=True, indent=2, allow_nan=False) + "\n"
    if format != "md":
        raise ValueError("unsupported report format")
    lines = [BANNER, "", "# Operational audit", "", "## Executive summary", "", escape(summary), "", escape(evidence["business"]["name"]), "", "## Findings", ""]
    for f in result["findings"]:
        lines.append(f"- {escape(f['process'])}: {escape(f['text'])} Evidence: {escape(citation(f['evidence_refs']))}")
    if not result["findings"]:
        lines.append("No findings.")
    lines += ["", "## Quantified waste", "", "| Process | Minutes per run | Runs per week | Weekly waste minutes | Evidence |", "| --- | --- | --- | --- | --- |"]
    for w in result["waste"]:
        lines.append("| " + " | ".join(escape(v) for v in (w["process"], w["measured_minutes_per_run"], w["runs_per_week"], w["weekly_waste_minutes"], citation(w["evidence_refs"]))) + " |")
    if not result["waste"]:
        lines += ["", "No quantified waste observed."]
    lines += ["", "## Friction points", ""]
    friction = [f for f in result["findings"] if f["rule"] in ("pain_note", "tool_switching", "high_manual_load")]
    lines += [f"- {escape(f['process'])}: {escape(f['text'])} Evidence: {escape(citation(f['evidence_refs']))}" for f in friction] or ["No friction observed."]
    lines += ["", "## Not observed", ""]
    lines += [f"- [ ] {escape(q['process'])}: {escape(q['question'])}" for q in result["not_observed"]] or ["No follow-up gaps identified."]
    lines += ["", "## Evidence appendix", ""]
    # Render each supplied field as literal text; no raw user Markdown or HTML.
    for key, value in evidence.items():
        lines.append(f"- {escape(key)}: {escape(json.dumps(value, ensure_ascii=True, allow_nan=False))}")
    return "\n".join(lines) + "\n"
