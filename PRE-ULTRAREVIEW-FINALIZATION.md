# Pre-UltraReview finalization — N1 and N2

Closing the two residual findings before UltraReview. Nothing else was touched:
no ground truth, no known remedy, no Case-05 calibration, no verifier or grader
requirement relaxed. No API key was requested and no remote call was made.

---

## 1. N1 — `current_config` exposed non-writable fields

### The problem

`authorized_action_space` was already correct, but `runner.py` passed the
failing stage's raw IR section as `current_config`:

```python
current_config=self.ir.section(spec.ir_section)
```

So the prompt could show `"global_effort": "medium"` — a field frozen precisely
because it has no rendered effect — alongside the schema that correctly omits
it.

The failure mode was fail-closed: a model proposing it would be rejected by
`apply_delta(agent=True)`, the run would fail, and no autonomy would be
claimed. But fail-closed is not the same as well-instrumented. We get one live
diagnosis; spending it on a field we showed the model and then forbade would be
our error, not the model's.

### The fix

One permission source, not two. `safety.authorized_current_values(ir, failure)`
intersects the current IR with `authorized_action_space(failure)` — the same
structure the validator enforces:

```python
current_config=authorized_current_values(self.ir, verdict.failure)
```

It covers **all** authorized sections consistently, not just the failing stage,
so the model sees current values for every field it may write and for nothing
else. No manually maintained field list was introduced.

### What Case 05 now shows the model

```
routing:    droute_iters=1, min_layer=1, max_layer=5,
            insert_filler=True, insert_diodes=True
placement:  target_density=0.55, routability_driven=True, padding_sites=0
floorplan:  core_utilization=0.45, aspect_ratio=1.0,
            core_margin_um=10.0, tapcell_distance_um=13.0
```

The injected value is visible (it must be — the model has to see what it is
diagnosing), the legitimate alternatives are visible, and none of the five
frozen fields appear anywhere in the prompt.

### Tests — `tests/test_prompt_current_values.py` (67)

* each of `routing.global_effort`, `floorplan.io_mode`, `placement.effort`,
  `placement.max_displacement_um`, `placement.congestion_overflow_limit` is
  absent from the current values **and** from the rendered prompt;
* for **every** failure class: every visible field is authorized, and every
  authorized field carries its actual current IR value;
* flipping `agent_writable=False` in the schema removes a field from the action
  space, the current values and the prompt, with no prompt-code change —
  proving there is one source and not two;
* Case 05 still shows `droute_iters: 1` and its alternatives;
* a source-level guard that the runner never passes a raw IR section again.

Tests build a real `DiagnosisRequest` and call `build_diagnosis_prompt`; none
uses a hand-filtered fixture.

---

## 2. N2 — the freeze was recorded but not enforced

### The problem

`benchmark_freeze.json` pinned the case, grader, harness, prompt code,
authorization code and action-space schema — and `grade.py` never checked it.
An edited grader could re-grade an old run with no hard mismatch, which is
exactly the retuning the void policy forbids.

### The fix

`grade.check_freeze()` runs **first**, before any causal check, because nothing
below it means anything if the thing doing the grading is not the thing that was
frozen. It:

1. loads the freeze recorded by *that run*;
2. recomputes the current hash of every component;
3. compares exact values;
4. on any difference, fails the grade, names the drifted components, and exits
   non-zero.

The run's `benchmark_freeze.json` is **never** regenerated or overwritten during
grading — it is evidence. The comparison is *recorded-before-the-run* against
*currently executing*, never current-against-newly-generated-current.

### The grader's own hash is enforced, deliberately

`grade.py` is in the frozen set with no exception. Editing the grader after a
run makes the stored grader hash differ from the grader now executing. That is
the point, and special-casing it away would defeat the mechanism.

This was demonstrated on the project's own previous run. After the N1/N2 edits,
re-grading `scripted_trial_01` produced:

```
[FAIL] the instrument is unchanged since the run -- VOID -- these components
       changed after the run: authorization_code_sha256 (7e5f47ed79b9 ->
       8fbfa942686c); grader_sha256 (4a9a4ae78976 -> affbb9292345);
       harness_sha256 (3082b15dd597 -> 672e8d099aec); prompt_code_sha256
       (17e12779ddaf -> 4792e108744f). A response graded under a modified
       evaluator is not evidence; re-run from scratch.

grader exit: 1
```

That run was valid when it ran (29/29). It was **not** re-graded under the new
grader — that is what the policy forbids. It was moved to
`runs/_voided/scripted_trial_01_pre_N1N2` with a written reason and superseded
by a fresh execution.

### Tests — `tests/test_freeze_enforcement.py` (19)

| Mutation | Result |
|---|---|
| unchanged instrument | PASS |
| case YAML edited | **VOID** |
| `grade.py` hash differs | **VOID** |
| `run_case.py` hash differs | **VOID** |
| `prompts.py` hash differs | **VOID** |
| `safety.py` hash differs | **VOID** |
| `ir.py` hash differs | **VOID** |
| `benchmark_freeze.json` missing | **FAIL** |
| any single required hash entry missing | **FAIL** (fails closed) |
| malformed JSON | **FAIL** |
| freeze is not an object | **FAIL** |
| grading rewrites the recorded freeze | asserted it does **not** |
| drift report names every changed component | asserted |

All comparisons are content hashes. No timestamps are used for any decision;
`frozen_at` is recorded for humans and never compared.

---

## 3. Void policy

`runs/_voided/case_05_pre_F1_fix` is preserved as historical evidence and is
not current. `runs/_voided/scripted_trial_01_pre_N1N2` joins it, with its own
written reason.

The enforced rule: **if any frozen instrument component changes after a
response exists, the run is VOID and requires fresh execution.** It cannot be
re-graded in place, and the grader now refuses to try.

---

## 4. Fresh scripted control

`benchmarks/autonomy/runs/scripted_trial_02`, real tools, no mocks, executed
from scratch on the post-N1/N2 instrument:

```
attempt 1   effective droute_iters = 1     script renders -droute_end_iter 1
            script sha 0b6d79dbeba4        route_violations = 2
            deterministic class: routing
diagnosis   scripted, bounded              accepted_delta {routing: {droute_iters: 32}}
            safety_result accepted         rollback_target routing (same-stage)
attempt 2   effective droute_iters = 32    route_violations = 0
downstream  21/21 stages, 11/11 GateEvidence, lineage coherent, signoff clean
            certification_id 0119145c2ec77a41...
grader      PASS (32/32), freeze verified: 6 components match
autonomy_evidence  false
candidate_valid    true
ground_truth_pass  true
```

Recorded freeze:

```
case_yaml_sha256            36828d8d401f3e26...
grader_sha256               affbb92923459579...
harness_sha256              672e8d099aecdc42...
prompt_code_sha256          4792e108744ff772...
authorization_code_sha256   8fbfa942686c329a...
action_space_schema_sha256  ea6c2e71ea374e38...
```

`result.json` and `grade.json` both report `passed: true`, from the same grader
run and the same freeze. An independent re-grade on the unchanged instrument
exits 0.

---

## 5. Synthetic-live control

`tests/test_simulated_live_attribution.py` re-run unchanged, no network:

```
network used                 NO
credential read              NO
anthropic package imported   NO
agent class                  ClaudeAgent (real production class)
call audit                   complete: 4 hashes, provider, model
runtime attribution          complete
autonomy_evidence            TRUE  -- synthetic test only
synthetic_transport          true
network_call                 false
```

Labelled throughout and never presented as real autonomy evidence.

---

## 6. Test results

```
before: 744 passed
after:  830 passed
new:    86
```

| File | Tests |
|---|---:|
| `test_prompt_current_values.py` | 67 |
| `test_freeze_enforcement.py` | 19 |

The 67 is mostly parametrisation: the "every visible field is authorized" and
"every authorized field has its current value" invariants run once per failure
class, which is the point — the guarantee is not routing-specific.

---

## 7. Remaining P0 / live-blocking P1

```
Remaining P0:                0
Remaining live-blocking P1:  0
```

N1 and N2 are closed. F1 and F2 remain closed and their regressions still pass.

### Still true, and disclosed

* The first question remains an easy one: the prompt shows the current value
  and the field's declared default, because a model that cannot see the legal
  range cannot propose a legal value.
* The grader trusts `gate_evidence.json`'s recorded hashes rather than
  re-hashing artifacts itself; the runner re-hashes at signoff, so this is
  missing redundancy rather than a hole.
* `authorized_action_space` permits a rollback target at or before the failing
  stage; deterministic policy constrains the floor, not the ceiling.

---

## 8. Recommendation

```
READY FOR ULTRAREVIEW
```
