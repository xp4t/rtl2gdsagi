# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`rtl2gdsagi` is an agentic RTL-to-GDSII orchestrator: it drives a 21-stage
open-source ASIC flow (Verilator → Yosys → OpenROAD → KLayout → EQY) on SKY130,
renders every tool script from a schema-bounded IR, parses the real tool
reports, and calls Claude **only** to diagnose failures. The whole project is
organised around one property: a check must never report clean unless it
actually looked at the right artifact with the right rules loaded.

## Commands

Everything runs out of the in-tree venv (`.venv/bin/...`); there is no
Makefile and no task runner.

```bash
./setup.sh --check                      # report toolchain/PDK state, change nothing
./setup.sh                              # install tools, PDK, venv (idempotent)
.venv/bin/pip install -e '.[dev]'

.venv/bin/rtl2gdsagi doctor             # tools + PDK + API key reachable?
.venv/bin/rtl2gdsagi stages             # the stage graph
.venv/bin/rtl2gdsagi taxonomy           # failure class -> responsible stage -> what it may not touch
.venv/bin/rtl2gdsagi schema [section]   # the agent's entire writable surface
.venv/bin/rtl2gdsagi status runs/<id>   # summarise a finished/in-flight run

# Full flow. --no-api replaces diagnosis with a scripted no-op (failures escalate).
.venv/bin/rtl2gdsagi run --config examples/register/register.yaml --no-api
.venv/bin/rtl2gdsagi run --rtl ~/design/rtl --top my_top --dry-run --no-api   # render scripts only
.venv/bin/rtl2gdsagi run --config ... --mock-tools   # full state machine, zero EDA invocations
```

Tests:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest tests/test_real_tool_parsers.py -q     # one file
.venv/bin/python -m pytest -q -k "antenna and not evidence"       # one test / pattern
```

`pythonpath = ["src"]` and `testpaths` come from `pyproject.toml`, so pytest
needs no install step. `DeprecationWarning` is an error.

Autonomy benchmark (adversarial injected-defect cases with pre-written ground
truth; see `benchmarks/autonomy/README.md`):

```bash
.venv/bin/python benchmarks/autonomy/run_case.py benchmarks/autonomy/case_01_floorplan_utilization.yaml
.venv/bin/python benchmarks/autonomy/grade.py <case.yaml> <run_dir>
```

`--diagnosis-source scripted` (the default) exercises the deterministic
machinery but is **not** autonomy evidence; only `live_model` is.

Exit codes: `0` clean · `1` error · `2` usage/config · `3` escalated to a human
(read `runs/<id>/failure_report.md`) · `4` budget exhausted · `5` safety boundary crossed.

## Architecture

Data flows one direction and every arrow is deterministic except the diagnosis
step:

```
stages.py (21 StageSpecs as data)
  └─ ir.py        typed schema  ── the ONLY thing an agent may write
       └─ render.py             ── the ONLY place tool syntax (TCL/scripts) is written
            └─ tools/invoker.py ── subprocess / OpenLane container; MockInvoker for tests
                 └─ checks/     ── parsers; the ONLY place a Verdict is constructed
                      └─ taxonomy.py  failure class → responsible stage, forbidden targets
                           └─ runner.py  Orchestrator: index-based loop that can jump backwards
```

Key modules:

| file | role |
|---|---|
| `stages.py` | the stage graph, gates (`hard`/`advisory`/`none`), consumes/produces keys |
| `taxonomy.py` | `FailureClass` → `Resolution` (retry/rollback/escalate) + `forbids` list |
| `ir.py` | `Field`/`SCHEMA`; range-checked, pattern-checked, `agent_writable` flags |
| `render.py` | pure `(IR section, RenderContext) → text`; byte-identical for identical IR |
| `runner.py` | orchestration, retries, rollback, escalation, signoff aggregation (largest file) |
| `checks/verdict.py` | `Verdict` — PASS / QOR_BELOW_TARGET / FAIL, never model-authored |
| `checks/{tools,klayout_drc,klayout_lvs,gds,pdn,spef,substrate_tie,deck_guard}.py` | per-tool report parsing |
| `artifacts.py` | content-addressed ledger; downstream stages request artifacts **by key**, never by path |
| `evidence.py` | `GateEvidence`/`GateContract` — what a PASS is allowed to rest on |
| `manifest.py` | release candidate: one final GDS sha256 that all signoff evidence must bind to |
| `safety.py` | immutable zones, non-extendable `IterationBudget`, diagnosis/delta review |
| `agent/` | `ClaudeAgent`, `ScriptedAgent`, `parse_diagnosis`, prompts |
| `spice.py`, `characterize.py`, `pdk.py` | CDL-ordered SPICE emission, RTL fact extraction, PDK discovery |

Two ideas do most of the work and are worth loading before changing anything:

- **Rollback is table-driven, not wired.** A failure resolves to a responsible
  stage through `taxonomy.py`; `downstream_of()` invalidates everything after
  it; the runner's index jumps backwards. Any stage is reachable from any
  failure without new code.
- **Certification is bound to bytes, not to state.** "Stage reached OK" is an
  orchestration fact; certification needs `GateEvidence` naming consumed
  artifacts and the grading report by hash, all re-checked at `signoff`
  against a single final-GDS sha256.

## Invariants — do not weaken these

These are enforced in code and pinned by tests (`test_architecture.py`,
`test_agent_boundary.py`, `test_autonomy_safety.py`, `test_evidence_lineage.py`,
`test_ir_safety.py`). Breaking one is a project-level regression, not a style
issue.

1. **Checks fail closed.** A missing report, an unparseable report, a report
   with zero rule categories loaded, a report about a different file — all
   FAIL. Never infer success from silence or from an exit code alone.
2. **The agent cannot construct a verdict.** Only `checks/` does. The model
   receives already-computed metrics and returns a `Diagnosis`.
3. **The agent cannot weaken a check.** Its write surface is `ir.py`. There is
   no field for waive/skip/relax, and `drc`/`lvs`/`antenna` expose performance
   knobs only. Adding a field that changes *what gets measured* breaks the
   property that makes the whole design safe — the audit found three such leaks
   (see `AUDIT-REMEDIATION.md`) and they are regression-tested.
4. **Immutable zones.** The PDK tree, signoff decks and the user's original RTL
   are read-only; repairs go to the run's private copy under `work/rtl/`.
5. **New `str` IR fields need a `pattern`.** Values are interpolated into Tcl,
   where `;` is a command separator.
6. **Renderers are pure.** No clock, no environment reads — a timestamp in a
   rendered script destroys the byte-identity that makes A/B diffs meaningful.
7. **Verdict-bearing parsers need a real-output fixture.** A parser and its mock
   can share the same wrong belief about a tool's syntax and stay green forever;
   the routing parser once matched *nothing* in a real OpenROAD log while 349
   tests passed. Add captured output to `tests/fixtures/real/<tool>/` with its
   provenance sidecar.

## Adding a stage

`StageSpec` in `stages.py` + renderer in `render.py` + checker in `checks/` +
taxonomy row. `runner.py` is generic and should not need to change.

## Repo layout notes

- `yosys/`, `eqy/`, `.sby-src/` are vendored upstream checkouts (separate git
  repos) used to build tooling — not part of this project's source. Only
  `src/rtl2gdsagi/resources/formal_pdk_proc.py` is vendored *into* the package
  (from EQY's SKY130 example) to preprocess SKY130 UDP cell models.
- The top-level `*.md` files are an engineering record, not stale scratch:
  `README.md` §8–9 is the authoritative account of what works and which false-clean
  bugs were found; `results.md` is the independent audit; `AUDIT-REMEDIATION.md`
  its disposition; the `CODEX-*` / `P0-*` / `FINAL-*` files are subsequent review
  rounds. Consult them before re-litigating a design decision.
- Runs land in `runs/<timestamp>/` (gitignored): `run.log`, `run.jsonl`,
  `run_state.json`, `signoff.json`, `failure_report.md`, `stages/NN_<name>/`,
  `checkpoints/`.

## Known open problems

Don't assume these are bugs you introduced:

- **LVS does not match.** Reference SPICE generation is solved; reconciling how
  extracted vs. reference netlists represent cell bulk/power pins is not.
- **LEC produces false counterexamples on some sequential designs** (the
  `counter` example). Netlist-vs-itself proves cleanly, so the fault is in
  gold/gate partition alignment. Because of this the tool never tells a user
  their design is broken — it says equivalence was not established.
- **Timing is a single typical corner.** No MCMM, no OCV.
- The self-healing loop has limited live-model exercise; most preserved runs
  used `--no-api`.

---

Codex (`~/.codex/config.toml`) and Gemini (`~/.gemini/`) configs exist on this
machine. To bring over MCP servers, slash commands, subagents, skills or
instructions, reply `/import` to see what's importable, then
`/import --yes=<digest>` to apply the user-level items.
