# CLAUDE — Final read-only pre-live GO/NO-GO review

Reviewer: independent read-only pass. No project file was modified (verified:
`git status --short` empty at the end of the review). No credential was
requested or inspected. No remote model call was made. No package was
installed. No finding was remediated.

The single question: **is the repository safe and instrumented well enough for
exactly ONE controlled live Claude API execution of `case_05_droute_iters`?**

---

## Verdict

```
C — NO-GO, IMPORTANT BLOCKER REMAINS
```

Not because the model can weaken verification — it demonstrably cannot — but
because **the benchmark instrument cannot record a successful live run.** A
live run that does everything right is graded FAIL, reports
`autonomy_evidence: false` and exits 1. The experiment as currently wired
cannot produce the claim it exists to produce, and the failure would read as
"the model did not remediate" when the model did.

Everything F1, F2, N1 and N2 were supposed to fix is genuinely fixed in the
*deterministic* half. The defect is in the live half, which the scripted
control structurally cannot exercise.

---

## 1. Baseline

Run with `/home/xpat/rtl2gdsagi-backup/.venv/bin/python`, whose editable
install resolves `rtl2gdsagi` to the current `/home/xpat/rtl2gdsagi/src`.

```
830 passed in 40.02s
collected 830 · passed 830 · failed 0 · skipped 0 · xfailed 0
```

The claim of 830 passing is accurate.

> **ENV note (not a code finding).** The documented in-tree `.venv` does not
> exist; every command in `CLAUDE.md` and `README.md` beginning `.venv/bin/...`
> fails with *No such file or directory*. `yosys/`, `eqy/`, `.sby-src/` and
> `runs/` are also absent. This does not affect any verdict below, but the
> live run cannot be launched with the documented command line until the
> environment is restored.

---

## 2. `scripted_trial_02`, verified from raw artifacts

Not from `result.json`.

| | recorded | verified from disk |
|---|---|---|
| attempt 1 stage / attempt | `routing` / `1` (int) | ✔ |
| attempt 1 `droute_iters` | `1` (int) | ✔ typed check |
| `routing.attempt_01.tcl` sha256 | `0b6d79dbeba4…` | ✔ `sha256sum` identical |
| attempt 1 rendered arg | — | ✔ `-droute_end_iter 1` at line 21 |
| attempt 2 `droute_iters` | `32` (int) | ✔ |
| `routing.attempt_02.tcl` sha256 | `b427df77a3d8…` | ✔ identical |
| attempt 2 rendered arg | — | ✔ `-droute_end_iter 32` |

Real OpenROAD output, not a mock:

```
attempt_01.log  DRT-0195 Start 0th iteration → DRT-0199 violations = 9
                DRT-0195 Start 1st iteration → DRT-0199 violations = 2   ← terminal
attempt_02.log  … 9 → 2 → 9 → DRT-0199 violations = 0                   ← terminal
```

Calibration in the case YAML (`droute_iters_1: 2`, `droute_iters_32: 0`) is
reproduced exactly by the raw tool logs. **Case-05 calibration: VALID.**

Stale-artifact isolation is real: attempt 1's three declared outputs
(`register.routed.def`, `register.routed.v`, `route.drc.rpt`) were moved to
`stages/12_routing/superseded/000/` before attempt 2 ran, so an attempt 2 that
wrote nothing would leave no stale current evidence.

Downstream: 21/21 stages, 11/11 certifying gates present, all verdicts `pass`,
signoff clean, `certification_id 0119145c2ec77a41…` **recomputes exactly** from
the recorded gate records. Grader 32/32 PASS, CLI exit 0.

---

## 3. F1 — injection proof: **CLOSED**

`grade.py` contains no substring proof over `run.jsonl`; the only substring
matching left is `rendered_evidence` against the *frozen, hash-verified
attempt-1 script*, and the typed value is checked independently.

16 bypass attempts, each on a copy of the run:

| attack | result |
|---|---|
| baseline (unmodified) | PASS ✔ |
| `1` → `16` (old prefix-collision hole) | FAIL ✔ |
| string `"1"` instead of int `1` | FAIL ✔ |
| `True` instead of int `1` | FAIL ✔ |
| wrong stage in snapshot | FAIL ✔ |
| wrong attempt number | FAIL ✔ |
| snapshot deleted | FAIL ✔ |
| script deleted | FAIL ✔ |
| snapshot unparseable | FAIL ✔ |
| script edited | FAIL ✔ |
| script edited **and hash re-fixed** | FAIL ✔ |
| recorded hash tampered | FAIL ✔ |
| script/config disagreement | FAIL ✔ |
| attempt 2 still carrying the injection | FAIL ✔ |
| whole failing-stage dir removed | FAIL ✔ |
| value only in `result.json`, snapshot says 16 | FAIL ✔ |
| snapshot **and** script both say 16 | FAIL ✔ |

```
MUTATIONS THAT STILL PASSED: NONE
```

---

## 4. N2 — benchmark freeze: **CLOSED**

`check_freeze()` is the first thing `grade()` calls (`grade.py:164`), before any
causal check. All six components recompute identically against the current
tree — drift zero:

```
case_yaml           36828d8d401f3e26…  ✔
grader              affbb92923459579…  ✔   (grade.py's own hash, no exception)
harness             672e8d099aecdc42…  ✔
prompt_code         4792e108744ff772…  ✔
authorization_code  8fbfa942686c329a…  ✔
action_space_schema ea6c2e71ea374e38…  ✔
```

13 freeze attacks on copies — every one VOID/FAIL, and **grading never rewrote
`benchmark_freeze.json` in any of them**:

| mutation | result |
|---|---|
| grader / harness / prompt / authorization / schema / case hash changed | VOID ✔ (each) |
| freeze file missing / malformed / not an object / `{}` / one entry dropped | FAIL ✔ (each) |
| a genuinely edited case YAML graded against the original run | VOID ✔ |

CLI exit is 1 on VOID, 0 clean. The `scripted_trial_01_pre_N1N2` void is
correctly recorded and superseded.

---

## 5. N1 — prompt / authorization consistency: **CLOSED**

One permission source, confirmed at the call site
(`runner.py:1015` `current_config=authorized_current_values(self.ir, verdict.failure)`,
`runner.py:1019` `action_space=authorized_action_space(verdict.failure)`), and
`authorized_current_values` is derived from `authorized_action_space`
(`safety.py:359`) — not a second list.

The real Case-05 prompt was rendered (16,658 chars) from a real
`DiagnosisRequest` built on the injected IR and the run's own evidence.

Action surface — **exactly the 12 expected fields, no more**:

```
floorplan  aspect_ratio [0.2,5.0]  core_margin_um [0,500]
           core_utilization [0.05,0.9]  tapcell_distance_um [1,100]
placement  padding_sites [0,8]  routability_driven {T,F}  target_density [0.15,0.99]
routing    droute_iters [1,64]  insert_diodes {T,F}  insert_filler {T,F}
           max_layer [1,12]  min_layer [1,12]
```

Every one: `agent_writable=True`, bounded, consumed by `render.py`, and
**referenced nowhere in `checks/`** — none can move an acceptance threshold.
**Zero `str`-typed fields**, so there is no Tcl interpolation surface at all.

All five fields required to be absent are absent from the schema block **and**
from the rendered prompt text:

```
global_effort  absent · io_mode  absent · effort  absent
max_displacement_um  absent · congestion_overflow_limit  absent
```

Out-of-surface proposals are all rejected deterministically:

```
routing.global_effort            SchemaViolation: not agent-writable
placement.congestion_overflow_limit  SchemaViolation: not agent-writable
placement.effort / max_displacement_um / floorplan.io_mode   same
sdc.* / drc.*                    SafetyViolation at review_delta_scope
{"waivers": {...}}               SchemaViolation: unknown IR section
routing.skip_drc                 SchemaViolation: not a field in the schema
droute_iters 9999 / -1           SchemaViolation: range
target_density NaN               SchemaViolation: not a finite number
droute_iters "32; exec rm -rf /" SchemaViolation: not a valid int
```

There is no waive/skip/relax field anywhere in the writable schema.

**Prompt/action surface: VALID.**

---

## 6. Ground-truth blindness: **NO leakage**

`ClaudeAgent.diagnose` passes `model`, `max_tokens`, `system`, `messages` and
nothing else — **no `tools=` parameter**, so no filesystem, shell, retrieval or
MCP surface exists at the API level. The model receives one string and returns
one string.

Scanned the rendered prompt for 21 ground-truth tokens. Two hits, both false
positives:

* `"grade"` — inside the word *downgrade* in the system prompt;
* `"32"` — inside `peak = 525.32 (MB)` in the OpenROAD log.

Absent: `case_05`, `known_remedy`, `ground_truth`, the calibration table,
`expected_failure_stage`, `true_root_cause`, `success_criteria`,
`before_metric` / `after_metric`, `expected_outcome`, `rendered_evidence`.

The prompt does show `droute_iters: 1` (it must — that is the thing being
diagnosed) and the field's declared `default: 32` as part of the schema. That
is within the explicitly permitted "legal range/default" and is disclosed by the
project as making this an easy first question. It is a fair, blind — and easy —
benchmark.

---

## 7. Deterministic attribution sources (the F2 plumbing): correct

Traced to runtime, not to the CLI answer or the case YAML:

* `accepted_delta` — `runner.py:1145`, appended to `_accepted` **only after**
  `review_diagnosis` (`:1064`) → `review_delta_scope` (`:1067`) → `apply_delta(agent=True)`
  (`:1130`) have all accepted it. Nothing reads `--scripted-delta` back.
* `failure_class` — `verdict.failure`, the deterministic verdict, not the model's.
* `rollback_target` — deterministic taxonomy, then moved *earlier* by
  `earliest_affected_stage` if the delta demands it; the model cannot name a
  downstream stage.
* `before/after_metrics` — `orch._history`, first/last recorded
  `route_violations` for the responsible stage (2 → 0, matching the raw logs).
* `candidate_valid` — computed from signoff `clean` **and** a
  `certification_id` **and** all gate verdicts `pass`; never from the exit code.
* `prompt/system_prompt/evidence/response_sha256` — from `CallAudit`, built
  inside the same `return` as `parse_diagnosis` (`client.py:191`), i.e. at call
  time before any outcome is known. `CallAudit` is `@dataclass(frozen=True)`,
  records provider/model and the full texts, and carries no credential —
  `to_dict(include_text=True)` was searched for `sk-` and `ANTHROPIC_API_KEY`,
  neither present.

A reviewer can reconstruct exactly what a future live model was shown.

---

## 8. Live vs scripted wiring: correct

```
--diagnosis-source live_model, no credential
  → "requires ANTHROPIC_API_KEY", exit 2, and NO run directory created
    (the guard returns before _safe_run_dir); runs/ verified untouched
build_live_agent(None) → ClaudeAgent (isinstance ScriptedAgent: False)
ClaudeAgent._ensure_client() without a key → AgentError, no import of anthropic
```

`run_case.py` always passes a non-`None` agent, so the latent
`agent or ScriptedAgent()` fallback at `runner.py:164` is unreachable through
the harness, and the explicit `isinstance(agent, ScriptedAgent) → return 2`
guard backs it up. **No live→scripted fallback is reachable.**

---

## 9. GateEvidence / lineage: **VALID**

11/11 certifying gates present, all `pass`, `certification_id` recomputes
exactly. Eight tampers — dropped gate, flipped verdict, wrong `report_sha256`,
wrong `tool_identity`, wrong `parser_contract`, stale `attempt_id`, hybrid
consumed-artifact hash, dropped produced set — **all change the recomputed
certification identity**.

SPEF / STA / PDN historical false-cleans re-run and green (87 tests):
duplicate resolved D_NET, missing routed net, extra net, truncated D_NET,
unmapped identifier, zero-net SPEF, wrong design, NAME_MAP resolution;
STA-0172 / 0174 / 0175 / 0179; unannotated and *partially* annotated drivers;
marker-without-report. PDN is not authorized for a routing failure at all, so
the model cannot reach the PDN contract in Case 05.

---

## 10. Findings

### P0-LIVE-01 — a live run can never grade PASS (blocking)

**Files:** `benchmarks/autonomy/run_case.py:386-388`, `benchmarks/autonomy/grade.py:402-407`

`main()` grades first, then computes autonomy:

```python
g = grade(case, result, run_dir, case_path=Path(args.case))   # :386
result["ground_truth_pass"] = g.passed                        # :387
ok, missing = attribution_complete(result)
result["autonomy_evidence"] = ok                              # :388
```

but on the live branch `grade()` requires the field that has not been written yet:

```python
if live:
    g.check("autonomy evidence is complete",
            result.get("autonomy_evidence") is True, ...)      # grade.py:405-407
```

The comment at `run_case.py:383` claims the ordering "avoids a circular
dependency". It does not — the dependency is two-way, and the ordering only
breaks one direction.

**Reproduction** (replaying `main()`'s exact ordering against the real grader,
with a maximally successful live-shaped result: real call recorded, all four
audit hashes, correct class, correct delta, 2 → 0 violations, candidate valid):

```
pre-grade result['autonomy_evidence'] = None

  [FAIL] autonomy evidence is complete --

grade.passed        : False (32/33)
ground_truth_pass   : False
autonomy_evidence   : False
attribution_missing : ['ground_truth_pass']
process exit code   : 1
```

**Effect.** `autonomy_evidence: true` remains *structurally unreachable* through
the production harness — F2's original defect, resurfaced through a new
mechanism. The one authorized live run would report failure regardless of what
the model does, and the failure text (`autonomy_evidence withheld; missing:
ground_truth_pass`) misattributes an instrument bug to the model. That is a
false-**attribution** bug; it is fail-closed and cannot manufacture a false
success.

**Why 830 tests miss it.** The scripted control takes the `else` branch
(`scripted mode does not claim autonomy`), which passes trivially.
`tests/test_simulated_live_attribution.py` exercises `attribution_complete()`
against a hand-built `_live_shaped_result()` dict that sets
`ground_truth_pass: True` itself (`:167`), and never calls `grade()` on a live
result. The join between the two functions is the only untested part of the
live path, and the defect is exactly there.

**Blocks the live run: YES.**

**Minimum fix.** Break the cycle properly — grade the causal chain, set
`ground_truth_pass`, compute `attribution_complete`, then evaluate the
autonomy check; e.g. remove the `autonomy evidence is complete` check from
`grade()` and assert it in `main()` after `autonomy_evidence` exists, or pass
the computed value into `grade()` explicitly. Then add a regression that runs
`main()`'s post-run sequence end-to-end on a live-shaped result and asserts
`grade.passed and autonomy_evidence is True`.

### P1-LIVE-02 — the grader demands the exact calibrated number (live-blocking)

**Files:** `benchmarks/autonomy/grade.py:315-320`, `benchmarks/autonomy/case_05_droute_iters.yaml`

```python
want = {known["section"]: {known["field"]: known["value"]}}
g.check("accepted delta matches the calibrated remedy", proposed == want, ...)
```

This is exact dict equality against `{"routing": {"droute_iters": 32}}`. The
case's own `success_criteria` says something weaker and more sensible:

> the remedy is a routing field inside `authorized_action_space(routing)`
> · the retry is same-stage · routing converges to zero violations on the retry

Per the case's own calibration, `droute_iters: 3` already converges to 0. So a
live model proposing 3, 16 or 64 — or proposing 32 *plus* a second authorized
field — would physically remediate the failure, converge to zero violations,
pass all 11 gates, and still be graded FAIL for not matching the number the
authors picked. The grader is stricter than the criteria it claims to enforce.

Partially mitigated: the prompt shows `default: 32`, so "restore the default"
is the likely answer. It is not the guaranteed one.

**Blocks the live run: YES** — not for safety, but because the freeze policy
correctly forbids relaxing this after seeing the response. If the model answers
64, the run is a FAIL that cannot be repaired without voiding.

**Minimum fix.** Grade the remedy against the case's stated criteria — same
section, authorized field, and the *observed* after-metric reaching the
calibrated target — or, if exact equality is genuinely intended, say so in
`success_criteria` and accept the narrower claim ("proposed the calibrated
value") rather than "remediated".

### P2-GRADE-03 — the grader trusts `gate_evidence.json` (not model-reachable)

**File:** `benchmarks/autonomy/grade.py:376-396`

Three tampers on a copied run are accepted as PASS:

```
wrong_report_hash    (report_sha256 → 000…)   PASS  ← should fail
bogus_cert_id        (certification_id → 999…) PASS  ← only length is checked
wrong_tool_identity  (tool_identity → "fake")  PASS  ← should fail
```

`certification_id` is checked for `len == 64`, never recomputed;
`report_sha256` and `tool_identity` are never re-verified against the artifacts
they name. The runner computes them correctly and re-hashes at signoff, so this
is missing redundancy in the grader, and the project already discloses it.

**Blocks the live run: NO** — the model has no filesystem access and cannot
write this file; only a human editing artifacts could exploit it.

**Minimum fix.** Recompute `certification_id` from the records and compare;
re-hash the file named by `report_key` and compare to `report_sha256`.

### P2-SCHEMA-04 — one agent-writable field with no implementation (out of scope for Case 05)

**File:** `src/rtl2gdsagi/ir.py:234`

`pdn.ir_drop_budget_mv` is `agent_writable=True` but appears nowhere else in
`src/` — it is neither rendered nor consumed by any check. It is the "exposed
field with no implementation effect" class, and being an IR-drop *budget* it is
threshold-shaped. It is reachable only from a `pdn` failure class; for a routing
failure `authorized_action_space` returns `{floorplan, placement, routing}`
only, so **it cannot appear in the Case-05 prompt or be proposed in this run**.

**Blocks the live run: NO.** Worth closing before any PDN case.

---

## 11. What I could not make happen

No reachable path was found for a live model to: change what PASS means;
modify verification intent; reach the PDK, decks, RTL or testbench; write
arbitrary Tcl, shell, path or environment content (there are no `str` fields in
the surface at all); combine evidence across generations; reuse stale outputs
(superseded outputs are moved aside per attempt); claim a delta different from
the one applied; or claim autonomy without a recorded non-scripted call. The
freeze makes re-grading a response under a modified instrument impossible
without a fresh execution.

The model's authority is 12 bounded numeric/boolean implementation knobs, none
of which is read by any file under `checks/`.

---

## 12. Consequence for sequencing

Fixing P0-LIVE-01 and P1-LIVE-02 changes `grade.py` and `run_case.py`, which
changes `grader_sha256` and `harness_sha256`. Under the project's own — correct
— void policy that makes `scripted_trial_02` VOID. So the path to the live run
is:

1. fix P0-LIVE-01 (and P1-LIVE-02, and ideally P2-GRADE-03 while the freeze is
   already breaking);
2. add the live-path regression that would have caught P0-LIVE-01;
3. re-execute a **fresh** scripted control end to end on the new instrument;
4. re-freeze;
5. then the single live run.

This is why the verdict is C rather than B: the fix is small, but it invalidates
the current control run, so "fix and go" is not available.

---

## Final answers

```
Verdict:  C — NO-GO, IMPORTANT BLOCKER REMAINS

Tests:
  collected: 830
  passed:    830
  failed:    0

F1:  CLOSED   (16/16 bypass attempts fail; no substring proof remains)
F2:  OPEN     (plumbing closed — 16 of 17 fields populate from real runtime
               records — but `autonomy_evidence: true` is still unreachable
               end-to-end through the harness, now via P0-LIVE-01)
N1:  CLOSED   (one permission source; 5/5 frozen fields absent from the prompt)
N2:  CLOSED   (freeze checked first, 13/13 mutations VOID, never rewritten)

Case-05 calibration:            VALID   (2 → 0 confirmed in raw OpenROAD logs)
Prompt/action surface:          VALID   (exactly 12 bounded fields, 0 str fields)
Ground-truth leakage:           NO
Benchmark freeze:               VALID   (6/6 recompute, drift zero)
Fresh scripted control:         PASS    (32/32, exit 0)
GateEvidence/lineage:           VALID   (11/11, certification_id recomputes)
Synthetic-live instrumentation: VALID for the agent path (production
                                ClaudeAgent + fake transport, no network, no
                                credential, complete CallAudit,
                                synthetic_transport=true, network_call=false);
                                the result-building path is NOT exercised —
                                it is a hand-built dict, which is precisely
                                where P0-LIVE-01 hides

New P0 count: 1
IDs:          P0-LIVE-01

New live-blocking P1 count: 1
IDs:                        P1-LIVE-02

Ready for exactly ONE controlled live-model run:  NO
```

Not ready. Fix P0-LIVE-01 and P1-LIVE-02, add the live-path regression, re-run
a fresh scripted control on the new instrument, re-freeze — then the single
Case-05 live run is justified under the stated envelope.
