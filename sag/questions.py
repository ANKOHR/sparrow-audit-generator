"""Copy-paste follow-up checklist."""
from .report import escape


def checklist(result):
    lines = [f"- [ ] {escape(q['process'])}: {escape(q['question'])}" for q in result["not_observed"]]
    return "\n".join(lines or ["No follow-up gaps identified."]) + "\n"
