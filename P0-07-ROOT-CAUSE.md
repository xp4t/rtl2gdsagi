# P0-07 VGND Must-Connect Root-Cause Investigation

Investigation only. `reg8` was preserved unchanged; every experiment ran in a
separate workspace against copies of its artifacts.

No LVS message was suppressed or downgraded. No deck or PDK file was touched.
No API key was requested and no live model was run.

**Headline:** the physical question is answered. The three messages do **not**
report a real top-level connectivity failure — the substrate and the ground
metal network are provably one connected component, and every flagged instance
sits in it. What is *not* answered is why KLayout's deep-mode extraction still
emits the message once that join exists. Because the second half is unproven,
this is filed as **Outcome C — unresolved**, and P0-07 stays open. See §8.

---

## 1. Exact errors

All three come from KLayout's LVS engine (`libklayout_lvs.so.0.30`), reported
**in the top circuit `register`**, not inside the cell:

| # | Instance | Cell | Kind | Polygon (µm) |
|---|---|---|---|---|
| 1 | `register/sky130_fd_sc_hd__clkbuf_1[m0 22.08,27.2]` | clkbuf_1 | `must-connect` | (21.89,24.24)–(23.65,27.44) |
| 2 | `register/sky130_fd_sc_hd__clkbuf_1[m0 10.12,16.32]` | clkbuf_1 | `must-connect` | (9.93,13.36)–(11.69,16.56) |
| 3 | `register/sky130_fd_sc_hd__clkbuf_1[m0 23.92,16.32]` | clkbuf_1 | `must-connect` | (23.73,13.36)–(25.49,16.56) |

Body, verbatim and identical for all three:

```
Must-connect subnets of VGND of circuit sky130_fd_sc_hd__clkbuf_1 must be
connected further up in the hierarchy - this is an error at chip top level.
```

Each polygon is that instance's cell bounding box grown by 0.19 µm, so the
message localises the *instance*, not a specific subnet. The LVS y-coordinate
is the cell's top edge; DEF placement y is 2.72 µm lower (the cells are `FS`).

---

## 2. Physical connectivity trace

Cell VGND pin from the LEF: one PORT, one met1 `RECT 0.0 -0.24 1.38 0.24`.
Placed instances from `reg8`'s routed DEF, against the PDN's met1 FOLLOWPIN
rails on the same net:

| Instance | Placed | Orient | VGND pin band | Rail | Overlap |
|---|---|---|---|---|---|
| `clkbuf_0_i_clk` | (22.08, 24.48) | FS | y 26.96–27.44 | y=27.20, x 10.12–38.64 | **yes** |
| `clkbuf_1_0__f_i_clk` | (10.12, 13.60) | FS | y 16.08–16.56 | y=16.32, x 10.12–38.64 | **yes** |
| `clkbuf_1_1__f_i_clk` | (23.92, 13.60) | FS | y 16.08–16.56 | y=16.32, x 10.12–38.64 | **yes** |

All three abut their row neighbours with gap `+0.000`
(`<row start>`/`fill_4`, `dfrtp_4`/`dfrtp_4`, `nand2_1`/`fill_4`).

The full ground stack is present at every tap site. Flattened geometry at the
tap at (23.0, 10.88):

```
tap    65/44  (23.145,11.200)-(23.315,11.725)
psdm   94/20  (23.000,11.070)-(23.460,11.855)   covers the tap  -> ptap_conn
licon  66/44  (23.145,11.435)-(23.315,11.605)   inside the tap
li1    67/20  (22.540,10.795)-(25.760,11.705)   covers the licon
mcon   67/44  (23.145,10.795)-(23.315,10.965)   inside the li1
met1   68/20  (10.120,10.640)-(38.640,11.120)   the VGND rail, covers the mcon
```

So `tap → licon1 → li1 → mcon → met1 rail` is unbroken.

---

## 3. Failing vs clean comparison

Every `clkbuf_1` in `reg8` fails (3 of 3), so no same-master clean control
exists there. Against masters that never fail:

| Cell | li1 clusters | met1 | mcon | tap layer | flagged |
|---|---:|---:|---:|---:|---|
| `clkbuf_1` | 5 | 2 | 6 | **0** | **yes** |
| `buf_1` | 5 | 2 | 6 | 0 | no |
| `inv_1` | 4 | 2 | 6 | 0 | no |
| `nand2_1` | 5 | 2 | 6 | 0 | no |
| `dfrtp_4` | 19 | 5 | 56 | 0 | no |
| `decap_3` | 2 | 2 | 6 | 0 | no |
| `tapvpwrvgnd_1` | 2 | 2 | 2 | **2** | no |

Ruled out here:

* **"the cell has no internal substrate tap"** — no standard cell has one. Only
  `tapvpwrvgnd_1` carries tap-layer geometry (65/44); `inv_1`, `nand2_1` and
  `dfrtp_4` are all tapless and unflagged.
* **"fragmented ground geometry"** — `dfrtp_4` has 19 li1 clusters against
  clkbuf_1's 5 and is never flagged.
* **"far from a tap"** — see E3 below: the flagged instance in that run
  *abuts* a tap (0.46 µm) and is still flagged.

---

## 4. Cell-model analysis

`sky130_fd_sc_hd__clkbuf_1` is two inverters in series. Extracted and
reference topologies agree exactly:

```
extracted   M$1 pfet X   $3 VPWR VPB     reference  MMIP1 X  Ab VPWR VPB
            M$2 pfet VPWR A  $3  VPB                MMIP0 Ab A  VPWR VPB
            M$3 nfet X   $3 VGND VGND               MMIN1 X  Ab VGND VGND
            M$4 nfet VGND A  $3  VGND               MMIN0 Ab A  VGND VGND
```

`$3` is `Ab`. Both nfets carry source **and bulk** on VGND, and inside the
extracted cell circuit VGND is a single net (id 4) holding both:

```
D3 nfet  T(S 2) T(G 3) T(D 4) T(B 4)
D4 nfet  T(S 4) T(G 6) T(D 3) T(B 4)
```

So the must-connect condition is not visible as two separate nets in the
extracted cell circuit.

---

## 5. Extracted topology analysis

At top level all three instances attach to the **same** VGND net — position 3
of the extracted pin order `VPB X VGND VPWR A`:

```
X$110 $17 $40 VGND $17 i_clk  sky130_fd_sc_hd__clkbuf_1
X$184 $17 $39 VGND $17 $40    sky130_fd_sc_hd__clkbuf_1
X$186 $17 $44 VGND $17 $40    sky130_fd_sc_hd__clkbuf_1
```

There is exactly one `VGND` name in the extracted netlist (161 occurrences, no
`VGND_1`-style variants), `.SUBCKT register` exposes `VGND` as a port, and the
comparison itself succeeds: 192 circuits cross-referenced, "Netlists match".

---

## 6. KLayout must-connect semantics

The message template lives in `libklayout_lvs.so.0.30`, in three variants. The
SKY130 deck contains no such string, so this is engine behaviour, not a
foundry rule.

The structural fact is in the database:

```
G(l1 VGND)
```

`G(...)` is a **global net declaration**: layer `l1`, the substrate, is
globally connected under the name `VGND`. That comes from the deck's
`connect_global(sub, substrate_name)` (sky130.lvs:1671) combined with the
`-rd lvs_sub=VGND` this flow passes.

So `VGND` denotes two things at once — the ground metal network and the global
substrate. Inside a tapless standard cell those are separate geometry sharing
one name, joined only where a tap cell exists, i.e. above the cell. That is
precisely the situation the message describes: "must be connected further up
in the hierarchy".

The deck's ground chain (sky130.lvs:971, 1630–1640):

```
ptap_conn = tap.and(psdm).not(nwell).not(diff_res).not(diff_cut).not(npnid).not(pnpid)
connect(sub, ptap_conn); connect(ptap_conn, licon); connect(licon, li_con)
connect(li_con, mcon);   connect(mcon, met1_con);   connect(met1_con, via1) ...
```

---

## 7. Controlled experiments

| # | Variable | Before | After | What it shows |
|---|---|---|---|---|
| **E1** | `lvs_sub=VGND` → omitted | 3 must-connect, netlists **match** | **0** must-connect, netlists **don't match** | The condition exists only because the substrate is aliased to the ground net's name. Without the alias every cell gains a 6th pin (`sky130_gnd`) the reference has no counterpart for. Not a fix — it trades three warnings for a comparison that fails outright. |
| **E2** | `tapcell_distance_um` 13 → 4 | 3 | run aborted at **placement** | Inconclusive; the variable could not be isolated at 4 µm. |
| **E3** | `tapcell_distance_um` 13 → 8 | 3 (clkbuf_1 ×3) | **1** (`nand3_1` ×1) | Decisive against the cell-property and the tap-distance theories: a *different master* is flagged, and the survivor **abuts a tap at 0.46 µm**. Netlists still match. |
| **E4** | no follow-pin rails → follow-pin rails | 8 across 5 masters | 3 on 1 master | Historical. Previously read as "the messages track genuine PG topology"; E3 and E5 show the set is re-drawn by placement, so this is placement sensitivity, not a connectivity gradient. |
| **E5** | conservative L2N connectivity proof on the signed-off GDS | — | **1 net, 12/12 taps, 131 met1 shapes; all 3 flagged instances inside it** | The substrate and the whole ground metal network are one connected component. See §7.1. |
| **E6** | same proof on the E3 layout | — | **1 net, 18/18 taps, 137 met1 shapes; the flagged `nand3_1` inside it** | Both layouts are fully tied, yet they report different messages. |
| **E7** | `run_mode=flat` vs `deep` | deep: 3, match | flat: 5, mismatch | Flat mode dissolves the cell hierarchy the comparison depends on, so its mismatch is an artifact of the mode, not a result. Recorded to close the option, not as evidence. |

### 7.1 The connectivity proof (E5/E6)

Run with KLayout's own `LayoutToNetlist` over the same GDS that was signed
off, declaring the deck's ground chain:

```
ptap_conn = tap(65/44) & psdm(94/20) - nwell(64/20)
ptap_conn -> licon -> li -> mcon -> met1 -> via1 -> met2 -> ... -> met5
```

Result on `reg8`:

```
nets carrying substrate taps : 1
tap shapes in that net       : 12  (of 12 in the layout)
met1 shapes in that net      : 131
probe (21.89,24.24)-(23.65,27.44) in ground net : true
probe  (9.93,13.36)-(11.69,16.56) in ground net : true
probe (23.73,13.36)-(25.49,16.56) in ground net : true
```

**Why this is authoritative and not merely suggestive.** The model declares
strictly *fewer* `connect()` relations than the full deck — it omits the
nsd/psd/poly paths and uses the `*_con` layers undivided. Removing connect
relations can only fragment nets further; it can never merge two nets the full
deck would keep apart. So a single component under this reduced model implies
a single component under the full deck. The proof is one-sided in the safe
direction.

An earlier version of this test stopped at met1 and found the taps split
across 6 nets. That was the model's fault, not the layout's: the rows join
through via1→met2→…→met5 straps. With the stack complete it is one net. The
intermediate result is recorded here because it is exactly the kind of
under-modelling that would have produced a confident wrong answer.

---

## 8. Root cause

```
Outcome C — UNRESOLVED
```

### What is now established

The physical claim the message makes is **false for this layout**. The
substrate taps and the ground metal network are one connected component
(E5/E6), all three flagged instances lie inside it, the full `tap → licon1 →
li1 → mcon → met1` stack is present at every tap (§2), and the netlist
comparison agrees (§5).

The mechanism that *creates* the condition is identified: aliasing the
substrate to the name `VGND` (§6) makes one name denote both the global
substrate and the ground metal, which inside a tapless cell are separate
geometry joined only above the cell.

Positively ruled out:

* not a fixed property of `clkbuf_1` — E3 flags a different master entirely;
* not tap distance — E3's survivor abuts a tap at 0.46 µm;
* not a met1 disconnection — all pins overlap a ground rail;
* not an abutment gap — all `+0.000`;
* not a reference-netlist defect — topologies agree, comparison matches;
* not a deck rule — the message is in the KLayout engine binary;
* not a missing internal tap — no standard cell has one, most are unflagged;
* not fragmented cell ground geometry — `dfrtp_4` is worse and unflagged;
* **not a real top-level ground disconnection** — E5/E6.

### Why this is still Outcome C and not Outcome B

Outcome B requires authoritative evidence that the message is benign under the
exact PDK, deck hash, KLayout version, cell and context. I have proof that the
*connectivity condition holds*. I do not have proof of **why KLayout's
deep-mode extraction reports the condition anyway** once the join exists above
the cell.

The best-supported explanation is deep-mode cell-variant formation: KLayout
builds per-instance variants from local context, and the global-vs-local
`VGND` name collision leaves the condition unresolved in some variants. That
is consistent with every observation, including the ones that break the other
theories — but it is inferred from external behaviour, not demonstrated. The
`.lvsdb` does not expose per-instance subnet membership, and I did not find a
supported way to extract it.

Without that, I cannot characterise when an exception would be *wrong*, and
the task's own instruction is not to guess. So the messages keep blocking.

---

## 9. Fix

**None applied. The gate is unchanged and still blocks.**

`lvs_sub=VGND` was deliberately *not* removed even though E1 shows it makes the
messages disappear: it would trade three explicit warnings for a netlist
comparison that fails outright, which is strictly worse evidence.

### Prepared but not wired in

`src/rtl2gdsagi/checks/substrate_tie.py` (new) implements the E5/E6 proof as a
reusable check: it emits the KLayout script, parses the result, binds it to the
GDS by sha256, and exposes `SubstrateTieProof.proved`, which is true only when
the layout has tap geometry, **exactly one** net carries every tap, that net
holds met1, and every flagged instance's message polygon is reached by it. Any
other state — no proof, unreadable proof, proof for a different layout,
fragmented taps, an unprobed instance — leaves `proved` false.

It is **not connected to the LVS gate.** The edit that would have wired it into
`src/rtl2gdsagi/checks/klayout_lvs.py` was refused by this session's permission
classifier, which guards edits to the LVS checker. I did not work around that.
The module is therefore dead code today: `parse_lvs_report` neither imports nor
consults it, and the must-connect class blocks exactly as before.

**This is a decision for the owner, not for me.** Wiring it in would turn the
must-connect class from an unconditional block into a block that clears only
when an independent geometric proof passes on the same GDS, on an approved
deck. That is an *added* proof obligation rather than a downgrade, and it fails
closed. But it is a change to the gate that exists to catch PG defects, and the
standing instruction is that a clean result obtained by weakening LVS is worse
than an open P0. It should be reviewed on its merits and, if accepted, landed
with the negative tests listed in §10.

---

## 10. Regression protection

In force now, unchanged:

* `klayout_lvs` blocks on the must-connect message class specifically, not on
  severity `W` — pinned by
  `test_only_the_named_condition_blocks_not_severity_w_in_general`;
* the real register `.lvsdb` fixture asserts `clean is False`, sidecar
  `verdict: fail`;
* `test_lvs_real_report_blocks_on_unresolved_must_connect` fails if the rule is
  weakened.

Required *before* `substrate_tie` may gate anything, none of which exist yet:

* no proof recorded → must-connect still blocks;
* proof whose `gds_sha256` differs from the checked GDS → blocks;
* proof with `nets_carrying_taps != 1` → blocks;
* a flagged instance with no corresponding probe → blocks;
* a must-connect message outside `SUBSTRATE_MESSAGE_RE` → blocks regardless of
  the proof;
* an unapproved deck sha256 → blocks regardless of the proof.

---

## 11. Test baseline

```
before investigation:  491 collected, 491 passed, 0 failed/skipped/xfailed
after  investigation:  491 collected, 491 passed, 0 failed/skipped/xfailed  (37.41 s)
```

The second figure was measured after all experiments and before
`substrate_tie.py` was added. **The suite has not been re-run since that file
was created**, because the permission classifier also refused the test
invocation. The module is additive and nothing imports it, so it cannot affect
the existing tests — but that is reasoning, not a measurement, and it should be
confirmed with `python -m pytest -q` before anything else is built on it.

---

## 12. Register result and remaining P0

```
run:                       reg8 (preserved; no fresh reference run performed)
candidate:                 none - signoff never runs
LVS must-connect errors:   3
certification:             NOT CLEAN

remaining P0 count: 1
remaining P0 IDs:   P0-07
```

A fresh full reference run was not attempted: its precondition is P0-07
resolved, and P0-07 is not resolved.

```
NOT READY FOR CODEX RE-AUDIT
```
