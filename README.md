# rtl2gdsagi

**Turn Verilog into a real chip layout — with checks that don't lie to you.**

If you've written Verilog that works on an FPGA and wondered "could this be an
actual chip?", this tool takes you the rest of the way: from your `.v` files to
a GDSII layout on the open-source SkyWater 130 nm process, running every
signoff check a real tapeout needs.

You need to know basic Linux. You do **not** need to know TCL, OpenROAD,
KLayout, or how any of the EDA tools work. The tool writes all of that for you.

```bash
rtl2gdsagi run --rtl ~/my_design/rtl --top my_top
```

---

## Table of contents

1. [What this actually does](#1-what-this-actually-does)
2. [Install](#2-install)
3. [Your first run](#3-your-first-run)
4. [Reading the output](#4-reading-the-output)
5. [The stages, in plain language](#5-the-stages-in-plain-language)
6. [When something fails](#6-when-something-fails)
7. [Configuration](#7-configuration)
8. [Why you can trust the results](#8-why-you-can-trust-the-results)
9. [Current status — what works, what doesn't](#9-current-status)
10. [For developers](#10-for-developers)

---

## 1. What this actually does

Getting from Verilog to a chip layout normally means running about eight
different programs, each with its own scripting language, in the right order,
with the right settings for your process technology. Most of the difficulty
isn't the design — it's the plumbing.

This tool is the plumbing. It:

- **writes every tool script for you** from a small set of settings, so you
  never hand-write TCL;
- **runs the tools in order**, carrying files between them;
- **reads the reports** and decides whether each step really passed;
- **asks Claude to diagnose failures** and propose a fix, then applies it within
  strict limits and retries;
- **refuses to declare success** unless every check genuinely passed.

That last point is the reason this project exists. Read
[section 8](#8-why-you-can-trust-the-results) — it is the most important part.

### What you provide

Just your RTL, and the name of your top module. That's it.

Timing constraints, floorplan settings, clock tree settings, DRC invocations —
all generated. If you *want* to control them you can
([section 7](#7-configuration)), but you don't have to.

---

## 2. Install

### 2.0 The short way

```bash
git clone https://github.com/xp4t/rtl2gdsagi.git
cd rtl2gdsagi
./setup.sh
```

That installs everything below, skipping whatever you already have, and prints
what it found. Re-run it any time. To see the state without changing anything:

```bash
./setup.sh --check
```

```
Tools
  ✓ verilator
  ✓ iverilog
  ✓ yosys
  ✓ klayout
  ✓ eqy
  ✓ sby (in venv)
  ✓ z3 (in venv)
  ✓ openroad + sta (via docker image)

PDK
  ✓ sky130A at ~/.volare/sky130A
```

The rest of this section explains what each piece is, if you would rather
install by hand or something went wrong.

### 2.1 The tools

You need these. On Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y verilator iverilog yosys klayout python3-venv git
```

**OpenSTA** (timing analysis) and **OpenROAD** (place & route) are not in
apt. The easiest route is Docker, which this tool uses automatically:

```bash
sudo apt-get install -y docker.io
sudo usermod -aG docker $USER      # then log out and back in
docker pull ghcr.io/the-openroad-project/openlane:ff5509f65b17bfa4068d5336495ab1718987ff69
```

If you have `openroad` and `sta` installed natively, they're used instead.

**eqy** proves your gate netlist still means the same thing as your RTL. Without
it the flow runs, but signoff refuses to certify — it will not assume something
it could not check. Install it plus a solver:

```bash
# eqy (equivalence checker)
git clone https://github.com/YosysHQ/eqy && cd eqy && make && sudo make install

# sby + z3 give it a stronger proof engine for sequential logic
git clone https://github.com/YosysHQ/sby
cd sby && make install PREFIX=/path/to/rtl2gdsagi/.venv
/path/to/rtl2gdsagi/.venv/bin/pip install click z3-solver
```

Installing `sby` and `z3` into the same virtualenv as this tool is deliberate:
they are found automatically, even if you never activate it.

### 2.2 The SKY130 process design kit

A PDK is the manufacturer's description of what you're allowed to build:
transistor models, cell layouts, spacing rules. SkyWater's 130 nm PDK is
open source.

```bash
pip install volare
volare enable --pdk sky130 bdc9412b3e468c102d01b7cf6337be06ec6e9c9a
```

This lands in `~/.volare/sky130A` and is found automatically.

### 2.3 This tool

```bash
git clone https://github.com/xp4t/rtl2gdsagi.git
cd rtl2gdsagi
python3 -m venv .venv
.venv/bin/pip install -e .
```

### 2.4 Your Claude API key

Only needed for the self-healing. Without it, use `--no-api` and the flow stops
at the first failure with a report instead of trying to fix it.

```bash
export ANTHROPIC_API_KEY=sk-ant-...      # put this in your ~/.bashrc
```

The key is read from the environment when a call is made. It is never written
into a config file, a log, or your run directory.

### 2.5 Check everything is working

```bash
.venv/bin/rtl2gdsagi doctor
```

```
tools:
  verilator   ok
  iverilog    ok
  yosys       ok
  eqy         ok
  sta         ok
  openroad    ok
  klayout     ok

pdk sky130A:
  root      /home/you/.volare/sky130A
  liberty   ok   .../sky130_fd_sc_hd__tt_025C_1v80.lib
  ...
  corners   18

api:
  ANTHROPIC_API_KEY set
  model             claude-opus-4-8
```

Anything `MISSING` tells you which gate it disables. Fix those before running.

---

## 3. Your first run

### 3.0 Start with the example

Before pointing this at your own design, run the one that ships with it. If this
works, your toolchain is good and anything that goes wrong afterwards is about
your design rather than your setup.

```bash
.venv/bin/rtl2gdsagi run --config examples/register/register.yaml --no-api
```

`examples/register/` is an 8-bit register — one clock, one reset, a
self-checking testbench. It takes a few minutes.

`examples/counter/` is a step up: a counter with load and enable, and a
testbench that checks reset, counting, hold, load, overflow and wraparound.
Worth reading as a model for writing your own self-checking testbench. Note
that it currently trips the equivalence checker — see
[section 9](#9-current-status), that is a known limitation of the tool, not a
bug in the design.

### 3.1 Requirements for your design

- Plain Verilog or SystemVerilog in one directory
- **Synthesisable** — no `#10` delays, no `initial` blocks for logic, no
  `$display` in the design itself (testbenches are fine, keep them separate)
- No FPGA-vendor primitives (`BUFG`, `IBUF`, Xilinx/Altera IP blocks). Those
  are FPGA parts and don't exist in an ASIC.
- Memories inferred from `reg [W:0] mem [0:N]` are fine if small. Large
  memories need a real SRAM macro, which is beyond a first run.

### 3.2 Try it

```bash
.venv/bin/rtl2gdsagi run --rtl ~/my_design/rtl --top my_top
```

You'll see each stage as it runs:

```
[lint] stage starting  (gate=hard tool=verilator)
[lint] stage ok after 1 attempt(s)
[sdc] SDC valid: 2 clock(s) constrained
[synthesis] synthesis clean: 929 cells, 8945um2
[floorplan] stage ok after 1 attempt(s)
...
```

A small design takes 15–30 minutes, most of it in routing.

### 3.3 Try it without running any tools first

Worth doing before a real run — it generates every script and stops:

```bash
.venv/bin/rtl2gdsagi run --rtl ~/my_design/rtl --top my_top --dry-run --no-api
```

Then read `runs/<timestamp>/stages/*/`. Those are real, working TCL scripts.
If you're learning the flow, they're a good place to start.

---

## 4. Reading the output

Every run creates a timestamped directory:

```
runs/2026-08-12T18-30-00Z/
├── run.log              human-readable log
├── run.jsonl            same thing, machine-readable
├── run_state.json       what passed, what failed, how many attempts
├── signoff.json         the final verdict bundle
├── failure_report.md    written whenever the run doesn't finish clean
├── work/rtl/            a copy of your RTL (your originals are never touched)
├── stages/
│   ├── 01_lint/         generated script, tool log, parsed results
│   ├── 04_synthesis/    ← your gate-level netlist lives here
│   ├── 12_routing/      ← the routed layout
│   └── 15_gdsout/       ← your GDSII
└── checkpoints/         saved state, used to roll back and retry
```

Check status any time:

```bash
.venv/bin/rtl2gdsagi status runs/2026-08-12T18-30-00Z
```

### Exit codes

| code | meaning |
|---|---|
| 0 | signoff clean |
| 1 | error |
| 2 | bad command line or config |
| 3 | stopped and is asking a human — read `failure_report.md` |
| 4 | ran out of retry budget |
| 5 | something tried to cross a safety boundary |

---

## 5. The stages, in plain language

Run `rtl2gdsagi stages` to see them. What each one is for:

| stage | what it does | why you care |
|---|---|---|
| `characterize` | reads your RTL, finds clocks and memories | picks sensible starting settings |
| `lint` | Verilator structural check | catches width mismatches, latches, unconnected ports |
| `sim` | runs your testbenches | lint says it's well-formed; simulation says it's *correct* |
| `sdc` | writes timing constraints | tells the tools how fast your clocks run |
| `synthesis` | Verilog → logic gates | your design becomes real standard cells |
| `lec_synth` | proves gates == RTL | mathematical proof nothing changed meaning |
| `sta_pre` | early timing estimate | advisory only — a guess before layout exists |
| `floorplan` | chip outline, cell rows, pin placement | decides how big your chip is |
| `pdn` | power distribution network | gets power to every cell |
| `placement` | positions every cell | closer-together = faster, but harder to wire |
| `cts` | clock tree synthesis | clock must reach every flip-flop at the same time |
| `sta_postcts` | timing with a real clock tree | **first point hold timing is meaningful** |
| `routing` | draws all the wires | the slow one |
| `extraction` | measures real wire resistance/capacitance | wires have delay; now we know how much |
| `sta_signoff` | timing with real wire data | **the authoritative timing check** |
| `gdsout` | writes the GDSII layout file | the file a foundry would fabricate |
| `drc` | design rule check | is this layout physically manufacturable? |
| `lvs` | layout vs schematic | does the layout match the netlist? |
| `antenna` | antenna rule check | prevents damage during manufacturing |
| `lec_route` | proves final netlist == RTL | layout steps changed the netlist; re-verify |
| `signoff` | re-checks everything against one GDS | the final gate |

### Hard vs advisory

Some gates **block** — the flow stops. Others are **advisory** — recorded but
never blocking. `sta_pre` is advisory on purpose: it's an estimate made before
any cell has been placed, and treating a guess as authoritative would stop good
designs for no reason.

---

## 6. When something fails

Read `failure_report.md`. It tells you the stage, what class of failure it was,
what evidence led there, and what the tool is not allowed to change.

### Common ones

**"top module not found"** — check `--top` matches your module name exactly.

**"verilator reported N error(s)"** — real RTL errors. Fix them; the messages
point at line numbers.

**"unmapped cells remain"** — you used something that doesn't map to standard
cells, usually an FPGA primitive or a large inferred memory.

**"the design has undefined clocks"** — the clock port wasn't recognised.
Name it something containing `clk` or `clock`, or set the period yourself in a
config file.

**"signoff hold WNS is negative"** — real hold violations found with real wire
data. This is a genuine result, not a tooling problem. The tool routes this to
the clock-tree stage; it will never "fix" it by editing your RTL, because
that's not how hold violations are fixed.

**"N violations in M categories"** — real DRC violations. The report lists them
by rule so you can see which rule and how many, and for the rules this project
has tracked down before it also says what usually causes them. `m2.x` is the
one a first design is most likely to hit: "floating met2" almost always means a
**top-level port that nothing in your RTL drives or reads**. Synthesis deletes
the logic, the port survives, and its pin is streamed out as metal connected to
nothing. Check the net in `stages/12_routing/*.routed.def` — if it reads
`- name ( PIN name ) + USE SIGNAL ;` with no instance pins after it, that is
the one. Delete the unused port or connect it.

**"skipping lec_synth: no equivalence prover found"** — install `eqy`. Signoff
will refuse to certify without it rather than assume your netlist is correct.

**"N of M testbench(es) failed"** — every testbench is run, so you get the whole
picture at once rather than one failure at a time. Look in
`stages/02_sim/<name>.compile.log` and `<name>.sim.log`. Common causes: the
testbench was written against an older revision of the RTL (you'll see
`port 'x' is not a port of uut`), or it uses constructs Icarus rejects. If your
testbenches live somewhere else, set `ir.sim.testbench_dir`.

Simulation is a hard gate on purpose: lint proves your design is well-formed,
not that it is *correct*, and a chip you cannot verify is a chip you should not
tape out.

### Resuming

```bash
.venv/bin/rtl2gdsagi run --rtl ... --top ... --resume-from routing
```

**This does not restore a previous run.** It only chooses where the stage loop
starts. Every run builds a fresh artifact ledger, so unless the earlier stages'
outputs are already in *this* run directory the stage stops immediately with:

```
required input is unavailable: "renderer needs input artifact 'cts_def'"
```

That is the intended behaviour rather than a bug — running a stage against
artifacts nobody produced is how a flow ends up verifying the wrong thing — but
it does mean persistent resume across separate runs is **not implemented**. The
switch is useful for re-entering a run directory that already has the earlier
outputs, and for nothing else.

---

## 7. Configuration

You don't need a config file. When you want one:

```yaml
top: cam_top
rtl: ~/ov7670/rtl

pdk:
  name: sky130A          # root is auto-discovered

retry_limit: 3           # attempts per stage

stages:                  # how many attempts each stage gets
  routing: {retry_limit: 5}
  drc:     {retry_limit: 1}

ir:                      # the actual tool settings
  floorplan:
    core_utilization: 0.35
  sim:
    testbench_dir: ~/OV7670-camera-asic/tb
```

Anything under `ir:` is validated when the file loads, so a typo is reported
straight away with the list of valid fields — not halfway through a 20-minute
run.

```bash
.venv/bin/rtl2gdsagi run --config myrun.yaml
```

To see every setting the tool (and Claude) may change:

```bash
.venv/bin/rtl2gdsagi schema             # everything
.venv/bin/rtl2gdsagi schema floorplan   # one section
```

Useful knobs when a run struggles:

| setting | try this |
|---|---|
| `floorplan.core_utilization` | **lower** (0.35) if routing fails — more room for wires |
| `placement.target_density` | lower if congested |
| `routing.droute_iters` | raise (48) if routing nearly converges |
| `sdc.default_clock_period_ns` | raise if timing fails — a slower clock is easier |
| `cts.target_skew_ns` | raise for multiple async clock domains |
| `sim.testbench_dir` | set when testbenches live outside your RTL directory |
| `pdn.strap_offset_um` | **lower** on a small design — see below |
| `pdn.core_ring` | set `false` if a small die can't fit a power ring |
| `lec.induction_steps` | raise if equivalence comes back "unknown" |
| `routing.insert_filler` | leave on — see the warning below |
| `pdk.filler_prefixes` | narrow the filler set if one cell type causes DRC |

`routing.insert_filler` is on by default and should stay that way. Turning it
off is not a small trade: on the OV7670 design it takes signoff DRC from 1
violation to **580** (397 × `nwell.2a`, 66 × `hvtp.2`, 58 × `nwell.1`,
58 × `hvtp.1`). Without filler the nwell is a row of islands rather than one
continuous strip. The switch exists because it makes that cost measurable, not
because it is a reasonable thing to disable.

`pdk.filler_prefixes` chooses *which* cells fill the gaps — by default anything
named `fill*` or `decap*`:

```yaml
pdk:
  name: sky130A
  filler_prefixes: [fill]   # skip the decaps
```

Useful if a particular filler cell turns out to be implicated in a DRC
violation. Be sure it really is implicated first: on this flow `decap_*` cells
looked responsible for 17 of 26 `li.3` violations and were entirely innocent —
they were just where the router had room to detour.

### Small designs

A first design is usually tiny, and a few defaults are sized for a real chip.
The symptom is `PDN-0185: insufficient width to add straps` — the power grid
does not fit inside a die that small. Fix it with:

```yaml
ir:
  pdn:
    strap_offset_um: 1.0
    strap_pitch_um: 10.0
    core_ring: false
  floorplan:
    core_utilization: 0.30    # a bigger die is also easier to route
```

---

## 8. Why you can trust the results

This is the part that matters, and it's why the project was built.

**The problem:** it is very easy for an EDA flow to report "clean" when it has
checked nothing. Not through malice — through ordinary mistakes that produce
convincing, well-formed, entirely empty results.

Every one of these is a real thing that happened on real hardware, and each is
now blocked:

### The check ran against the wrong file

A DRC run came back with *"No DRC violations were found"*. It had checked
pre-merge macro layouts instead of the final streamed-out GDS. The real layout
had **4,743 violations**.

KLayout's report cannot help you here — it writes the "which file did I read"
field *empty*. So the tool tracks it: the exact SHA-256 of the GDS is recorded
when it's handed to KLayout, and every signoff report must agree on that hash.
On top of that, `gdsout` refuses to hand over a layout that still has
unresolved cell references — the structural signature of a pre-merge file.

That real 4,743-violation report is in the test suite. If a change ever makes
the parser call it clean, the tests fail.

### The check ran, but had no rules loaded

The SKY130 DRC deck gates every rule group behind a switch (`feol`, `beol`,
`offgrid`, `floating_met`). Invoke it without them and it loads fine, writes a
perfectly well-formed report, and checks **nothing**. Zero violations. Looks
clean.

So the tool passes every switch explicitly, *and* refuses any report that
declares zero rule categories.

### The check never ran at all

A real LVS deck on this machine ends with:

```ruby
logger.info('INFO : Congratulations! Netlists match.')
logger.info('INFO : (17,018 devices and nets verified successfully)')
```

There is no `compare` call gating those lines, and the device count is a
literal. It's a `print` statement. Any checker that greps the log for "Netlists
match" passes that deck forever.

So an LVS verdict here requires the exit code, the log, **and** the `.lvsdb`
cross-reference to agree, and a deck with no reachable failure branch is
rejected before it runs.

### The check reported something the parser didn't recognise

OpenROAD prints `[INFO ANT-0002] Found 1 net violations.` An earlier version of
this tool's pattern expected different wording, scored zero, and — because the
word "antenna" appeared in the log — its "did anything run?" guard was
satisfied too. **A real antenna violation would have passed.** Found by reading
actual tool output, now pinned by a test using the exact strings.

### The safety rules

Three things follow from all this, and they're enforced in code rather than
requested politely:

**Claude never decides whether something passed.** The orchestrator runs the
tool, parses the report, and produces the verdict. Only then is the model called,
and only to diagnose. There is no code path from a model response to a verdict.

**Claude cannot weaken a check.** Its only writable surface is a schema of typed
settings. Run `rtl2gdsagi schema drc` — the only fields are `threads` and
`deep_mode`. "Skip this rule" isn't rejected; it's *unrepresentable*.

That property is structural, but it is not self-enforcing, and an independent
audit found three places where it had leaked. All three are now closed and
regression-tested, and they are worth knowing about because they show the shape
of the problem:

- the timing **guardband** was applied backwards, so asking for a *larger*
  margin made worse timing pass;
- the **clock period** could be lengthened in response to a timing failure,
  which moves the target rather than fixing the design;
- the model's choice of *which stage to roll back to* overrode the deterministic
  policy, including naming a stage after the failure — which skips the stages
  in between.

The lesson is that "the model cannot construct a verdict" is a much weaker
guarantee than "the model cannot change what gets measured".

**Some things are never touched.** Your original RTL (edits go to a copy), the
PDK, and the signoff decks are read-only. Timing problems never result in RTL
edits — hold violations are a clock-tree problem, and no real chip flow fixes
them by rewriting your logic.

---

## 9. Current status

Honest picture, tested on a real design (an OV7670 camera controller, 929 cells)
against the real SKY130 PDK.

### What an independent audit found

This project has been through several rounds of independent review, and the
central finding of the first was correct: several checks could report a pass on evidence that
was missing, one-sided, self-contradictory, or never parsed at all. The worst
was that **the routing violation parser matched nothing in a real OpenROAD log**
— it was written for `violations: 0` when the tool writes `violations = 0`, so
every routing stage in every real run passed without ever reading a number.

All of the false-clean paths those reviews found are now closed and covered by
tests, and the numbers in this section were re-measured afterwards. Each defect
has a named regression in `tests/` -- see `test_audit_regressions.py`,
`test_codex_p0_regressions.py`, `test_spef_identity.py`, `test_evidence_lineage.py`
and `test_pdn_contract.py` -- so the record of what was wrong lives in the tests
that would fail if it came back.

Two limits are worth stating up front, because they bound everything below:

- **Timing uses a single typical corner.** There is no MCMM, no OCV, and the
  constraints are generated rather than reviewed. Treat the timing numbers as
  "this flow's OpenSTA result", not as signoff timing.
- **The self-healing loop has never run against a live model.** Every preserved
  run used `--no-api`. The retry/rollback machinery is unit-tested against a
  scripted agent; autonomous remediation of a real failure is **not**
  demonstrated.

### Working end to end

All 21 stages run against the real PDK, and the `register` example completes
every one of them:

`characterize` · `lint` · `sim` · `sdc` · `synthesis` · `lec_synth` ·
`sta_pre` · `floorplan` · `pdn` · `placement` · `cts` · `sta_postcts` ·
`routing` · `extraction` · `sta_signoff` · `gdsout` · `drc` · `lvs` ·
`antenna` · `lec_route` · `signoff`

On the `register` example: the testbench compiles, runs and self-checks;
equivalence is formally **proved**; timing is met with real extracted
parasitics; routing converges to **0 violations**; and signoff DRC comes back
**clean — 0 violations across 211 active rule categories**.

On the OV7670 design signoff DRC reports exactly **1** violation, and it is a
finding about the RTL rather than about the layout: `m2.x`, "floating met2".
The design declares an input port, `i_sda_in`, that nothing reads. Synthesis
removes the logic behind it, the port survives into the layout, and its pin is
streamed out as a piece of metal connected to nothing. The routed DEF says so
plainly — `- i_sda_in ( PIN i_sda_in ) + USE SIGNAL ;`, no instance pins at
all. Fix the RTL and it goes away.

On the larger OV7670 design (939 cells) everything through `gdsout` also runs —
routing converged 870 → 152 → 80 → 19 → 0, and extraction produced an 884 KB
SPEF over 967 nets.

### What the flow found on that design

Timing across the three checkpoints:

```
sta_pre       setup +5.955   hold +0.109      estimate, advisory
sta_postcts   setup +5.224   hold +0.061      real clock tree
sta_signoff   setup +4.914   hold -0.170      real wire parasitics  ← blocks
```

Hold looks comfortable at both early checkpoints and is genuinely violated once
real wire data exists. **A flow without a post-route timing check would have
shipped that.**

Reporting it was not enough — the flow could see the violation and had no way
to fix it. Hold repair now runs inside `routing`, and where it runs is the
whole trick. Run at CTS time it finds nothing: with placement-based estimates
OpenROAD reports "No hold violations found" and hold reads +0.058, because the
wire delay that causes the problem does not exist yet. Run after
`detailed_route` and it is too late to wire up the buffers it wants to add. It
goes after `global_route`, with `estimate_parasitics -global_routing` — close
enough to final to expose the problem, early enough that the detailed route
afterwards can connect the fix:

```
[INFO RSZ-0046] Found 120 endpoints with hold violations.
[INFO RSZ-0032] Inserted 1 hold buffers.
```

Signoff hold went from **−0.124 ns (TNS −10.28)** to **+0.094 ns, TNS 0.0**,
and `sta_signoff` passes.

### Signoff DRC: a clean zero, and how two fake ones got there first

On the `register` example the real SKY130 runset now reports **0 violations**
across 211 active rule categories.

That number was also "0" a while ago, and that zero was a lie — produced by
this flow's own signoff step. Worth reading, because it is the exact failure
mode the project exists to prevent, and it very nearly shipped.

The stream-out was not passing a **layer map** to KLayout's LEF/DEF reader.
Without one the reader numbers DEF geometry sequentially, so routing landed on
`3/0`, `5/0`, `7/0` instead of SKY130's `li1 67/20`, `met1 68/20`,
`met2 69/20`. The GDS opens correctly in a viewer. DRC runs, loads all 211 rule
categories, and finds nothing wrong — because it inspects real layer numbers
and **never saw a single routing wire**. It was checking only the standard
cells, whose geometry came from the cell GDS with correct layers all along.

It also explains why LVS extracted a top cell with almost no pins.

Two things changed. The stream-out now passes the PDK's own
`libs.tech/klayout/tech/sky130A.map`. And `gdsout` fails outright if the written
GDS carries geometry numbered below the lowest layer the PDK defines, since
that can only mean the map was not applied. The floor is read from the PDK
rather than hardcoded, so it holds for other processes.

**If you take one thing from this project, take that one.** A checker reporting
zero is not evidence of a clean design until you know it was looking at
something.

Getting there meant finding a missing step. Every violation was in four rules —
`nwell.1`/`nwell.2a` and `hvtp.1`/`hvtp.2`, all *width* and *spacing* on two
layers — and the count scaled with cell count (14 on a 22-cell design, 440+ on a
939-cell one). Eliminated along the way: a bad deck or library (a lone PDK cell
DRCs clean), unmerged hierarchy (flattening changed 2%), and missing well taps
(adding 265 made it **worse**, which turned out to be the useful clue).

The cause was that **no filler cells were being inserted**. `nwell.1` is a
minimum-width rule, so the violations were narrow nwell slivers, and those
appear wherever cells in a row do not abut. Filler exists to close exactly those
gaps and make the nwell one continuous strip. Every observation fits: more cells
means more gaps; taps are more cells; flattening never touched the geometry; a
cell with no neighbours has no gaps.

Where the fix goes matters as much as the fix. Inserting filler after
*placement* is worse than not inserting it at all — the clock-tree buffers then
have nowhere to go and CTS dies with `DPL-0036` naming a `FILLER` instance. It
belongs at the **end of routing**, after CTS and antenna repair, once nothing
further will be placed.

### The second fake zero: the router said clean, the deck disagreed

With the layer map in place, DRC reported `li.3` (minimum li1 spacing, 0.17 µm)
— 1 on `register`, 26 on OV7670. Meanwhile OpenROAD's own `detailed_route`
reported **0 violations** on the same layout. One of them had to be wrong.

The routing script set the layer range like this:

```tcl
set_routing_layers -signal met1-met5 -clock met3-met5
```

That binds the *global* router only. The detailed router takes its own
`-bottom_routing_layer` / `-top_routing_layer`, and given neither it uses the
whole stack — including `li1`, which the global route never planned for. The
evidence was a single net, `_0304_`, carrying a 20 µm vertical li1 wire at
x = 9.89 µm in the margin left of the placement rows, its right edge landing
0.145 µm from the leftmost cells' li1 power rails. Every row it passed produced
one violation, which is why they arrived in neat consecutive runs.

`detailed_route` called that clean because it does not check li1 against cell
rails it believes are out of its scope. **The router's own DRC report is not a
signoff check** — it answers "did I violate my own constraints", and its
constraints were wrong.

Passing the bounds to both routers fixes it: OV7670 went 27 → 1 violations,
`register` 1 → 0, and li1 routing segments dropped from 4174 to 3456 (what
remains is legitimate pin access).

Two false leads worth recording, because both looked convincing. Adding
placement padding made it *worse* (27 → 46), and 17 of the 26 violations sat on
`decap_*` filler cells — which pointed hard at the filler set, and was pure
correlation. Fillers are simply where the router had free space to detour
through. With the layer bounds correct, the default filler set (decaps
included) is clean.

### The power grid was not connected to the design

Found while chasing LVS, and the most serious bug this project has had.

The PDN generated straps and connected them to each other:

```tcl
add_pdn_connect -grid stdcell -layers {met4 met5}
```

Nothing ever tied that grid *down* to the met1 standard-cell rails. The GDS
proved it: exactly **one** via on layer 68/44. Every layout this flow produced
had a power grid floating above it, delivering no power to any cell.

It routed cleanly. It met timing. It streamed out. It would have been dead
silicon.

**Neither DRC nor STA can see this.** Only LVS can, which is precisely why the
architecture review insisted LVS be its own hard gate instead of being bundled
into a single "DRC/LVS Completed?" boolean. LVS had been saying so all along,
in its own vocabulary: *"must-connect subnets of VGND must be connected further
up in the hierarchy."*

The fix draws the cell rails (`add_pdn_stripe -layer met1 -followpins`) and ties
the grid to them (`add_pdn_connect -layers {met1 met4}`). Afterwards the via
stack is complete — 6 vias on 68/44, then 69/44, 70/44, 71/44 — and DRC is
unchanged at 1 violation.

### LVS runs, but does not yet match

It reads both netlists, extracts the design, and produces a real comparison.
Everything up to the verdict works; the verdict is still `Netlists don't match`.

The reference side is solved and tested. It cannot come from `yosys
write_spice`: SPICE subcircuit calls are positional, and no two views of a
SKY130 cell agree on pin order —

```
.SUBCKT sky130_fd_sc_hd__inv_1 A VGND VNB VPB VPWR Y     CDL
module   sky130_fd_sc_hd__inv_1 (Y, A);                   blackbox
module   sky130_fd_sc_hd__inv_1 (Y, A, VPWR, VGND, VPB, VNB);   power-pin
```

so positional emission miswires every instance while producing a file that
looks entirely reasonable. `rtl2gdsagi.spice` takes the order from the PDK's own
CDL and places the netlist's *named* connections into it. It also keeps
physical-only cells (fill, decap, taps — they are unmistakably in the layout),
prunes the CDL to what the design uses (the full file aborts the run:
`macro_sparecell` uses a `/` call syntax KLayout mis-counts, on a cell nothing
instantiates), and emits the supplies as top-level pins.

What remains is reconciling how the two sides represent power pins:

```
extracted: .SUBCKT ..inv_1 VPB A Y VPWR VGND      5 pins, no VNB
reference: .SUBCKT ..inv_1 A VGND VNB VPB VPWR Y  6 pins
```

Extraction merges a cell's bulk pin into the supply when the layout ties them
*inside* the cell, and whether that happens depends on each cell's internal
connectivity — so the pin lists cannot be predicted per cell. A flat mode
(`to_spice(..., flatten=True)`) expands cells to transistors to sidestep it;
that changes the failure from pin-list noise to net-level differences, but does
not resolve it either. Tried and ruled out: `schematic_simplify`, `combine`,
`.GLOBAL` declarations, and aligning the substrate name via `lvs_sub`.

One more thing worth knowing: the LVS runset has **no `$top_cell` variable**
(the DRC runset does). It infers the top cell, so the GDS must contain exactly
one — which is why stream-out prunes every cell the design does not use.

**Formal equivalence (LEC)**: working, and **not yet trustworthy on every
design**. Read this before believing what it tells you.

The infrastructure works. SKY130's cell models use Verilog UDPs that Yosys
cannot parse — the thing that blocks a naive equivalence check — and a vendored
preprocessor (`formal_pdk_proc.py`, from EQY's own SKY130 example) handles them.
Memories are lowered to logic on *both* sides so the comparison stays fair. Two
strategies are tried: fast SAT, then SMT via `sby` + `z3`.

It proves plenty. An 8-bit register with an asynchronous reset proves cleanly,
end to end, inside the flow. But an 8-bit counter with load and enable inputs —
also certainly correct — comes back with a counterexample.

| design | sequential? | LEC result |
|---|---|---|
| register, async reset (`o_data <= i_data + 1`) | yes | **proved** |
| counter with load + enable mux chain | yes | counterexample |
| any combinational partition | no | **proved** |

Evidence that the fault is in the comparison rather than the design:

| experiment | result |
|---|---|
| netlist compared against **itself** | **proves cleanly**, sequential partitions included |
| async reset → sync reset | no change |
| stripping `init` attributes from both sides | no change |
| removing `setundef -zero` / `hilomap` from synthesis | no change |

So the setup is sound, and the fault is specific to matching the RTL side
against the mapped netlist for some next-state logic. Unresolved.

**Because of this, the tool does not tell you your design is broken.** It says
equivalence was *not established*, notes that this flow produces false
counterexamples on sequential logic, and asks you to look at the trace before
changing any RTL. Signoff still refuses to certify — unverified is unverified —
but an unqualified "your netlist is wrong" would be the worst thing this tool
could say to someone learning.

On the larger OV7670 design the picture is different again: 11 partitions
proved, the rest "equivalence unknown" (z3 reports basecase PASS, induction
FAIL, so k-induction is not strong enough), and **zero** counterexamples.
Raising `lec.induction_steps` from 8 to 40 changed nothing but the runtime.

Two outcomes, worded differently on purpose:

| EQY says | the tool says |
|---|---|
| `partitions not equivalent` | "equivalence NOT established … the prover reported a counterexample … treat as unverified rather than proof of a bug" |
| `equivalence unknown` | "could not be proved … **this is not evidence that the netlist is wrong**" |

### If you are picking this up

The next thing to try is the partition alignment between gold and gate — the
control experiment narrows the fault to how the RTL side and the mapped netlist
are matched up, since both sides prove fine against themselves.

---

## 10. For developers

```bash
.venv/bin/pip install pytest
.venv/bin/python -m pytest -q
```

The suite has three layers, and the middle one is the one that matters most:

* **state machine** against a fake toolchain — retries, rollback to a distant
  stage, escalation, budget exhaustion;
* **`tests/test_real_tool_parsers.py`** — every verdict-bearing parser against
  *captured real tool output* in `tests/fixtures/real/`, each fixture carrying
  a provenance sidecar recording the tool, version, design and expected result.
  This layer exists because a parser and its mock can share the same false
  belief about a tool's syntax and produce a green suite forever: the routing
  parser matched **nothing** in a real OpenROAD log while 349 tests passed;
* **safety** — `tests/test_autonomy_safety.py` drives the adversarial
  remediation proposals in `benchmarks/autonomy/` against the real validator.

The count is deliberately not written down here; it goes stale. Run the suite.

### Layout

| file | purpose |
|---|---|
| `stages.py` | the 21 stages as data |
| `taxonomy.py` | failure class → which stage to fix; what may never be touched |
| `ir.py` | the schema — the agent's entire writable surface |
| `render.py` | schema → TCL. The only place tool syntax is written |
| `runner.py` | the orchestrator |
| `checks/` | report parsers; the only place verdicts are made |
| `safety.py` | immutable paths, iteration budget, diagnosis review |

### Adding a stage

Add a `StageSpec` to `stages.py`, a renderer to `render.py`, a checker to
`checks/`, and a taxonomy row. The runner doesn't change — it's generic.

### The one rule

If you add a check, it must fail closed. A missing report, an unparseable
report, a report with no rules loaded, a report about a different file — all of
those are failures, never passes. Never infer success from silence or from an
exit code.
