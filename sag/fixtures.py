"""Synthetic deterministic fixture, documented seed 7."""
from pathlib import Path
import random
import yaml

SEED = 7


def generate(out):
    rng = random.Random(SEED)
    def process(name, minutes=None, runs=None, notes=None):
        p = dict(name=name, description="Staff perform the described operational process.",
                 steps=["open source", "perform task", "request approval"],
                 tools_used=["PDF reader", "ledger spreadsheet"], pain_notes=notes or [])
        if minutes is not None:
            p["measured_minutes_per_run"] = minutes
        if runs is not None:
            p["runs_per_week"] = runs
        return p
    entries = [process("invoice data entry", 30, 4, ["typos cause rework", "approver is a bottleneck"]),
               process("stock reconciliation", rng.choice([10, 15, 20]), 2, ["email handoff delays completion"]),
               process("supplier onboarding", 25, notes=["takes forever"]),
               process("customer filing"),
               process("approval routing", 10, 3, ["waiting for approval"]),
               process("approval routing", 15, 3, ["waiting for approval"])]
    data = dict(business=dict(name="Fictional Paperclip Co", fictional=True), observed_by="Henry Williams",
                observed_date="2026-09-30", processes=entries)
    destination = Path(out) / "observation.yaml"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("# SYNTHETIC FIXTURE - not a real business\n" + yaml.safe_dump(data, sort_keys=False), encoding="utf-8", newline="\n")
    return destination
