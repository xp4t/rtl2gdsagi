# rtl2gdsagi Audit Remediation Report

Remediation of the independent audit in `results.md` (audit snapshot 2026-08-13).

Everything below was verified against the actual source and against preserved or
newly produced run artifacts before any code was changed. Where the audit is
right, the underlying cause is fixed and a regression test added. Where it is
wrong, the evidence is given.

---

## 1. Executive summary

| Disposition | Count |
|---|---:|
| Confirmed and fixed | 13 |
| Partially confirmed (fixed in part, remainder documented) | 4 |
| Confirmed, not fixed this pass (documented, still open) | 6 |
| Rejected as incorrect | 0 (one partial) |
| Already fixed before the audit ran | 2 |

**The audit's central claim is correct.** Multiple independent paths could
produce a deterministic PASS from evidence that was missing, stale, one-sided,
self-contradictory, or never parsed at all. I reproduced the most serious ones
directly, including the single worst: **the routing violation parser matched
nothing whatsoever in a real OpenROAD log**, so every routing stage in every
real run passed with no violation evidence.

The overall verdict stands after remediation: this is a promising experimental
orchestration platform, **not** an autonomous signoff authority. What changed is
that the false-clean paths the audit found are now closed and covered by tests,
and the documentation no longer claims capabilities that were not demonstrated.

---

## 2. Finding-by-finding disposition

| Audit ID | Claim | Disposition | Evidence | Change |
|---|---|---|---|---|
| P0-01 | Automatic sim/LEC skips still certify | **CONFIRMED** | `SIGNOFF_GATES` excluded `sim`/`lec_synth`; the skip check covered only `cfg.skip_stages`. Reproduced: mock clean run certified with sim skipped | `REQUIRED_VERIFICATION` gate; verdict-kind check |
| P0-02 | STA passes with missing setup/hold; guardband relaxes; NaN bypasses | **CONFIRMED (all three)** | `hold is not None and hold < limit` skipped the gate; `limit = -abs(guardband)` made gb=5 accept hold −4; NaN compares False | Required metrics per stage; `limit = abs(gb)`; non-finite refused |
| P0-03 | Generated SDC is not a valid signoff constraint model | **CONFIRMED, NOT FIXED** | Single TT view, all IO on one clock, no MCMM/OCV | Documented as an open blocker |
| P0-04 | DRC passes after tool failure / partial rules | **CONFIRMED (exit code)** | `_judge_drc(self, ctx)` never received the `ToolRun` | rc/timeout check added |
| P0-05 | Routing does not parse real OpenROAD output | **CONFIRMED — worst finding** | Regex found **0 matches** in `ov9` routing log | New regex, all iterations, terminal result, completion marker |
| P0-06 | Simulation and LEC pass without functional proof | **CONFIRMED (all parts)** | Advisory counted as a pass; no-testbench returned `passed`; LEC short-circuited on `outcome == "PASS"` | Advisory propagated; no-testbench fails; LEC contradiction/rc/vacuity checks |
| P0-07 | Signoff is status aggregation, not candidate certification | **PARTIALLY CONFIRMED** | Only DRC/LVS carry `checked_gds_sha256`; no manifest | Verification gates now bound; full manifest still open |
| P0-08 | Tcl injection + causal-policy bypass | **CONFIRMED (both)** | `root_buffer` accepted `"buf; exec …"` and rendered into `-root_buf`; model's `implicated_stage`/`failure` were authoritative | `pattern` on schema field; deterministic policy authoritative; forward rollback refused |
| P0-09 | LVS/antenna/GDS false-clean paths | **PARTIALLY CONFIRMED** | Antenna one-sided and duplicate-result cases reproduced | Antenna fixed; truncated-LVS and hollow-GDS remain open |
| P1-01 | Persistent resume not implemented | **CONFIRMED** | `--resume-from routing` starts an empty ledger | Fails closed already; CLI help + README corrected |
| P1-02 | Attempt fingerprints omit material causality | **CONFIRMED, NOT FIXED** | Fingerprint omits rendered script, tool/PDK identity | Open |
| P1-03 | Rollback leaves stale state and files | **CONFIRMED, NOT FIXED** | Only checkpointed stages reset | Open |
| P1-04 | Stage criteria are tool-completion checks | **PARTIALLY CONFIRMED** | Routing/antenna now have real postconditions; PDN/CTS/extraction still do not | Partially closed |
| P1-05 | Immutability is not process-level enforcement | **CONFIRMED, NOT FIXED** | Native tools inherit the environment | Open |
| "Cannot weaken SDC" listed as False | Model can relax timing constraints | **CONFIRMED** | `SDC_TARGETS` token existed but `sdc` was never in `_SECTION_GUARD` | `sdc` guarded; SETUP/HOLD forbid it |
| P3 | README test count stale (263 vs 349); "seventeen stages" lists sixteen | **CONFIRMED** | Counted 349 at baseline | Corrected to 381 and to all 21 stages |
| §5 | "Zero-rule DRC — partially fixed" | **ALREADY FIXED** | Zero declared categories already fails | None needed |
| §5 | "Unconditional LVS success — known fixture blocked" | **ALREADY FIXED** | `deck_guard` rejects it | None needed |
| §7 | "440 → 576 after taps" conflates two variants | **CORRECT, and the audit says so** | Agreed | README already states taps were disproven |
| §3 | "Deterministic rendering — set-order clock selection" | **CONFIRMED** (I first judged this wrong — see §5) | `ref_clock = next(iter(set))`; 3 different clocks in 6 processes | Reference clock taken from the ordered list |

---

## 3. P0/P1 fixes

### P0-05 — the routing parser matched nothing in a real log

**Problem.** OpenROAD writes `[INFO DRT-0199]   Number of violations = 900.`
The pattern required a digit immediately after whitespace following
"violations", so the `=` broke it.

**Root cause.** The regex was written from a guess at the syntax and validated
against a *mock* that emitted `Total number of violations: 0` — a form OpenROAD
never produces. The fixture confirmed the bug rather than catching it.

**Old behaviour.** `if stage is ROUTING and (m := search(...))` — no match, so
no check ran at all and routing passed with no violation evidence. Verified: 0
regex matches against `ov9/stages/12_routing/attempt_01.log`.

**New behaviour.** Matches `:` and `=`; collects every iteration; requires the
`DRT-0198 Complete detail routing` marker; grades the **terminal** count. Absent
count or absent completion fails closed. (Naively switching to `search` would
have picked the *first* count — 900 — and failed a converged route.)

**Regression tests.** `test_real_openroad_violation_syntax_is_parsed`,
`test_the_terminal_iteration_decides_not_the_first`,
`test_routing_without_any_violation_count_fails_closed`,
`test_routing_that_never_completed_fails_closed`.

**Validation.** Real register run now reports `route_violations=0` across
`route_violation_iterations=4` — previously no metric existed at all.

### P0-02 — STA

**Problem.** Three independent ways to pass bad or absent timing.

**Root cause / old behaviour.**
1. `hold is not None and hold < limit` — a report with no hold number skipped
   the hold gate entirely.
2. `limit = -abs(guardband)` inverted the field's meaning: a guardband of 5 ns
   *accepted* a hold slack of −4 ns. The field is model-writable, so "propose a
   larger guardband" was a working remedy for a real timing violation.
3. NaN compares False against everything, disabling every comparison.

**New behaviour.** `sta_signoff` requires both `setup_wns` and `hold_wns`;
`sta_postcts` requires `hold_wns`; missing or non-finite fails closed;
`limit = abs(guardband)` so slack must be **at or above** the guardband; a
non-finite guardband is refused. The schema also now rejects non-finite numbers
outright.

**Regression tests.** `test_guardband_tightens_acceptance_and_never_relaxes_it`,
`test_a_missing_timing_number_cannot_pass_its_own_gate`,
`test_a_non_finite_guardband_is_refused_rather_than_ignored`,
`test_non_finite_numbers_are_rejected_by_the_schema`.

Note: the previous test `test_guardband_is_applied` asserted the **inverted**
semantics (`guardband=0.2` accepts `setup=-0.05` → PASS). The audit flagged this
exact line. It is rewritten, not deleted.

### P0-06 — simulation and LEC could pass without proof

**Simulation.** `check_sim` correctly grades a non-self-checking testbench as
below-target, but the aggregator did `if v.blocks: … else: passes.append(…)` —
an advisory has `blocks=False`, so it was counted as a pass and the stage
announced "all testbenches passed". Separately, `if not benches:` returned
`passed(spec.id, "no testbenches found")`. Both fixed: advisories are tracked
separately and propagate as a stage-level `qor_below_target`; no testbench is
now a failure.

**LEC.** `if outcome == "PASS" or …` short-circuited past every contradiction
check. A log could contain `DONE (PASS)` *and* a mismatched partition, *and* a
nonzero exit, *and* zero proved partitions, and still certify. Now all four are
checked before equivalence may be claimed.

**Regression tests.** `test_a_gate_that_proved_nothing_does_not_certify`,
`test_lec_pass_text_with_a_nonzero_exit_is_refused`,
`test_lec_pass_text_alongside_a_mismatch_is_refused`,
`test_lec_pass_text_alongside_an_unknown_is_refused`,
`test_lec_that_proved_no_partitions_is_not_a_proof`.

### P0-01 — automatically skipped gates certified

**Root cause.** `SIGNOFF_GATES` covers only stages bound to the final GDS.
`sim` and `lec_synth` are not, so they appeared in no check; and the skip check
looked only at `cfg.skip_stages`, which holds *user* skips.

**New behaviour.** `REQUIRED_VERIFICATION = (SIM, LEC_SYNTH)`. Signoff requires
each to be `OK` **and** to have produced a `pass` verdict — a stage that ran but
proved nothing does not certify. `StageState.last_verdict` was added because
status alone cannot distinguish "passed" from "completed without checking".

**Regression tests.** `test_an_automatically_skipped_gate_still_blocks_signoff`,
`test_a_gate_that_proved_nothing_does_not_certify`.

**Note on the test suite itself.** The mock toolchain hardcoded iverilog as
unavailable "so the optional-skip path is exercised", while
`test_clean_run_reaches_signoff` asserted a clean signoff. The suite's central
happy-path test therefore *asserted the false-clean*. The fixture now has all
tools present and a real self-checking testbench; tests that want the skip path
request it explicitly and assert that signoff refuses.

### P0-04 — DRC read a clean report out of a failed tool run

`_judge_drc(self, ctx)` did not take the `ToolRun` at all, so the exit code was
structurally unavailable. Now takes `run` and fails on timeout or nonzero rc
before parsing. Regression test:
`test_drc_cannot_pass_when_the_tool_exited_nonzero`.

### P0-09 — antenna

A missing side defaulted to `0` (`nets = int(m.group(1)) if m else 0`), so a
one-sided report read as clean; and `.search()` took the first match, so an
early `0/0` hid a later `4/5`. Now both halves are required and the **worst**
count over the whole log decides. Regression tests:
`test_antenna_needs_both_halves_of_the_answer`,
`test_a_later_antenna_result_cannot_be_hidden_by_an_earlier_clean_one`.

### P0-08 — model authority

**Tcl injection.** `cts.root_buffer` is a bare `str` interpolated into
`-root_buf {buffers[0]}`. Tcl treats `;` as a command separator. Confirmed: the
schema accepted `"buf; exec touch /tmp/PWNED ;#"`. `Field` now supports a
`pattern`, and `root_buffer` is restricted to a plain cell identifier.

**Causal policy.** `target = diag.implicated_stage or responsible_stage(diag.failure, …)`
made the model authoritative over both the classification and the rollback
target, including naming a stage *after* the failure — which skips every stage
in between, so the signoff gates would grade artifacts nobody regenerated. Now
the deterministic `verdict.failure` drives policy; a proposed target is accepted
only if it is at or before the failing stage; forward proposals are logged and
refused. `review_diagnosis` also takes `policy_failure` so forbidden sections
follow the deterministic class rather than the model's own label.

**SDC weakening.** The `SDC_TARGETS` token and the SDC taxonomy entry already
named this, but `sdc` was never in `_SECTION_GUARD`, so for a SETUP or HOLD
failure the guard never fired. `sdc` is now guarded and both timing classes
forbid it. Regression tests:
`test_a_cell_name_field_cannot_carry_tcl` (6 payloads),
`test_a_proposed_rollback_to_a_later_stage_is_refused`,
`test_timing_cannot_be_fixed_by_relaxing_the_clock`,
`test_reclassifying_a_failure_cannot_unlock_a_forbidden_section`.

---

## 4. P2/P3 improvements

- **Latent fail-open default.** `_judge`'s fallthrough was
  `return passed(sid, …)`. Currently unreachable, but any new hard-gated stage
  without a checker would have passed silently. Now fails closed for hard gates.
- **README corrected**: test count 263 → 381; "Seventeen stages" (which listed
  sixteen) → all 21, named; `--resume-from` no longer implies it restores a run.
- **Mock fidelity**: routing and EQY mock output replaced with captured real
  tool syntax.

---

## 5. Audit findings rejected

**Only one, and it is a partial rejection.**

I initially wrote up "nondeterministic set-order clock selection" as incorrect,
on the reasoning that `characterize.py` stores clocks in a source-ordered list.
That reasoning was wrong and I checked it before publishing the claim rather
than after. `render_sdc` built a **set** of clock names and then took
`ref_clock = next(iter(clock_names), "vclk")`. Python randomises string hashing
per process, so on a multi-clock design the clock that every
`set_input_delay`/`set_output_delay` referenced changed between runs:

```
$ for i in 1..6: python -c "<the same four clocks>"
      4 i_pclk
      1 i_clk
      1 sys_clock
```

**CONFIRMED, and now fixed** — the reference clock is the first *declared*
clock, taken from the ordered list. Regression test:
`test_the_sdc_reference_clock_is_stable_across_processes`, which renders in six
subprocesses and requires one answer. This finding is recorded here rather than
in §3 because of how nearly it was dismissed: it is the only one I got wrong,
and the failure mode — identical inputs producing different constraints —
invalidates any A/B comparison between runs.

**Partially rejected — "Simulation is a hard gate | FALSE AS CERTIFICATION
CLAIM".** The claim was correct at the time and is now fixed, but the implied
remedy — that `sim` should not be `optional=True` — is wrong: a missing *tool*
must not look like a design failure. The distinction that matters is optional to
*run* versus optional to *certify*, which is how it is now implemented.

---

## 6. New issues discovered during remediation

These were **not** in `results.md`.

1. **`_EQY_PROVED` matched only one of EQY's two phrasings, case-sensitively.**
   EQY prints both `run: Proved equivalence of partition 'x'` and
   `Successfully proved equivalence of partition x`. The pattern required a
   capital "P" and no prefix. Real logs happen to contain both forms so the
   count was right by luck; a log with only the second form scored **zero**
   proved partitions. Before the P0-06 fix that was harmless (the
   `outcome == "PASS"` short-circuit ignored it); after it, it would have become
   a false *failure*. Fixed and covered by
   `test_both_eqy_phrasings_count_as_a_proved_partition`.

2. **A fixture that validated a bug.** The routing mock emitted syntax OpenROAD
   never produces. This is the mechanism by which P0-05 survived a 349-test
   suite, and it is worth calling out as a class of defect: a mock written from
   the same misunderstanding as the parser tests nothing.

3. **The suite's happy path asserted the false-clean.** See P0-01 above.

4. **`_judge` fallthrough defaulted to PASS** for any unhandled stage.

---

## 7. Test delta

```
before:  collected 349, passed 349, failed 0, skipped 0, xfailed 0   (3.27 s)
after:   collected 382, passed 382, failed 0, skipped 0, xfailed 0   (5.33 s)
new:     33 tests, of which 28 are in tests/test_audit_regressions.py
```

No test was deleted. Three were **rewritten** because they asserted the
defective behaviour:

- `test_guardband_is_applied` → `test_guardband_tightens_acceptance_and_never_relaxes_it`
- `test_physical_only_cells_survive_the_conversion` → `test_deviceless_cells_are_omitted_because_extraction_purges_them`
- `test_optional_stage_without_tooling_is_skipped_not_failed` (kept, but the
  clean-signoff assertion it depended on moved to a test that asserts refusal)

---

## 8. Real-tool validation

All stages below ran against real tools and the real SKY130 PDK after the fixes.

| Stage | Tool | Result | Real/mock | Artifact evidence |
|---|---|---|---|---|
| lint | verilator | pass | real | `reg5/stages/01_lint` |
| sim | iverilog + vvp | pass | real | `reg5/stages/02_sim/*.sim.log` |
| sdc | internal | pass | real | `reg5/stages/03_sdc/register.sdc` |
| synthesis | yosys | pass | real | `reg5/stages/04_synthesis` |
| lec_synth | eqy + z3 | pass, 1 partition proved | real | `reg5/stages/05_lec_synth` |
| sta_pre | OpenSTA | pass | real | setup +7.080 / hold +1.458 |
| floorplan / pdn / placement / cts | OpenROAD | pass | real | `reg5/stages/07..10` |
| sta_postcts | OpenSTA | pass | real | setup +6.978 / hold +1.226 |
| routing | OpenROAD | pass, **0 violations over 4 iterations** | real | `route_violations=0` |
| extraction | OpenROAD | pass | real | SPEF written |
| sta_signoff | OpenSTA | pass | real | setup +6.922 / hold +1.177 |
| gdsout | KLayout | pass | real | `reg5/stages/15_gdsout/register.gds` |
| drc | KLayout | pass, **0 violations / 211 categories** | real | `drc_summary.json` |
| lvs | KLayout | pass, "Netlists match" | real | `lvs_summary.json` |
| antenna | OpenROAD | pass, 0 net / 0 pin | real | both halves present |
| lec_route | eqy + z3 | pass | real | `reg5/stages/19_lec_route` |
| signoff | internal | **clean** | real | `reg5/signoff.json` |

The metrics matter as much as the passes: `route_violations` and
`route_violation_iterations` are now populated from real output. Before this
work no such metric existed, because the parser matched nothing.

---

## 9. Simulation status

`iverilog` is installed (`Icarus Verilog version 11.0 (stable)`) and the gate is
genuinely active.

- **What it actually verifies:** it compiles each testbench with the design
  sources and *runs* it under `vvp`. A pass requires the testbench to print an
  explicit pass marker. `$error`/`$fatal`/`FAILED` fail the stage and escalate.
- **Who provides the testbench:** the user. The tool never writes or repairs
  one — deliberately.
- **No-result case:** now graded `qor_below_target` at stage level and **blocks
  certification**. Previously it was silently promoted to a stage pass.
- **No-testbench case:** the stage is skipped (missing input, not a design
  fault) and signoff now refuses to certify.
- **register example:** real self-checking testbench, passes.
- **OV7670:** still skipped — no testbench in `~/ov7670/rtl` matches `*_tb.v`.
  The external benches in `~/OV7670-camera-asic/tb/` target a different RTL
  revision (elaboration failures, nonexistent ports). **Not fixed, and it now
  correctly blocks signoff instead of being ignored.**

---

## 10. LEC status

`eqy` is installed (`EQY v0.68`) with `sby` and `z3` in the venv. LEC is
authoritative: a missing prover blocks certification rather than being assumed.

| Design | lec_synth | lec_route |
|---|---|---|
| register | **PASS** — 1 partition proved | **PASS** |
| OV7670 | **FAIL** — 11 proved, **38 unknown**, `eqy_outcome=FAIL` | not reached |

The OV7670 result is a genuine "equivalence not established" and escalates
(`lec_mismatch` is not autonomously resolvable). This is pre-existing and was
not caused by the remediation.

**Still blocking certification of any OV7670 GDS:** 38 unproven partitions.

Separately, the known limitation recorded in `check_lec` remains: this flow
reports a counterexample on the *sequential* partition of designs that are
certainly correct (the `counter` example). The wording deliberately says
"unverified" rather than accusing the design.

---

## 11. Timing status

Real numbers from the post-remediation register run (`reg5`):

```
sta_pre       setup +7.0805   hold +1.4580     advisory
sta_postcts   setup +6.9782   hold +1.2261     hard hold gate
sta_signoff   setup +6.9220   hold +1.1773     hard, extracted parasitics
```

Signoff STA consumes the SPEF from the same routed checkpoint. **One TT corner
only — there is no MCMM and no OCV.** That is a real limitation (P0-03) and the
timing intent is generated, not reviewed, so these numbers are not a
substitute for a signoff timing methodology.

The OV7670 hold repair reported previously (−0.124 → +0.094) remains valid as a
*numerical* result but is a developer renderer change, not runtime remediation.

---

## 12. DRC status

**register (post-remediation, `reg5`): 0 violations across 211 categories.**

OV7670, post-remediation physical-evidence run (`ov11`, LEC skipped so the
physical stages could be measured — it is explicitly not a signoff):

```
14 stages OK
routing     0 violations over 6 optimisation iterations
drc         1 violation   {'m2.x': 1}
stopped at  drc
```

Cause of that one, with evidence: the design declares an input `i_sda_in` that
nothing reads. Synthesis removes the logic, the port survives, and its pin is
streamed out as isolated metal. The routed DEF shows
`- i_sda_in ( PIN i_sda_in ) + USE SIGNAL ;` with no instance pins. **This is a
finding about the RTL, not about the flow.**

Alternative hypotheses considered and rejected for the earlier `li.3` violations:

- *Well taps* — disproven earlier; adding 260 taps made it worse. Not revived.
- *Filler cell choice* — 17 of 26 violations sat on `decap_*` cells, which
  looked conclusive and was **pure correlation**: fillers are simply where the
  router had free space to detour. With the routing layer bounds corrected the
  default filler set (decaps included) is clean.
- *Placement padding* — made it worse (27 → 46).
- **Actual cause:** `detailed_route` was given no `-bottom_routing_layer` /
  `-top_routing_layer`, so it routed on `li1` despite `set_routing_layers
  met1-met5`. Evidence: a 20 µm vertical li1 wire on net `_0304_` at x=9.89 µm,
  0.145 µm from the leftmost cells' li1 rails, against a 0.17 µm rule.
  OpenROAD's own `detailed_route` reported 0 violations throughout — **the
  router's DRC report is not a signoff check.**

Well-tap insertion is retained because the process requires it, and the README
no longer attributes the well/HVTP violations to it.

---

## 13. Remaining signoff blockers

**register: SIGNOFF CLEAN** (all 21 stages, exit 0, `reg5`).
Caveats that apply to the claim: single TT corner, generated timing intent, no
MCMM/OCV, and no release-candidate manifest.

**OV7670: NOT SIGNOFF CLEAN.** Blockers:

1. `lec_synth` — 38 partitions unproven. Hard blocker.
2. `sim` — no matching testbench; the gate is skipped and now blocks
   certification.
3. `drc` — 1 × `m2.x`, caused by the unused `i_sda_in` port in the RTL. The
   run stops here, so `lvs`, `antenna`, `lec_route` and `signoff` were never
   reached and nothing downstream of DRC has been measured on this design.
4. Everything under §14 applies to both designs.

---

## 14. Runtime autonomy evidence

The audit is right and I want to be unambiguous about it.

| Category | What happened |
|---|---|
| **Developer-fixed** | Every fix in this report. Routing/antenna/STA/LEC/DRC parsers, signoff gating, schema hardening, causal policy, filler, layer bounds, hold repair, LVS reference construction |
| **Deterministically fixed at runtime** | Nothing beyond per-stage retry with a scripted (empty) delta |
| **Runtime-agent fixed** | **None.** No preserved run contains a live model diagnosis. Every `attempt_*_api.json` records `model: scripted`, `confidence: 0`, `config_delta: {}` |

Autonomous cross-stage causal remediation is **not demonstrated**. The machinery
exists and is unit-tested against a scripted agent; it has never been exercised
against a live model on a real failure. `ANTHROPIC_API_KEY` is not set in this
environment, so every run in this report used `--no-api`.

Confidence is still recorded and still has no operational effect. I did not
invent a threshold policy for it; claiming one would be worse than the current
honest gap.

---

## 15. Current trust assessment

**Would trust unattended:**

- Running the deterministic flow and reporting what the tools said.
- Refusing to certify. The fail-closed direction is now well covered: missing
  evidence, one-sided evidence, contradictory evidence, crashed tools, skipped
  gates and vacuous proofs all block.
- Not modifying your RTL or the PDK.

**Would not trust unattended:**

- Any statement that a design is *fit to manufacture*. Single corner, generated
  timing intent, no manifest binding every gate to one release candidate.
- Autonomous remediation of a real failure — never demonstrated live.
- Resume, checkpoint restore, or duplicate avoidance across restarts.
- OS-level enforcement of PDK immutability for native (non-Docker) tools.

**The most important residual risk** is not on this list because it is not
fixable by testing: the P0-05 class of defect, where a parser and its fixture
share the same misunderstanding of a tool's output. The routing parser matched
nothing for the entire life of the project and 349 passing tests never noticed.
Every parser here should be re-validated against captured real output, not
against what its author believes the tool prints.
