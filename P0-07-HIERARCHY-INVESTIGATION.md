# P0-07 KLayout Hierarchical Must-Connect Investigation

The mechanism is now established, with a controlled reproduction that emits the
exact three messages and a single-variable matrix that turns them on and off.

**Answer to the primary question.** KLayout is not reporting that the ground
metal is disconnected. It is reporting that a *nominal* (name-based) join was
made between two subnets that are not physically joined inside the cell, and
that the obligation to join them physically was never discharged. The second
subnet is the deck's substrate pseudo-node, which in the SKY130 KLayout deck
carries **no geometry at all** — so that obligation cannot be discharged by any
layout, at any tap density.

Classification: **extraction/configuration defect**, remedy identified but not
implemented. P0-07 stays **OPEN**.

---

## 1. Test-suite verification

Run before anything else, per Phase 0:

```
collected: 491
passed:    491
failed:    0
skipped:   0
xfailed:   0
runtime:   34.64s
```

`substrate_tie.py` existed on disk for this run and is dead code — nothing
imports it. Measured, not assumed.

No production source was modified during this investigation, so this is also
the final suite result.

---

## 2. Exact current must-connect errors

From `reg8`'s `lvs.lvsdb`, all three severity `W`, reported in circuit
`register`:

| Instance | Master | Net | Group | Hierarchy | Location (µm) |
|---|---|---|---|---|---|
| `sky130_fd_sc_hd__clkbuf_1[m0 22.08,27.2]:$114` | clkbuf_1 | `VGND` | must-connect subnets of VGND | reported in `register`, obligation owned by circuit `sky130_fd_sc_hd__clkbuf_1` | (21.89,24.24)–(23.65,27.44) |
| `sky130_fd_sc_hd__clkbuf_1[m0 10.12,16.32]:$188` | clkbuf_1 | `VGND` | same | same | (9.93,13.36)–(11.69,16.56) |
| `sky130_fd_sc_hd__clkbuf_1[m0 23.92,16.32]:$190` | clkbuf_1 | `VGND` | same | same | (23.73,13.36)–(25.49,16.56) |

The extracted circuit `X(sky130_fd_sc_hd__clkbuf_1)` appears **once** in the
database. Its `VGND` net (id 4) holds licon, three mcon, li, met1 and one text
label `J(l28 VGND)` on layer 68/5, plus both nfet bulk terminals (`T(B 4)`).

**Correction to the previous report:** the message template lives in
`libklayout_db.so.0.30.3`, not `libklayout_lvs.so`. The LVS library contains
zero occurrences of the string. The earlier attribution was wrong; the
conclusion drawn from it (that the message is engine behaviour rather than a
deck rule) is unchanged and still correct.

---

## 3. What flat connectivity proves (E5/E6)

A conservative `LayoutToNetlist` run over the signed-off GDS using the deck's
ground chain — `ptap_conn = tap & psdm - nwell`, then
`licon → li → mcon → met1 → via1 → … → met5`:

```
reg8:      1 net, 12/12 taps, 131 met1 shapes, all 3 flagged instances inside it
reg_tap8:  1 net, 18/18 taps, 137 met1 shapes, flagged nand3_1 inside it
```

The model's faithfulness was verified this pass rather than assumed. The deck
derives only two of the layers used here:

```
li_con   = li.not(li_res).not(vpp)
met1_con = met1.not(met1_res).not(vpp)
```

and `li_res`, `met1_res`, `vpp` have no geometry in this design, so
`li_con ≡ li` and `met1_con ≡ met1`. `licon`, `mcon`, `via1`, `tap`, `psdm`
and `nwell` are raw `polygons(...)` in the deck, identical to the model. The
model's `ptap` omits `.not(diff_res).not(diff_cut).not(npnid).not(pnpid)`,
which can only shrink the layer. So the model uses the same or smaller layers
and strictly fewer `connect` relations, and finding one component is a
lower-bound proof.

**Proven:** every substrate tap contact and the whole ground metal network are
one connected component, and each flagged instance sits in it.

---

## 4. What flat connectivity does NOT prove

It proves a property of the *tap contact geometry*. KLayout's must-connect
obligation is about something else entirely, and the two are not the same
claim.

The engine's own documentation, read out of `libklayout_db.so.0.30.3`:

> "Use this method to register a pattern for net labels considered in implicit
> net joining. Implicit net joining allows connecting multiple parts of the
> same nets (e.g. supply rails) **without need for a physical connection**. The
> pattern specifies labels to look for. When parts are labelled with a name
> matching the expression, the parts carrying the same name are joined."

and

> "In top level mode, must-connect warnings are turned into errors for example."

So `must-connect` is the bookkeeping KLayout attaches to a join it made *by
name rather than by geometry*. The obligation is: these parts were treated as
one net on the strength of their labels, so they had better be physically
joined further up. It is a claim about **the deck's `sub` pseudo-layer**, not
about the tap contacts the flat proof measured. §6 shows the two are disjoint.

---

## 5. Internal VGND subnet topology

Inside every tapless standard cell, two physically separate things end up
carrying the name `VGND`:

```
subnet (a)  labelled ground metal
            met1 rail piece + li1 + licon + mcon, carrying the text label
            "VGND" on layer 68/5

subnet (b)  the deck's substrate pseudo-node
            reaches the cell only through the nfet bulk terminals
            (extract_devices(..., "W" => sub))
```

They are not joined inside the cell — a standard cell has no tap; only
`tapvpwrvgnd_1` carries tap-layer geometry (65/44). The join is expected from
the parent. That is precisely the reported condition.

---

## 6. Deep/hierarchical extraction and the decisive fact

A harness was built that reproduces the deck's setup with `LayoutToNetlist`:
the same layers, `ptap_conn = tap & psdm - nwell`, an **empty** `sub =
polygon_layer` exactly as the deck declares it (sky130.lvs:867), nfet
extraction with `"W" => sub`, `connect(sub, ptap_conn)` (sky130.lvs:1630),
`connect_global(sub, name)` (sky130.lvs:1671), `join_net_names("*")`
(= the deck's `connect_implicit("*")`, sky130.lvs:1676) and `top_level_mode`.

It reproduces the messages exactly:

```
CONFIG tie=true sub_name=VGND join="*" toplevel=true
  log entries=3  MUST_CONNECT=3
  [Error] x3 Must-connect subnets of VGND of circuit
          sky130_fd_sc_hd__clkbuf_1 must be connected further up in the
          hierarchy - this is an error at chip top level
```

Two facts from that same run settle the case.

**(i) The top-level VGND net already contains everything.**

```
net VGND  name=VGND  ptap=12  met1=131
```

In the very extraction that emits the error, the top-level `VGND` net holds
all twelve substrate tap contacts and all 131 ground met1 shapes. There is no
top-level metal disconnection to find.

**(ii) The substrate node has no geometry.** Rename the substrate and it
separates cleanly:

```
sub_name=VSUBS:
  net $20     name=(none)   ptap=12  met1=131     <- the real ground network
  net VSUBS   name=VSUBS    ptap=0   met1=0       <- the substrate node
```

`VSUBS` is **empty**: zero taps, zero metal. It carries only nfet bulk
terminals. This follows directly from `sub = polygon_layer` being an empty
layer — `connect(sub, ptap_conn)` connects an empty layer to the taps and
therefore joins nothing.

Confirmed by direct experiment: toggling `connect(sub, ptap_conn)` on and off
changes nothing.

```
tie=true   -> MUST_CONNECT=3
tie=false  -> MUST_CONNECT=3
```

**Consequence.** In this deck's model the substrate is a floating logical node,
disjoint from all geometry by construction. The must-connect obligation created
by aliasing it to `VGND` can therefore **never** be satisfied by any layout, at
any tap density, no matter how the design is built.

---

## 7. Deep vs flat comparison

```
deep (production, run_mode=deep) : 3 must-connect, "Netlists match", exit 0
flat (run_mode=flat)             : 5 must-connect, "Netlists don't match", exit 1
```

Flat mode dissolves the cell hierarchy the comparison depends on, so its
mismatch is an artifact of the mode and not a result. It is recorded to close
the option, not as evidence. The meaningful comparison is §6's matrix, which
varies one modelling switch at a time while hierarchy is held fixed.

---

## 8. Failing vs clean instance comparison

The strongest control available: run the harness with **each master as top
cell**, removing placement from the picture entirely.

| Cell | must-connect standalone |
|---|---|
| `clkbuf_1` | 1 |
| `inv_1` | 1 |
| `nand2_1` | 1 |
| `nand3_1` | 1 |
| `nor2_1` | 1 |
| `dfrtp_4` | 1 |
| `xnor2_1` | 1 |
| `decap_3` | 1 |
| `a21oi_1` | 1 |

**`clkbuf_1` is not special.** Every tapless standard cell carries the same
obligation. The property that differs between a flagged and an unflagged
*instance* in a full design is therefore not a property of the cell at all —
KLayout reports representative instances of a per-circuit obligation, and which
representatives surface depends on the hierarchical arrangement. That is why
the reported master and count move with placement (E3) while the underlying
condition is universal.

This also retires the search for "the one property that differs when the
warning moves between instances": there is no such physical property. The
condition holds for all of them.

---

## 9. `lvs_sub=VGND` analysis

The hypothesis is confirmed by controlled experiment, not intuition.

| sub_name | `join_net_names` | top_level_mode | must-connect |
|---|---|---|---|
| `VGND` | `"*"` | true | **3 (Error)** |
| `VGND` | `""` | true | 0 |
| `VSUBS` | `"*"` | true | 0 |
| `VSUBS` | `""` | true | 0 |
| `VGND` | `"*"` | false | 3 (Warning) |

The condition appears **iff both**:

1. the substrate global net is given the same name as the cells' ground label
   (`-rd lvs_sub=VGND`), and
2. implicit joining by name is enabled (the deck's `connect_implicit("*")`).

`top_level_mode` only controls severity — matching the engine's documented
"must-connect warnings are turned into errors". `connect(sub, ptap_conn)` is
irrelevant (§6).

Where it enters production: `src/rtl2gdsagi/runner.py:790` passes
`-rd lvs_sub=VGND`. The existing comment records why — without it the extracted
side carries a `sky130_gnd` net the reference has no counterpart for, and every
cell mismatches. That is a **reference-netlist modelling gap**, and aliasing the
substrate onto `VGND` papers over it by merging the substrate into the ground
net by name.

---

## 10. Cell-variant analysis

Tested and **rejected**. The extracted database contains exactly one
`X(sky130_fd_sc_hd__clkbuf_1)` circuit — no `clkbuf_1$1`, `$2` or equivalent
variant identities. The previous report's "best-supported explanation" of
deep-mode cell-variant formation is wrong and is withdrawn. §8 supplies the
correct explanation: the obligation is universal across tapless cells, and only
representative instances are reported.

---

## 11. Minimal reproduction

Not a separate layout — the harness in §6 is the minimal reproduction, and it
is stronger than a synthetic cell would have been because it runs on the real
signed-off GDS with one switch varied at a time. Scripts live in the
investigation workspace (`hier.rb`, `bulk.rb`, `cell.rb`, `glob.rb`,
`conn2.rb`, `conn3.rb`); none are in the repository.

---

## 12. Causal experiments

| Experiment | Change | Must-connect | Flat connectivity | Interpretation |
|---|---|---|---|---|
| E3 | tap pitch 13 → 8 µm | 3 (clkbuf_1) → 1 (nand3_1) | unchanged, 1 component | Taps do not fix it; reported instance moves with placement |
| E5 | conservative L2N, reg8 | — | 1 net, 12/12 taps, 131 met1 | Ground metal + tap contacts are one component |
| E6 | same, reg_tap8 | — | 1 net, 18/18 taps, 137 met1 | Same, different layout |
| E7 | `run_mode` deep → flat | 3 → 5 | unchanged | Mode artifact; not evidence |
| **E8** | harness reproduction | **3, identical text** | top net VGND has ptap=12, met1=131 | The error is emitted while the top-level net already contains both |
| **E9** | `connect(sub, ptap_conn)` on → off | 3 → 3 | unchanged | The deck's substrate tie line joins nothing |
| **E10** | `sub_name` VGND → VSUBS | 3 → **0** | unchanged | Substrate node is empty (ptap=0, met1=0); name collision is the trigger |
| **E11** | `join_net_names` `"*"` → `""` | 3 → **0** | unchanged | Implicit name-joining is the other necessary condition |
| **E12** | `top_level_mode` true → false | 3 Error → 3 Warning | unchanged | Severity only |
| **E13** | each master as top cell | 1 each, 9/9 cells | — | The obligation is universal, not clkbuf_1-specific |

---

## 13. Exact KLayout-reported obligation

> Inside circuit `sky130_fd_sc_hd__clkbuf_1`, the net named `VGND` consists of
> two subnets that are not physically connected within the cell: **(a)** the
> labelled ground metal network (met1/li1/licon/mcon, label `VGND` on 68/5),
> and **(b)** the deck's global substrate node, reaching the cell through the
> nfet bulk terminals. These were joined *by name* under
> `connect_implicit("*")`. KLayout requires that nominal join to be made good
> by a physical connection higher in the hierarchy, and reports that it was
> not.

**Is that exact obligation satisfied?** No — and it cannot be. Subnet (b) is
the deck's `sub` pseudo-layer, which has no geometry (E10: `VSUBS ptap=0
met1=0`). Nothing in any layout can be physically connected to it. The
obligation is unsatisfiable by construction.

So the honest reading is neither "real PG defect" nor "benign warning". The
message is a true statement about a model in which the substrate is a floating
node, created by naming that node after a real net.

---

## 14. Root cause

```
extraction/configuration defect
```

Confidence: high for the mechanism — reproduced exactly, with necessary and
sufficient conditions isolated one variable at a time (E8–E13).

The chain, end to end:

1. The LVS reference netlist does not model the substrate/bulk node, so the
   extracted side's substrate net has no counterpart and every cell mismatches.
2. To make the comparison run, `runner.py:790` passes `-rd lvs_sub=VGND`,
   naming the global substrate after the ground net.
3. The deck declares `sub = polygon_layer` — an empty layer — so the substrate
   node holds no geometry, and `connect(sub, ptap_conn)` joins nothing (E9).
4. Inside every tapless standard cell, the labelled ground metal and the
   substrate node now share the name `VGND` while being physically disjoint.
5. `connect_implicit("*")` joins them by name — documented as joining "without
   need for a physical connection" — creating a must-connect obligation (E11).
6. `top_level_mode` renders it an error (E12).
7. The obligation is unsatisfiable, because subnet (b) has no geometry (E10).
   Adding taps cannot help (E3, E9).

**It is not a physical defect.** The ground metal and every tap contact are one
connected component (E5/E6), and the same extraction that raises the error
reports a top-level `VGND` net containing all 12 taps and 131 met1 shapes (E8).

### Remedy (identified, not implemented)

Fix the **reference construction**, not the gate and not the deck: build the
LVS reference so it carries the substrate/bulk node the extraction produces,
then stop passing `lvs_sub=VGND` and let the substrate keep its own name.

That removes the name collision, so no implicit join is made and no
must-connect obligation is created — and it makes the comparison *stronger*,
because bulk connectivity would then be compared rather than name-merged away.

This has **not** been implemented or validated. It changes production
verification code and requires a full rerun to confirm, which Phase 15
excludes at this stage. Until then the messages keep blocking.

---

## 15. `substrate_tie.py`

```
diagnostic value:      high - it is the measurement behind E5/E6, and it
                       correctly proves the tap-contact/ground-metal component
production-gate status: dead code; nothing imports it; 491/491 unaffected
safe to wire:          NO
```

Not safe to wire, and for a sharper reason than before: §4 and §13 show the
property it proves is **not** the property KLayout is asserting. It measures
tap-contact-to-metal connectivity; KLayout's obligation concerns the deck's
geometry-less substrate node. Those are different claims, so the semantic
equivalence that an override would require is not merely unproven — it is
**false**. The module must stay diagnostic.

---

## 16. Remaining P0

```
count: 1
IDs:   P0-07
```

`reg8` remains the evidence baseline; no new run, no new candidate.

---

# FINAL RESPONSE

## Tests

```
collected: 491
passed:    491
failed:    0
runtime:   34.64s
```

## Flat connectivity

```
reg8:      1 net, 12/12 taps, 131 met1 shapes, all 3 flagged instances inside it
reg_tap8:  1 net, 18/18 taps, 137 met1 shapes, flagged nand3_1 inside it
what this proves:      the tap contacts and the ground metal network are a
                       single connected component in both layouts
what this does not prove: anything about KLayout's must-connect obligation,
                       which concerns the deck's geometry-less substrate node
                       and not the tap contacts measured here
```

## Hierarchical finding

```
internal VGND subnets: 2 - (a) labelled ground metal (met1/li1/licon/mcon,
                       label VGND on 68/5), (b) the global substrate node
                       reaching the cell via nfet bulk terminals
parent-level merge:    the top-level VGND net already contains all 12 tap
                       contacts and all 131 ground met1 shapes, in the same
                       extraction that raises the error
exact unresolved obligation: subnet (a) and subnet (b) of VGND inside
                       sky130_fd_sc_hd__clkbuf_1 were joined by name under
                       connect_implicit("*") and must be joined physically
                       further up. They cannot be: subnet (b) is the deck's
                       sub = polygon_layer, which has no geometry at all
                       (measured: ptap=0, met1=0)
```

## Deep vs flat

```
deep: 3 must-connect, netlists match, exit 0
flat: 5 must-connect, netlists don't match, exit 1
interpretation: flat dissolves the hierarchy the comparison relies on, so its
                mismatch is a mode artifact, not a result. The informative
                comparison is the single-variable matrix at fixed hierarchy
```

## `lvs_sub=VGND`

```
role:     names the global substrate after the ground net, creating a name
          collision with every standard cell's VGND label. Necessary condition
          for the messages. Entered production at runner.py:790 to work around
          a reference netlist that does not model the substrate node
evidence: sub_name=VGND -> 3 must-connect; sub_name=VSUBS -> 0 (E10)
          join_net_names("*") -> 3; join_net_names("") -> 0 (E11)
          connect(sub, ptap_conn) on/off -> 3 either way (E9)
          top_level_mode only switches Warning/Error (E12)
```

## Cell variants

```
observed:            none - exactly one X(sky130_fd_sc_hd__clkbuf_1) circuit,
                     no $1/$2 variant identities
relation to failure: none. The previous variant-formation hypothesis is
                     withdrawn. Every tapless master reproduces the obligation
                     standalone (9/9 tested), so it is universal and KLayout
                     reports representative instances
```

## Root cause

```
classification: extraction/configuration defect
confidence:     high - exact reproduction, necessary and sufficient conditions
                isolated one variable at a time (E8-E13)
exact mechanism: the deck models the substrate as sub = polygon_layer, an empty
                layer with no geometry, so the substrate node is disjoint from
                all layout by construction. Passing lvs_sub=VGND names that
                node after the ground net; connect_implicit("*") then joins it
                to each cell's labelled ground metal by name, which KLayout
                records as a must-connect obligation to be discharged higher up.
                The obligation is unsatisfiable, because nothing can physically
                connect to a layer with no geometry - which is why adding taps
                moves the reported instance but never clears the condition
```

## substrate_tie.py

```
keep:                  YES - it is the E5/E6 measurement
wire diagnostically:   YES - safe, cannot change PASS/FAIL
allow to override LVS: NO
```

## Remaining P0

```
count: 1
IDs:   P0-07
```

## Recommendation

```
NOT READY FOR CODEX RE-AUDIT
```
