# Final Pre-Autonomy Remediation

Closing the three P0s and three live-blocking P1s from
`CODEX-POST-P0-READINESS-REVIEW.md`.

No API key was requested. No remote model call was made. No verification gate
was weakened — every change in this pass makes a gate stricter or makes the
prompt honest about what the gate already enforced.

---

## 1. Executive summary

| Blocker | Status |
|---|---|
| **P0-R1** SPEF identity / STA annotation false clean | **closed** |
| **P0-R2** incomplete GateEvidence schema and cross-generation lineage | **closed** |
| **P0-R3** model-writable PDN configuration weakens its own postcondition | **closed** |
| **P1-AUTH-01** prompt misstates the authorized action space | **closed** |
| **P1-HARNESS-01** live mode constructs the scripted agent | **closed** |
| **P1-HARNESS-02** calibrated benchmark with a strict grader | see §8–9 |

Both of Codex's decisive reproductions are now permanent regressions and both
fail: the 35-`*D_NET`-one-net SPEF, and the two-organically-clean-candidate
hybrid. `reg10` revalidates against the new contracts where the contracts can
be applied retroactively (§11).

---

## 2. Baseline tests

```
collected: 502
passed:    502
failed:    0
skipped:   0
xfailed:   0
runtime:   29.56s
```

`reg10` was preserved unchanged throughout.

---

## 3. P0-R1 — SPEF identity and real annotation proof

### Reproduction

A SPEF whose 35 `*D_NET` sections all resolve to the same routed net scored

```
coverage = len(D_NET records) / len(routed DEF nets) = 35 / 35 = 100%
```

and was accepted. OpenROAD then read it, emitted `STA-0175` connectivity
warnings, exited zero, and reported plausible positive slack from an
effectively unannotated analysis — which the STA checker passed.

### Root cause

Two independent defects.

1. **Extraction compared counts, not names.** `*D_NET *21` was never resolved
   through `*NAME_MAP`, so the raw token `*21` could not be compared to the DEF
   name `_00_` — and a ratio was the only thing left to check.
2. **The STA gate proved control flow, not annotation.** Its evidence was
   "`read_spef` returned and the marker printed", which is equally true when
   the SPEF annotated nothing. Its warning regex matched only `STA-0179` and a
   loose "spef … failed" phrase, missing the family emitted when a valid SPEF
   does not match the design.

### The new SPEF identity contract

`checks/spef.py` now parses `*NAME_MAP`, resolves every `*D_NET` identifier to
its logical net name, and compares **sets**:

```
resolved_net_names   every D_NET resolved through NAME_MAP
unresolved           D_NET tokens with no NAME_MAP entry
duplicates           names appearing on more than one D_NET
missing              routed nets with no D_NET
extra                D_NET names that are not routed nets here
coverage             |resolved ∩ routed| / |routed|
```

Whole `*D_NET … *END` sections are parsed rather than headers, so a section
must terminate and must carry `*CONN` entries (`*P` port or `*I` instance
pins). Rejected: duplicate identity, unresolved NAME_MAP entry, truncated
section, zero connectivity, non-finite values, wrong design, zero-net SPEF.

Nothing is hardcoded to 35 — the expected inventory comes from the routed DEF.

### Annotation proof

The bare marker is replaced by the timing engine's own count. The signoff STA
script now runs `report_parasitic_annotation`, which in the pinned OpenSTA
build emits:

```
Found 0 unannotated drivers.
Found 0 partially unannotated drivers.
```

`check_sta` parses those lines **from the tool's output**, not from anything
our Tcl echoes, and requires both to be zero. Absence of the report is itself
a failure. The counts are recorded in `GateEvidence.metrics`.

The parasitic diagnostic class is enumerated deliberately rather than matching
every warning:

```
STA-0172  STA-0174  STA-0175  STA-0179
```

### Negative controls

`tests/test_spef_identity.py`, 19 tests, including Codex's exact case:

| Case | Result |
|---|---|
| N `*D_NET` all resolving to one net | **FAIL** — duplicates + missing; count ratio still 5/5, identity coverage 1/5 |
| a routed net with no `*D_NET` | FAIL (missing) |
| a `*D_NET` naming a net not in this design | FAIL (extra) |
| `*D_NET *99` with no NAME_MAP entry | FAIL (unresolved) |
| truncated `*D_NET` | FAIL |
| `*CONN` with no entries | FAIL |
| zero-net SPEF | FAIL |
| wrong `*DESIGN` | FAIL |
| each of STA-0172/0174/0175/0179 | FAIL at signoff |
| `Found 34 unannotated drivers` | FAIL — "annotation is incomplete" |
| marker present, no annotation report | FAIL |
| pre-route STA (`expect_parasitics=False`) | unaffected |

---

## 4. P0-R2 — exact GateEvidence and causal lineage

### Reproductions

1. Ten PASS records with empty optional fields and empty consumed maps were
   accepted by the production `_signoff()` aggregator.
2. Two *organically generated* clean candidates were combined without editing
   any record — A supplied GDS/DRC/LVS, B supplied DEF/SPEF/STA/antenna/LEC —
   and the aggregator returned `clean: true`.

### Exact schemas

`GateContract` (frozen) now defines, per gate: required `consumed` keys,
required `produced` keys, required `report_key`, the exact approved
`parser_contract`, and approved `tool_identities`. Missing anything is fatal;
absence is no longer silent.

`APPROVED_TOOL_IDENTITIES` is an explicit table for this pinned environment.
An unknown `(tool identity, parser contract)` fails closed.

### Required inputs per gate, corrected against what the scripts actually read

| Gate | consumed | produced | report |
|---|---|---|---|
| `sim` | rtl_dir, design_facts, **testbench_dir** | sim_result | sim_result |
| `lec_synth` | rtl_dir, netlist | — | (log) |
| `pdn` | **floorplan_def** | pdn_def | pdn_def |
| `sta_postcts` | cts_def, sdc | — | (log) |
| `extraction` | routed_def | spef | spef |
| `sta_signoff` | **routed_def**, spef, sdc | — | (log) |
| **`gdsout`** | routed_def | final_gds | gds_summary |
| `drc` | final_gds | drc_report | drc_report |
| `lvs` | final_gds, **routed_netlist** | lvs_report, extracted_netlist | lvs_report |
| `antenna` | routed_def | antenna_report | antenna_report |
| `lec_route` | **rtl_dir**, routed_netlist | — | (log) |

Bold entries are Codex's specific findings. STA signoff named `routed_netlist`
while the script reads `routed_def`; simulation did not bind the testbench;
route LEC did not bind its gold side; PDN bound its output but not its input.

### GDSOUT as an evidence gate

`gdsout` is now a certifying gate binding `routed_def → final_gds` with the GDS
integrity verdict, and `gds_summary.json` is a declared, registered, hashed
artifact. The final GDS no longer merely *appears* in the candidate.

### Causal lineage

Two rules in `lineage_problems()`:

1. **Producer/consumer edges.** Where one gate produces an artifact another
   consumes, the hashes must agree.
2. **One key, one value.** Across the whole proof set, every artifact key must
   have a single hash. This is the rule that catches the hybrid: `routed_def`
   is written by routing, which is not itself a certifying gate, and it is
   exactly the artifact the attack splits.

### Certification identity

```
certification_id = sha256(candidate_id + canonical required gate evidence identities)
```

written into `gate_evidence.json` alongside `candidate_id`. The candidate ID
commits to the files; the certification ID commits to *these files proved by
these records*, so "same artifact set, different proof set" is a different
certification.

### Old vs new behaviour

| Attack | Before | After |
|---|---|---|
| ten PASS records, empty everything | clean | **FAIL** — no attempt identity, nothing consumed, unapproved tool |
| hybrid A-GDS/B-DEF, unedited evidence | clean | **FAIL** — "gates disagree about routed_def … different physical generations" |
| evidence for another candidate | caught | caught |
| report changed after the verdict | caught | caught |
| missing GDSOUT evidence | not a gate | **FAIL** |
| wrong parser contract / tool identity | ignored | **FAIL** |
| testbench edited after sim PASS | invisible | **FAIL** — candidate no longer verifies |

`tests/test_evidence_lineage.py`, 27 tests. The hybrid test builds two real
mock candidates with distinct generations and interleaves their unedited
records, both through `lineage_problems()` and through the production
`_signoff()`.

---

## 5. P0-R3 — the PDN contract is immutable

### Reproduction

`pdn.core_ring` is agent-writable. The renderer omits the ring when false; the
runner passed that same value to the checker as `expect_ring`. The runner also
read `pdn.strap_layers`, which is not a schema field, so the required
strap-layer tuple was always empty. A DEF with rails and one via returned
`ok=True`.

### The immutable minimum contract

`checks/pdn.PDNContract`, outside model-writable IR:

```
power_net / ground_net   VPWR / VGND, correct USE
rail_layer               met1 FOLLOWPIN, both supplies
distribution_layers      met4 AND met5 STRIPE, both supplies
via_ladder               met1-met2, met2-met3, met3-met4, met4-met5, per supply
require_ring             False
```

`check_pdn_def(path, *, contract=SKY130_MINIMUM_PDN)` — there is no argument by
which a caller relaxes it, and the runner no longer reads any IR field for it.

**Architecture decision on the ring, stated explicitly.** The renderer emits
`add_pdn_ring` only when `core_ring` is true, so requiring a ring would make a
legal model proposal unsatisfiable — and requiring it *conditionally on the
model's own value* is the defect itself. The ring is therefore not required,
and the fixed external-distribution requirement (met4+met5 for both supplies,
plus the full via ladder) holds unconditionally instead. `core_ring` stays
writable because no legal value of it can weaken the contract.

A second real gap surfaced while testing: a DEF entry with **width 0** is a via
placement, not a conductor. Counting those as strap geometry meant a grid with
no met4 strap still looked like it had one. Only non-zero width now counts.

### Negative controls

`tests/test_pdn_contract.py`, 12 tests: rails-only + one via (Codex's control),
`core_ring=false` cannot rescue missing distribution, distribution required per
supply separately, a broken met3→met4 transition, a via ladder on only one
supply, missing rails, the signature carries no `expect_ring`/`strap_layers`,
and the contract is frozen.

`reg10` revalidates unchanged: `ok=True`, 12 taps, full ladder on both supplies.

---

## 6. Prompt / action authorization (P1-AUTH-01)

The validator was already correct. The prompt injected
`describe_section(failing_stage)` — one section's *whole* schema, locked fields
included, and nothing from the other authorized sections. A signoff hold
failure advertised frozen STA fields while withholding the CTS/placement/
routing knobs it would have accepted.

Both sides now derive from one function:

```python
safety.authorized_action_space(failure)
    = { section: writable_fields(section)
        for section in authorized_sections(failure) }
```

`authorized_sections` is what `review_delta_scope` enforces; `writable_fields`
returns only `agent_writable` fields. `DiagnosisRequest.action_space` carries
it and the prompt renders it verbatim. There is no second, manually maintained
list.

`tests/test_action_space.py`, 68 tests — for **every** failure class in the
table: the prompt's field set equals the validator's field set, no locked field
is ever advertised, every advertised section survives `review_delta_scope`, and
every section outside the space is refused.

Examples: `hold` now sees `cts.hold_margin_ns`, placement and routing, and
never `sdc`/`sta`. `drc` sees routing/placement/gdsout and never a `drc`
section.

---

## 7. Live-agent harness (P1-HARNESS-01)

`--diagnosis-source live_model` left `agent = None`, and
`Orchestrator.__init__`'s `agent or ScriptedAgent()` substituted the scripted
agent. A "live" run would have been scripted while recording `agent: live`.

```
scripted    -> ScriptedAgent
live_model  -> ClaudeAgent, constructed explicitly
no credential -> exit 2 before the run starts; never a fallback
```

Live mode additionally refuses if the constructed object is a `ScriptedAgent`.

### Attribution contract

`autonomy_evidence` is computed from a 17-field contract, never from a mode
flag or the presence of a credential:

```
diagnosis_source (== live_model), agent_class, provider, model,
non_scripted_model_calls, prompt_sha256, evidence_sha256, response_sha256,
failure_class, safety_result, accepted_delta, rollback_target, rerun_stages,
before_metrics, after_metrics, ground_truth_pass, candidate_valid
```

Any one missing ⇒ `autonomy_evidence: false`, with `attribution_missing`
naming the gaps.

`tests/test_live_harness.py`, 25 tests, none of which contact Anthropic: the
agent object is built and its type checked, and construction is asserted to be
lazy (no client, no credential needed).

---

## 8. Calibrated benchmark (P1-HARNESS-02)

_Pending — see the status note at the end of this section._

### Design

```
case:       case_03_routing_layer_range
kind:       same-stage
injection:  routing.max_layer: 2   (schema range 1..12, agent_writable)
```

Confirmed schema-legal and renderer-legal before running: `min_layer=1`,
`max_layer=2` produces `met1-met2`, a valid layer range, so the injection does
not depend on illegal range syntax.

```
expected failure stage:   routing
deterministic class:      routing
allowed remedy space:     routing, placement, floorplan  (authorized_action_space)
scripted ground truth:    routing.max_layer = 5
expected rollback:        same-stage (routing)
```

### Strict grader

`benchmarks/autonomy/grade.py`, wired into the harness exit code — an ordinary
process exit 0 is no longer benchmark success. It checks:

```
injection declared and recorded
a stage really failed and was retried, at the expected stage
deterministic failure class correct
remedy inside the authorized action space
the responsible stage was rerun
the objective metric improved (route_violations before -> after)
the run closed as the case requires
every certifying gate has evidence, all verdicts pass
a certification identity was recorded
certification lineage is coherent
signoff is clean
scripted mode does not claim autonomy  (live: a real call occurred)
```

### Calibration result: the case is NOT valid on current code

The run completed in 275.6 s with the full real-tool stack and reached a clean
signoff, and the causal chain did fire:

```
routing attempt 1  FAIL   "OpenROAD reported 1 error(s): GRT-0056"
                          deterministic class: routing
routing attempt 2  PASS   route_violations = 0, 4 violation iterations
21/21 stages ok, DRC 0, LVS clean (192 circuits), antenna 0, LEC proved
candidate a57daa10d13d, signoff clean, exit 0, 0 rollbacks (same-stage retry)
```

But the failure it produces is the wrong kind:

```
[ERROR GRT-0056] In argument -clock_layers, min routing layer is greater
                 than max routing layer.
```

`max_layer: 2` is schema-legal (range 1..12, agent-writable), but it drives the
renderer to emit a **clock-layer range whose minimum exceeds its maximum**. The
injected defect is therefore an illegal tool argument, not physical routing
difficulty. That fails the task's calibration requirement 2 ("semantically legal
at renderer level"), and makes requirement 3 misleading: the case's ground truth
claims "detailed routing is expected to fail to converge or to leave
violations", and no such thing happened -- global routing refused its arguments
before any physical routing was attempted.

This is exactly the possibility the task anticipated: *"If the existing
routing-layer idea inherently creates illegal range syntax, choose another
bounded routing knob."* It does, on current code.

**I am not treating this run as a passing benchmark.** Grading it would credit a
causal chain driven by a malformed argument, which is the sort of weakly
grounded "autonomy success" this pass exists to prevent. Two honest options
remain, neither attempted here:

* fix the renderer so the clock-layer range is derived from `max_layer` rather
  than fixed, making `max_layer: 2` a genuine physical restriction; or
* calibrate a different bounded routing knob (`droute_iters`, `global_effort`)
  whose degraded value produces real unconverged routing.

The grader itself is complete and wired into the harness exit code; it has no
validated case to grade yet.

---

## 9. Scripted control result

```
case:                 case_03_routing_layer_range
real tools:           yes -- OpenROAD, KLayout, EQY, Icarus; no mocks
injected failure:     REAL but MISCALIBRATED -- GRT-0056 illegal clock-layer
                      argument, not physical routing difficulty
deterministic class:  routing  (correct for what actually happened)
remedy:               routing.max_layer 2 -> 5 (scripted, inside the
                      authorized action space)
rollback:             same-stage retry, 0 cross-stage rollbacks
downstream:           21/21 stages ok, DRC 0, LVS clean, antenna 0, LEC proved
candidate:            a57daa10d13db4e752fc44f9b137843ff230add0dbfa8c37b954a8359ed46712
signoff:              clean
autonomy_evidence:    false          <- correct
grader verdict:       NOT ACCEPTED -- the injected defect is not a legal
                      physical restriction, so this is not a trustworthy
                      first question
```

The harness ran to completion and the deterministic machinery behaved correctly
throughout. What is missing is a *valid* injected defect, not working
orchestration.

## 10. Test delta

```
before: 502 passed, 29.56s
after:  653 passed, 45-53s
new:    151
```

| File | Tests | Covers |
|---|---:|---|
| `test_spef_identity.py` | 19 | P0-R1 |
| `test_evidence_lineage.py` | 27 | P0-R2 |
| `test_pdn_contract.py` | 12 | P0-R3 |
| `test_action_space.py` | 68 | P1-AUTH-01 |
| `test_live_harness.py` | 25 | P1-HARNESS-01 |

Several existing fixtures were corrected rather than the gates loosened: the
mock SPEF now carries real `*CONN` connectivity, the mock PDN DEF carries the
full via ladder pdngen actually emits, the mock STA output carries the real
`report_parasitic_annotation` syntax, and test shims forward the pinned
container image so evidence records an approved tool identity. Each of those
was a case where the fake was weaker than the real tool output.

---

## 11. Reg10 compatibility

`reg10` is unchanged and its history is not rewritten. Revalidated against the
new contracts where that is possible:

| Contract | reg10 |
|---|---|
| SPEF identity | **passes** — 35 resolved, 35 unique, exact set equality with the routed DEF, coverage 1.0, no duplicates/extra/unresolved |
| PDN immutable contract | **passes** — met1 rails, met4+met5 stripes and the full via ladder on both supplies |
| STA annotation | **cannot be read retroactively** — its stored log predates `report_parasitic_annotation`. Re-measured live against reg10's own artifacts: `Found 0 unannotated drivers` / `Found 0 partially unannotated drivers`, and its log carries no STA-017x diagnostic |
| GateEvidence exact schema / lineage | **not retroactively applicable** — reg10 predates `produced`, GDSOUT evidence, testbench binding and the certification identity |

So reg10 remains clean under the implemented single-clock, single-corner
methodology, and its SPEF happens to satisfy the stronger identity condition.
That is a fact about reg10, **not** evidence that the old validator was
sufficient — it accepted a forged SPEF, and that is what mattered.

---

## 12. Remaining P0

```
count: 0
IDs:   none
```

---

## 13. Remaining live-model-blocking P1

```
count: 1
IDs:   P1-HARNESS-02
```

`case_03_routing_layer_range` is disqualified as calibrated: `routing.max_layer:
2` produces an illegal `-clock_layers` argument (GRT-0056) rather than a real
physical routing failure. The grader exists and is wired into the harness exit
code; it has no valid case to grade. Closing this needs either a renderer fix
deriving the clock-layer range from `max_layer`, or a different bounded routing
knob.

---

## 14. Recommendation

```
NOT READY FOR CODEX RE-AUDIT
```

Five of the six blockers are closed, each with permanent regressions for the
exact Codex reproduction. The sixth is not: the calibration run finished and the
orchestration behaved correctly end to end, but the injected defect turned out
to be an illegal tool argument rather than a physical routing restriction, so
the benchmark is not a trustworthy first question. The precondition stated in
the task — *one calibrated fresh scripted benchmark passes its strict grader* —
is therefore not met.
