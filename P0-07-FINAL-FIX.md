# P0-07 Final Fix Report

P0-07 is **closed**. The substrate is now modelled explicitly on both sides of
the LVS comparison, the `lvs_sub=VGND` workaround is gone, and a fresh full
register run reaches a clean signoff with valid gate evidence.

No LVS message was suppressed or downgraded. No exception was added. No PDK,
standard-cell CDL or KLayout deck file was modified.

---

## 1. Baseline

Measured before any change (Phase 0):

```
collected: 491
passed:    491
failed:    0
skipped:   0
xfailed:   0
runtime:   34.23s
```

---

## 2. Old workaround

`src/rtl2gdsagi/runner.py:790` passed `-rd lvs_sub=VGND`, and
`spice.globalize_substrate()` **deleted** each cell's `VNB` bulk pin from the
reference, rewriting its occurrences to `VGND`.

Why it existed, from the code's own comment: left at its default, the extracted
side carries a `sky130_gnd` net the reference has no counterpart for, and every
cell mismatches on it. The workaround made the comparison run by making both
sides call the substrate `VGND`.

Why that was fatal:

* the deck models the substrate as `sub = polygon_layer` (sky130.lvs:867) — an
  **empty layer with no geometry** — promoted to a global net by
  `connect_global(sub, substrate_name)` (sky130.lvs:1671);
* `connect_implicit("*")` (sky130.lvs:1676) joins same-named parts by name,
  documented in the engine as working *"without need for a physical
  connection"*;
* so inside every tapless standard cell the labelled ground metal and the
  geometry-less substrate node were joined **by name**, and KLayout recorded a
  must-connect obligation to discharge higher up;
* nothing can discharge it, because there is no geometry to connect with.

That produced three permanent, unfixable LVS failures on `reg8`, and it also
meant bulk connectivity was never actually compared — it was merged into ground
by name before the comparison started.

---

## 3. Correct substrate reference model

One substrate node, one name, declared identically on both sides:

```
extraction   -rd lvs_sub=VSUBS
             deck names its global substrate net VSUBS

reference    .SUBCKT sky130_fd_sc_hd__clkbuf_1 A VGND VSUBS VPB VPWR X
             MMNA0 Y A1 sndA1 VSUBS sky130_fd_pr__nfet_01v8 ...
             .SUBCKT register ... VGND VSUBS
```

* the CDL's `VNB` pin is **renamed, not deleted**, so every transistor's bulk
  terminal lands on a real node;
* `VSUBS` is declared as a top-level port, matching extraction promoting the
  global substrate to a pin on the top cell;
* the name deliberately does **not** collide with any net the standard cells
  label (`VGND`, `VPWR`, `VPB`), so implicit name-joining has nothing to join
  and no must-connect obligation is created.

Verified on the extracted side of the corrected run:

```
.SUBCKT sky130_fd_sc_hd__clkbuf_1 VPB X VGND VPWR A VSUBS
M$3 X \$3 VGND VSUBS sky130_fd_pr__nfet_01v8 L=0.15 W=0.52 ...
M$4 VGND A \$3 VSUBS sky130_fd_pr__nfet_01v8 L=0.15 W=0.52 ...
```

Source is `VGND`, bulk is `VSUBS`, and they are separately identifiable — which
is the whole point.

---

## 4. Production changes

| File | Change |
|---|---|
| `src/rtl2gdsagi/spice.py` | New `SUBSTRATE_NET = "VSUBS"`. New `model_substrate()` — renames the bulk pin instead of deleting it, tracking `*.PININFO`. `to_spice()` gains `substrate_net`: keeps the bulk pin, maps `VNB`/`substrate_pin` to it, adds it to the top-level ports. Legacy path retained (`substrate_net=None`) so the old behaviour stays reproducible in tests. |
| `src/rtl2gdsagi/runner.py` | `_run_lvs` passes `substrate_net=SUBSTRATE_NET` to `write_spice`, and `-rd lvs_sub={SUBSTRATE_NET}` replaces the hardcoded `lvs_sub=VGND`, with the reason recorded inline. |
| `src/rtl2gdsagi/render.py` | `render_antenna` captures `check_antennas`'s return value and appends a completion marker with the violation count to the report — see §8. |
| `src/rtl2gdsagi/checks/tools.py` | New `ANTENNA_COMPLETE_MARKER`. |
| `src/rtl2gdsagi/checks/substrate_tie.py` | Docstring corrected to its actual (diagnostic-only) role — see §10. No behavioural change. |

`klayout_lvs.py` was **not** touched. The must-connect class still blocks
unconditionally.

---

## 5. Negative proof

Four controlled runs against the same signed-off GDS. Only the reference and
the substrate name vary.

| # | Reference | `lvs_sub` | must-connect | Result |
|---|---|---|---|---|
| 1 | old (bulk deleted, tied to VGND) | `VGND` | **3** | match, exit 0 — *the shipped state* |
| 2 | new (bulk on VSUBS) | `VSUBS` | **0** | match, exit 0 — *the fix* |
| 3 | new, one nfet's bulk corrupted to `VPWR` | `VSUBS` | 0 | **MISMATCH**, exit 1 |
| 4 | substrate/ground conflated (old reference) | `VSUBS` | 0 | **MISMATCH** |

Run 3 is the direct negative control: corrupting a **single** transistor's bulk
node in the generated reference makes LVS fail. Bulk connectivity is genuinely
compared now.

Run 4 is the one that shows the fix *added* a check rather than removed a
diagnostic. It is exactly the substrate/ground conflation the old workaround
asserted unconditionally: a reference claiming every bulk sits on the ground
net, checked against an extraction that models the substrate as its own node.
Under the old configuration that claim was true by construction and
unfalsifiable. It now fails.

**Honest scope note.** Run 3's defect (bulk `VGND` → `VPWR`) is also caught
under the old configuration — it changes topology visibly either way. The
defect class the fix *newly* makes detectable is run 4's: any disagreement
between reference and layout about whether the substrate is the ground node.
That class was previously invisible by construction, which is the accurate
claim and the one worth making.

Corruption was applied only to generated reference files in a scratch
workspace. The PDK, the standard-cell CDL and the deck were not touched.

---

## 6. Targeted real LVS

Against `reg8`'s signed-off GDS, before any full rerun:

```
must-connect before:  3
must-connect after:   0
LVS:                  exit 0, "Netlists match", 192 circuits cross-referenced
log entries:          0 (no warnings, no errors of any severity)
database:             complete, balanced
```

`reg8` previously carried 3 must-connect entries. The corrected comparison
emits **no log entries at all**.

Substrate participation confirmed rather than assumed: `VSUBS` appears 120
times in the extracted netlist, is a pin on every standard-cell subcircuit, and
carries every nfet bulk terminal.

---

## 7. Test delta

```
before: 491 passed, 34.23s
after:  502 passed, 39.21s
new:    11
```

New production-gate tests:

* `tests/test_substrate_model.py` (8) — the bulk pin survives as a substrate
  pin; nfet bulk sits on the substrate, not ground; the substrate is a
  top-level port; substrate and ground names stay distinct; the legacy
  conflating model is pinned as a documented contrast; `model_substrate`
  renames rather than removes and does not match `VNBX`; **the production
  invocation contains no `lvs_sub=VGND`** and derives its name from the same
  constant the reference uses.
* `tests/test_antenna_evidence.py` (3) — a clean antenna run still writes a
  report; the report records the check's return value; rendering stays
  deterministic.

Pre-existing regressions confirmed still passing:
`test_lvs_real_report_blocks_on_unresolved_must_connect` (the preserved `reg8`
failure database still parses as a failure) and
`test_only_the_named_condition_blocks_not_severity_w_in_general` (generic
severity-W suppression is still forbidden).

---

## 8. A second defect this exposed

The first run to get all the way past LVS (`reg9`) still failed at signoff:

```
antenna's report antenna_report is not registered
```

`check_antennas` writes **nothing** to its `-report_file` when the design is
clean. The artifact ledger skips zero-length outputs, so `antenna_report` was
never registered — its recorded hash was `e3b0c442…`, the sha256 of the empty
string — and P0-03's evidence check correctly refused the candidate.

This was invisible before, because no run had ever reached signoff.

Fixed by making a clean antenna result a positive record rather than an absent
one: the stage's Tcl captures `check_antennas`'s return value and appends it to
the report. The ledger was **not** relaxed to accept empty artifacts.

```
RTL2GDSAGI_ANTENNA_COMPLETE violations=0
```

---

## 9. Fresh register run

```
run:            reg10   (fresh directory; reg8 and reg9 preserved, not reused)
candidate ID:   401a2d020d6f28bdacccc7f10901c083777cd6b09649913771fc5ac425a6215a
21 stages:      21/21 ok, 1 attempt each, 0 rollbacks
LVS:            0 must-connect, netlists match, 192 circuits, 0 log entries
DRC:            0 violations
antenna:        0 violations
LEC (route):    1 partition proved, 0 unknown, 0 non-equivalent
signoff:        CLEAN
exit code:      0
```

Every stage passed first time. Budget spent: 0 of 24.

---

## 10. GateEvidence validation

All ten required hard gates, read from `reg10/gate_evidence.json` and checked
against `release_candidate.json`:

| Gate | Verdict | Report bound | Tool identity | Parser contract |
|---|---|---|---|---|
| `sim` | pass | `sim_result` | Icarus Verilog | `tools.check_sim/v2-self-checking` |
| `lec_synth` | pass | (log) | EQY v0.68 | `tools.check_lec/v2-terminal-coherent` |
| `pdn` | pass | `pdn_def` | container digest | `pdn.check_pdn_def/v1` |
| `sta_postcts` | pass | (log) | container digest | `tools.check_sta/v2-required-metrics` |
| `extraction` | pass | `spef` | container digest | `spef.validate_spef/v1` |
| `sta_signoff` | pass | (log) | container digest | `tools.check_sta/v2-annotation-proven` |
| `drc` | pass | `drc_report` | KLayout 0.30.3 | `klayout_drc.parse_drc_report/v2-inventory-bound` |
| `lvs` | pass | `lvs_report` | KLayout 0.30.3 | `klayout_lvs.parse_lvs_report/v2-complete+must-connect` |
| `antenna` | pass | `antenna_report` | container digest | `tools.check_openroad/antenna-v2-both-halves` |
| `lec_route` | pass | (log) | EQY v0.68 | `tools.check_lec/v2-terminal-coherent` |

```
required gates:                            10
valid:                                     10
missing / mismatched:                      0
consumed-artifact hashes match candidate:  YES
bound artifacts in candidate:              14
artifacts with no hash:                    none
signoff clean:                             True
```

Contrast with `reg9` (same code except the antenna fix): 10/10 gates passed and
LVS was clean, but `antenna_report` had no hash and signoff refused the
candidate with exit code 3. The gate held.

---

## 11. `substrate_tie.py`

Kept, **unwired**, and its rationale rewritten to match reality.

```
diagnostic value:       real, and now complementary rather than overlapping
production-gate status: dead code; nothing imports it
allowed to override LVS: NO
```

Its value is sharper after the fix. LVS now compares the substrate as a
*logical* node properly, but no LVS run can confirm the well taps physically
tie the p-substrate to the ground metal, because the deck's substrate node has
no geometry to tie anything to. `substrate_tie.py` measures exactly that gap,
conservatively.

On `reg10`'s signed-off GDS, as diagnostic evidence only:

```
nets carrying substrate taps: 1
tap shapes in that net:       12 of 12
met1 shapes in that net:      131
```

If it is ever wired in, it may only be conjunctive (LVS pass **and** proof
pass), never substitutive.

---

## 12. Remaining P0

```
count: 0
IDs:   none
```

P0-03 and P0-07 are both closed.

---

## 13. Remaining P1

Listed, not worked on this pass.

- **P1-02** CTS `target_skew_ns` / `max_fanout` / `balance_levels` are no-ops.
- **P1-03** GDS scanner counts elements before `ENDEL` (partial).
- **P1-04** checkpoint persistence; several stage input declarations do not
  match what the stage really consumes.
- **P1-05** no tool-version → parser-contract mapping (the contract id is
  recorded, but nothing refuses an unvalidated version).
- **P1-08** benchmark cases uncalibrated; case 01 still schema-invalid.
- **P1-09** multi-clock SDC assigns all IO to the first clock; unknown STA
  corners fall back to the default Liberty.
- **P1-10** containment: native tools inherit the host environment.

---

## 14. Status of the register reference

```
CLEAN UNDER THE IMPLEMENTED SKY130 SINGLE-CORNER METHODOLOGY
```

This is **not** production signoff, not manufacturing-ready, and not "full
signoff clean". Known methodology limitations remain: single-corner timing, no
MCMM, no OCV, and no IR / EM / current-density signoff.

---

## 15. Recommendation

```
READY FOR CODEX RE-AUDIT
```
