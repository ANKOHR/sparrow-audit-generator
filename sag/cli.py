"""CLI entry point; no network or measurement operations."""
import argparse
from decimal import InvalidOperation
from pathlib import Path
import sys
from .evidence import load_evidence
from .findings import analyze
from .fixtures import generate
from .questions import checklist
from .report import render


def main(argv=None):
    parser = argparse.ArgumentParser(prog="sag")
    commands = parser.add_subparsers(dest="command", required=True)
    fixtures = commands.add_parser("fixtures")
    fixtures.add_argument("--out", required=True)
    for name in ("validate", "audit", "questions"):
        command = commands.add_parser(name)
        command.add_argument("--evidence", required=True)
        if name == "audit":
            command.add_argument("--report", choices=("md", "json"), default="md")
            command.add_argument("--out")
            command.add_argument("--manual-threshold", default="20", help="manual load threshold in minutes (default: 20)")
    args = parser.parse_args(argv)
    try:
        if args.command == "fixtures":
            print(generate(args.out))
            return 0
        evidence = load_evidence(args.evidence, allow_empty=args.command != "validate")
        if args.command == "validate":
            print("Valid observation file.")
            return 0
        result = analyze(evidence, getattr(args, "manual_threshold", 20))
        output = checklist(result) if args.command == "questions" else render(evidence, result, args.report)
        if getattr(args, "out", None):
            Path(args.out).write_text(output, encoding="utf-8", newline="\n")
        else:
            sys.stdout.write(output)
        return 0
    except (ValueError, OSError, InvalidOperation) as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
