# RTL2GDS AGI — Architecture Review

*A box-by-box critique of the current flow diagram, and a proposed corrected architecture for an agentic RTL-to-GDS system.*

---

## Table of Contents

1. [Executive Assessment](#1-executive-assessment)
2. [Complete Reconstruction of the Diagram](#2-complete-reconstruction-of-the-diagram)
3. [What the Current Architecture Gets Right](#3-what-the-current-architecture-gets-right)
4. [Technical Problems and Omissions](#4-technical-problems-and-omissions)
5. [Correct RTL-to-GDS Architecture](#5-correct-rtl-to-gds-architecture)
6. [Agent Architecture](#6-agent-architecture)
7. [TCL / Script-Generation Architecture](#7-tclscript-generation-architecture)
8. [Failure Taxonomy](#8-failure-taxonomy)
9. [Backward-Propagation Architecture](#9-backward-propagation-architecture)
10. [Checkpoint / Rollback Architecture](#10-checkpointrollback-architecture)
11. [QoR Optimization Architecture](#11-qor-optimization-architecture)
12. [Design-Space Exploration](#12-design-space-exploration)
13. [Agent Memory / State](#13-agent-memorystate)
14. [Verification Hierarchy and Safety Boundaries](#14-verification-hierarchy-and-safety-boundaries)
15. [Open-Source EDA Tool Mapping](#15-open-source-eda-tool-mapping)
16. [Current vs. Proposed Architecture — Comparison Table](#16-current-vs-proposed-architecture--comparison-table)
17. [Novelty Assessment](#17-novelty-assessment)
18. [Recommended Final Flow Diagram](#18-recommended-final-flow-diagram)
19. [Implementation Roadmap](#19-implementation-roadmap)
20. [Critical Changes to Make Immediately](#20-critical-changes-to-make-immediately)

---

## 1. Executive Assessment

The diagram is not the "FAIL → Claude → regenerate TCL → retry" loop you explicitly said you wanted to avoid — but it is that loop for **most** of its decision points, and the one place it clearly is *not* that loop (the central `RTL2GDS AGI ENGINE`) is only half-wired.

Here is the single most important fact I found by tracing every arrow: **every major quality/validity gate from `Valid Synthesis Report?` through `DRC/LVS Completed?` correctly converges on one shared `RTL2GDS AGI ENGINE` box.** That's the right instinct — one diagnostic brain, not eight. But when I traced the *outputs* of that engine, only **two** re-entry points exist anywhere in the diagram: back to `CLAUDE API to Fix Syntax Errors` (top of the flow) and back to `STATIC TIMING ANALYSIS`. Floorplanning, Placement, CTS, Routing, and GDS generation each report failures *up* to the engine, but nothing routes back *down* into them. Information flows in; remediation doesn't flow out. This is the architectural gap that matters most, and it's fixable — but not by drawing more arrows (I'll explain why in Section 9).

Beyond that central issue, the diagram has a second, independent problem: the input side. `INPUT synthesis.tcl → TCL Valid?` requires the user to hand-write a synthesis TCL script — which directly contradicts the project's own stated premise that the user should never need to write EDA TCL. And every single regeneration box in the diagram — all eight of them — is labeled "Build from SCRATCH," which is literally Option A in your own five-option taxonomy (Section 7 below), and it's the option with the weakest reproducibility and highest hallucination risk of the five.

There are also real gaps in flow completeness independent of the agent architecture: no formal equivalence checking anywhere, no RTL simulation/testbench gate, no explicit PDN or parasitic-extraction stage, DRC/LVS/antenna collapsed into one gate, and — this one I verified directly and it surprised me — **there is only one STA invocation in the entire diagram**, positioned *before* floorplanning. There is no post-CTS timing check and no post-route signoff timing check anywhere. `DRC/LVS Completed?` flows straight to `FINAL GDSOUT` with zero timing re-verification after the design is actually placed and routed.

None of this means the underlying idea is bad — the idea (centralized diagnosis, stage-aware rollback, QoR-driven iteration rather than pass/fail iteration) is sound and, as far as I can tell, not yet a commodity capability in open-source EDA tooling. But as currently drawn, the diagram implements maybe 30% of that idea. The rest of this document reconstructs exactly what's drawn, says precisely what's missing, and proposes a corrected architecture that keeps your core thesis intact.

---

## 2. Complete Reconstruction of the Diagram

I traced this from the actual uploaded image at full resolution, in six overlapping crops plus three targeted zooms on the ambiguous regions (the engine box, the top-of-page routing, and the STA return path), rather than relying on a flattened read of the whole page. Where something is genuinely not resolvable at the image's resolution, I've marked it **[unclear from diagram]** rather than guessing — per your instruction.

### 2.1 Nodes, in flow order

**Input / validation stage**
- Box: `CLAUDE API to Fix Syntax Errors` — top of page. Confirmed: receives an incoming arrow from a long-range connector that traces back to the right-side feedback bus (see 2.2). Its own output appears to feed back down into the lint-check diamond for re-evaluation, based on position, though I could not find an explicit "NO" label at this specific junction — **[unclear from diagram]** whether this box is triggered by a local lint failure, by the distant bus only, or both.
- Box (input): `INPUT RTL Design Files`
- Diamond: `verilator lint check.` — receives RTL input; passes RTL forward (via a left-margin routing line that also carries SDC and TCL down to Yosys Synthesis, confirmed in the image).
- Box (input): `INPUT SDC Constraints`
- Diamond: `SDC Valid?` → **NO** → `CLAUDE API to Redesign SDC/Build from SCRATCH` → loops back to `SDC Valid?` for re-check (confirmed, local self-contained loop) → **YES** ↓
- Box (input): `INPUT synthesis.tcl`
- Diamond: `TCL Valid?` → **NO** → `CLAUDE API to Redesign TCL/Build from SCRATCH` → loops back to `TCL Valid?` (confirmed, same local pattern) → **YES** ↓

**Synthesis stage**
- Box (process): `YOSYS SYNTHESIS (LOCAL)` — confirmed to receive RTL, SDC, and synthesis.tcl as three converging inputs from the left margin.
- Diamond: `Valid Synthesis Report?` → **NO** → `RTL2GDS AGI ENGINE` (small, dashed-border box) → **YES** ↓ (to STA)
- Box (dashed): `RTL2GDS AGI ENGINE` — connected by a hollow (outline-style) arrow to a separate, larger descriptive box of the same name off to the right, listing its responsibilities: *Diagnose / Reason / Generate patches / Optimize QoR / Maintain state*. Confirmed: this large box is a one-way descriptive callout (a "what this engine does" legend) — it has no outgoing arrow of its own back into the flow. The dashed engine box is the actual live flow node; the large labeled box is documentation of what happens inside it.
- **Confirmed by direct pixel tracing:** the dashed `RTL2GDS AGI ENGINE` box also receives a second incoming arrow at its bottom edge, arriving from the shared vertical bus that runs down the entire right side of the page (see 2.2). This is the same bus that later collects `Timing Met?`, `Valid Floorplan?`, `Valid Placement?`, `Valid Routing?`, `Valid GDS?`, and `DRC/LVS Completed?`.

**Pre-layout STA stage**
- Diamond: `STA TCL Available?` → routes to `STATIC TIMING ANALYSIS (OpenSTA)`; also connects to `CLAUDE API to Redesign TCL/Build from SCRATCH` (a different instance from the ones above — there are eight of these boxes total in the diagram, each local to its own stage).
- Box (input, standalone): `Technology Files (Default SKY130)` — confirmed to feed into the STA-stage redesign box directly, and via a left-margin vertical run, into the floorplan-stage redesign box as well. I did not find a confirmed connection from this box to the placement/CTS/routing/GDS-stage redesign boxes further down — **[unclear/likely absent from diagram]**, flagged in Section 4.
- Box (process): `STATIC TIMING ANALYSIS (OpenSTA)` — **confirmed by direct pixel tracing to be the only EDA execution box in the entire diagram that receives a return arrow from the right-side feedback bus** (two separate return lines terminate here — one into the STA box itself, one into its adjacent redesign-TCL box).
- Diamond: `Timing Met?` → **NO** → joins the shared vertical bus (confirmed) → **YES** ↓

**Floorplanning stage**
- Diamond: `FP TCL Availalbe?` [as labeled in the diagram] → `FLOORPLANNING (OpenLane)`; adjacent `CLAUDE API to Redesign TCL/Build from SCRATCH`.
- Box (process): `FLOORPLANNING (OpenLane)`
- Diamond: `Valid Floorplan?` → **NO** → joins the shared vertical bus (confirmed) → **YES** ↓

**Placement stage**
- Diamond: `Placement TCL Availalbe?` → `Placement (OpenLane)`; adjacent redesign box.
- Box (process): `Placement (OpenLane)`
- Diamond: `Valid Placement?` → **NO** → joins the shared vertical bus (confirmed) → **YES** ↓

**CTS stage**
- Diamond: `CTS TCL Availalbe?` → `CTS (OpenLane)`; adjacent redesign box.
- Box (process): `CTS (OpenLane)`
- Diamond: `Valid CTS?` → **NO** → joins the shared vertical bus (position confirmed consistent with the pattern; exact arrowhead not individually re-verified but follows the identical drawn pattern as its neighbors above and below) → **YES** ↓

**Routing stage**
- Diamond: `Routing TCL Availalbe?` → `Routing (OpenLane)`; adjacent redesign box.
- Box (process): `Routing (OpenLane)`
- Diamond: `Valid Routing?` → **NO** → joins the shared vertical bus (confirmed) → **YES** ↓

**GDS generation stage**
- Diamond: `GDSOUT TCL Availalbe?` → `GDSOUT (Klayout)`; adjacent redesign box.
- Box (process): `GDSOUT (Klayout)`
- Diamond: `Valid GDS?` → **NO** → joins a bus line (confirmed, though at this point in the page the specific line appears distinct from the main 3–4-line bundle above — **[unclear from diagram]** whether this is the same logical bus or a separate one) → **YES** ↓

**Signoff stage**
- Box (process): `DRC/LVS CHECKS Klayout`
- Diamond: `DRC/LVS Completed?` → **NO** → joins the bus, routed via the widest/rightmost jog in the whole diagram → **YES** ↓
- Box (output, terminal): `FINAL GDSOUT`

**Important correction to note explicitly:** an earlier plain-text rendering of this diagram that I had access to before opening the actual image file suggested a *second* `STATIC TIMING ANALYSIS` box and a *second* `RTL2GDS AGI ENGINE` descriptive box near the bottom, between `DRC/LVS Completed?` and `FINAL GDSOUT`. I want to flag clearly that **I do not find these in the actual image.** I checked this specific region at 2x zoom across the full page width. `DRC/LVS Completed?` connects directly to `FINAL GDSOUT` with nothing in between. There is exactly one STA invocation and exactly one engine-description box in the whole diagram, both located just after synthesis. I'm calling this out explicitly rather than silently correcting it, because it changes the severity of one of the findings below (Section 4.3) — the missing signoff-timing gate is not "under-specified," it's **entirely absent**.

### 2.2 The right-side feedback bus — what I can and can't confirm

Running down roughly the right third of the page is a bundle of 3–5 near-parallel vertical lines. I traced these across every band of the image. Here's what direct pixel inspection supports:

- **Confirmed:** `Timing Met?`, `Valid Floorplan?`, `Valid Placement?`, `Valid Routing?`, and `DRC/LVS Completed?` each send their NO-branch into this bundle via a short right-then-up jog with a clear arrowhead.
- **Confirmed:** the bundle terminates at the top by entering the bottom of the (single) dashed `RTL2GDS AGI ENGINE` box.
- **Confirmed:** exactly two return paths exist from this bundle back into an executable stage: into `STATIC TIMING ANALYSIS` / its redesign box, and into `CLAUDE API to Fix Syntax Errors` at the very top of the page.
- **Not resolvable at image resolution:** which *specific* one of the 3–5 parallel lines carries which *specific* diamond's signal. With five failure points converging into a narrow multi-line corridor, I can't certify a clean one-to-one mapping (e.g., "the `Valid Placement?` line is specifically the third line from the left, and it is *not* the same physical line as `Valid Routing?`"). I'm marking this **[unclear from diagram]** rather than asserting a precise mapping I can't back up.

This last point matters less than it might seem, because the higher-level conclusion is the same either way: **whether the bus is one shared line or five distinct ones, only two of its lines are ever drawn going back down into an executable stage.** Even under the most generous possible reading (every diamond has its own dedicated line), the diagram still doesn't show the engine being able to *cause* a re-run of Floorplanning, Placement, CTS, Routing, or GDS generation. That's true regardless of how the ambiguous middle section resolves, which is why I can state it as a firm finding rather than a hedge.


---

## 3. What the Current Architecture Gets Right

Worth stating plainly before the critique, because these are the right instincts and shouldn't get lost:

1. **Centralized failure aggregation for QoR gates is (mostly) real, not aspirational.** I went in expecting to find eight independent local loops with a decorative engine box bolted on. What I actually found is that `Valid Synthesis Report?`, `Timing Met?`, `Valid Floorplan?`, `Valid Placement?`, `Valid Routing?`, and `DRC/LVS Completed?` all genuinely converge on one box. That's the hard part of "one diagnostic brain" — you already have it on the input side.

2. **The macro-ordering of physical stages is correct and matches real flows.** Floorplan → Placement → CTS → Routing → GDS → DRC/LVS is the standard OpenLane/OpenROAD stage order. Nothing here is out of sequence.

3. **There's an implicit — if inconsistent — two-tier failure model already present.** Every "`X TCL Available?`" gate (STA, FP, Placement, CTS, Routing, GDSOUT) is handled by a cheap, local, stage-scoped regeneration. Every "`Valid X?`" gate (synthesis report, timing, floorplan, placement, routing, DRC/LVS) is handled — or at least reported — through the central engine. That split (*"is a script available"* is cheap and local; *"is the tool's output actually good"* is expensive and needs real diagnosis) is a legitimate architectural principle. It reads as something that emerged from how the diagram was drawn rather than a deliberate decision, but it's worth keeping and making explicit rather than discarding.

4. **A rollback concept is visibly attempted, not just implied in prose.** The loops back into `SDC Valid?`, `TCL Valid?`, and — critically — the return arrows into `STATIC TIMING ANALYSIS` show that whoever drew this was already thinking about "go back and redo a specific earlier thing," not just "restart everything." The STA return path is, structurally, a working prototype of exactly the mechanism the rest of the flow needs. It just needs to be generalized to every other stage rather than left unique to STA.

5. **Technology/PDK files are treated as a first-class input**, separate from RTL/SDC/TCL, which is correct — a real flow needs the PDK bundle threaded through synthesis, physical implementation, STA, and signoff, and the diagram at least gestures at this rather than hard-coding paths invisibly.

---

## 4. Technical Problems and Omissions

### 4.1 The input contradicts the project's own stated premise

Your prompt says the user should provide "RTL, SDC constraints, PDK/technology files, standard-cell libraries, relevant design requirements/objectives" — TCL is explicitly *not* on that list, and the stated goal is that the user should not need to know how to write Yosys/OpenSTA/OpenROAD/KLayout TCL. But the diagram's actual front door is `INPUT synthesis.tcl → TCL Valid?`, which presumes the user hand-wrote a synthesis TCL script. Every later stage instead asks "is a TCL *available*" (implying the system checks a cache and generates one if absent) rather than asking the user to supply one. These are two different mental models for the same problem, applied inconsistently to the same diagram — the front door assumes hand-written TCL; everything downstream assumes system-generated TCL. This needs to be unified, and it should be unified toward "the system always generates it," including for synthesis. **This is the single most direct contradiction between the diagram and your stated intent, and I'd fix it first.**

### 4.2 "Build from SCRATCH" is Option A in your own taxonomy, applied universally

All eight regeneration boxes in the diagram carry the literal label "Build from SCRATCH." Take this at face value — it's real information about the current design intent, not just a placeholder string. That's Approach A from your Section 4 (Claude generates complete TCL from scratch every time), and it's the weakest of the five options you asked me to compare, for reasons that compound specifically in this domain:

- **Reproducibility breaks.** Two runs hitting the "same" failure can produce syntactically different TCL due to ordinary sampling variance, which means you can't diff "what changed between attempt 3 and attempt 4" — and that diffability is exactly what Section 10 (design-space exploration) and Section 8 (checkpointing) both depend on.
- **Hallucinated syntax is a real, tool-specific risk here**, not a generic LLM caveat. Yosys, OpenSTA, and OpenROAD each have their own TCL command surface, and it's easy for a model to blend idioms across them (or from commercial-tool muscle memory) — inventing a flag that doesn't exist, or using an OpenROAD-style command inside an OpenSTA context. Free-form generation has no structural guard against this; only something downstream that actually tries to execute (or better, statically validate) the command against that tool's real grammar does.
- **PDK-specific values can't be reliably free-generated.** Site names, row height, track pitch, LEF/tech-LEF paths, corner names — these have to come from the technology bundle, not from the model's judgment, or you're trusting the model to either know or correctly infer facts that are actually just data lookups.
- **It's also a safety problem, not just a quality problem** — "build from scratch" gives the model maximum freedom on every single retry, including freedom to quietly loosen a constraint or drop a check rather than genuinely fix the underlying issue. See Section 14.

### 4.3 There is no signoff-quality timing gate anywhere in the flow

This is the sharpest finding from the direct image trace (Section 2.1): there is exactly **one** STA invocation in the entire diagram, and it happens *before floorplanning* — before CTS even exists. At that point in the flow:

- No clock tree has been built yet, so hold analysis at this checkpoint is close to meaningless (hold is dominated by clock-tree skew, which doesn't exist as a physical structure until CTS runs).
- Setup numbers are estimated from wireload models or synthesis-stage assumptions, not real placement/routing.
- After CTS, after routing, after parasitic extraction — there is no STA anywhere. `DRC/LVS Completed?` flows straight into `FINAL GDSOUT`.

This means the flow, as drawn, can produce a GDS that has never once been timing-checked with real clock-tree latency or real extracted parasitics. That's not a QoR nitpick — it's the literal absence of the check that timing signoff *is*. I'd treat this as the single highest-severity gap in the whole diagram, on par with the missing formal-equivalence check below.

### 4.4 No formal equivalence checking anywhere

There is no LEC (logical equivalence check) stage at any point — not RTL-vs-post-synthesis-netlist, not pre-ECO-vs-post-ECO. This matters more here than in a purely manual flow, because you're explicitly building a system that's allowed to autonomously patch configs and re-run stages. The moment any of those patches could plausibly touch synthesis strategy, retiming, or any optimization pass that legally transforms the netlist, LEC is the only mechanism that verifies the transform didn't change *function* — which is precisely the failure mode you flag yourself in Section 12 ("changing functional behavior to achieve timing"). Right now nothing in the diagram would catch that if it happened.

### 4.5 No RTL simulation / functional verification gate

`verilator lint check` is a style/structural check (unconnected ports, width mismatches, latch inference, obvious X-prop risk) — it is not functional verification. As drawn, a design that lints clean and synthesizes/routes cleanly can reach `FINAL GDSOUT` without ever having been simulated against a testbench. Lint catches a category of bug; it doesn't catch "this design does the wrong thing." This should be an explicit gate before synthesis, not folded into lint.

### 4.6 Binary "Valid X?" gates conflate different failure classes that need different remediation

`Valid Synthesis Report?`, `Valid Floorplan?`, `Valid Placement?`, `Valid CTS?`, `Valid Routing?`, `Valid GDS?` are each single yes/no gates. Each one is actually hiding at least two very different situations:

- The tool **crashed or errored** (a script bug, a missing file, a license issue) — needs a mechanical/environment fix.
- The tool **completed successfully but produced output below a quality threshold** (excessive area, congestion, negative slack) — needs an optimization-type response, not an error-type response.

Collapsing these into one gate means the same downstream remediation logic has to handle both, which is exactly the kind of ambiguity that leads to an agent applying the wrong class of fix. Section 8 below gives each of these its own taxonomy entry for this reason.

### 4.7 DRC, LVS, and antenna are one gate; they shouldn't be

`DRC/LVS CHECKS Klayout → DRC/LVS Completed?` bundles three checks with genuinely different root causes and genuinely different fixes:
- DRC: geometry/spacing rule violations → usually a routing-stage fix.
- LVS: netlist-vs-layout connectivity mismatch → could originate in routing, in netlist export, or in a library/LEF integrity problem (see the worked example in Section 9.4).
- Antenna: charge-accumulation violations during fabrication → fixed via diode insertion or jumper insertion, a routing-adjacent but distinct remediation.

A single "completed?" boolean can't tell the engine which of these three actually failed, which defeats root-cause diagnosis before it even starts.

### 4.8 Missing or under-specified stages, checked against your own list

| Stage from your list | Status in the diagram |
|---|---|
| RTL validation | Present (lint), but see 4.5 — not functional verification |
| Elaboration | Not a separate visible checkpoint; buried inside the Yosys box |
| SDC validation | Present, but likely syntax-only — no visible check for semantic completeness (missing clocks, unconstrained paths) |
| Synthesis | Present |
| Synthesis validation | Present but binary (4.6) |
| Pre-layout STA | Present, but positioned as a hard gate when it should be advisory (4.9) |
| Floorplanning | Present |
| PDN | **Not visible as a distinct stage or checkpoint anywhere** |
| Placement | Present |
| CTS | Present |
| Routing | Present |
| Parasitic extraction | **Not visible as a distinct stage anywhere** — unclear what feeds timing analysis with real RC data, since there's no STA after routing at all (4.3) |
| Post-route STA | **Absent** (4.3) |
| GDS generation | Present |
| DRC | Present, bundled (4.7) |
| LVS | Present, bundled (4.7) |
| Antenna | **Not a distinct gate** (4.7) |
| Formal equivalence | **Absent anywhere in the flow** (4.4) |
| Final signoff | Represented only as "a GDS file exists," not as "all hard constraints re-verified against that exact GDS" (4.10) |

### 4.9 Pre-layout STA is treated as an equal-weight hard gate to signoff STA

Even setting aside that it's the *only* STA in the flow, its positioning treats a synthesis-stage timing estimate as a pass/fail gate with the same authority as a real signoff check. Pre-placement numbers are known to shift substantially once real placement, CTS, and routing exist. Hard-blocking the flow here risks stopping (or, worse, triggering an expensive synthesis-strategy rollback) on a number that physical implementation would have resolved anyway. This gate should be advisory/soft — log it, flag it if wildly off, but don't treat a marginal fail here the same way you'd treat a marginal fail at post-route signoff.

### 4.10 "FINAL GDSOUT" conflates "a file was written" with "the file is signoff-clean"

The terminal box's only visible precondition is `DRC/LVS Completed? = YES`. Given 4.3 and 4.4, that means final output can be declared with no timing signoff and no functional-equivalence verification. An autonomous system needs a final gate that re-checks *every* hard constraint (STA, DRC, LVS, antenna, LEC) against the literal, exact final GDS — not a patchwork of different checks having passed at different points across different iterations of the design.

### 4.11 No visible iteration budget or human-escalation path

Nothing in the diagram bounds how many times a loop can retry, and there's no branch for "the engine can't confidently resolve this, hand it to a human" — relevant for cases like a library/LEF integrity issue (Section 9.4) that the agent has no business trying to autonomously "fix."


---

## 5. Correct RTL-to-GDS Architecture

A stage list that closes the gaps in Section 4, in execution order. Each stage lists what gates it and — critically — whether that gate should be a **hard constraint** (blocks progress) or **advisory** (logged, informs strategy, doesn't block).

1. **RTL characterization** (deterministic, not agent-driven) — module hierarchy, clock domains, macro/memory presence, rough size. Feeds the Flow Planner (Section 6), not a pass/fail gate itself.
2. **Lint** (Verilator) — hard gate. Structural RTL issues.
3. **RTL simulation / testbench pass** — hard gate. This is the functional-correctness gate that's currently missing entirely (4.5).
4. **SDC validation** — hard gate, but split into *syntax-valid* and *semantically complete* (has clocks defined for every clock port, no fully-unconstrained endpoints, consistent units).
5. **Synthesis** (Yosys) — execution stage.
6. **Synthesis validation** — split into *tool-executed-without-error* (hard gate) and *QoR-meets-target* (soft, feeds optimizer if below target rather than hard-failing).
7. **RTL-vs-netlist formal equivalence (LEC)** — hard gate. Currently absent (4.4).
8. **Pre-layout STA** — **advisory only** (4.9). Logged, used to sanity-check synthesis output, does not hard-block floorplanning.
9. **Floorplanning** (die/core sizing, IO placement, macro placement) — execution stage.
10. **PDN generation + check** — hard gate on IR-drop/strap-coverage thresholds. Currently absent as a distinct checkpoint (4.8).
11. **Floorplan validity** — split tool-error vs. QoR-below-target (utilization, aspect ratio, macro legality), same pattern as synthesis.
12. **Placement** — execution stage.
13. **Placement validity + routability estimate** — hard gate on tool errors; soft gate that folds in a **congestion estimate from global-route overflow** before committing to CTS/routing. Catching this here is far cheaper than discovering it after a failed routing run.
14. **CTS** — execution stage.
15. **Post-CTS STA** — hard gate, hold-focused. This is the first point where hold analysis is actually meaningful (real clock latency exists), and it's currently missing entirely (4.3, 4.8).
16. **Routing** — execution stage.
17. **Parasitic extraction (SPEF)** — execution stage, currently absent (4.8).
18. **Post-route (signoff) STA** — **hard gate**, using real extracted parasitics, all corners/modes. This is the authoritative timing check and it must exist (4.3).
19. **GDS streamout** (KLayout) — execution stage.
20. **DRC** — hard gate, its own checkpoint (4.7).
21. **LVS** — hard gate, its own checkpoint (4.7).
22. **Antenna** — hard gate, its own checkpoint (4.7).
23. **Post-route/post-ECO LEC** — hard gate, verifying any hold-fixing or ECO buffer insertion preserved function.
24. **Signoff aggregation** — hard gate: re-verify the *entire* hard-constraint set against the one exact final GDS hash, not a patchwork of individually-passing historical runs (4.10).
25. **Final GDS + reproducible config bundle** — output.

The distinction between hard constraints and advisory checks running throughout this list is doing real work: it's what lets Section 11's optimizer distinguish "must fix before proceeding" from "worth improving if there's iteration budget left."

---

## 6. Agent Architecture

Your intended split — *agent = planner + diagnostician + optimizer + script/config generator; EDA tools = execution + physical implementation + verification* — is the right one. Whether the diagram represents it is a mixed answer.

**What's aligned:** nowhere in the diagram does a Claude box try to *replace* Yosys, OpenSTA, OpenROAD, or KLayout. Every physical-implementation and verification step is still done by the real tool. That separation is intact.

**What's not aligned, and it's the central finding of this whole review:** the diagram currently implements two *different* agent patterns depending on which gate you look at, and they're not the two patterns you actually want.

- At the eight "`X TCL Available?`" gates: a **local, stateless, per-stage repair reflex** — diamond fails, a nearby box regenerates that one stage's script "from scratch," loops back to the same diamond. No cross-stage context, no shared diagnosis, no memory of what was tried before. This is architecturally indistinguishable from the FAIL → Claude → regenerate → retry pattern you explicitly said is *not* what you want — it's just been distributed across eight copies instead of drawn as one.
- At the QoR gates (synthesis report, timing, floorplan, placement, routing, DRC/LVS): failures correctly converge on the **one** central engine. This is the pattern you actually want. But as Section 2.2 establishes, that engine's diagnosis only has two confirmed ways to act on the flow — restart from RTL syntax, or re-run STA. It can't (as drawn) cause a targeted re-run of Floorplanning, Placement, CTS, Routing, or GDS generation, even though it receives failure reports from all of them.

So the fix isn't "add a ninth Claude box" — it's the opposite. **Every regeneration box in the diagram should be the same agent, invoked with different context**, not eight conceptually separate ones. Concretely: collapse all eight local "Redesign TCL" boxes and the central engine into one service with one entry point (diagnose-and-propose) and one exit point (a structured action written to the state store — Section 13), which a separate, deterministic orchestrator then executes. The orchestrator, not the agent, is what actually triggers re-execution of a stage. This also resolves the "only two re-entry points exist" problem directly: once remediation is "write an action to shared state" instead of "be a specific box with a specific hand-drawn arrow," every stage becomes reachable by construction, because reachability no longer depends on someone having drawn a line to it.


---

## 7. TCL / Script-Generation Architecture

Comparing your five options directly against this domain's actual failure modes:

- **A — generate complete TCL from scratch every time.** This is what the diagram currently specifies (4.2). Weakest on reproducibility, weakest on hallucination resistance, weakest on safety. Not recommended as the default path for anything that drives OpenROAD/OpenLane/KLayout directly.
- **B — select from validated templates.** Reproducible and safe, but brittle: real designs need continuous-valued parameters (utilization, density, skew targets), and a fixed template library can't cover the space without either an enormous template count or falling back to A anyway when nothing matches.
- **C — modify parameterized templates.** Much better — reproducible as long as the parameter surface is well-scoped, and the LLM's freedom is bounded to values, not syntax.
- **D — structured intermediate representation, deterministically rendered to TCL.** The strongest option on reproducibility and safety: the LLM never emits tool syntax at all, only a schema-validated config (e.g., `stage: floorplan, core_utilization: 0.65, aspect_ratio: 1.0, pdn_style: standard`), which a deterministic renderer turns into TCL. Two runs with identical IR produce byte-identical TCL, which is what makes controlled A/B comparison (Section 12) actually possible.
- **E — hybrid.**

**Recommendation: D implemented through C, i.e., a bounded version of E** — this isn't just "the safe answer," it maps onto something that already exists in your intended toolchain. OpenLane's `config.json` *is already* a structured IR that gets deterministically expanded into an OpenROAD/Yosys/KLayout flow. Generating validated OpenLane config overrides (rather than either raw hand-written OpenLane TCL, or free-form OpenROAD Tcl from scratch) is the most natural fit for your existing tool choice, not an abstraction layered on top of it.

Concretely:
- The LLM's only write surface is a schema: numeric/enum fields with declared valid ranges (e.g., `core_utilization ∈ [0.3, 0.85]`), rejected before rendering if out of bounds.
- A deterministic renderer (templates + the technology-file bundle) produces the actual TCL/config. The LLM never sees or writes raw tool syntax.
- This is a **structural** safety mechanism, not a behavioral one — the model can't express "disable this DRC check" because that isn't a field in the schema, not because it was told not to. That's a materially stronger guarantee than a prompt-level instruction, and it's the honest answer to your Section 12 concern about suppressed checks.
- For situations the schema genuinely doesn't cover (a real edge case, not a shortcut), allow a narrow, explicitly-bounded **patch** — a diff against a known-good template, confined to a marked `# BEGIN AGENT PATCH / # END AGENT PATCH` region, always dry-run-validated against the tool's own parser before it's ever used to drive an actual run, and always logged as a diff. This is "from scratch" narrowed down to "a reviewable delta," which is the meaningful distinction — not whether the LLM is involved, but whether its output is unconstrained free text or a bounded, checkable change.
- "Build from SCRATCH" should not appear anywhere as the default behavior. If you keep any instance of scratch-generation as a fallback, it should require: (1) dry-run syntax validation against the real tool parser before execution, never execute-then-see-if-it-crashes, and (2) explicit logging that this was a fallback path, since it's the one place reproducibility is knowingly weaker.

---

## 8. Failure Taxonomy

For each class: likely root causes, where evidence comes from, which stage actually needs to change, where re-execution should restart, and — just as important — what the agent must never touch in response.

| Failure class | Likely root cause(s) | Evidence source | Stage to modify | Restart point | Must NOT modify |
|---|---|---|---|---|---|
| RTL/syntax | Malformed Verilog/SystemVerilog, missing files | Verilator output | RTL (mechanical fixes only, e.g. syntax) | Lint | Functional logic, without human review |
| Elaboration | Unresolved module refs, parameter mismatches, width errors | Yosys elaboration log | RTL or synthesis.tcl top-level config | Synthesis | Cell library contents |
| Library | Missing/malformed Liberty or LEF cells, corrupt PDK install | Tool load errors, missing-cell errors | Environment/PDK setup | Environment fix (not a design-stage rollback) | The library files themselves — flag to human, don't "repair" a foundry file |
| SDC | Missing `create_clock`, unconstrained paths, unit mismatch | SDC parser output, OpenSTA `check_setup` | SDC config | SDC validation | RTL |
| Synthesis (tool error) | Crash, unsupported construct, license/tool failure | Yosys exit code + log | Synthesis invocation/environment | Synthesis | Synthesis *strategy* (that's a QoR fix, not an error fix) |
| Synthesis QoR | Area/timing far off target despite clean run | Synthesis report metrics vs. threshold | Synthesis strategy (effort, optimization flags) | Synthesis | RTL (unless RTL itself is structurally the bottleneck, which needs human sign-off) |
| Pre-layout timing (advisory) | Estimate-only slack shortfall | Pre-layout STA report | Logged only; informs strategy | N/A (soft gate) | Anything, automatically — this gate should never trigger an autonomous rollback by itself |
| Floorplan | Illegal geometry, macro overlap, bad aspect ratio | OpenROAD floorplan log | Floorplan config | Floorplan | Placement/CTS/routing configs (they haven't run yet) |
| PDN | IR-drop violation, insufficient strap coverage | PDN analysis report | PDN/floorplan config (strap density, ring width) | Floorplan (PDN is generated within it) | Cell library, routing config |
| Placement | Illegal placement, tool crash | OpenROAD placement log | Placement config | Placement | Floorplan (unless placement failure is itself downstream of a floorplan-level cause — see Section 9.1) |
| Congestion | Global-route overflow post-placement | GRT congestion/overflow report | Placement density locally, or floorplan utilization if global | Placement, or Floorplan if global | Routing config (routing didn't cause this) |
| CTS | Clock tree build failure, excessive buffer count | CTS log, clock tree report | CTS config (strategy, target skew) | CTS | RTL, SDC clock definitions (unless the definition is itself wrong) |
| Hold violations | Short paths, clock skew, insufficient useful skew | Post-CTS/post-route STA hold report | CTS config or targeted hold-fixing (ECO buffer insertion) | CTS or post-route ECO | **RTL — never.** See Section 9.3 |
| Setup violations | Long logic paths, insufficient drive strength, real interconnect delay | Post-route STA setup report, delta vs. pre-layout estimate | Synthesis strategy *or* placement, depending on delta analysis (Section 9.2) | Synthesis or Placement | Whichever stage the delta analysis rules out |
| Routing | DRC-during-route violations, unroutable congestion | OpenROAD routing log, DRC markers | Routing config, or placement/floorplan if congestion-rooted | Routing, or earlier per Section 9.1 | Cell library |
| DRC | Spacing/width rule violations | KLayout DRC report | Routing config/rules | Routing | LVS/antenna decks |
| LVS | Netlist-vs-layout mismatch | KLayout LVS report, mismatch location | Routing, netlist export, or library — see Section 9.4 for triage | Depends on triage outcome | Never auto-"fix" by editing the extracted netlist to match |
| Antenna | Long metal runs without diode protection | Antenna check report | Routing (add diodes/jumpers) | Routing | Cell library |
| Parasitic extraction | Extraction tool failure, missing SPEF | Extraction log | Environment/tool invocation | Extraction step | Design data |
| Post-route timing | Real parasitics reveal violations not seen pre-route | Signoff STA report | Depends on delta analysis — could implicate any earlier stage | Earliest stage implicated | RTL functional logic |
| Tool/runtime failures | OOM, timeout, segfault | Exit code, system logs | Environment (resources, tool version) | Same stage, same config | Design config — don't treat a crash as a design problem |
| TCL/config errors | Malformed rendered script, bad schema value | Tool parse error at invocation | The IR/schema value that produced it | Same stage | The template itself (that's a system bug, not a design iteration — flag to human) |
| Environment/config errors | Wrong PDK path, missing tool, version mismatch | Startup/setup errors | Environment | N/A — not a design-space problem at all | Nothing design-related; escalate |


---

## 9. Backward-Propagation Architecture

### 9.0 Why the diagram struggles to show this, and why more arrows isn't the fix

Here's the underlying reason Section 2.2 found what it found: a static flowchart is the wrong representation for "any stage's failure might need to roll back to any earlier stage." With N stages, that's potentially N² possible rollback edges. No flowchart stays legible at that fan-out — which is exactly why the diagram, even where it clearly *intends* central diagnosis, only manages to draw two concrete return paths. This isn't a drawing-skill problem, and redrawing it more carefully won't fix it.

The fix is to stop representing rollback targets as arrows at all, and represent them as **data**: a table (or state-machine transition function) mapping `failure_class → responsible_stage`, resolved at runtime by the diagnostic engine and executed by the orchestrator. The diagram's job then shrinks to showing that this table-driven jump *exists* as a single generic edge ("root-cause engine → checkpoint/rollback manager → any stage"), rather than trying to enumerate every possible jump by hand.

### 9.1 Example 1 — Routing congestion → placement → floorplan

The agent should not default to "congestion means floorplan is wrong." It should look at *where* the congestion is:

1. Pull the OpenROAD global-route overflow map and the placement density heatmap for the same region.
2. If overflow hotspots spatially correlate with **uniformly high density across the whole core** — and overall utilization is above the rule-of-thumb range for this design's net-length profile — the root cause is floorplan-level: utilization was set too aggressively for how much routing this design actually needs. **Roll back to Floorplanning**, reduce core utilization or grow the die, then re-run Floorplan → Placement → CTS → Routing.
3. If overflow is **localized** — concentrated near a specific macro's routing halo, or around a handful of high-fanout nets — a placement-only fix (local density target, a placement blockage, pin-order adjustment) is more likely sufficient. **Roll back only to Placement**, not Floorplan.
4. The agent should default to the *shallowest* rollback consistent with the evidence, and only escalate to the deeper one if the shallow fix is retried and fails, or if the congestion signature is unambiguously global from the start. Wasting a floorplan-level rerun on a locally-fixable problem is expensive; the reverse (repeatedly re-trying placement on a genuinely floorplan-rooted problem) is just as wasteful in the other direction.

### 9.2 Example 2 — Setup violation after routing → placement/CTS vs. synthesis strategy

This is where the **checkpoint delta-analysis** technique is the generalizable idea worth calling out on its own: compare the *same* critical path's timing at two different checkpoints.

1. Pull the post-route STA critical path report. Classify the dominant delay component: **net delay** (interconnect-dominated) vs. **cell/logic delay** (gate-chain dominated).
2. Look up that same path in the pre-layout STA snapshot, if it existed there.
3. If the path was **already near-critical at the pre-layout estimate**, and only marginally worse post-route, the degradation is structural — too many logic levels, or under-sized cells for the target period. **Roll back to Synthesis**, try a different strategy (increased timing-driven effort, retiming if the RTL structure allows it, adjusted max-fanout constraints), and re-run the full downstream chain.
4. If the path was **fine at the estimate and only became critical after real placement/routing**, the estimate was misleading and the real cause is physical: cells landed far apart, or routing took a detour. **Roll back only to Placement** (or add a proximity/grouping constraint), leaving synthesis untouched.
5. This "diff the same path across two checkpoints" pattern generalizes well beyond this one example — it's the core diagnostic primitive for distinguishing "this was always going to be a problem" from "this stage introduced the problem," and it's worth implementing once as a reusable utility rather than re-deriving per failure class.

### 9.3 Example 3 — Hold violation after CTS → CTS config, not RTL

Hold violations are a clock-tree/race-condition problem, essentially never an RTL problem, and this should be encoded as a hard rule, not left to case-by-case judgment:

1. Check whether violations cluster on **very short register-to-register paths with minimal logic** — the classic hold signature — versus appearing broadly across many unrelated paths.
2. The short-path signature points to a CTS-level fix: useful skew insertion, or targeted hold-buffer/delay-cell insertion (OpenROAD's hold-fixing pass does this directly). **Roll back to CTS.**
3. The broad, uniform signature more often points to an SDC-level issue — `set_clock_uncertainty` mis-specified for the actual skew budget. **Fix at the SDC/constraint level**, still not RTL.
4. **Hard rule, not a judgment call:** the agent must never rewrite RTL functional logic in response to a hold or setup violation. This is exactly the class of error your Section 12 names directly ("changing functional behavior to achieve timing"), and hold violations are the case where the temptation is lowest to justify it but the domain convention against it is strongest — there is essentially no real ASIC flow where fixing hold means touching RTL.

### 9.4 Example 4 — LVS failure → routing/layout, netlist generation, or library mapping

LVS compares the netlist extracted from the GDS against the netlist that drove place-and-route. A mismatch has three structurally different possible origins, and the report tells you which:

1. **Shorts/opens tied to a specific physical location** (a DRC-adjacent metal short, a missing via) — check the mismatch's (x, y) coordinates against the DEF. This is a **routing-stage** problem. Roll back to Routing.
2. **The same mismatch pattern repeats across every instance of one particular cell** — this is not a design bug at all, it's a **library integrity problem**: the LEF pin geometry doesn't match what's actually in the GDS for that cell. The agent should **not** attempt to "fix" a foundry-provided or vendor-provided library file. This should escalate to a human-review flag, full stop.
3. **Structural mismatch with no specific physical location** (extra/missing devices appearing globally, not tied to one spot) — usually means a netlist-export synchronization bug, most often from an ECO or repair pass (e.g., OpenROAD's `repair_timing` inserting buffers) that updated the physical database but didn't correctly re-export the netlist. This is a **tool-flow bug**, not a design-space problem — roll back to re-running the specific ECO/export step, and if it recurs, escalate rather than loop.

The general principle across all four examples: **the report tells you which of these three shapes you're looking at before you ever have to guess** — spatially localized, cell-type-repeated, or globally structural. Root-cause classification should be built around reading that shape, not around pattern-matching the failure's *name* to a fixed remediation.

---

## 10. Checkpoint / Rollback Architecture

**Checkpoints**, one per stage that produces a durable artifact:

| Checkpoint | Artifact stored | Also stored |
|---|---|---|
| CP0 — RTL validated | Lint-clean RTL | Testbench pass result |
| CP1 — Synthesis | Gate-level netlist | Synthesis report, SDC used, rendered TCL, LEC-vs-RTL result |
| CP2 — Floorplan | DEF | Floorplan config, PDN report, utilization |
| CP3 — Placement | DEF | Placement report, congestion estimate |
| CP4 — CTS | DEF | Clock tree report, post-CTS STA (hold) |
| CP5 — Routing | DEF/routing guide | Routing report, in-route DRC markers |
| CP6 — Extraction + signoff STA | SPEF | Signoff timing report (all corners) |
| CP7 — GDS + physical signoff | GDS | DRC/LVS/antenna reports, post-ECO LEC |
| CP8 — Final | Final GDS | Full signoff bundle, full state-store log |

Each checkpoint stores the **exact rendered config** (not just the IR — both, so you can regenerate from IR and confirm it matches what actually ran) and a **content hash of every input** (RTL hash, SDC hash, PDK/library version, template version). That hash is what lets the rollback manager skip re-running a stage whose true inputs haven't actually changed, instead of blindly re-executing everything downstream of a rollback point.

**Rollback rule:** given a diagnosed root-cause stage *R*, restore the last checkpoint *before* R, apply the (schema-bounded) config change to R only, and **invalidate every checkpoint from R onward** — not just R — since anything causally downstream of a changed stage is stale by construction, even if that downstream stage's own config didn't change. Then re-run forward from R through to wherever the flow originally failed. This means the checkpoint store needs to be a dependency chain (effectively a linear DAG here, since the stage order is fixed), not a flat list — "roll back to floorplan" has to mean "floorplan through routing are all now invalid," not "just re-run floorplan and leave the old placement/CTS/routing results sitting there."

**Avoiding wasted loops:** every attempt gets fingerprinted by its full config hash. The orchestrator refuses to re-execute an exact duplicate configuration that's already failed. Combined with a per-stage attempt cap and a global iteration budget (Section 14), this is what keeps "iterate until it works" from becoming "iterate forever."


---

## 11. QoR Optimization Architecture

The flow needs to ask two different questions, not one:

**Hard constraints (must pass, non-negotiable):** LEC pass, zero DRC violations, zero LVS mismatches, zero antenna violations, setup slack ≥ 0 (plus guardband) at every signoff corner, hold slack ≥ 0 at every signoff corner after derating.

**Soft objectives (optimize once hard constraints are met):** area, total power (leakage + dynamic), slack margin beyond zero, wirelength, via count, congestion score, cell count.

**Objective function:** once hard constraints are satisfied, score remaining candidates with a weighted combination —

```
score = w_area · norm(area) + w_power · norm(power)
      + w_timing · norm(slack_margin) + w_congestion · norm(congestion)
```

— with the weight vector selected by strategy: timing-first (heavy weight on slack margin, low tolerance for any pre-signoff negative slack even before it's a hard failure), area-first (heavy weight on utilization/die size), or balanced.

**On Pareto optimization:** a single scalar score forces an arbitrary weighting choice on trade-offs that are genuinely not reducible to one number — tighter timing usually costs area and power. Rather than collapsing to one weighted score by default, the optimizer should maintain the **non-dominated set** across everything it's tried (configs where no other explored config is simultaneously better-or-equal on every axis and strictly better on at least one), and only apply scalarization as a default *presentation* choice when you haven't expressed a preference — the underlying search should keep the whole frontier, not throw away information by scoring too early.

---

## 12. Design-Space Exploration

For each tunable knob (core utilization, placement density, synthesis effort/strategy, CTS target skew, routing layer usage):

- **Candidate generation should be diagnosis-guided, not exhaustive.** Don't grid-search every combination of every knob — that's combinatorially intractable when each trial costs a full EDA run. Vary only the knob(s) the root-cause engine actually implicated, holding everything else fixed (controlled, one-factor-at-a-time by default). Broader search is a later-phase capability (Section 19, Phase 9), not a v1 requirement.
- **Execution should parallelize where compute allows** — independent candidate configs can run as separate containerized OpenLane invocations rather than serially, since wall-clock time compounds badly with EDA run durations otherwise.
- **Every result is written to the shared state store** (Section 13) and scored against the objective function (Section 11).
- **Retain the best (or Pareto-best set), and explicitly track "tried and worse"** by config hash — this reuses the same fingerprinting mechanism from Section 10's rollback-loop avoidance, so a candidate that's already been tried and scored lower never gets silently re-run.

---

## 13. Agent Memory / State

This needs to be an actual structured store the deterministic orchestrator reads and writes — not something that lives only in an LLM's conversation history. Over a long iterative flow (tens of stage-retries), context-window summarization is lossy by nature; if state only exists in what the model remembers saying earlier, it *will* drift or get truncated. The store is the source of truth; the model gets a precise, freshly-queried summary of the relevant slice of it at each decision point.

Minimum schema:

```
run_id
design_fingerprint          # hash(RTL) + hash(SDC) + PDK version
current_stage
stage_history: [
  {
    stage, checkpoint_id, config_hash,
    start_time, end_time, tool_exit_code,
    parsed_metrics: {...},
    verdict: pass | fail | qor_below_target,
    attempt_number
  }, ...
]
global_attempt_budget_remaining
best_known_config_per_stage: {...}
best_known_overall_metrics: {...}
active_diagnosis: {
  failure_class, evidence, implicated_stage, confidence
}
pending_action: {
  type: rollback | patch | proceed,
  target_stage, config_delta
}
human_escalation_flags: [...]
```

`verdict` and `parsed_metrics` are written exclusively by deterministic code (Section 14) — the model reads them, reasons over them, and writes `active_diagnosis` and `pending_action`, but never writes `verdict` itself. That boundary is what makes the safety property in Section 14 actually hold at the architecture level rather than as a promise.

---

## 14. Verification Hierarchy and Safety Boundaries

### 14.1 Verification hierarchy — what's authoritative

| Check | Where it belongs | Authority |
|---|---|---|
| RTL simulation | Before synthesis | Hard gate — currently missing (4.5) |
| Lint | Before synthesis | Hard gate — present |
| Synthesis | — | Execution |
| RTL-vs-netlist LEC | Immediately after synthesis, and after any subsequent netlist-modifying step | Hard gate — currently missing (4.4) |
| STA | Advisory pre-layout; hard gate post-CTS (hold) and post-route (signoff) | Only post-route is authoritative for signoff — currently the *only* instance present is the non-authoritative one (4.3) |
| DRC | Post-route | Hard gate |
| LVS | Post-GDS | Hard gate |
| Antenna | Post-route/GDS | Hard gate |
| Final signoff | End of flow | AND of all of the above, evaluated against the *same* final artifact |

The governing principle, stated as an architectural constraint rather than a hope: **Claude does not author verdicts.** The deterministic orchestrator reads tool exit codes and parses report files; it alone sets `verdict` in the state store. The model only ever sees already-computed metrics and verdicts, and its role is strictly diagnosis and proposal on top of them. This is the concrete way to guarantee "Claude says PASS ≠ EDA says PASS" can never become a real bug — not by instructing the model not to claim success, but by never giving it the ability to set that field in the first place.

### 14.2 Explicit boundaries

**Allowed:** TCL/config parameters within the validated schema (Section 7); SDC constraint values, only when correcting a genuine input error (a missing `create_clock`), never to relax a real target; floorplan geometry, synthesis strategy/effort selection, CTS strategy, routing strategy — all within schema bounds.

**Never allowed, as hard architectural constraints, not prompted behavior:**
- Modifying RTL functional logic in response to any timing, DRC, or physical-implementation problem. RTL changes happen only in response to an actual functional bug caught by simulation, and even narrow, mechanically-verifiable RTL edits should default to requiring human sign-off.
- Loosening an SDC constraint solely to make a check pass, with no physical justification — named directly in your own prompt, and worth calling out as its own boundary rather than folding into "don't touch SDC."
- Suppressing, filtering, or downgrading a DRC/LVS/antenna/STA violation. This should be architecturally impossible per 14.1, not merely forbidden.
- Editing PDK files, standard-cell libraries, LEF/Liberty/DRC decks. These are immutable ground truth; a mismatch involving them is a human-escalation case (Section 9.4), never an auto-fix target.
- Self-extending the iteration budget or attempt cap it was configured with.
- Declaring final signoff without a complete, freshly-generated, all-clean report bundle against the exact final GDS hash (4.10).

**Also worth building in from day one:** full audit logging of every config change and every diagnosis, with the actual report data that motivated it — not just for safety review, but because you will want to debug this system when it's wrong, and "why did it decide to touch CTS here" needs a real answer trail, not a re-run-and-hope.

---

## 15. Open-Source EDA Tool Mapping

| Tool | Role | Key inputs | Key outputs |
|---|---|---|---|
| **Yosys** | RTL elaboration, generic optimization, technology mapping (ABC-based) | RTL, cell library (Liberty, for mapping) | Gate-level netlist, synthesis QoR report |
| **OpenSTA** | Static timing analysis at *every* stage it's invoked — the tool itself doesn't know if it's "pre-layout" or "post-route"; that's entirely determined by what parasitics you feed it | Liberty, SDC, netlist + (nothing, estimated, or real SPEF depending on stage) | Timing reports, slack, critical paths |
| **OpenROAD / OpenLane** | Floorplanning (die/core sizing, macro placement, PDN), global+detail placement, CTS, global+detail routing, RC extraction, built-in repair utilities (`repair_timing`, `repair_design`, `repair_antennas`, hold-fixing) | LEF, DEF (progressively refined), SDC, netlist | DEF, SPEF, updated netlist, physical reports |
| **KLayout** | GDS streamout (DEF + cell GDS → GDS), DRC (PDK rule deck), LVS (netlist extraction from GDS + comparison) | DEF, GDS cell library, DRC/LVS decks | GDS, DRC report, LVS report |

Worth being explicit about one distinction: **OpenROAD is the engine** (a toolkit with a Tcl API); **OpenLane is a specific opinionated flow/config system built on top of it.** Given your labels already say "(OpenLane)" at each physical stage, the natural TCL-generation target (Section 7) is validated OpenLane `config.json` overrides, not raw hand-written OpenROAD Tcl — OpenLane's config system is already most of the way to being the structured IR Section 7 recommends; you'd be extending an existing deterministic-rendering layer rather than building one from nothing.

**Data format flow:**

| Format | Produced by | Consumed by | Present at |
|---|---|---|---|
| LEF | PDK / macro vendor | Floorplan, Placement, CTS, Routing | Physical stages |
| Liberty (.lib) | PDK / cell vendor | Synthesis, OpenSTA (every invocation) | Synthesis, every STA run |
| DEF | OpenROAD stages, progressively refined | Every physical stage after floorplan; GDS streamout | Floorplan → GDS |
| SPEF | Parasitic extraction | Post-route OpenSTA | Post-route STA only |
| SDC | User/agent-generated | Synthesis, every STA run, timing-driven P&R | Synthesis onward |
| Verilog netlist | Yosys (out); re-exported after any netlist-modifying physical step | Floorplan (logical input), LEC | Synthesis onward |
| GDS | KLayout streamout | DRC, LVS | End of flow |


---

## 16. Current vs. Proposed Architecture — Comparison Table

| # | Current component | Problem | Why it's a problem | Recommended change | Priority |
|---|---|---|---|---|---|
| 1 | `INPUT synthesis.tcl` + `TCL Valid?` | User must hand-write TCL | Directly contradicts the stated project premise | Remove; system always generates synthesis config from RTL + objectives | **CRITICAL** |
| 2 | All 8 "Redesign TCL/Build from SCRATCH" boxes | Free-form regeneration every retry | Non-reproducible, hallucination-prone, weak safety guarantees | Switch to IR + deterministic template rendering (Section 7) | **CRITICAL** |
| 3 | 8 local, isolated "Redesign TCL" boxes | Not routed through the central engine | Implements the exact FAIL→Claude→regenerate→retry pattern the project explicitly rejects, at most of its gates | Unify all remediation through one stateful diagnostic service | **CRITICAL** |
| 4 | Right-side feedback bus | Only 2 of 8 failure gates have a confirmed return path into an executable stage | Diagnosis without a mechanism to act on it — the core claim of "backward propagation" isn't actually wired for most stages | Represent rollback targets as data (a stage-lookup table), not static arrows (Section 9.0) | **CRITICAL** |
| 5 | Single STA box, positioned before floorplanning | No post-CTS or post-route timing check anywhere | A GDS can be produced that was never checked with real clock-tree latency or real parasitics | Add post-CTS (hold) and post-route (signoff) STA as hard gates | **CRITICAL** |
| 6 | No LEC stage | No safety net against functional drift from agent-applied patches | Directly undermines your own Section 12 concern about changed functional behavior | Add LEC after synthesis and after any netlist-modifying step | **CRITICAL** |
| 7 | No RTL simulation gate | Functionally broken RTL can reach GDS if it lints and routes cleanly | Lint ≠ functional correctness | Add a simulation/testbench-pass gate before synthesis | **CRITICAL** |
| 8 | `FINAL GDSOUT` gated only on `DRC/LVS Completed?` | Conflates "file exists" with "signoff-clean" | Given #5 and #6, "final" could mean untimed and unverified | Add a signoff aggregator re-checking all hard constraints against the final GDS hash | **CRITICAL** |
| 9 | `Valid X?` gates (synthesis, floorplan, placement, CTS, routing, GDS) | Binary — conflates tool-crash with QoR-shortfall | Blocks differentiated remediation; an error-class fix and a QoR-class fix are not the same action | Split each into execution-status + QoR-threshold sub-checks | HIGH |
| 10 | `DRC/LVS CHECKS` / `DRC/LVS Completed?` | DRC, LVS, antenna bundled into one gate | Hides which specific check failed, blocking root-cause diagnosis | Split into three distinct gates | HIGH |
| 11 | No parasitic extraction stage shown | Unclear what feeds post-route timing (which is itself absent) | Signoff timing requires real SPEF, not estimates | Add explicit extraction stage between routing and signoff STA | HIGH |
| 12 | No agent memory/state store depicted | Cross-stage diagnosis and duplicate-avoidance aren't structurally possible | Delta-analysis (Section 9.2) and DSE (Section 12) both require it | Add a persistent structured state store as a first-class element | HIGH |
| 13 | No visible iteration budget or escalation path | Risk of unbounded retry loops on unresolvable cases (e.g., library mismatches) | Section 9.4's library-mismatch case has no valid autonomous resolution | Add explicit budget guard + human-escalation branch | HIGH |
| 14 | No PDN stage/checkpoint | IR-drop/strap issues invisible until much later | Cheaper to catch at floorplan-adjacent stage than downstream | Add explicit PDN generation + check | MEDIUM/HIGH |
| 15 | Pre-layout STA treated as a hard gate | Pre-placement numbers are known to be unreliable | Risks blocking or mis-triggering rollback on a number physical implementation would resolve anyway | Make pre-layout STA advisory, not blocking | MEDIUM |
| 16 | `Technology Files` connectivity | Appears to reach only STA- and floorplan-stage redesign boxes | PDK data is needed at nearly every stage | Thread technology bundle explicitly through synthesis, all P&R stages, STA, and GDS/DRC/LVS | MEDIUM |
| 17 | Front-door TCL model vs. later-stage TCL model | Inconsistent mental model within the same diagram (hand-written vs. system-generated) | Signals the diagram evolved without normalization | Unify on one model everywhere (Section 4.1) | MEDIUM |

---

## 17. Novelty Assessment

Taking the instruction to evaluate this objectively rather than validate it:

**As currently diagrammed**, this sits closest to *ordinary automation with LLM-assisted script generation and retry* — the dominant pattern at most decision points really is regenerate-and-retry, just distributed across eight boxes rather than centralized. There's one genuine piece of *LLM-assisted EDA flow* architecture (the central engine's input side), but it isn't yet wired into an *autonomous EDA agent* in any load-bearing sense, because autonomy in this domain has to mean closed-loop diagnosis **and** verified, safe remediation **and** QoR-aware iteration acting together — and right now the remediation half is the part that's missing for most stages.

**What would justify "autonomous EDA agent":** the fixes in Sections 6 and 9 actually implemented — one diagnostic service reachable from every stage, genuine multi-stage backward propagation demonstrated working (not just architected) across cases like the routing→floorplan and setup→synthesis examples, a failure taxonomy actually driving differentiated remediation rather than uniform regeneration, deterministic verdict authority, and — this is the part a diagram can't establish on its own — a real evaluation showing recovery across a reasonably broad set of *injected* failure scenarios, not just a description of intended capability.

**What would additionally justify "optimization agent":** the QoR/DSE machinery in Sections 11–12 actually implemented and shown, on a real benchmark set, to find configurations better than a fixed default.

**On the name itself:** "AGI" refers to human-level or greater general cognitive capability across arbitrary domains. Even in its most fully-realized form, what's described here — however sophisticated — is a narrow, domain-specific autonomous agent for one engineering discipline. That's a different category from AGI, not a lesser version of it. I'd say this directly because I think the "AGI" framing actually undersells the project rather than inflating it: a genuinely autonomous, safety-bounded, backward-propagating RTL-to-GDS agent would be a real, hard, currently-uncommoditized capability on its own terms, and it doesn't need to borrow weight from an unrelated research goal to be worth building. I'd call it what it's actually aiming to be — an **autonomous/agentic RTL-to-GDS system** — and let the engineering carry the claim.

---

## 18. Recommended Final Flow Diagram

Your own sketch, kept intact where it was already right, with the fixes from Sections 5, 6, 9, and 14 folded in:

```
USER INPUT
  (RTL, SDC, PDK/technology files, standard-cell libraries, objectives)
        │
        ▼
INPUT VALIDATION  (deterministic: lint, SDC syntax+semantic check,
                    PDK/library integrity check, RTL sim/testbench pass)
        │
        ▼
DESIGN CHARACTERIZATION  (deterministic facts: size, clock count,
                           macros, memories, fanout — feeds the planner,
                           is not itself a pass/fail gate)
        │
        ▼
FLOW PLANNER  (agent: initial strategy — synthesis effort, utilization
               target, CTS/routing strategy — from characterization + objectives)
        │
        ▼
CONFIG / IR GENERATOR  (agent emits schema-validated structured config;
                         deterministic renderer produces the actual TCL/
                         OpenLane config — Section 7)
        │
        ▼
EDA EXECUTOR  (deterministic: runs Yosys / OpenSTA / OpenROAD-OpenLane /
               KLayout for the current stage; captures exit code, logs, artifacts)
        │
        ▼
REPORT PARSER  (deterministic: raw logs/reports → structured metrics
                 in the state store; computes verdict against thresholds
                 — the model never authors this verdict, Section 14)
        │
        ▼
VERIFICATION GATE  (deterministic: hard-constraint check)
   │
   ├── PASS, QoR meets target ─────────► next stage (or SIGNOFF if last)
   │
   ├── PASS, QoR below target ─────────► OPTIMIZER ──► DSE candidate
   │                                       (Sections 11–12, loops within
   │                                        the current stage's search space)
   │
   └── FAIL ──► FAILURE CLASSIFIER  (taxonomy, Section 8)
                       │
                       ▼
                ROOT-CAUSE ENGINE  (agent: delta-analysis across
                                    checkpoints + domain heuristics,
                                    Section 9 — identifies earliest
                                    implicated stage, or raises a
                                    human-escalation flag)
                       │
                       ▼
                CHECKPOINT / ROLLBACK MANAGER  (deterministic: invalidates
                                                 every checkpoint from the
                                                 implicated stage onward,
                                                 restores the prior one)
                       │
                       ▼
                CONFIG / IR GENERATOR  (agent proposes a bounded delta,
                                        within schema — loops back to
                                        EDA EXECUTOR at the restored stage)
        │
        ▼  (once every stage has passed with acceptable QoR)
SIGNOFF AGGREGATOR  (deterministic: re-verify every hard constraint —
                      STA, DRC, LVS, antenna, LEC — against the one
                      exact final GDS hash, Section 4.10)
        │
        ▼
FINAL GDS + REPRODUCIBLE CONFIG BUNDLE
  (GDS, all rendered configs, full state-store log, signoff report)


        ⇕ (read/write throughout, not a linear step)
   AGENT STATE STORE (Section 13)
   ITERATION BUDGET GUARD + HUMAN ESCALATION PATH (Section 14)
```

The load-bearing change from your original sketch: `ROOT-CAUSE ENGINE → CHECKPOINT/ROLLBACK MANAGER` is drawn as a **single generic edge** capable of targeting any earlier stage, resolved through the state store at runtime — not as N hand-drawn arrows to N specific stages. That's what makes every stage reachable by construction instead of by whichever lines happened to get drawn.


---

## 19. Implementation Roadmap

Ten phases, each building strictly on the last. The ordering principle: prove the deterministic backbone before adding any agent, prove single-stage remediation before multi-stage propagation, and prove propagation on one design before claiming generalization.

**Phase 1 — Deterministic baseline executor (no LLM at all)**
*Objective:* one fixed reference design (small, known-good, open RTL) running end-to-end through Yosys → OpenSTA → OpenLane/OpenROAD → KLayout, fully scripted, zero agent involvement.
*Inputs:* one RTL+SDC+SKY130 test case. *Outputs:* a working GDS, an established checkpoint directory structure. *Tools:* Yosys, OpenSTA, OpenLane, KLayout, a thin Python orchestrator.
*Difficulty:* Medium — mostly integration; the pieces already exist. *Risk:* PDK/toolchain setup friction eating disproportionate time. *Success criteria:* one command reproduces a clean, signoff-passing GDS twice in a row, byte-identical.

**Phase 2 — Structured config/IR + deterministic template rendering (still no LLM)**
*Objective:* the reproducibility backbone from Section 7. *Inputs/Outputs:* JSON/YAML schema per stage; a renderer producing OpenLane config/TCL from it. *Tools:* Python, a templating engine, schema validation.
*Difficulty:* Medium. *Risk:* under-scoping the schema — mitigate by using OpenLane's own config surface as the v1 field list. *Success criteria:* re-rendering from IR reproduces the Phase 1 GDS exactly.

**Phase 3 — Structured report/log parsing**
*Objective:* turn raw tool output into the state-store schema (Section 13). *Tools:* parsers per tool, using machine-readable report formats where available.
*Difficulty:* Medium-High — EDA report formats are version-fragile. *Risk:* brittle parsers breaking across tool upgrades — mitigate with versioned parsers and fixture tests. *Success criteria:* 100% of relevant metrics extracted correctly for the Phase 1 reference run, checked against manual inspection.

**Phase 4 — LLM failure diagnosis, read-only**
*Objective:* validate diagnostic quality before granting any write access. The model explains likely root cause over structured facts; a human reviews every output; nothing is auto-applied.
*Difficulty:* Medium. *Risk:* trusting fluent-but-wrong diagnoses — mitigate by validating against a labeled set of *injected* failures spanning the Section 8 taxonomy. *Success criteria:* ≥80% correct root-cause-stage identification across ≥20 injected failures, human-graded.

**Phase 5 — Bounded automatic parameter modification, single-stage only**
*Objective:* close the loop for the simplest case — same-stage retry with a schema-bounded change, no multi-stage rollback yet.
*Difficulty:* Medium-High. *Risk:* schema-valid-but-still-bad proposals — mitigate with the Section 11 objective function gating whether a change is kept. *Success criteria:* resolves a meaningful fraction of the injected-failure benchmark unattended, with **zero** out-of-schema or unsafe configs across the whole run.

**Phase 6 — Checkpoint/rollback manager**
*Objective:* the DAG-based invalidation/restoration from Section 10, still driven by a diagnosed single target stage (not yet cross-stage tracing).
*Difficulty:* Medium. *Risk:* cache-invalidation bugs — mitigate by invalidating conservatively (everything downstream, always) and hashing everything. *Success criteria:* rolling back to stage N and re-running with an unchanged config reproduces byte-identical downstream artifacts to the original run — this proves the mechanism is trustworthy before it's used for real changes.

**Phase 7 — True backward/root-cause propagation**
*Objective:* the actual novel core of the project — extend Phase 4's diagnosis to trace *across* stages using the delta-analysis technique (Section 9.2), driving Phase 6's rollback to a distant stage automatically.
*Difficulty:* High — the hardest, most novel part. *Risk:* mis-attributed root causes causing expensive wasted rollback cycles. *Success criteria:* on a benchmark of **multi-stage-origin** injected failures (e.g., a bad floorplan utilization that only manifests as a routing failure), the agent correctly identifies and rolls back to the true distant origin in a target majority of cases, with total compute spent compared against an "always restart from RTL" baseline to demonstrate real efficiency gain — not just correctness.

**Phase 8 — QoR optimization loop**
*Objective:* move from "does it pass" to "how good is it," for designs already meeting hard constraints (Sections 11–12).
*Difficulty:* Medium-High. *Risk:* runaway compute from combinatorial exploration — mitigate with the guided, one-factor-at-a-time default and hard budgets. *Success criteria:* DSE finds a configuration measurably better than the Phase 1 fixed-default baseline (smaller area at equal margin, or better margin at equal area) within a bounded budget.

**Phase 9 — Design-aware initial strategy selection**
*Objective:* use RTL/design characterization (Section 5's characterization step) to start from a smarter default per design, rather than iterating from the same fixed starting point every time — and, critically, test this on designs *other than* the one reference design used so far.
*Difficulty:* High — this is where real generalization gets tested, not assumed. *Risk:* overfitting strategy heuristics to the handful of designs tried. *Success criteria:* across 3–5 meaningfully different designs (size, clock count, macro presence), the system reaches passing, reasonable-QoR results without manual per-design tuning.

**Phase 10 — Full closed-loop autonomous flow with human escalation**
*Objective:* integrate everything — generalization, full backward propagation, QoR optimization, the safety boundaries of Section 14, and a real escalation path for the taxonomy's unresolvable cases.
*Difficulty:* Very High — long-tail EDA failure modes will always outrun any fixed taxonomy. *Risk:* treat this as expected, not a defect — confident escalation is a feature. *Success criteria:* unattended, end-to-end runs across a benchmark suite spanning real difficulty range, hitting signoff-clean GDS for a target fraction without intervention, and *correctly escalating* — rather than looping or falsely claiming success — on the rest.

---

## 20. Critical Changes to Make Immediately

If you only act on five things from this whole review, make it these — they're the ones with compounding cost the longer they stay unfixed:

1. **Drop the hand-written-TCL front door.** `INPUT synthesis.tcl → TCL Valid?` contradicts the project's own premise. The system should generate synthesis config the same way it's meant to generate every other stage's config.
2. **Stop generating "from scratch."** Move to schema-validated IR + deterministic rendering (Section 7) as the default for every stage, not just some. This one change fixes reproducibility, most of the hallucination risk, and a meaningful chunk of the safety exposure simultaneously.
3. **Add signoff-quality timing.** Right now there is no post-CTS and no post-route STA anywhere in the flow. This is the highest-severity single gap — a GDS can currently be declared "final" without ever having its real timing checked.
4. **Add LEC.** After synthesis, and after anything that legally transforms the netlist. Without it, nothing verifies that an autonomous patch didn't change what the design actually does.
5. **Replace the arrow-based rollback with a table-driven one.** This is the fix for the central finding of this whole review (Section 2.2, Section 9.0): centralized diagnosis without a general-purpose way to act on it isn't backward propagation yet, it's centralized *reporting*. Making every stage reachable through the state store rather than through a hand-drawn line is what actually closes the loop your project is named for.

Everything else in this document — the taxonomy, the DSE machinery, the Pareto optimization, the ten-phase roadmap — only starts paying off once these five are in place. They're also, not coincidentally, the cheapest ones to fix relative to how much of the rest of the architecture depends on them.

