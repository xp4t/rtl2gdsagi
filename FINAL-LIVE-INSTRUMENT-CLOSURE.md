# Final live-instrument closure — L1, L2, L3 and the retry envelope

Closing the remaining instrument defects from `CLAUDE-FINAL-LIVE-GO-NOGO.md`.

No API key was requested, no remote call was made. Case-05 calibration, the
injected value and the ground truth are unchanged.

---

## 1. L1 — the standalone grader dropped live checks

### The defect

`run_case.py` graded correctly, but the documented standalone entry point

```
python benchmarks/autonomy/grade.py <case> <run_dir>
```

called `grade()` alone. For a live run that omits the live-only checks —
including *"a real non-scripted model call was recorded"* — so it could
overwrite `grade.json` with PASS and exit 0 while `result.json` still said
FAIL. Two files describing one experiment, disagreeing.

### The fix

`grade.main()` now runs `grade()` and, when
`diagnosis_source == "live_model"`, `grade_live_attribution(result, g)` — the
same function the harness uses, reused rather than reimplemented. A test greps
the CLI body to make sure it never grows its own copy.

The re-grade reads recorded attribution as-is: it inspects a run, it does not
re-run it, so nothing is recomputed or fabricated and `result.json` is left
untouched. If the recorded `grade_passed` disagrees with the fresh verdict, the
CLI prints a warning that the run should be treated as void rather than either
file trusted.

### Regressions

| Case | Result |
|---|---|
| live-shaped run, zero non-scripted calls | CLI exits non-zero, `grade.json` FAIL, live checks present |
| complete valid live-shaped run | CLI exits 0, PASS |
| `grade.json` vs `result.json` overall success | asserted equal |
| CLI reimplements live checks | asserted it does not |

---

## 2. L2 — prefix-vulnerable rendered-evidence matching

### The defect

The rendered-argument check was substring membership, so

```
"-droute_end_iter 1"  in  "... -droute_end_iter 16 ..."   ->  True
```

A run that never applied the injection satisfied it.

### The fix

The ground-truth string is out of the loop entirely. The frozen script is
tokenised, the value following the option is extracted as an exact token, and
it is compared against the **typed** value in that attempt's snapshot:

```
snapshot effective_ir.droute_iters  ==  parsed token after -droute_end_iter
```

Type is compared too, so `"1"` never satisfies `1`. The mapping from IR field
to tool option is an explicit table (`RENDERED_AS`), extended deliberately
rather than pattern-guessed. The script-hash check remains independent.

| Script | Snapshot | Result |
|---|---|---|
| `-droute_end_iter 1 -verbose 1` | 1 | PASS |
| `-droute_end_iter 16` | 1 | **FAIL** |
| `-droute_end_iter 10`, `100`, `11` | 1 | **FAIL** |
| `-droute_end_iter 1foo` | 1 | **FAIL** |
| option absent | 1 | **FAIL** |
| `-droute_end_iter 1 -droute_end_iter 16` | 1 | **FAIL** (refuses to guess) |
| attempt 2 script `64` | 32 | **FAIL** |

Attempt 2 is bound to its own typed values the same way.

---

## 3. L3 — one production post-run path

### The defect

The regressions transcribed `run_case.main()`'s post-run sequence by hand.
That is precisely how P0-LIVE-01 survived: the hand-written copy did not have
the cycle the real one had, so it passed while production was broken. A defect
that exists only in production is invisible to a test that reimplements
production.

### The fix

`run_case.finalize_run_result(case, result, run_dir, case_path, write=...)`
owns the whole sequence:

```
causal grade -> ground_truth_pass -> attribution_complete
             -> autonomy_evidence -> live attribution checks
             -> one Grade object -> result.json + grade.json
```

`main()` calls it. The synthetic-live regressions call it. The previously
duplicated `_evaluate()` in `test_live_grading_cycle.py` now delegates to it,
so there is no second implementation left. A test asserts `main()` no longer
contains the sequence inline.

`write=False` exists only so tests can grade without touching disk; it changes
no logic.

---

## 4. First-live retry envelope, enforced structurally

### `retry_limit` semantics, established from the source

From `runner._attempt_stage`: `st.attempts` is incremented *before* each
execution, and the limit is tested **before** diagnosing —
`if st.attempts >= limit: escalate`. So:

```
limit = N  ->  N attempts allowed, N-1 diagnoses
limit = 2  ->  attempt 1, ONE diagnosis, attempt 2, then escalate
```

That is exactly the approved envelope: one diagnosis, one remediation retry.
The value was read from the code, not guessed.

### Where it lives

In the case file, not in operator memory:

```yaml
envelope:
  retry_limits:
    routing: 2
  max_model_calls: 1
  max_retries: 1
```

`run_case` applies `retry_limits` as real `StageOverrides`, so the orchestrator
enforces it. A second live diagnosis is unreachable for this benchmark without
editing the case — which would change a frozen component and void the run.

### And verified from the artifacts

The grader independently checks the envelope rather than trusting it: the
responsible stage's attempt count, the absence of any `attempt_03_config.json`,
the recorded call count, and — because only one call is permitted — that
`prompt_sha256`, `evidence_sha256` and `response_sha256` all match the single
recorded call audit. A run stitched together from two exchanges fails.

Regressions: a third attempt fails; two model calls fail; a response hash that
does not belong to the audited call fails.

---

## 5. Fresh scripted control

`benchmarks/autonomy/runs/scripted_trial_05`, real tools, no mocks, from
scratch on the post-L1/L2/L3 instrument:

```
attempt 1   snapshot droute_iters = 1     script renders -droute_end_iter 1
            script sha 67e6b9b825bd       route_violations = 2
            deterministic class: routing
diagnosis   scripted, bounded             accepted_delta {routing: {droute_iters: 32}}
attempt 2   snapshot droute_iters = 32    script renders -droute_end_iter 32
            route_violations = 0          injection gone
third attempt   NONE -- only attempt_01_config.json and attempt_02_config.json
envelope    routing 2 attempts, 0 model calls (scripted), within max 1
downstream  21/21 stages, 11/11 GateEvidence, lineage coherent, signoff clean
            certification identity recomputes: 4346ae2fb675
            7 report hashes re-verified
grader      PASS (41/41)
freeze      6 components match
ground_truth_pass  true
autonomy_evidence  false
```

Both attempt scripts were checked by typed binding, not substring:

```
routing.attempt_01.tcl:  droute_end_iter 1
routing.attempt_02.tcl:  droute_end_iter 32
```

### Standalone re-grade agrees

```
$ python benchmarks/autonomy/grade.py case_05_droute_iters.yaml runs/scripted_trial_05
  => PASS (41/41 checks)
exit: 0

result.json grade_passed: True
grade.json  passed:       True        -> agree
```

---

## 6. Synthetic-live production finalization

Real `ClaudeAgent`, fake transport injected into `_ensure_client`. No network,
no credential, `anthropic` never imported.

```
production helper used   yes -- finalize_run_result()
model calls              exactly 1 (synthetic)
ground_truth_pass        true
autonomy_evidence        true    -- synthetic only
final grade              PASS
```

Then, each required link removed in turn → FAIL; zero calls → FAIL; two calls →
FAIL on the envelope; hashes not tied to the audited call → FAIL.

Everything carries `synthetic_transport: true`, `network_call: false`, and is
never presented as real autonomy evidence.

---

## 7. Test results

```
before: 858 passed
after:  892 passed
new:    34
```

All 34 are in `tests/test_live_instrument_closure.py`, covering L1 (standalone
CLI semantics), L2 (typed render binding), L3 (the production helper) and the
retry envelope. The previously duplicated `_evaluate()` in
`test_live_grading_cycle.py` was retired rather than kept in parallel.

---

## 8. Remaining

```
Remaining P0:                    0
Remaining live-blocking P1:      0
Remaining known non-blocking P1: 3
```

Non-blocking, disclosed rather than fixed in this pass:

* **P1-02** CTS `target_skew_ns` / `max_fanout` / `balance_levels` are no-ops
  in the renderer. They are frozen out of the model's action space, so they
  cannot be proposed; they remain operator-facing knobs that do nothing.
* **P1-04** several `StageSpec.consumes` declarations still differ from what a
  stage actually reads. GateEvidence binds the real inputs, so this affects
  documentation rather than verification.
* **P1-10** native tools inherit the host environment; only OpenROAD is
  container-pinned. The `eqy`/`click` fault earlier in this work is an example
  of what that permits — it failed closed, but it failed.

Also still true and previously disclosed: the first question is an easy one
(the prompt shows current values and declared defaults), and
`authorized_action_space` constrains the rollback floor rather than the
ceiling.

---

## 9. Recommendation

```
READY FOR FINAL TARGETED READ-ONLY CONFIRMATION
```
