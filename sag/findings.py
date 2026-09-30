"""Deterministic evidence rules. Default manual threshold: 20 minutes."""
from decimal import Decimal, localcontext
import re

MEASUREMENTS = ("measured_minutes_per_run", "runs_per_week")
HANDOFF = re.compile(r"\b(handoff|hand-off|hand off|approval|approver|email|send|sent|forward|transfer)\b", re.I)


def number(value):
    return format(Decimal(str(value)), "f")


def analyze(evidence, manual_threshold=20):
    threshold = Decimal(str(manual_threshold))
    if not threshold.is_finite() or threshold < 0:
        raise ValueError("manual threshold must be finite and non-negative")
    groups = {}
    for p in evidence["processes"]:
        groups.setdefault(p["name"], []).append(p)
    findings, waste, questions = [], [], []
    for name, entries in sorted(groups.items()):
        def refs(*fields):
            return [{"process": name, "field": field} for field in fields]
        def finding(rule, text, *fields):
            findings.append(dict(process=name, rule=rule, text=text, evidence_refs=refs(*fields)))
        def question(field, text):
            questions.append(dict(process=name, field=field, question=text, evidence_refs=refs(field)))
        conflict = any(len({p[field] for p in entries if field in p}) > 1 for field in MEASUREMENTS)
        if conflict:
            finding("conflicting_evidence", "Conflicting measurements supplied; waste withheld pending resolution.", *MEASUREMENTS)
            question("measurements", "Resolve conflicting measurements for this process.")
        for field in MEASUREMENTS:
            if any(field not in p for p in entries):
                question(field, f"What is the observed {field.replace('_', ' ')}?")
        if any(not p["pain_notes"] for p in entries):
            question("pain_notes", "What friction or pain was observed in this process?")
        # Never combine partial entries or count duplicate entries twice.
        complete = [p for p in entries if all(field in p for field in MEASUREMENTS)]
        if complete and not conflict:
            p = complete[0]
            a, b = (Decimal(str(p[field])) for field in MEASUREMENTS)
            with localcontext() as context:
                context.prec = max(28, len(a.as_tuple().digits) + len(b.as_tuple().digits))
                total = a * b
            row = dict(process=name, measured_minutes_per_run=number(a), runs_per_week=number(b),
                       weekly_waste_minutes=number(total), evidence_refs=refs(*MEASUREMENTS))
            waste.append(row)
            finding("measured_waste", f"{number(a)} minutes per run * {number(b)} runs per week = {number(total)} weekly waste minutes.", *MEASUREMENTS)
        seen = set()
        for p in entries:
            for note in p["pain_notes"]:
                if note not in seen:
                    finding("pain_note", note, "pain_notes")
                    seen.add(note)
            if len(p["tools_used"]) >= 2 and any(HANDOFF.search(n) for n in p["pain_notes"]):
                finding("tool_switching", "Multiple tools and observed handoff language indicate tool-switching friction.", "tools_used", "pain_notes")
            if "measured_minutes_per_run" in p and Decimal(str(p["measured_minutes_per_run"])) > threshold:
                finding("high_manual_load", f"Measured manual load: {number(p['measured_minutes_per_run'])} minutes per run exceeds the configured manual threshold.", "measured_minutes_per_run")
    unique = { (f["process"], f["rule"], f["text"]): f for f in findings }
    return dict(findings=sorted(unique.values(), key=lambda f: (f["process"], f["rule"], f["text"])),
                waste=waste, not_observed=questions)
