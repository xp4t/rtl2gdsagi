# Codex Pre-Autonomy Remediation

Remediation of `CODEX-PRE-AUTONOMY-REVIEW.md` (review dated 2026-08-14).

No API key was requested, no live model was run, and no benchmark was altered
to make scripted results count as autonomous evidence.

---

## 1. Executive summary

```
P0 reviewed:  11
P0 fixed:      9
P0 open:       2   (P0-03 not implemented; P0-07 reproduced and now blocking,
                    but the underlying defect is unresolved)

P1 reviewed:  10
P1 fixed:      3   (P1-01 placement, P1-03 partial, P1-05 partial via deck identity)
P1 open:       7
```

**Recommendation: NOT READY FOR CODEX RE-AUDIT.** Two P0s remain, and one of
them is a real unresolved connectivity defect in the reference design.

The single most important result of this pass is negative and worth stating
first: **the register reference design is not clean.** A fresh real run
(`reg7`) still produces three `must-connect` VGND conditions, and with the
severity assumption corrected its LVS now fails. Codex was right to demand the
label be withdrawn, and it stays withdrawn.

---

## 2. Finding disposition

| Codex ID | Reproduced? | Root cause | Fix | Regression | Real validation |
|---|---|---|---|---|---|
| P0-01 model write authorization | **Yes** — `sdc`, `sim`, `sta` writable for any failure | No field-level write control; `agent_writable` existed but was never set False; no per-failure scope; rollback ignored the delta | 17 verification-intent fields frozen; `AUTHORIZED_SECTIONS` per failure class; `earliest_affected_stage` forces rollback to follow the delta | `test_codex_p0_regressions.py` (14 tests) | mock pipeline |
| P0-02 stale attempt outputs | **Yes** — Codex's exact scenario | `_execute` never cleared outputs; only `_rollback` retired them, and same-stage retries skip it | Declared outputs retired before **every** invocation; failure to retire is a hard error | `test_a_retry_that_writes_nothing_cannot_certify_the_previous_attempt` | mock pipeline |
| P0-03 signoff is status aggregation | **Yes** (accepted from review) | Manifest requires only GDS+SDC; gates carry no evidence records | **NOT FIXED** | — | — |
| P0-04 unconstrained endpoints | **Yes** — 99 endpoints → `ok=True` | Advisory verdict on an untimed path | Hard failure at post-CTS and signoff; pre-layout stays advisory | `test_unconstrained_endpoints_block_the_deciding_gates` | real STA fixture |
| P0-05 PDN has no postcondition | **Yes** — one-byte DEF passed | Generic "file exists" check | New `checks/pdn.py`: supplies, follow-pin rails, straps, ring, vias, empty nets; `pdn_summary.json` | real + synthetic | **`reg7`: 11 rails, 51 vias** |
| P0-06 meaningless SPEF | **Yes** — wrong-design zero-net SPEF passed | Non-empty file was sufficient; STA ignored parse warnings | New `checks/spef.py` (header, design, units, nets, finiteness, termination, DEF coverage) + STA annotation marker and parse-warning refusal | real + synthetic | **`reg7`: 35 nets, coverage 1.0** |
| P0-07 register VGND must-connect | **Yes** — and reproduced on a *fresh* run | Severity `W` treated as non-blocking although the message says "error at chip top level" | Narrow rule: the must-connect class blocks regardless of severity letter | `test_lvs_real_report_blocks_on_unresolved_must_connect` | **`reg7` LVS now fails** |
| P0-08 truncated LVS database | **Yes** — 15% of the file passed clean | No completeness check | Balanced-S-expression completeness; truncation always detected | truncation at 6 offsets | real database |
| P0-09 one-rule DRC | **Yes** — 1 dummy category passed | Only "≥1 category" required | Approved deck hash → expected 211-name inventory hash | `test_drc_*` | real reports (register + OV7670 share the inventory) |
| P0-10 LEC contradictions | **Yes** — PASS+ERROR and PASS-then-FAIL both passed | `search()` took the first terminal; errors checked after the pass branch | All terminals collected; disagreement fails; error before a pass claim fails | 6 tests | real EQY fixtures |
| P0-11 LVS deck trust | **Yes** — `if false` wrapper trusted | Lexical token search treated as reachability proof | `APPROVED_DECKS` content hashes; lexical guard demoted to defence in depth | `test_only_an_approved_deck_identity_is_trusted` | real PDK decks |
| P1-01 placement fail-open | **Yes** | Metric absence → PASS | Terminal `Finished with Overflow` required; non-convergence flagged | real fixture tests | `reg7` |
| P1-02 CTS telemetry | Accepted | `target_skew_ns` unused | **NOT FIXED** | — | — |
| P1-03 GDS element counting | Accepted | Counts before ENDEL | **PARTIAL** — layer-floor and hollow checks exist; record-state machine not rewritten | existing | — |
| P1-04 causal identity/persistence | Accepted | Paths not contents; no persistence | **NOT FIXED** | — | — |
| P1-05 parser version contract | Partially | No tool identity in `ToolRun` | **PARTIAL** — deck identity bound; tool versions in the manifest; no version→parser contract | — | — |
| P1-06..P1-10 | Accepted | — | **NOT FIXED** | — | — |

---

## 3. Verification-intent isolation

**Frozen — the model cannot write these at all** (17 fields):

```
lint.fail_on_warning        lint.waived_rules
sim.timeout_s               sim.testbench_glob      sim.testbench_dir
sim.plusargs
sdc.default_clock_period_ns sdc.clock_uncertainty_ns
sdc.input_delay_frac        sdc.output_delay_frac   sdc.output_load_pf
sta.corners                 sta.derate_setup        sta.derate_hold
sta.slack_guardband_ns
extraction.corner           extraction.min_net_coverage
```

The user still sets all of them (`apply_delta(..., agent=False)`).

**Model-writable implementation knobs** remain in `synthesis`, `floorplan`,
`pdn`, `placement`, `cts`, `routing`, `gdsout`, `lec`, `sta.max_paths`, and the
`drc`/`lvs`/`antenna` performance knobs (`threads`, `deep_mode`) only.

Codex's three reproductions now fail at the schema:

```
routing + {sdc.default_clock_period_ns: 100}     SchemaViolation
routing + {sim.testbench_glob: <weaker tb>}      SchemaViolation
setup   + {sta.corners: [<optimistic>]}          SchemaViolation
```

---

## 4. Causal field → rollback mapping

`SECTION_EARLIEST_STAGE` maps each IR section to the earliest stage that can
consume it. `earliest_affected_stage(delta)` returns the minimum by stage
index, and `_diagnose` uses it as a **floor**:

```
delta {floorplan: ...}  proposed target routing
   -> earliest affected  = floorplan
   -> rollback target    = floorplan  (proposal overridden, logged)
```

Per-failure authorisation (`AUTHORIZED_SECTIONS`) is applied first, so a
section the failure cannot cause is refused before it reaches this. The sets
follow the taxonomy's own escalation chain — a routing failure authorises
`routing`, `placement` and `floorplan`, which is what keeps genuine
cross-stage remediation possible — while `sdc`, `sim` and `sta` appear in no
set at all.

---

## 5. Attempt isolation

Before **every** invocation, `_retire_expected_outputs` moves each declared
output into `stages/NN_stage/superseded/NNN/`. Failure to move one raises
`Escalation` rather than logging a warning.

Codex's scenario, replayed as
`test_a_retry_that_writes_nothing_cannot_certify_the_previous_attempt`:

```
attempt 1   writes routed DEF, reports 7 violations   -> FAIL
diagnosis   {routing.droute_iters: 48}                 (IR changes)
attempt 2   clean terminal routing log, writes NOTHING

before:  pipeline rc 0, signoff clean=true, attempt 1's DEF certified
         under attempt 2's IR fingerprint
after:   attempt 2 finds no DEF (it was retired), the stage cannot
         register an output, rc != 0, signoff not clean
```

---

## 6. Release candidate evidence model

Unchanged from the previous phase and **still insufficient**, which is P0-03.
What exists: a derived `candidate_id` over GDS/netlists/SPEF/SDC/DEF/config/IR
plus PDK and tool versions, re-hashed from disk at signoff.

What does not exist: per-gate `GateEvidence` records binding each verdict to
its own consumed artifacts, report hash, attempt id and tool identity. Signoff
still reads `StageState` for most gates. **P0-03 is open.**

---

## 7. PDN validation

`checks/pdn.py` verifies, from the post-pdngen DEF:

- both configured supplies exist as SPECIALNETS with the right `USE`;
- follow-pin rails exist, on the expected layer (`met1`);
- configured strap layers and the core ring exist;
- vias exist, so the layers are tied together rather than stacked apart;
- no declared special net is left with no geometry.

`reg7` result: `nets VGND, VPWR; 11 follow-pin rail segments; 51 vias`.
A one-byte DEF now fails with "no SPECIALNETS section".

**IR drop, electromigration and current density are NOT verified**, and
`pdn_summary.json` lists them explicitly under `unverified`.

---

## 8. SPEF / parasitic annotation

From the `reg7` run:

```
spef_design       register
spef_net_count    35
routed_net_count  35
coverage          1.0
verdict           SPEF valid
```

STA annotation is proven positively: a successful `read_spef` is silent, so the
signoff script now emits `RTL2GDSAGI_SPEF_ANNOTATED` immediately after it. The
marker cannot appear if `read_spef` aborted, and `check_sta` additionally
refuses any SPEF parse warning (`STA-0179` and similar). Codex's reproduction —
zero-net SPEF, warning, identical no-parasitic numbers, PASS — now fails at
both extraction and signoff.

---

## 9. LVS resolution — the register is not clean

The three messages, verbatim:

```
Must-connect subnets of VGND of circuit sky130_fd_sc_hd__clkbuf_1 must be
connected further up in the hierarchy - this is an error at chip top level.
```

What I established:

- there are exactly **3** `sky130_fd_sc_hd__clkbuf_1` instances in the design
  and **all 3** are flagged, so this is a property of that cell's PG topology
  in this layout, not an anomaly of one placement;
- a **fresh** run (`reg7`) reproduces all three, so it is not stale evidence;
- the netlist comparison itself matches (192 circuits cross-referenced) — the
  defect is power connectivity, not logical structure.

What I did **not** do: decide it was benign. The parser now blocks on the
must-connect class specifically — not on severity `W` in general, which would
be its own dishonesty and is pinned by
`test_only_the_named_condition_blocks_not_severity_w_in_general`.

**What remains unknown:** whether the three subnets are genuinely unconnected
at top level, or whether KLayout reports this for any cell whose internal VGND
is split even when the met1 rail joins them. Answering it needs the extracted
top-level VGND topology examined per instance. Until then:

```
REGISTER = NOT CLEAN
```

The fixture sidecar that recorded `verdict: pass` has been corrected to
`verdict: fail`, with the reasoning written into it. That sidecar was the exact
implementation/test/fixture shared assumption the real-output campaign exists
to catch, and it caught it a phase late.

---

## 10. Parser hardening

| Parser | Change |
|---|---|
| STA | unconstrained endpoints fail closed at post-CTS/signoff; SPEF annotation marker required; SPEF parse warnings refused |
| LEC | all terminal markers collected, disagreement fails, explicit error before a pass claim fails; config errors still classify as `TCL_CONFIG` |
| LVS | balanced-expression completeness; must-connect class blocks; deck trust by content hash |
| DRC | deck hash → expected 211-name rule inventory; unknown deck identity fails |
| PDN | new structural checker (§7) |
| SPEF | new validator (§8) |
| Placement | terminal `Finished with Overflow` required; non-convergence flagged |
| Deck guard | `APPROVED_DECKS` by sha256; lexical guard demoted |

Three mock outputs were replaced with realistic ones (SPEF, PDN DEF, routed
DEF) because the old placeholders would never have survived the new contracts —
the same fixture-shares-the-bug pattern, found by making the contracts real.

---

## 11. Test results

```
before:  collected 454, passed 454, failed 0, skipped 0, xfailed 0   (10.99 s)
after:   collected 478, passed 478, failed 0, skipped 0, xfailed 0   (13.80 s)
new:     24 (tests/test_codex_p0_regressions.py = 21, plus STA/LVS/deck tests)
```

Tests rewritten because they encoded a superseded assumption:
`test_constant_driven_endpoints_do_not_block`, `test_guarded_verdict_is_accepted`,
`test_lvs_real_match_report`, `test_the_two_real_decks_are_distinguished`.

---

## 12. New reference register run

`reg7`, all 21 stages, real tools:

```
sim          self-checking testbench passed
lec_synth    1 partition proved
pdn          11 follow-pin rails, 51 vias, structurally sound
placement    overflow 0.0998, converged
routing      0 violations, terminal
extraction   SPEF valid, 35/35 nets, coverage 1.0
sta_signoff  annotated (marker present, no parse warnings)
drc          0 violations, 211-name inventory matched to the approved deck
lvs          NETLISTS MATCH, but 3 must-connect VGND conditions -> NOT CLEAN
antenna      0 net / 0 pin
lec_route    proved
```

The run exited 0 because it predates the must-connect rule by minutes; its
database re-parsed under current rules gives `clean = False`. **No candidate ID
is offered as certified.** The next run will fail LVS, which is correct.

---

## 13. OV7670

Untouched this pass, as instructed. Blockers unchanged: `lec_synth` 11 proved /
38 unknown; no compatible testbench so `sim` is skipped; DRC 1 × `m2.x` from an
unused RTL port. Its LEC and DRC evidence also come from different runs
(`ov10`, `ov11`), so they are not one candidate lineage.

---

## 14. Benchmark integrity

**Not addressed this pass** (P1-06, P1-07, P1-08 open). The harness still infers
its mode from credential presence, still returns zero unconditionally, still
deletes `--run-dir` without containment checks, and case 01 remains
schema-invalid (0.92 against a 0.90 maximum). No live model was used.

---

## 15. Remaining P0/P1

**P0 open**

- **P0-03** — signoff is still status aggregation. No `GateEvidence`, no
  per-gate artifact/tool binding, required artifacts still only GDS+SDC.
- **P0-07** — the register's three must-connect VGND conditions now block, but
  the underlying question (real defect vs. tool semantics) is unresolved.

**P1 open** — P1-02 (CTS fields are no-ops), P1-04 (causal identity and
checkpoint persistence), P1-05 (no version→parser contract), P1-06/07/08
(benchmark attribution, path safety, calibration), P1-09 (multi-clock SDC and
unknown-corner fallback), P1-10 (containment).

---

## 16. API-key readiness

```
NOT READY FOR INDEPENDENT RE-AUDIT
```

Two P0s are open and one of them is an unresolved connectivity defect in the
design used as the reference. Per the exit criteria, that alone settles it.
