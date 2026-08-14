# Live-harness final fix — F1, F2 and first-run action-surface freeze

Closing the two live-blocking findings from `CLAUDE-CLEANROOM-LIVE-GO-NOGO.md`,
plus the first-run hygiene items F3/F5/F6/F7.

No API key was requested. No remote model call was made. No verification gate
was weakened. Case-05 ground truth was not touched.

---

## 1. F1 — old reproduction

The first link of the causal chain was the one link not actually proved. The
grader grepped the whole of `run.jsonl` for the substring `'"droute_iters": 1'`.

**Hole A — prefix collision.** `'"droute_iters": 1'` is a prefix of
`'"droute_iters": 16'`. A run rewritten to use 16 throughout, never 1, graded
as a success.

**Hole B — no anchoring.** Deleting *every* routing event still passed: the
surviving match was the config-load note emitted before any stage ran. The
check proved "the config file declared it", never "the tool was configured that
way on the attempt that failed".

It also had a bad provenance. The stronger check it replaced
(grep the rendered `routing.tcl`) had *correctly* failed, because a retried
stage is re-rendered and the surviving script carries the remedy. The right
response was to snapshot per attempt; what happened instead was a substitution
at the weakest available strength, after seeing a failing grade.

---

## 2. F1 — new exact per-attempt proof

The runner now freezes each attempt's configuration **before invoking the
tool** (`Orchestrator._snapshot_attempt`), producing two immutable artifacts
per attempt:

```
stages/12_routing/routing.attempt_01.tcl      # the exact script that ran
stages/12_routing/attempt_01_config.json      # the exact typed IR that produced it
```

```json
{
  "stage": "routing",
  "attempt": 1,
  "attempt_id": "routing#1",
  "ir_section": "routing",
  "effective_ir": {"droute_iters": 1, "min_layer": 1, "max_layer": 5, ...},
  "script": "routing.attempt_01.tcl",
  "script_sha256": "836dc3abce46..."
}
```

The grader reads that record and compares **typed values**, anchored to stage
and attempt. No substring matching anywhere:

```
[PASS] the failing stage directory exists -- 12_routing
[PASS] attempt 1 configuration snapshot exists and parses
[PASS] the snapshot is anchored to the failing stage -- routing
[PASS] the snapshot is anchored to attempt 1 -- attempt 1
[PASS] attempt 1 effective routing.droute_iters == 1 -- droute_iters=1
[PASS] the attempt 1 script snapshot exists -- routing.attempt_01.tcl
[PASS] the attempt 1 script matches its recorded hash -- 836dc3abce46
[PASS] attempt 1 script renders '-droute_end_iter 1' -- present
[PASS] attempt 2 effective droute_iters == 32 -- droute_iters=32
```

Value **and** type are compared (`got == value and type(got) is type(value)`),
so `"1"` does not satisfy `1`. The script is independently re-hashed, so an
edited snapshot is caught. And the remedy attempt is required *not* to still
carry the injection.

### F1 negative tests — `tests/test_injection_proof.py` (15)

| Attack | Result |
|---|---|
| `droute_iters = 16` (the prefix collision) | **FAIL** |
| `10`, `11`, `100` | **FAIL** |
| value only in a pre-run config note | **FAIL** |
| value only on attempt 2 | **FAIL** |
| attempt-1 snapshot missing | **FAIL** |
| snapshot belongs to another stage | **FAIL** |
| snapshot belongs to another attempt | **FAIL** |
| effective IR says 1, frozen script says 32 | **FAIL** |
| script edited after the fact (hash mismatch) | **FAIL** |
| script snapshot missing | **FAIL** |
| `"1"` (string) instead of `1` (int) | **FAIL** |
| honest run | PASS |

Plus a source-level assertion that the substring check cannot return.

---

## 3. F2 — old unreachable `autonomy_evidence`

The contract required 17 fields; `run_case.py` populated four
(`diagnosis_source`, `agent`, `non_scripted_model_calls`, `injected`). The
remaining thirteen were never written, so `attribution_complete()` could not
return `True` for any run, live or otherwise. The existing test built
`{field: "recorded"}` and proved the *validator* accepted it — which tests
nothing about the harness.

`accepted_delta` was read back from the harness's own `--scripted-delta`
argument: the answer it was handed, not what the system did, and unavailable in
live mode.

---

## 4. F2 — new runtime attribution path

Every field is now derived from a runtime record.

| Field | Source |
|---|---|
| `diagnosis_source` | CLI, declared, never inferred |
| `agent_class` | `type(agent).__name__` of the object actually constructed |
| `provider`, `model` | the agent's own `CallAudit` |
| `non_scripted_model_calls` | count of `CallAudit` records the agent emitted |
| `prompt_sha256`, `system_prompt_sha256`, `evidence_sha256`, `response_sha256` | `CallAudit`, hashed at call time |
| `failure_class` | deterministic `verdict.failure`, recorded when the delta was accepted |
| `safety_result` | recorded only after `review_diagnosis` + `review_delta_scope` + `apply_delta` all passed |
| `accepted_delta` | **the applied delta from that chain**, not the CLI argument |
| `rollback_target` | the deterministic retry/rollback decision |
| `rerun_stages` | stages whose `attempts > 1` |
| `before_metrics` / `after_metrics` | first and last `route_violations` from the responsible stage's own verdicts |
| `candidate_valid` | signoff clean **and** certification identity present **and** every gate verdict pass — never the exit code |
| `ground_truth_pass` | the strict grader's verdict |

### The one source of truth for the accepted delta

```
model proposal → review_diagnosis → review_delta_scope → apply_delta
                                                     ↓
                                        Orchestrator._accepted
                                                     ↓
                                        result.accepted_delta
```

Scripted mode produces the same record naturally, because it travels the same
path. Nothing reads `--scripted-delta` any more.

### Evaluation order (no circular dependency)

```
run completes → build attribution → grade causal criteria → ground_truth_pass
              → compute autonomy_evidence → write result.json + grade.json
```

`result.json` and `grade.json` are now written in the same pass from the same
`Grade` object, so they cannot disagree (F7).

---

## 5. Actual prompt persistence

`"<prompt recorded by agent>"` is gone. `ClaudeAgent.diagnose` returns a frozen
`CallAudit`:

```
provider, model
system_prompt_sha256, user_prompt_sha256
evidence_payload_sha256, response_sha256
system_prompt, user_prompt, response_text     # preserved for local review
synthetic_transport
```

Built in the same `return` as the parsed diagnosis — i.e. at call time, before
any remediation outcome exists, so it cannot be retrofitted (asserted by a
source-order test). No credential is stored: the key is read from the
environment at call time and never recorded, and a test greps the serialised
audit for `sk-` and `ANTHROPIC_API_KEY`.

---

## 6. Result-building test with a fake live transport

`tests/test_simulated_live_attribution.py` (23 tests) runs `ClaudeAgent`
against a fake transport shaped exactly like the anthropic client surface,
injected into `_ensure_client`'s cache. **No network request, no credential
read, `anthropic` never imported.**

It proves the agent records a complete audit for a live-shaped call, that the
hashes really are of the recorded text, and that a fully populated live-shaped
result reaches `autonomy_evidence: true` — the thing that was structurally
impossible. Each of the 17 fields is then removed one at a time and required to
withhold it.

Everything synthetic is labelled: `synthetic_transport: true`,
`network_call: false`. **This is not autonomy evidence and must never be
presented as such.**

---

## 7. First-run action-space field list

For a routing failure the model now sees exactly:

```
routing:    droute_iters, insert_diodes, insert_filler, max_layer, min_layer
placement:  padding_sites, routability_driven, target_density
floorplan:  aspect_ratio, core_margin_um, core_utilization, tapcell_distance_um
```

Twelve fields across three sections. Every one was verified to be consumed by
`render.py` (test asserts it mechanically, so a future no-op cannot be added
silently).

---

## 8. Fields frozen, and why

| Field | Reason |
|---|---|
| `routing.global_effort` | no rendered effect — nothing in `render.py` consumes it |
| `floorplan.io_mode` | no rendered effect |
| `placement.effort` | no rendered effect |
| `placement.max_displacement_um` | no rendered effect |
| `placement.congestion_overflow_limit` | moves an **acceptance threshold**, not the implementation |

They are marked `agent_writable=False`, **not deleted** — operators keep them,
the model does not see them. The last one matters most: it let the subject move
the bar instead of clearing it.

The surface was deliberately **not** narrowed to `droute_iters`. A test
requires ≥3 routing fields and ≥2 sections, so trimming it to the known answer
would fail — that would be overfitting the model to the answer, not blindness.

---

## 9. Neutral run-directory policy

The run directory is now `benchmarks/autonomy/runs/scripted_trial_01` — no
`droute_iters`, no `routing`, no `case_05`, no remedy in the path (F6). The
live experiment should use `live_trial_01`.

The model has no filesystem access at all (no `tools=`, asserted at source
level), so a path could only leak through the evidence excerpt. The prompt
blindness tests already assert `benchmarks/autonomy` never appears in it.

---

## 10. Benchmark freeze

`freeze_instrument()` hashes the whole instrument **before anything executes**
and writes `benchmark_freeze.json` into the run directory; the result embeds
the same object.

```
case_yaml_sha256           36828d8d401f3e26...
grader_sha256              4a9a4ae78976e1ff...
harness_sha256             3082b15dd5970773...
prompt_code_sha256         17e12779ddafaf4c...
authorization_code_sha256  7e5f47ed79b949c5...
action_space_schema_sha256 df231c3781de66d4...
frozen_at                  2026-08-14T08:33:xxZ
```

### No post-answer retuning

If, after a model response, `grade.py`, the case YAML, the ground truth or the
success criteria change, **the run is VOID** and must be re-run from scratch.
Never re-grade the same response under a modified evaluator.

That policy is applied to this project's own history: the previous run was
moved to `benchmarks/autonomy/runs/_voided/case_05_pre_F1_fix` with a written
reason, because its `result.json` and `grade.json` came from different grader
revisions with no re-run between them (F7). It is preserved for audit and is
not evidence.

---

## 11. Fresh scripted control

`benchmarks/autonomy/runs/scripted_trial_01`, real tools, no mocks, from
scratch:

```
attempt 1   effective droute_iters = 1    script renders -droute_end_iter 1
            route_violations = 2          deterministic class: routing
diagnosis   scripted, bounded             accepted_delta {routing: {droute_iters: 32}}
            safety_result accepted        rollback_target routing (same-stage)
attempt 2   effective droute_iters = 32   script renders -droute_end_iter 32
            route_violations = 0
downstream  21/21 stages, DRC 0, LVS clean, antenna 0, LEC proved
            11/11 gates pass, lineage coherent, signoff clean
grader      PASS (29/29)
autonomy_evidence  false        (7 attribution fields absent: no model call)
candidate_valid    true
ground_truth_pass  true
```

`result.json` and `grade.json` describe the same grader version and the same
run.

---

## 12. Simulated-live control — no network

Covered by `tests/test_simulated_live_attribution.py` rather than a separate
run directory, because the point is instrumentation capability, not another
EDA execution:

```
network used                 NO
credential read              NO
anthropic package imported   NO
agent class                  ClaudeAgent (real production class)
call audit                   complete: 4 hashes, provider, model
autonomy_evidence            TRUE  (in this synthetic test only)
synthetic_transport          true
network_call                 false
```

---

## 13. Grader mutation tests

`tests/test_benchmark_grader.py` mutates the real run and requires each break
to fail: no injection, no retry, no history, remedy outside the authorized
space, remedy that is not the calibrated one, non-zero exit, autonomy claimed
in scripted mode, and an after-metric that did not improve. A further test
asserts no PASS line ever carries a failure-phrased detail.

Two grader defects the clean-room review flagged were also fixed:

* the dead `if not proposed:` branch made the action-space check pass
  vacuously; an empty delta is now an explicit failure;
* `after < before or after == 0` treated `0 → 0` as an improvement; it is now
  `after < before`.

---

## 14. Test results

```
before: 687 passed
after:  744 passed
new:    57
```

| File | Tests |
|---|---:|
| `test_injection_proof.py` | 15 |
| `test_simulated_live_attribution.py` | 23 |
| `test_first_run_action_surface.py` | 13 |
| `test_benchmark_freeze.py` | 6 |

---

## 15. Remaining P0

```
count: 0
IDs:   none
```

---

## 16. Remaining live-blocking P1

```
count: 0
IDs:   none
```

F1 and F2 are closed. F3, F5, F6 and F7 are addressed.

### Still true, and disclosed

* The first question remains an easy one: the prompt legitimately shows the
  current value and the field's declared default.
* The grader trusts `gate_evidence.json`'s recorded hashes rather than
  re-hashing the files itself. The runner re-hashes at signoff, so this is
  missing redundancy rather than a hole.
* `authorized_action_space` still permits a rollback target at or before the
  failing stage; deterministic policy constrains the floor, not the ceiling.

---

## 17. Recommendation

```
READY FOR FINAL INDEPENDENT REVIEW
```
