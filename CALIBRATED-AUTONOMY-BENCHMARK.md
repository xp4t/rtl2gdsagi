# Calibrated Autonomy Benchmark

Closing P1-HARNESS-02: one calibrated, semantically valid, real-tool benchmark
whose answer was established before any model sees it.

No API key was requested. No live model call was made. No gate was weakened.

---

## 1. Executive result

`case_03_routing_layer_range` is **disqualified and superseded**. Its injection
(`routing.max_layer: 2`) made the renderer emit an inverted clock-layer range,
which OpenROAD rejected outright — a configuration-legality failure, not a
physical one.

The replacement is **`case_05_droute_iters`**: `routing.droute_iters: 1` is
schema-legal, renderer-legal and tool-legal. OpenROAD accepts the command, runs
real detailed routing, and terminates with genuine DRC violations still open
because the iteration budget ran out. Raising the iteration count resolves them.

Separately, an objective renderer bug was found and fixed on its own merits
(§4), and one candidate knob was rejected as a no-op (§2).

---

## 2. Candidate knobs tested

| Knob | Values tried | Renderer legal | Real failure? | Reproducible? | Selected? |
|---|---|---|---|---|---|
| `routing.max_layer` (case 03) | 2 | **NO** — emitted `-clock met3-met2` | no — `[ERROR GRT-0056]` before any routing | n/a | **rejected** |
| `routing.global_effort` | low / medium / high | n/a | **no** — the field is never rendered | n/a | **rejected (no-op)** |
| `routing.droute_iters` | 1, 2, 3, 32 | yes | **yes** — real unresolved DRC violations | yes (2/2 identical) | **SELECTED** |
| `placement.*`, `floorplan.*` | not reached | — | — | — | not needed |

`global_effort` is declared in the IR schema as an agent-writable enum, but
`grep -n global_effort src/rtl2gdsagi/render.py` returns nothing — no rendered
option consumes it. Using it would have produced a benchmark whose "remedy"
changes no tool behaviour at all. It is recorded here as a finding, not fixed
(rendering it is outside this pass's scope).

The search stopped at option A: the preferred outcome is a simple same-stage
routing benchmark, and one was found with clear causality, so options C and D
(cross-stage placement/floorplan) were deliberately not pursued.

### Calibration sweep

Targeted replay of the routing stage only, against `reg10`'s CTS checkpoint —
same LEF/liberty/DEF/SDC, only `-droute_end_iter` varied. This is valid because
routing consumes a fixed upstream checkpoint; it does not compromise causality,
and it avoids a full 21-stage flow per data point.

| `droute_iters` | tool rc | `[ERROR]` count | `Number of violations` | Detailed routing completed |
|---:|---:|---:|---:|---|
| 1 | 0 | 0 | **2** | yes |
| 2 | 0 | 0 | **9** | yes |
| 3 | 0 | 0 | 0 | yes |
| 32 (schema default) | 0 | 0 | 0 | yes |

Non-monotonicity between 1 and 2 is expected — the router's per-iteration
strategy differs — and is irrelevant: both are non-zero, and the parser fails
on any non-zero count.

Reproducibility, two independent replays at `droute_iters=1`:

```
repeat-a  rc=0  Number of violations = 2
repeat-b  rc=0  Number of violations = 2
```

The violations are real geometry, not a counter artifact:

```
violation type: Metal Spacing
  srcs: net:_01_
  bbox = ( 22.61, 17.3 ) - ( 22.895, 17.395 ) on Layer met1
violation type: Short
  srcs: net:_01_ net:_05_
  bbox = ( 18.56, 19.82 ) - ( 18.7, 19.96 ) on Layer met1
```

---

## 3. Selected benchmark

```
case:       case_05_droute_iters
design:     examples/register/register.yaml   (register, not OV7670)
kind:       same-stage
injection:  routing.droute_iters: 1     (schema int, range 1..64, agent_writable)
```

The question it poses to a future live model:

> *Detailed routing completed but left violations. Diagnose the cause and
> propose one authorized routing change that deterministic verification
> confirms.*

---

## 4. Why the injection is semantically legal

```
schema-valid:        YES -- droute_iters is int, range 1..64; 1 is in range
renderer-valid:      YES -- rendered verbatim as `-droute_end_iter 1`
tool-argument-valid: YES -- OpenROAD accepts it; rc=0; no [ERROR ...]; the log
                            reports "Complete detail routing"
```

The failure occurs **after** the tool has accepted the command and done real
work, which is exactly the standard case 03 failed.

### The renderer bug fixed independently

Case 03's failure exposed a genuine correctness defect, evaluated on its own
merits before deciding whether to touch it:

```
before:  set_routing_layers -signal met{lo}-met{hi} -clock met{max(lo,3)}-met{hi}
```

For any schema-legal `max_layer < 3` this emits a clock range whose minimum
exceeds its maximum (`met3-met2`), and OpenROAD rejects it with GRT-0056. Since
`max_layer` is agent-writable over 1..12, the renderer could turn a legal IR
into an illegal tool argument — a bug for any operator, not only for the
benchmark. Fixed by clamping the clock floor into the signal range:

```
after:   -clock met{min(max(lo,3), hi)}-met{hi}
```

| `max_layer` | rendered |
|---:|---|
| 1 | `-signal met1-met1 -clock met1-met1` |
| 2 | `-signal met1-met2 -clock met2-met2` |
| 3 | `-signal met1-met3 -clock met3-met3` |
| 5 (default) | `-signal met1-met5 -clock met3-met5` — unchanged |

Pinned by `tests/test_routing_layer_legality.py` (16 tests), which asserts a
legal range for **every** value in the schema's declared 1..12 bound, that the
clock range never escapes the signal range, and that the default configuration
is untouched.

This fix is **not** what makes the benchmark work — case 05 does not depend on
it, and case 03 remains disqualified as an autonomy benchmark regardless.

---

## 5. Baseline control (CONTROL A)

`droute_iters` at the schema default, via targeted replay:

```
droute_iters = 32  ->  rc 0, 0 errors, Number of violations = 0, routing PASS
```

`reg10` itself is the full-flow baseline: 21/21 stages, DRC 0, LVS clean,
signoff clean, at the same default.

---

## 6. Injected failure control (CONTROL B)

```
droute_iters = 1   ->  rc 0, 0 errors, Number of violations = 2
                       real DRC: 1 Metal Spacing + 1 Short on met1
                       reproduced twice, identical count
```

Deterministic verdict: routing FAIL, failure class `routing`, driven by the
`Number of violations = N` parser (the P0-05 contract), not by exit code.

---

## 7. Scripted remedy control (CONTROL C)

Full 21-stage real-tool run, 289.7 s, no mocks:

```
attempt 1  routing  FAIL  route_violations = 2   class: routing
delta      routing.droute_iters 1 -> 32   (bounded, authorized, same section)
attempt 2  routing  PASS  route_violations = 0
rollback   none -- same-stage retry, exactly as calibrated
downstream 21/21 stages ok, DRC 0, LVS clean, antenna 0, LEC proved
signoff    clean
exit       0
autonomy_evidence  false
```

---

## 8. Ground truth

Frozen in `benchmarks/autonomy/case_05_droute_iters.yaml` before the run:

```yaml
expected_failure_stage: [routing]
true_root_cause:        routing
responsible_stage:      routing
expected_rollback:      same_stage
rendered_evidence:      ["-droute_end_iter 1"]
forbidden:              [rtl, sdc, pdk, sta, extraction]
calibration:            {1: 2 viol, 2: 9 viol, 3: 0, 32: 0}
known_remedy:           {section: routing, field: droute_iters, value: 32}
before_metric:          {route_violations: 2}
after_metric:           {route_violations: 0}
```

The grader proves the injection was *in effect* by reading `run.jsonl`, the
orchestrator's own per-attempt audit trail, rather than trusting
`result.json`. The `rendered_evidence` key is retained as documentation of what
the injection renders to; it is no longer the grading mechanism, because a
retried stage is re-rendered and the surviving Tcl carries the remedy (§10).

---

## 9. Blindness / leakage audit

Two independent properties, both tested in
`tests/test_benchmark_blindness.py` (8 tests):

**No retrieval surface.** `ClaudeAgent.diagnose` sends one text prompt and
parses one text reply. It declares no `tools=`, no `tool_choice`, no
`tool_use`. The model has no filesystem, shell or retrieval access, so it
cannot open `benchmarks/autonomy/*.yaml`, the run directory, or the injection
path. The prompt is the entire input, and the test greps the production source
to keep it that way.

**No leakage in the prompt.** `DiagnosisRequest`'s field list is pinned by test,
so a new field is a new leak surface that must be reviewed. The prompt for this
exact failure is asserted to contain none of: the case id, `benchmarks/autonomy`,
`ground_truth`, `known_remedy`, `success_criteria`, `true_root_cause`,
`responsible_stage`, `calibration`, `after_metric`, the string
`droute_iters=32`, or the words `inject`/`injected`/`benchmark`.

**What the prompt does contain, deliberately.** The current IR values
(`droute_iters: 1`) and the schema of the authorized fields, including each
field's declared range and default (`"default": 32`). This is stated plainly
rather than hidden: a model that cannot see the legal range cannot propose a
legal value, and a human engineer diagnosing this failure has exactly the same
information. Nothing tells the model that `1` was injected or that the default
is the graded answer — but an honest reading is that this first question is an
easy one, which is appropriate for a first experiment and is why it is
described as a *trustworthy* question rather than a hard one.

Blindness is not achieved by starving the model: the prompt is asserted to
carry the real evidence (`DRT-0199`, `Number of violations = 2`,
`route_violations`, and the `droute_iters` field it may write).

---

## 10. Strict grader result

```
=> PASS (21/21 checks)
```

```
[PASS] injection is declared -- {'routing': {'droute_iters': 1}}
[PASS] injection recorded in result -- {'routing': {'droute_iters': 1}}
[PASS] the run has an audit trail
[PASS] the injected routing.droute_iters=1 was in effect -- recorded in run.jsonl
[PASS] the rendered configuration was legal for the tool -- no GRT-0056 / inverted range
[PASS] a stage really failed and was retried
[PASS] deterministic failure class is correct -- routing
[PASS] remedy is inside the authorized action space
[PASS] accepted delta matches the calibrated remedy -- {'routing': {'droute_iters': 32}}
[PASS] the responsible stage was rerun -- routing attempts=2
[PASS] before_metric.route_violations matches calibration -- route_violations=2
[PASS] after_metric.route_violations matches calibration -- route_violations=0
[PASS] the objective metric improved -- route_violations 2 -> 0
[PASS] the run closed
[PASS] gate evidence was written
[PASS] every certifying gate has evidence
[PASS] all gate verdicts are pass
[PASS] a certification identity was recorded
[PASS] certification lineage is coherent
[PASS] signoff is clean
[PASS] scripted mode does not claim autonomy
```

### Two grader defects found and fixed while validating it

1. **It checked the wrong file.** "The injection reached the rendered script"
   grepped the routing Tcl for `-droute_end_iter 1`, and failed — because a
   retried stage is *re-rendered*, so the surviving Tcl carries the remedy
   (`32`), not the injection. Corrected to read `run.jsonl`, the orchestrator's
   own per-attempt audit trail, which records both values. This was a genuine
   catch by the grader against itself.
2. **PASS lines printed failure-phrased details** (`[PASS] ... -- not recorded
   in run.jsonl`). A report that reads as if it contradicts itself is corrosive
   for something whose only job is to be believed; `check()` now takes a
   separate `on_pass` fact.

### The grader is proved to reject, not only to accept

`tests/test_benchmark_grader.py` mutates the real run one link at a time and
requires each to fail: no injection, no retry, no history, a remedy outside the
authorized space, a remedy that is not the calibrated one, a non-zero exit, an
autonomy claim in scripted mode, and an after-metric that did not improve.

The grader (`benchmarks/autonomy/grade.py`, wired into the harness exit code)
checks:

```
injection declared and recorded
injection reached the rendered script  (-droute_end_iter 1 in the routing Tcl)
rendered configuration was legal       (no GRT-0056 / inverted range in any log)
a stage really failed and was retried, at the expected stage
deterministic failure class correct
remedy inside authorized_action_space()
accepted delta matches the calibrated remedy exactly
the responsible stage was rerun
before/after metrics match calibration
the objective metric improved
the run closed as the case requires
every certifying gate has evidence; all verdicts pass
a certification identity was recorded
certification lineage is coherent
signoff is clean
scripted mode does not claim autonomy
```

For a later live run it additionally requires a recorded non-scripted model
call and the complete 17-field attribution contract.

---

## 11. GateEvidence / certification validation

```
candidate_id     : 9f6a9942dbd5bda4586c7e9edf83b82a...
certification_id : 1dd2f6bc6cf3fb5439c9f415a5476ed8...
certifying gates : 11 / 11 present, all verdict=pass
bound artifacts  : 19, unhashed: none
lineage          : coherent (no producer/consumer or cross-gate disagreement)
signoff          : clean
```

Lineage edges recorded by the run:

| Gate | produced |
|---|---|
| `sim` | sim_result |
| `pdn` | pdn_def |
| `extraction` | spef |
| `gdsout` | final_gds |
| `drc` | drc_report |
| `lvs` | lvs_report, extracted_netlist, **lvs_reference** |
| `antenna` | antenna_report |

### One integrity gap closed here

Validating the first control run showed `lvs_reference` in the candidate with
**no hash**: the previous pass added it to `BOUND_ARTIFACTS` so that "which
schematic was this layout compared against" is part of the candidate, but
nothing ever registered it. The runner now registers the generated reference
SPICE and the LVS gate records it as a produced lineage edge. The final control
run has no unhashed bound artifact.

---

## 12. Test results

```
before: 653 passed
after:  687 passed
new:    34
```

| File | Tests | Covers |
|---|---:|---|
| `test_routing_layer_legality.py` | 16 | the renderer emits a legal layer range for every schema-legal `max_layer` |
| `test_benchmark_blindness.py` | 8 | no retrieval surface; no ground truth in the prompt |
| `test_benchmark_grader.py` | 10 | the grader rejects an incomplete causal chain |

No test was added merely to raise the count; both files pin a specific defect
or property established in this pass.

---

## 13. Remaining P0

```
count: 0
IDs:   none
```

---

## 14. Remaining live-model-blocking P1

```
count: 0
IDs:   none
```

P1-HARNESS-02 is closed: `case_05_droute_iters` is calibrated, semantically
legal, reproducible, blind, and passes the strict grader 21/21 in scripted mode
with `autonomy_evidence: false`.

### Known limitations, stated rather than buried

* **The first question is an easy one.** The prompt legitimately shows the
  current value (`droute_iters: 1`) and the field's declared default (`32`), so
  a capable model may reach the remedy quickly. That is appropriate for a first
  experiment and is why this is described as *trustworthy*, not *hard*.
* **It is same-stage only.** Cross-stage causal reasoning is deliberately not
  exercised; the task explicitly does not require it for the first experiment.
* **`routing.global_effort` is a no-op** in the schema — agent-writable but
  never rendered. Not fixed here (out of scope); recorded so it is not mistaken
  for a usable knob.
* **`case_03_routing_layer_range` remains in the tree** as a
  configuration-legality artifact. It is not a valid autonomy benchmark and is
  not graded as one.

---

## 15. Recommendation

```
READY FOR CODEX RE-AUDIT
```

Remaining P0 = 0. Remaining live-model-blocking P1 = 0. One calibrated fresh
scripted benchmark passes its strict grader 21/21 with `autonomy_evidence:
false`, on real tools, against ground truth frozen before the run.
