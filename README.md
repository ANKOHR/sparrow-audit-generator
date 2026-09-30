# Sparrow Audit Generator

Sparrow's positioning is "see the system, remove the friction, give people their time back". The product is time. `sag` turns supplied operational observations into a credible discovery audit without inventing measurements.

> We only count what we measured. Everything else is listed as not observed.

## Quickstart

Python 3.10 or newer and PyYAML are required. Runtime dependencies are the standard library and PyYAML only. pytest is a development dependency. There are no model calls, network calls, GPU operations, or GPU dependencies in the tool.

```powershell
python -m pip install -e "."
python -m pip install pytest
sag fixtures --out demo
sag validate --evidence demo/observation.yaml
sag audit --evidence demo/observation.yaml --report md --out demo/audit.md
sag audit --evidence demo/observation.yaml --report json
sag questions --evidence demo/observation.yaml
python -m pytest -q
```

If the `sag` command is not on PATH, use `python -m sag` with the same arguments. Install dependencies beforehand in an offline environment. Installation commands may use the package index; the CLI itself does not use the network.

For the two-minute demo, generate the fixture and run the Markdown audit. Show the honesty note, the traceable waste table, and Not observed. Approval routing is contradictory and therefore has no waste figure. It is flagged for clarification, never averaged. Real observation files use precisely the same command and schema.

## Architecture

```text
YAML observation file
    -> evidence.py: safe_load and schema validation
    -> findings.py: deterministic rules and evidence references
    -> report.py: mandatory-banner Markdown or JSON
    -> questions.py: copy-paste follow-up checklist

fixtures.py -> labelled synthetic observation file
cli.py     -> validate | audit | questions | fixtures
```

## HONESTY BOUNDARY

The tool never measures anything itself. It computes only from supplied numeric measurements. Both measurements must occur on the same process entry before multiplication is allowed. It never imputes missing measurements, extracts numbers from adjectives or pain notes, averages contradictions, silently clamps absurd values, or invents costs or savings. Recorded process time is labelled weekly waste for the requested audit metric; it is not proof that all that time is avoidable. Manual load and tool-switching are explicit deterministic flags, not inferred time estimates.

Every report begins with the fixed honesty note. In JSON the first property is `honesty_note`, containing the same exact text:

HONESTY NOTE: every number in this audit is computed from the supplied observation file. This tool measured nothing and inferred nothing. Items that were not observed are listed under Not observed.

Waste rows and every finding carry `evidence_refs`, each containing the process name and source field. The appendix preserves supplied observations, including conflicting entries. Reports contain no generated timestamps, invented totals, threshold numbers, or numbered evidence identifiers. Decimal calculations avoid binary floating-point multiplication artifacts; JSON measurement and waste values are exact decimal strings, not floating-point approximations. Observed metadata and verbatim notes may contain supplied numbers. Rule thresholds are configuration, not measurements, and are not printed as audit numbers.

## Schema reference

```yaml
business:
  name: "Fictional Paperclip Co"
  fictional: true
observed_by: "Henry Williams"
observed_date: "2026-09-30"
processes:
  - name: "invoice data entry"
    description: "AP clerk retypes supplier invoices into the ledger"
    steps: ["open PDF", "retype lines", "email for approval"]
    measured_minutes_per_run: 30
    runs_per_week: 4
    tools_used: ["PDF reader", "ledger spreadsheet"]
    pain_notes: ["typos cause rework", "approver is a bottleneck"]
```

| Field | Required | Meaning and validation |
| --- | --- | --- |
| business.name | Yes | Non-empty business name |
| business.fictional | Yes | Boolean; use false for real observations |
| observed_by | Yes | Non-empty observer name |
| observed_date | Yes | ISO calendar date; quote it in YAML |
| processes | Yes | List of process mappings |
| process.name | Yes | Non-empty name; exact names group duplicate entries |
| process.description | Yes | Non-empty observed description |
| process.steps | Yes | List of non-empty strings; empty list allowed |
| process.tools_used | Yes | List of non-empty tool names; empty list allowed |
| process.pain_notes | Yes | List of non-empty verbatim observations; empty list means not observed |
| process.measured_minutes_per_run | No | Finite, non-negative numeric measurement |
| process.runs_per_week | No | Finite, non-negative numeric frequency; fractions allowed |

Omit unmeasured fields entirely. Null, strings, booleans, negative and non-finite measurement values are invalid. Zero is a valid observation and is retained. Large non-negative values are accepted and shown without smoothing. Files are parsed only with `yaml.safe_load`.

Named schema failures are `MissingFieldError` for missing or malformed structure, `InvalidMeasurementError` for invalid measurements, and `EmptyEvidenceError` for an empty process list. To reconcile strict validation with the empty-report requirement, `validate` rejects an empty list; `audit` and `questions` allow it. Empty audits say "No processes observed", have no findings, and retain the banner. Valid YAML that is not an observation returns a named error without a traceback.

## Rule list

- `measured_waste`: multiply minutes per run by runs per week only if both occur in one entry. Cite both fields.
- `pain_note`: surface each distinct note verbatim, citing pain_notes. Markdown escapes it as literal text.
- `tool_switching`: require at least two listed tools and handoff language in that entry's notes. The case-insensitive whole-word vocabulary is handoff, hand-off, hand off, approval, approver, email, send, sent, forward, transfer. Cite tools_used and pain_notes.
- `high_manual_load`: measured minutes strictly exceed the default threshold of 20 minutes, configurable using `--manual-threshold`. Cite measured_minutes_per_run. Equality does not trigger it.
- `conflicting_evidence`: any different supplied values for either measurement among entries sharing an exact name suppress all waste for that name. Cite measurement fields and ask for resolution.
- Not observed: ask about each missing measurement and absent pain notes. If any duplicate entry lacks a field, retain that follow-up question even when another entry is complete. Partial entries are never joined into a fabricated complete observation.

Identical duplicate measurements are counted once per process, not once per entry. Findings are deduplicated and sorted by process name, rule name, then finding text. Waste and questions are ordered by process name, with missing measurements in schema order followed by pain notes. Repeated runs produce byte-identical reports. Markdown escapes HTML, Markdown punctuation, pipes, and line breaks in evidence so supplied names cannot change report structure.

## CLI reference

| Command | Options | Result |
| --- | --- | --- |
| sag fixtures | --out DIRECTORY | Write observation.yaml, creating the directory |
| sag validate | --evidence FILE | Schema check only; conflicts are valid observations |
| sag audit | --evidence FILE --report md or json --out FILE --manual-threshold NUMBER | Render audit; report defaults to md, out is optional |
| sag questions | --evidence FILE | Copy-paste Not observed checklist |

Successful commands exit 0; schema, threshold, and file errors exit 1 with a named diagnostic on stderr. Invalid command syntax exits 2. Audit output goes to stdout unless `--out` is supplied. Thresholds must be finite and non-negative. Output directories for reports must already exist. The CLI has no publishing command or custom templates that can remove the banner.

## Synthetic fixtures

The fixture uses a local random generator with fixed seed **7**. Its first line is `# SYNTHETIC FIXTURE - not a real business`, its business is Fictional Paperclip Co, and `fictional: true` is mandatory. It mixes fully measured, partially measured, and unmeasured processes plus contradictory approval-routing entries. Generation is deterministic, including repeated generation in different directories. The checked-in example is generated by the same function. No real prospect data is included.

## Verification

The pytest suite covers schema failures, all finding rules, traceable arithmetic, absent measurements, adjective non-inference, conflicting and repeated entries, extreme and fractional values, fixture labels and determinism, output determinism, Markdown injection, empty reports, unsafe YAML rejection, question checklists, CLI errors, and end-to-end CLI runs in both formats.

## Improvement hook and lifecycle

After each real audit, paste `sag questions` into call notes and log which questions the prospect answers. Count answered questions across audits. Promote the most frequently answered questions into first-class schema fields in the next schema version, based on evidence rather than assumptions. The fixture checklist is the starting set.

Maintain this as Sparrow sales tooling. Integrate it into the Sparrow site's start flow after a real prospect audit has been run. Reconsider and kill it only if no real audit is run within six months and the ROI calculator covers the need alone. After first real use, the verdict is to promote the most-answered questions into the schema. The reusable KOML lesson is that every reported number should cite a source measurement and unknowns should be labelled rather than filled.

Publishing is a separate verification step. This build does not publish to GitHub or anywhere else. BUILD-DONE.txt records the tested implementation commit and test count; the subsequent marker-only commit keeps the final repository clean without attempting a self-referential commit hash.
