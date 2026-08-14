# Final P0 Closure Report

Closing the two P0s left open by `CODEX-PRE-AUTONOMY-REMEDIATION.md`.

No API key was requested. No live model was run. No attempt was made to make
the register design look clean.

---

## 1. Baseline

```
tests before:  collected 478, passed 478, failed 0, skipped 0, xfailed 0  (12.14 s)
tests after:   collected 491, passed 491, failed 0, skipped 0, xfailed 0  (34.72 s)
new:           13 (11 in tests/test_gate_evidence.py, 2 benchmark safety)
```

The runtime increase is the tree hashing of the RTL directory and the
re-hashing of every bound artifact at signoff — both are real work that was
not being done before.

---

## 2. P0-03 — gate evidence

### The old model

Signoff read `StageState`. A stage that reached `OK` counted as a gate that
passed. That conflates two questions:

```
did this stage finish?     <- orchestration
is this design verified?   <- certification
```

They come apart whenever a report is regenerated, an upstream artifact
changes, or a retry grades an earlier attempt's file.

### The new model

`src/rtl2gdsagi/evidence.py`. Every certifying gate emits an immutable record:

```
GateEvidence
    gate, verdict, attempt_id
    report_key, report_sha256          <- the file the verdict was read from
    consumed: {artifact key -> sha256} <- what it actually read
    tool, tool_identity                <- container digest, or version string
    parser_contract                    <- e.g. klayout_lvs/v2-complete+must-connect
    metrics, created_at
```

### Required evidence per gate

| Gate | Consumed artifacts bound | Report bound |
|---|---|---|
| `sim` | rtl_dir, design_facts | sim_result |
| `lec_synth` | rtl_dir, netlist | — (log) |
| `pdn` | pdn_def | pdn_def |
| `sta_postcts` | cts_def, sdc | — (log) |
| `extraction` | spef, routed_def | spef |
| `sta_signoff` | routed_netlist, spef, sdc | — (log) |
| `drc` | final_gds | drc_report |
| `lvs` | final_gds | lvs_report |
| `antenna` | routed_def | antenna_report |
| `lec_route` | routed_netlist | — (log) |

### Candidate binding

`ReleaseCandidateManifest.BOUND_ARTIFACTS` now covers the design, the physical
artifacts, **and the verification outputs themselves** (`drc_report`,
`lvs_report`, `antenna_report`, `sim_result`) — a candidate that binds the
layout but not the reports can have its evidence rewritten underneath it.

At signoff each record is checked against the candidate:

```
for each certifying gate:
    evidence exists                                   else FAIL
    evidence.verdict == pass                          else FAIL
    report still hashes to evidence.report_sha256     else FAIL
    every consumed artifact == the candidate's        else FAIL
```

Rollback deletes evidence for every stage at or after the target, so a
superseded gate cannot certify.

### Source identity

`rtl_dir` was registered with `sha256=""` — the design was bound to a signoff
**by path**. `artifacts.tree_sha256()` now hashes relative paths plus file
contents in sorted order, excluding mtimes and location, so identical sources
hash identically wherever they live and a source edit mid-run is visible.

### Tool identity

The OpenROAD/OpenSTA container is pinned by image digest, which is exact.
Native tools (yosys, klayout, eqy, iverilog, verilator) record a version
string. **Residual limitation, stated rather than papered over:** two builds of
the same native version are indistinguishable here.

### Negative tests

`tests/test_gate_evidence.py`, 11 tests, all driving the production
aggregator: no evidence with all states OK; evidence from another candidate;
report changed after the verdict; non-pass verdict; report named with no hash;
a certifying gate losing its evidence; a required artifact unbound; RTL bound
by content not path; tree hash ignoring location and timestamps; reports bound
to the candidate.

---

## 3. P0-03 direct reproduction

Codex's construction, replayed through `_signoff` in
`test_all_stages_ok_with_no_evidence_still_fails`:

```
every StageState  = OK
final_gds         = a file containing "not a gds"
sdc               = a file containing "not sdc"
history           = empty
evidence          = none

before:  clean: true,  problems: []
after:   clean: false, problems include
         "sim produced no verification evidence, so nothing certifies it
          (a completed stage is not a verified one)"   ... for every gate
```

---

## 4. P0-07 investigation

One flagged buffer, traced end to end.

**The message** (KLayout LVS engine, `libklayout_lvs.so.0.30` — *not* the
SKY130 deck, which contains no such string):

```
Must-connect subnets of VGND of circuit sky130_fd_sc_hd__clkbuf_1 must be
connected further up in the hierarchy - this is an error at chip top level.
Instance path: register/sky130_fd_sc_hd__clkbuf_1[m0 10.12,16.32]:$184
```

**Physical trace** — cell LEF VGND pin `RECT 0.0 -0.24 1.38 0.24` on met1,
placed instances from the routed DEF, against the PDN's met1 FOLLOWPIN rails:

```
clkbuf_0_i_clk       at (22.08,24.48) FS  pin y[26.96,27.44] -> rail y=27.20 x[10.12,38.64]  OVERLAP
clkbuf_1_0__f_i_clk  at (10.12,13.60) FS  pin y[16.08,16.56] -> rail y=16.32 x[10.12,38.64]  OVERLAP
clkbuf_1_1__f_i_clk  at (23.92,13.60) FS  pin y[16.08,16.56] -> rail y=16.32 x[10.12,38.64]  OVERLAP
```

All three VGND pins overlap a ground rail.

**Abutment** — all three abut their row neighbours with zero gap, so the li1
rail is continuous through them:

```
clkbuf_1_0__f_i_clk   left <row start>   right fill_4    gap +0.000
clkbuf_1_1__f_i_clk   left dfrtp_4       right dfrtp_4   gap +0.000
clkbuf_0_i_clk        left nand2_1       right fill_4    gap +0.000
```

**Netlist trace** — all three connect to the same top-level `VGND` (position 3
of the extracted pin order `VPB X VGND VPWR A`), and there is exactly one
`VGND` net name in the extracted netlist:

```
X$110 $17 $40 VGND $17 i_clk  sky130_fd_sc_hd__clkbuf_1
X$184 $17 $39 VGND $17 $40    sky130_fd_sc_hd__clkbuf_1
X$186 $17 $44 VGND $17 $40    sky130_fd_sc_hd__clkbuf_1
```

**Topology** — extracted and reference clkbuf_1 agree (4 transistors, `$3` =
`Ab`, two inverters in series). The netlist comparison matches: 192 circuits
cross-referenced, log says "Netlists match".

**Is it cell-structural or connectivity-sensitive?** This is the decisive
measurement, taken across every preserved LVS database:

| run | must-connect | cells flagged |
|---|---:|---|
| `lvsrun` (before the PDN follow-pin fix) | **8** | clkbuf_1, decap_3, dfrtp_4, nor2_1, xnor2_1 |
| reg2 … reg8 (after) | **3** | clkbuf_1 only |

The count and the set of cells **change with the layout**, and they dropped
8 → 3 exactly when the floating power grid was fixed. So the condition tracks
real PG connectivity. It is **not** a fixed property of `clkbuf_1`, which is
the hypothesis I was drifting toward and which this disproves.

---

## 5. P0-07 root cause

```
UNRESOLVED
```

What the evidence rules **out**:

- *not* a fixed cell property — the flagged set varies with the layout (8 → 3);
- *not* a met1 disconnection — all three pins overlap a ground rail;
- *not* an abutment gap — all three abut with zero gap;
- *not* a reference-netlist defect — extracted and reference topologies agree
  and the comparison matches;
- *not* a deck rule — the message comes from KLayout's LVS engine.

What remains unexplained: why three instances that are physically on a rail,
abutted, and merged into a single top-level VGND net are nevertheless reported
as having unjoined must-connect subnets. Answering it requires reading the
per-instance subnet decomposition out of KLayout's extractor — the level at
which VGND is split *inside* the cell — which I could not do without a
KLayout-side extraction script that reports subnet membership per instance.

Per the allowed outcomes this is **C**, and no exception was added. The parser
blocks on the must-connect class specifically (not on severity `W` generally,
which is pinned by `test_only_the_named_condition_blocks_not_severity_w_in_general`).

---

## 6. Register result

```
new run ID:      reg8
candidate ID:    none — signoff never ran
21 stages:       16 OK, stopped at lvs
LVS:             FAILED — 3 must-connect VGND subnets unresolved
certification:   NOT CLEAN
```

Everything upstream of LVS passed under the new gates: PDN structural (rails +
vias), SPEF semantic (35/35 nets, coverage 1.0), STA with proven annotation,
DRC with the full 211-name inventory bound to the approved deck.

`reg8` is not promoted and no candidate is offered as certified.

---

## 7. Remaining P0

```
count: 1
IDs:   P0-07  (register VGND must-connect root cause unresolved)
```

P0-03 is closed.

---

## 8. Remaining P1

- **P1-02** CTS `target_skew_ns` / `max_fanout` / `balance_levels` are no-ops.
- **P1-03** GDS scanner counts elements before `ENDEL` (partial).
- **P1-04** checkpoint persistence; several stage input declarations still do
  not match what the stage really consumes.
- **P1-05** no tool-version → parser-contract mapping (the contract id is now
  *recorded* in evidence, but nothing refuses an unvalidated version).
- **P1-08** benchmark cases uncalibrated; case 01 still schema-invalid.
- **P1-09** multi-clock SDC assigns all IO to the first clock; unknown STA
  corners still fall back to the default Liberty.
- **P1-10** containment: native tools inherit the host environment.

Fixed this pass (cheap safety wins, kept separate from P0 work):

- **P1-06** `--diagnosis-source {scripted,live_model}` is now required and
  never inferred from credential presence; `autonomy_evidence` additionally
  requires a recorded non-scripted model call; the harness exits non-zero when
  a case misses its ground truth.
- **P1-07** benchmark run directories are confined to
  `benchmarks/autonomy/runs/`; `/`, `$HOME`, the repository and any path
  outside the results root are refused before any deletion.

---

## 9. Recommendation

```
NOT READY FOR CODEX RE-AUDIT
```

One P0 remains. The register reference design has an unresolved top-level
power-connectivity condition, and the evidence says that condition tracks real
PG connectivity rather than being a tool artifact.
