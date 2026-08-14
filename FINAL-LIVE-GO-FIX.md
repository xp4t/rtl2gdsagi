# Final pre-live fix — P0-LIVE-01, P1-LIVE-02, P2-GRADE-03

Closing the last live-path blockers from `CLAUDE-FINAL-PRE-LIVE-REVIEW.md`.

No API key was requested and no remote call was made. Case-05 calibration, the
injected value and the ground truth are unchanged.

---

## 1. P0-LIVE-01 — the grading/attribution cycle

### The cycle

```
grade()            required  result["autonomy_evidence"] is True
autonomy_evidence  required  ground_truth_pass
ground_truth_pass  came from grade()
```

So `autonomy_evidence: true` was unreachable for any genuine live run. The
scripted control never exposed it, because the scripted branch asserts the
*opposite* (`is not True`) and is satisfiable without attribution. Every one of
the 830 tests either graded a scripted run or exercised
`attribution_complete()` in isolation — which is exactly why none of them
caught it.

### The fix: ordering, not loosening

`grade()` no longer reads `autonomy_evidence` at all. The live-only checks moved
to `grade_live_attribution(result, g)`, called after attribution is computed and
**extending the same `Grade` object**, so there is one verdict and
`result.json`/`grade.json` cannot disagree.

```
execute
  -> collect runtime attribution
  -> grade causal criteria            (no dependency on attribution)
  -> ground_truth_pass = g.passed
  -> attribution_complete()           (consumes ground_truth_pass)
  -> grade_live_attribution()         (live only, extends the same Grade)
  -> write result.json + grade.json   (once, from one object)
```

Nothing was relaxed. A live run still needs a recorded non-scripted call and all
17 attribution fields; the questions are simply asked in an order that can be
answered.

### Live-path regression — `tests/test_live_grading_cycle.py`

Exercises the production post-run sequence, never hand-setting
`ground_truth_pass`. A live-shaped success reaches
`ground_truth_pass=true`, `autonomy_evidence=true`, final grade **PASS**. Then
each of the eleven critical links is removed one at a time and required to fail:
`non_scripted_model_calls`, `prompt_sha256`, `evidence_sha256`,
`response_sha256`, `failure_class`, `safety_result`, `accepted_delta`,
`rollback_target`, `before_metrics`, `after_metrics`, `candidate_valid`. A
failed causal grade is separately required to withhold autonomy.

No network. `synthetic_transport=true`, `network_call=false` throughout. This
is instrumentation testing, not autonomy evidence.

---

## 2. P1-LIVE-02 — grade the outcome, not the secret answer

### What was wrong

```python
g.check("accepted delta matches the calibrated remedy", proposed == want)
```

Case 05's own calibration records `droute_iters=3 -> 0 violations`. A model
proposing 3 would have produced a correct, safe, bounded remediation that closed
the failure — and been graded a failure for not choosing the author's number.
The benchmark's claim is *"the model safely remediated the calibrated routing
failure"*, not *"the model guessed 32"*.

### What replaced it

The exact-equality check is gone. A proposal now has to satisfy, all together:

* deterministic failure class is `routing`;
* the accepted delta is non-empty;
* every changed field is in `authorized_action_space(routing)`;
* every changed field is model-writable and actually implemented (checked
  against `ir.writable_fields`, so a frozen no-op like `global_effort` fails);
* no forbidden section (`rtl`, `sdc`, `pdk`, `sta`, `extraction`) is touched;
* **the accepted delta is what the successful rerun actually used** — compared
  against attempt 2's frozen `effective_ir`;
* the injection no longer appears in the rerun;
* `route_violations` before > 0 and after == 0;
* all downstream gates, evidence and lineage valid.

`known_remedy=32` remains in the case file as calibration data and is *reported*
as a reference note, but it no longer gates anything.

The causal-linkage check is what stops a coincidental zero counting: a run
claiming `droute_iters=16` while attempt 2 actually ran 32 now fails, where
before it would have failed only for not being 32.

### Tests

| Case | Result |
|---|---|
| `32` accepted, 2 → 0 | PASS |
| `3` accepted, 2 → 0 | PASS |
| `8`, `64` accepted, 2 → 0 | PASS |
| `2` accepted, violations 2 → 9 | FAIL (metric did not improve) |
| unauthorized `sdc.default_clock_period_ns` + forged 0 | FAIL |
| frozen no-op `routing.global_effort` | FAIL (not implemented) |
| empty delta | FAIL |
| delta `16` while the rerun used `32` | FAIL (causal linkage) |
| injection surviving into attempt 2 | FAIL |
| dirty certification | FAIL |

The alternative acceptable values are asserted **not** to appear in the prompt,
so widening the accepted answers does not leak them.

---

## 3. P2-GRADE-03 — fixed, not deferred

Cheap to do while `grade.py` was already changing, and it reuses production
functions rather than adding a second evidence implementation:

* `certification_id` is **recomputed** with the production
  `evidence.certification_id()` instead of being length-checked;
* every gate record is validated through the same
  `GateEvidence.problems_against()` contract signoff uses — exact schema,
  approved tool identity, approved parser contract;
* recorded report hashes are re-verified by re-hashing the files.

### A defect in my own first attempt at this

The first version of the report-hash check guessed the filename from the
artifact key (`pdn_def` → anything starting `pdn`), so it hashed `pdn.tcl` and
`pdn_summary.json` instead of `register.pdn.def` and reported a stale hash for
a run whose hashes were correct. It now reads the path the release candidate
records. Guessing is not verification, and the run it wrongly failed
(`scripted_trial_03`) is preserved under `_voided` with that explanation.

---

## 4. Fresh scripted control

`benchmarks/autonomy/runs/scripted_trial_04`, real tools, no mocks, from
scratch on the stable instrument:

```
attempt 1   effective droute_iters = 1     script renders -droute_end_iter 1
            script sha 2a3a0df3fdd8        route_violations = 2
            deterministic class: routing
diagnosis   scripted, bounded              accepted_delta {routing: {droute_iters: 32}}
            safety_result accepted         rollback_target routing (same-stage)
attempt 2   effective droute_iters = 32    route_violations = 0
            injection no longer present
downstream  21/21 stages, 11/11 GateEvidence, lineage coherent, signoff clean
            certification identity recomputes: 02043add7c9f
            7 report hashes re-verified against the candidate's paths
grader      PASS (37/37)
freeze      6 components match
ground_truth_pass  true
autonomy_evidence  false      (scripted: 7 attribution fields absent)
candidate_valid    true
```

`result.json` and `grade.json` come from the same `Grade` object and the same
freeze; `grade_passed: true` is embedded in both.

---

## 5. Simulated-live end-to-end

`tests/test_live_grading_cycle.py` and
`tests/test_simulated_live_attribution.py`, both no-network:

```
network used         NO      (fake transport injected into _ensure_client)
credential read      NO
synthetic_transport  true
ground_truth_pass    true
autonomy_evidence    true    -- synthetic only
final live grade     PASS
```

Removing any single attribution link flips it to FAIL. This is the path the
previous 830 tests did not cover.

---

## 6. Environment

The review's finding was correct: `/home/xpat/rtl2gdsagi/.venv` was missing,
and the vendored `yosys` working tree had been removed.

```
project-local .venv restored: YES
interpreter:  /home/xpat/rtl2gdsagi/.venv/bin/python  (CPython 3.10.12)
packages:     pyyaml 6.0.3, pytest 9.1.1, anthropic 0.122.0, click 8.3.0
```

Nothing depends on `/home/xpat/rtl2gdsagi-backup/.venv`.

### A second environment fault, found by a failing run

The first control attempt failed at `lec_synth` with
`ModuleNotFoundError: No module named 'click'`. `eqy` is a Python script with
`#!/usr/bin/env python3`, so when the harness runs inside the venv, `eqy`
resolves to the **venv** interpreter and needs its dependency there. `click` is
now installed in the venv and recorded in `pyproject.toml`'s dev extras.

Worth stating plainly: the LEC gate **failed closed** on the tool crash — it
refused to assume equivalence and stopped the run. The gate behaved correctly;
the environment was at fault.

---

## 7. Void policy

Three runs are now quarantined under `benchmarks/autonomy/runs/_voided/`, each
with a written reason:

| Run | Why void |
|---|---|
| `case_05_pre_F1_fix` | result/grade from different grader revisions |
| `scripted_trial_01_pre_N1N2` | N1/N2 changed 4 frozen components |
| `scripted_trial_02_pre_live_fix` | P0-LIVE-01/P1-LIVE-02 changed `grade.py`, `run_case.py` |
| `scripted_trial_03_pre_hashfix` | the report-hash check was wrong; fixing it changed a frozen component |

None was re-graded in place. Each was superseded by a fresh execution, which is
the whole point of the rule.

---

## 8. Test results

```
before: 830 passed
after:  858 passed
new:    28
```

`tests/test_live_grading_cycle.py` (28) covers both P0-LIVE-01 and
P1-LIVE-02: the live end-to-end path, each attribution link removed in turn,
and the remedy-outcome matrix. Existing suites were corrected rather than
extended where the new hardening exposed weak fixtures.

---

## 9. Remaining

```
Remaining P0:                0
Remaining live-blocking P1:  0
```

P0-LIVE-01, P1-LIVE-02 and P2-GRADE-03 are closed. F1, F2, N1 and N2 remain
closed and their regressions still pass.

### Still true, and disclosed

* The first question remains an easy one: the prompt shows the current value
  and each authorized field's declared default.
* The grader's evidence validation reuses `problems_against` but supplies an
  empty ledger, so artifact-presence problems are skipped there; the runner
  re-hashes artifacts at signoff and the grader re-hashes the reports, so the
  gap is redundancy rather than a hole.
* `authorized_action_space` permits a rollback target at or before the failing
  stage; deterministic policy constrains the floor, not the ceiling.

---

## 10. Recommendation

```
READY FOR ONE FINAL READ-ONLY GO/NO-GO REVIEW
```
