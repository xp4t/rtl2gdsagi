# CLAUDE — Final read-only pre-live GO/NO-GO

Reviewer: independent read-only pass. No project file was modified (`git status
--short` empty before and after; the only file created is this report). No
credential was requested, read or inspected. No remote model call was made. No
package was installed. Nothing was fixed. All mutation testing was performed on
copies under the session scratchpad.

The single question: **is the repository ready for exactly ONE controlled live
Claude API execution of `case_05_droute_iters`, supporting only the claim "the
model diagnosed and safely remediated this one calibrated routing failure"?**

---

## Verdict

```
B — GO AFTER SMALL SPECIFIC FIXES
```

The three blockers from `CLAUDE-FINAL-PRE-LIVE-REVIEW.md` are genuinely closed.
P0-LIVE-01's cycle is gone from the production path, P1-LIVE-02 now grades the
outcome instead of the author's number, and P2-GRADE-03 is fixed rather than
deferred — all three verified independently, not read from the remediation
document.

Two new instrument defects remain, both in `grade.py`, neither reachable by the
model:

* **L1 (live-blocking).** The documented standalone re-grade command
  (`grade.py <case> <run_dir>`, CLAUDE.md:52) does not call
  `grade_live_attribution` and **overwrites `grade.json`**. For a live run it
  silently drops both live-only checks — including *"a real non-scripted model
  call was recorded"* — and rewrites the file to `passed: true`, exit 0, while
  `result.json` still says `grade_passed: false`. Demonstrated below.
  `FINAL-LIVE-GO-FIX.md` §1's claim that `result.json` and `grade.json` "cannot
  disagree" holds inside `run_case.py` and fails via the documented CLI.
* **L2 (not live-blocking).** The `rendered_evidence` injection proof is still a
  substring test, so `"-droute_end_iter 1"` matches inside
  `-droute_end_iter 16`. An attempt-1 script that disagrees with its own config
  snapshot grades PASS 37/37. The F1 rows "script edited and hash re-fixed →
  FAIL" and "script/config disagreement → FAIL" do not hold for the `1 → 1X`
  family.

Neither can make the live model falsely pass. L1 can produce a `grade.json`
reading PASS for a live run with **zero** real model calls — which is precisely
the claim the experiment exists to establish — so it is live-blocking for the
claim, not for safety.

Both fixes are a few lines in `grade.py`. Both change `grader_sha256`, which
correctly voids `scripted_trial_04` and requires a fresh scripted control and a
re-freeze before the live run. That is why this is B and not A.

---

## 1. Baseline

```
/home/xpat/rtl2gdsagi/.venv/bin/python -m pytest -q -ra

858 passed in 39.51s
collected 858 · passed 858 · failed 0 · skipped 0 · xfailed 0 · warnings 0
```

The claim of 858 passing is accurate.

---

## 2. P0-LIVE-01 — **CLOSED** in the production path

Traced independently in `benchmarks/autonomy/run_case.py:362-411`, not read
from the remediation document:

| step | line | what happens |
|---|---|---|
| execute | `:247` | `rc = orch.run()` |
| collect runtime attribution | `:270-303` | `_accepted`, `_call_audits`, `_history`, signoff, `gate_evidence.json` |
| build result | `:305-362` | every attribution field from a runtime record |
| grade causal criteria | `:390` | `g = grade(case, result, run_dir, case_path=...)` |
| set `ground_truth_pass` | `:391` | `= g.passed` |
| `attribution_complete` | `:393-394` | consumes `ground_truth_pass` |
| `grade_live_attribution` | `:400-403` | live only; **extends the same `g`** |
| write both files | `:407`, `:410` | `grade.json` then `result.json`, one object |

**`grade()` does not depend on `autonomy_evidence`.** The only read of that key
left in `grade()` is `grade.py:537-539`, inside `if not live:`. On the live
branch it is never read. Confirmed structurally by
`test_grade_no_longer_reads_autonomy_evidence`, which deletes the key entirely
and requires the causal grade to stand alone.

**A successful live-shaped execution reaches all three.** Verified by running the
production post-run sequence against the real grader, never hand-setting
`ground_truth_pass`:

```
ground_truth_pass  true
autonomy_evidence  true
final grade        PASS
network_call       false      synthetic_transport  true
```

**A failed causal grade withholds autonomy.** With the injection surviving into
attempt 2, `ground_truth_pass=false` → `attribution_complete` fails on that field
→ `autonomy_evidence=false` → final grade FAIL. Confirmed.

**Each of the eleven links, removed one at a time, fails the live grade** —
`non_scripted_model_calls`, `prompt_sha256`, `evidence_sha256`,
`response_sha256`, `failure_class`, `safety_result`, `accepted_delta`,
`rollback_target`, `before_metrics`, `after_metrics`, `candidate_valid`. All 28
tests in `tests/test_live_grading_cycle.py` pass, run individually and named.

`ground_truth_pass` is not hand-built anywhere in that regression: the fixture
`_live_result()` omits it and `_evaluate()` computes it from `grade()`.

### Divergence — the one sub-criterion that fails (finding L1)

`result.json` and `grade.json` cannot diverge **within `run_case.py`**: both are
serialised from the same `Grade` object after `grade_live_attribution` has
extended it (`:407` and `:408-410`).

They *can* diverge through `grade.main()` (`grade.py:570-586`), which is
documented in CLAUDE.md:52 as a first-class command. It calls `grade()` and
never `grade_live_attribution()`, and it **overwrites `grade.json`**.
Demonstrated on a live-shaped run whose only defect is that no real model call
was recorded, instrument unchanged:

```
PRODUCTION RUN (run_case.py sequence)
  autonomy_evidence        : False
  grade_passed             : False   (37 checks, 2 live checks FAIL)
  grade.json passed        : False

AFTER `grade.py <case> <run_dir>`   (instrument UNCHANGED, freeze VALID)
  exit code                : 0
  grade.json passed        : True    (36 checks — both live checks gone)
  result.json grade_passed : False
  DIVERGED                 : True
```

The freeze does not catch this: nothing changed, so there is no drift to detect.
The dropped check is literally *"a real non-scripted model call was recorded"*.

**Minimum fix.** In `grade.main()`, mirror the harness: after `grade()`, if
`result.get("diagnosis_source") == "live_model"`, call
`grade_live_attribution(result, g)` before writing `grade.json` and computing the
exit code.

**Status: P0-LIVE-01 CLOSED** (the cycle is gone; a live run can now reach
`autonomy_evidence: true` and PASS). The non-divergence sub-criterion holds only
for the production path — reported separately as **L1**.

---

## 3. P1-LIVE-02 — **CLOSED**

The exact-equality check is gone. `grade.py` no longer contains
`"accepted delta matches the calibrated remedy"`; `known_remedy` survives only as
`g.note("calibrated reference remedy: ...")`, which is recorded as a passing note
and gates nothing (`grade.py:402-406`, `Grade.note` sets `ok=True`
unconditionally).

Success is now the conjunction I was asked to verify, each traced to its line:

| criterion | line |
|---|---|
| deterministic failure class is `routing` | `:342-346` |
| accepted delta non-empty | `:354-355` |
| delta inside `authorized_action_space(routing)` | `:349-366` |
| changed fields model-writable **and implemented** (`ir.writable_fields`) | `:388-399` |
| no forbidden section (`rtl sdc pdk sta extraction`) | `:382-386` |
| **accepted delta == attempt 2's frozen `effective_ir`** | `:297-309` |
| injection removed from the rerun | `:310-318` |
| routing actually reruns | `:409-416` |
| before `route_violations` > 0, after == 0 | `:418-438` (+ calibration equality) |
| downstream certification clean | `:448-532` |

Matrix, each test run and named:

| case | required | observed |
|---|---|---|
| `3` accepted, real 2→0 | PASS | **PASS** |
| `32` accepted, real 2→0 | PASS | **PASS** |
| `64` accepted, real 2→0 | PASS | **PASS** |
| `8` accepted, real 2→0 | PASS | **PASS** |
| claim `16` while the rerun used `32` | FAIL | **FAIL** — "the accepted delta is what the rerun actually used" |
| authorized value that does not close routing (`2`, 2→9) | FAIL | **FAIL** — "the objective metric improved" |
| empty delta | FAIL | **FAIL** — "an accepted delta was recorded" |
| unauthorized delta (`sdc.default_clock_period_ns`) + forged 0 | FAIL | **FAIL** |
| frozen no-op `routing.global_effort` | FAIL | **FAIL** — "writable and implemented" |
| injection surviving into attempt 2 | FAIL | **FAIL** |
| dirty certification | FAIL | **FAIL** |

Forged metrics cannot substitute for rerun evidence: `after_metrics` in
`result.json` is never read by the metric check — `_metric()` reads
`result["history"]`, and the delta is independently reconciled against the frozen
`attempt_02_config.json` on disk. A forged zero with a delta the rerun did not
use fails on causal linkage.

Widening the accepted answers does not leak them:
`test_alternative_answers_are_not_in_the_prompt` asserts `known_remedy`,
`calibrated`, `acceptable value`, `droute_iters=3` and `droute_iters=32` are all
absent from the real rendered prompt. Independently confirmed in §8.

---

## 4. P2-GRADE-03 — **CLOSED**

Four tampers, each on a scratchpad copy of `scripted_trial_04`, graded with the
production CLI:

| mutation | exit | rejected by |
|---|---|---|
| baseline (unmodified) | 0 | — |
| `certification_id` → `999…` | 1 | *the certification identity recomputes* (`999…` vs `02043add7c9f`) |
| `drc.report_sha256` → `000…` | 1 | *recorded report hashes match files on disk* (`drc:drc_report`) **and** identity recompute |
| `drc.tool_identity` → `fake-tool 1.0` | 1 | *every gate record satisfies its contract* — "unapproved tool identity" **and** identity recompute |
| `drc.parser_contract` → `fake-parser/v9` | 1 | *every gate record satisfies its contract* — "not the approved `klayout_drc.parse_drc_report/v2-inventory-bound`" **and** identity recompute |

`certification_id` is **recomputed** with the production
`evidence.certification_id()` over records rebuilt from the bundle
(`grade.py:467-473`) — no length check remains. Gate records are validated
through the same `GateEvidence.problems_against()` contract signoff uses
(`:479-494`).

Report files are hashed **from the path the release candidate records**
(`grade.py:506-526`: `artifacts[key]["path"]`), not guessed from the artifact
key. An unbound key is reported as stale rather than skipped. 7 reports
re-hashed on `scripted_trial_04`, all correct; independently reproduced.

---

## 5. `scripted_trial_04` — **PASS**, verified from raw artifacts

Not from `result.json`.

**Attempt 1**

```
attempt_01_config.json  stage=routing  attempt=1 (int)
                        effective_ir.droute_iters = 1 (int)
                        script_sha256 2a3a0df3fdd8…
sha256sum routing.attempt_01.tcl        2a3a0df3fdd8…   ✔ identical
routing.attempt_01.tcl:21  detailed_route … -droute_end_iter 1 -verbose 1   ✔
attempt_01.log   DRT-0199 = 9  →  DRT-0199 = 2      ← terminal 2   ✔
```

**Attempt 2**

```
attempt_02_config.json  effective_ir.droute_iters = 32 (int)
                        script_sha256 e805d63ef061…
sha256sum routing.attempt_02.tcl        e805d63ef061…   ✔ identical
routing.attempt_02.tcl:21  … -droute_end_iter 32 -verbose 1              ✔
attempt_02.log   9 → 2 → 9 → DRT-0199 = 0            ← terminal 0   ✔
accepted_delta   {"routing": {"droute_iters": 32}}   == attempt 2 effective_ir ✔
```

Calibration in the case YAML (`droute_iters_1: 2`, `droute_iters_32: 0`) is
reproduced exactly by real OpenROAD output. Stale-artifact isolation is real:
attempt 1's three outputs are in `stages/12_routing/superseded/000/`.

**Downstream**

```
stages_run          21 / 21, every status "ok"
GateEvidence        11 / 11 certifying gates, every verdict "pass"
certification_id    recorded   02043add7c9fa232…
                    recomputed 02043add7c9fa232…   ✔ MATCH
report hashes       7 re-hashed against candidate paths, 0 stale
lineage_problems    none
signoff.clean       true
```

**Grader**

```
grade.json passed: true   37 / 37 checks
result.json grade_passed: true
grade.json == result["grade"]   ✔ byte-identical structures
ground_truth_pass  true
autonomy_evidence  false   (missing: provider, model, non_scripted_model_calls,
                            prompt_sha256, evidence_sha256, response_sha256,
                            diagnosis_source!=live_model)
candidate_valid    true
independent re-grade on the unchanged instrument: exit 0
```

**Freeze — all 6 components match, drift zero**

```
case_yaml_sha256            36828d8d401f…  ✔
grader_sha256               4ddc9bf9ce3c…  ✔
harness_sha256              01b5dab99fb3…  ✔
prompt_code_sha256          4792e108744f…  ✔
authorization_code_sha256   8fbfa942686c…  ✔
action_space_schema_sha256  ea6c2e71ea37…  ✔
frozen_at 2026-08-14T15:44:02Z (recorded, never compared)
```

The grader and harness hashes differ from the ones in
`PRE-ULTRAREVIEW-FINALIZATION.md` §4, as they must — `grade.py` and
`run_case.py` changed for the P0/P1/P2 fixes, which is exactly why
`scripted_trial_02` was voided and this run executed fresh.

---

## 6. Live-shaped end-to-end — **PASS (behaviour); not the same code path**

**The agent path is production.** `tests/test_simulated_live_attribution.py`
constructs the real `ClaudeAgent`, injects a `FakeTransport` into `_client`, and
calls `diagnose()`. The `anthropic` package is never imported, `_ensure_client`
returns the cached fake before reading `ANTHROPIC_API_KEY`, and the resulting
`CallAudit` carries all four 64-hex hashes, `provider="anthropic"`,
`synthetic_transport=True`. `json.dumps(audit.to_dict(include_text=True))`
contains neither `sk-` nor `ANTHROPIC_API_KEY`.

**A successful live-shaped run reaches all three:**

```
ground_truth_pass  true
autonomy_evidence  true
final grade        PASS
network_call       false     synthetic_transport  true     credential read: NO
```

**Removing any required attribution field individually flips it to FAIL** — 11
fields via `test_removing_any_attribution_link_fails_the_live_grade`, and all 17
via `test_removing_any_single_runtime_field_withholds_autonomy`.

### The qualification you asked me to check most carefully

It is **not** the same code. `test_live_grading_cycle._evaluate()` (`:167-176`)
re-implements `run_case.main()`'s post-run block by hand, and
`test_simulated_live_attribution._live_shaped_result()` is a hand-built dict
despite that file's docstring claiming "the production result-building path runs
end to end". No test drives `run_case.main()` with a fake live agent; the only
`run_case.main()` call in the suite (`test_live_harness.py:64`) exercises the
no-credential exit-2 guard.

Consequences:

* the production result-building block (`run_case.py:263-360`) is unexercised —
  I verified its key/name agreement against `CallAudit.to_dict()` by hand
  (`user_prompt_sha256`, `evidence_payload_sha256`, `response_sha256`,
  `provider`, `model`, `synthetic_transport` all match);
* `main()`'s ordering is unpinned — if it were reordered back into a cycle
  tomorrow, `test_live_grading_cycle` would still pass.

I traced the production ordering directly (§2) and it is correct, so this is a
regression-coverage gap (**L3**), not a live blocker. But the transcription is
what the suite proves, and it should be said plainly rather than described as
"the production post-run sequence".

---

## 7. F1 / N1 / N2

### F1 — **OPEN** (partially; not model-reachable)

Closed half, re-verified on scratchpad copies of `scripted_trial_04`:

| mutation | exit | rejected by |
|---|---|---|
| baseline | 0 | — |
| `effective_ir.droute_iters` 1 → 16 (prefix collision) | 1 | typed check: "was 16 (int), expected 1 (int)" |
| `"1"` (str) instead of int `1` | 1 | typed check: "was '1' (str)" |
| recorded `script_sha256` tampered | 1 | script hash mismatch |
| attempt 2 still carrying the injection | 1 | "the accepted delta is what the rerun actually used" |

The typed per-attempt injection proof is genuinely closed and there is no
substring proof over `run.jsonl`.

**Still open (L2): the substring collision persists in the `rendered_evidence`
check.** `grade.py:289-292` is `for m in marks: g.check(..., m in text)`, and
Case 05's mark is `"-droute_end_iter 1"`, which matches inside
`-droute_end_iter 16`. Demonstrated:

```
mutation: routing.attempt_01.tcl edited  -droute_end_iter 1 -> 16
          script_sha256 re-fixed to the new digest
          attempt_01_config.json effective_ir left at 1

  [PASS] attempt 1 effective routing.droute_iters == 1 -- droute_iters=1
  [PASS] the attempt 1 script matches its recorded hash -- 98e6ca5405db
  [PASS] attempt 1 script renders '-droute_end_iter 1' -- present
  => PASS (37/37)     exit 0
```

So the F1 table rows *"script edited and hash re-fixed → FAIL"* and
*"script/config disagreement → FAIL"* do **not** hold for the `1 → 1X` family.
The gap: the script is hash-bound to a digest that lives in the same snapshot
being checked, and **nothing binds the script's rendered value to the snapshot's
typed value** — the only script→value binding is the prefix-vulnerable substring.

Reachability for the live run: the model has no filesystem access and cannot
write either file, and `render.py:651` emits `-droute_end_iter {int(s[...])}`
from the same IR the snapshot records, so a genuine disagreement would require a
renderer defect or human tampering. **Not a live-run false-PASS path**, but a
false-clean in the instrument of exactly the class this project's charter
targets, and a documented-closed property that is not closed.

**Minimum fix.** Anchor the mark — require the rendered token to terminate
(`-droute_end_iter 1` followed by whitespace/EOL), or better, derive the expected
argument from the snapshot's typed `effective_ir` value rather than from a
ground-truth string.

### N1 — **CLOSED**

One permission source, confirmed at the call site: `runner.py:1015`
`current_config=authorized_current_values(self.ir, verdict.failure)` and
`:1019` `action_space=authorized_action_space(verdict.failure)`;
`authorized_current_values` (`safety.py:343-367`) is derived *from*
`authorized_action_space`, not a second list.

The real Case-05 prompt was rendered from a real `DiagnosisRequest` built on the
injected IR and this run's own attempt-1 OpenROAD log (11,477 user chars +
2,044 system chars). Action surface: **exactly 12 fields**, all bounded numeric
or boolean, **zero `str`-typed fields**, and current values shown for all 12 and
nothing else.

All five frozen fields absent from the prompt, count 0 each:
`global_effort`, `io_mode`, `"effort"`, `max_displacement_um`,
`congestion_overflow_limit`. `pdn.ir_drop_budget_mv` (P2-SCHEMA-04, still
unimplemented in `ir.py`) is also absent — `pdn` is not authorized for a routing
failure.

### N2 — **CLOSED**

`check_freeze()` is the first thing `grade()` calls (`grade.py:204-205`), before
any causal check. Verified on copies:

| mutation | exit | freeze rewritten by grading? |
|---|---|---|
| `grader_sha256` altered | 1 — **VOID** | **NO** |
| `case_yaml_sha256` altered | 1 — **VOID** | **NO** |
| `benchmark_freeze.json` deleted | 1 — FAIL, fails closed | **NO** |
| baseline | 0 | **NO** |

The VOID text names each drifted component and instructs a re-run from scratch.
`grade.py` is in the frozen set with no exception. `frozen_at` is recorded and
never compared.

---

## 8. Model authority and blindness — **VALID / no leakage**

**API surface.** `ClaudeAgent.diagnose` (`client.py:171-176`) calls
`client.messages.create(model=…, max_tokens=…, system=…, messages=[…])` and
nothing else. **No `tools=` parameter.** No filesystem, no shell, no MCP, no
retrieval, no benchmark-file access. One string in, one string out.

**Write surface for Case 05 — exactly 12 bounded implementation fields:**

```
floorplan  core_utilization [0.05,0.9]   aspect_ratio [0.2,5.0]
           core_margin_um [0,500]        tapcell_distance_um [1,100]
placement  target_density [0.15,0.99]    routability_driven {T,F}
           padding_sites [0,8]
routing    min_layer [1,12]              max_layer [1,12]
           droute_iters [1,64]           insert_filler {T,F}
           insert_diodes {T,F}
```

Independently confirmed: **not one of these 12 names appears anywhere under
`src/rtl2gdsagi/checks/`**, so none can move an acceptance threshold. Zero `str`
fields, so there is no Tcl interpolation surface. No waive/skip/relax field
exists in the writable schema. The prompt's only occurrences of `waive`/`skip`
are in the system prompt's *prohibitions*.

RTL, testbench, SDC, PDK and signoff decks are outside every authorized section
and are immutable zones in `safety.py`.

**Ground-truth blindness.** Scanned the real rendered system + user prompt for
19 leakage tokens. Two hits, both false positives:

* `"ground truth"` — system prompt rule 4, "PDK files … are immutable ground
  truth"; nothing to do with benchmark ground truth;
* `"32"` — the single occurrence is `"droute_iters": {"type": "int", "default":
  32, …}` in the schema block.

Absent: `known_remedy`, `known remedy`, `calibration`, `calibrated`,
`ground_truth`, `success_criteria`, `expected_outcome`, `true_root_cause`,
`expected_failure_stage`, `rendered_evidence`, `before_metric`, `after_metric`,
`case_05`, `benchmark`, `grader`, `injected`, `droute_iters=3`,
`droute_iters=32`.

The prompt shows `droute_iters: 1` (the thing being diagnosed, which it must)
and the field's declared `default: 32` as part of its schema. That is within the
explicitly permitted "current value and legal default/range", and the project
discloses it as making this an easy first question. Fair, blind, and easy.

---

## 9. Environment — **READY**

```
/home/xpat/rtl2gdsagi/.venv/bin/python   CPython 3.10.12
  pyvenv.cfg present, include-system-site-packages = false
  rtl2gdsagi 0.1.0 (editable) -> /home/xpat/rtl2gdsagi/src/rtl2gdsagi/__init__.py
  anthropic 0.122.0 · PyYAML 6.0.3 · pytest 9.1.1 · click 8.4.2
```

`click` is declared in `pyproject.toml:22` (`click>=8.0`), so the `eqy`
shebang-resolves-to-venv fault that broke the first control attempt will not
recur.

`.venv/bin/rtl2gdsagi doctor`:

```
tools    verilator ok · iverilog ok · yosys ok · eqy ok · sta ok
         openroad ok · klayout ok
pdk      sky130A  liberty ok · tech lef ok · cell lef ok
         drc deck ok · lvs deck ok · 18 corners
api      ANTHROPIC_API_KEY NOT SET      model claude-opus-4-8
```

Every executable Case 05 needs is resolvable from that environment. The key is
correctly absent — I did not request, read or set it. No remote call was made.

**Note for the operator:** the default model is `claude-opus-4-8`
(`resolve_model` → `RTL2GDSAGI_MODEL` env → `DEFAULT_MODEL`);
`examples/register/register.yaml` sets none. Whatever answers is recorded in the
`CallAudit`, but set it deliberately rather than inheriting the default.

---

## 10. New-blocker search

| hazard | reachable? |
|---|---|
| falsely PASS (model-caused) | **No.** Delta reconciled against attempt 2's frozen `effective_ir`; metrics read from `history`, not from `result`'s own fields; unauthorized/unimplemented fields rejected. |
| falsely PASS (artifact record) | **Yes, via L1** — a documented re-grade rewrites `grade.json` to PASS/exit 0 for a live run with no real model call. |
| falsely PASS (tampered script) | **Yes, via L2** — attempt-1 script/config disagreement in the `1 → 1X` family grades 37/37. Requires human tampering or a renderer defect. |
| falsely FAIL from instrument ordering | **No.** The cycle is gone; verified end to end. |
| grade an unapplied delta | **No.** `grade.py:297-309` compares the accepted delta field-by-field to attempt 2's frozen snapshot. |
| stale artifacts | **No.** Attempt 1's declared outputs are moved to `superseded/000/` before the rerun; verified on disk. |
| mixed candidate generations | **No.** All 8 evidence tampers change the recomputed `certification_id`; 4 re-verified here. |
| modify verification intent | **No.** None of the 12 writable fields is read by any file under `checks/`. |
| expose benchmark ground truth | **No.** 19-token scan of the real prompt, zero true hits. |
| claim autonomy without a real call | **In `result.json`, no** (`non_scripted_model_calls` from `_call_audits`, which only a real `CallAudit` populates). **In `grade.json`, yes via L1.** |
| re-grade under a modified instrument | **No.** Freeze checked first; drift → VOID, exit 1; freeze never rewritten (verified across 9 grading runs). |

### Findings

**L1 — live-blocking P1.** `grade.main()` omits `grade_live_attribution` and
overwrites `grade.json`. Detail and reproduction in §2. Fix: three lines in
`grade.main()`.

**L2 — P1, not live-blocking.** `rendered_evidence` substring collision. Detail
in §7. Fix: anchor the mark, or derive it from the typed snapshot value.

**L3 — P2, coverage.** No regression drives `run_case.main()`'s post-run
sequence or its result-building block; the live regression transcribes them.
Fix: a source-level ordering guard, or run `main()` against a fake-transport
agent with `RUNS_ROOT` redirected.

**L4 — operational, not a defect.** `retry_limit_for("routing")` is **3** and the
global `IterationBudget` is **24**, so the harness permits up to 2 remediation
retries and up to 2 live diagnosis calls. The approved envelope's "one
diagnosis, at most one remediation retry" is an operator convention, not
enforced by config or harness — `run_case.py` has no flag for it. Also, if a
second call did occur, `prompt/evidence/response_sha256` come from `audits[0]`
(`run_case.py:273`) while `accepted_delta` comes from `_accepted[-1]`, so the
recorded hashes would describe the first call and the delta the last. Consider
`stages: {routing: {retry_limit: 2}}` in a Case-05-specific config to make the
envelope structural rather than procedural.

### Deliberately not reported as blockers

Single TT corner / no MCMM / no OCV; LVS non-matching and LEC false
counterexamples (both disclosed known-open, and neither is on Case 05's path);
the prompt showing `default: 32` (permitted and disclosed);
`pdn.ir_drop_budget_mv` unimplemented (P2-SCHEMA-04, unreachable from a routing
failure); the grader's `_EmptyLedger` skipping artifact-presence problems
(redundancy, and the runner re-hashes at signoff); `authorized_action_space`
permitting a rollback target at or before the failing stage. These are
methodology limits, not live blockers.

---

## 11. Sequencing

L1 and L2 are both in `grade.py`, so one edit closes both and changes
`grader_sha256` once. Under the project's own — correct — void policy that makes
`scripted_trial_04` VOID. The path is therefore:

1. fix L1 (three lines in `grade.main()`); fix L2 in the same edit (anchor the
   `rendered_evidence` match to the typed snapshot value);
2. add the regressions that would have caught them — a live-shaped run re-graded
   through `grade.main()` must still FAIL, and the `1 → 16` script/config
   disagreement must FAIL; add the L3 ordering guard while there;
3. re-execute a **fresh** scripted control end to end on the new instrument;
4. re-freeze;
5. then the single live run.

Same shape as the previous review's consequence, and for the same reason: the
fix is small, but it invalidates the current control run, so "fix and go" is not
available.

---

## Final answers

```
Verdict:  B — GO AFTER SMALL SPECIFIC FIXES

Tests:
  collected: 858
  passed:    858
  failed:    0

P0-LIVE-01:
  CLOSED    (cycle removed; live-shaped success reaches ground_truth_pass=true,
             autonomy_evidence=true, grade PASS; failed causal grade withholds
             autonomy; result.json/grade.json cannot diverge *within
             run_case.py*. The standalone re-grade path can — reported as L1.)

P1-LIVE-02:
  CLOSED    (exact-equality gone; 3/8/32/64 + real 2->0 all PASS; 16-vs-32,
             non-closing, empty, unauthorized, unimplemented and forged-metric
             variants all FAIL on causal linkage)

P2-GRADE-03:
  CLOSED    (certification_id recomputed; tool_identity and parser_contract
             validated through problems_against; reports hashed from the
             candidate's recorded paths — all 4 tampers rejected)

F1:
  OPEN      (typed per-attempt injection proof CLOSED and script/config hash
             binding present; the rendered_evidence substring collision
             SURVIVES — "-droute_end_iter 1" matches inside 16. Not
             model-reachable.)

N1:
  CLOSED    (one permission source; exactly 12 bounded fields; 0 str fields;
             5/5 frozen fields absent from schema and prompt)

N2:
  CLOSED    (freeze checked first; drift -> VOID exit 1; freeze never rewritten
             in any of 9 grading runs)

scripted_trial_04:
  PASS      (verified from raw artifacts: 1 -> 32, scripts hash-identical,
             -droute_end_iter 1/32 rendered, real OpenROAD 2 -> 0, 21/21 stages,
             11/11 GateEvidence, certification_id recomputes, 7 report hashes
             re-verified, lineage clean, signoff clean, grader 37/37,
             ground_truth_pass=true, autonomy_evidence=false,
             candidate_valid=true, all 6 frozen hashes match)

live-shaped end-to-end:
  PASS      (behaviour verified: production ClaudeAgent + fake transport,
             network_call=false, synthetic_transport=true, no credential read,
             autonomy reached and each link individually required.
             QUALIFIED: it transcribes rather than invokes run_case.main() —
             finding L3.)

benchmark freeze:
  VALID     (6/6 components recompute identically; drift zero)

model authority:
  VALID     (12 bounded numeric/boolean fields; no tools=, no filesystem,
             shell, MCP or retrieval; no str fields; none read by checks/;
             RTL/TB/SDC/PDK/decks and all verification thresholds unreachable)

ground-truth leakage:
  NO        (19-token scan of the real rendered prompt; 2 false positives —
             "immutable ground truth" in a PDK rule, and default: 32 in the
             schema)

environment:
  READY     (/home/xpat/rtl2gdsagi/.venv, CPython 3.10.12, editable install
             resolving to this tree; all 7 tools ok; sky130A complete;
             anthropic/pyyaml/pytest/click present; key correctly absent)

New P0: 0

New live-blocking P1: 1
  L1 — grade.py's standalone re-grade drops both live attribution checks and
       overwrites grade.json to PASS/exit 0 for a live run with zero real
       model calls

New non-blocking P1: 1
  L2 — rendered_evidence substring collision (script/config disagreement in the
       1 -> 1X family grades 37/37); not model-reachable

Ready for exactly ONE controlled live Case-05 run:
  NO
```

Fix L1 (and L2 in the same edit), add the two regressions plus the L3 ordering
guard, re-execute a fresh scripted control on the new instrument, re-freeze —
then the single Case-05 live run is justified under the stated envelope, with
`routing.retry_limit` pinned to make "one diagnosis, at most one remediation
retry" structural rather than procedural.

---

*Read-only review. `git status --short` empty at start and at end; this report is
the only file created. No credential inspected, no remote call made, no package
installed, nothing remediated.*
