# Codex Post-P0 Readiness Review

**Audit date:** 2026-08-14  
**Repository:** `/home/xpat/rtl2gdsagi`  
**Audit scope:** deterministic verification integrity and readiness for a tightly
controlled local live-model experiment. No live model was used, no credential
was requested or inspected, no package was installed, and no source file was
modified.

## 1. Executive verdict

### Verdict: D — NOT READY — NEW P0 FALSE-CLEAN FOUND

The repository has improved substantially. The deterministic failure class now
governs remediation authorization, timing intent and testbench selection are
locked against model writes, same-stage outputs are retired before every tool
attempt, and the preserved `reg10` run is internally coherent. Its candidate ID
recomputes exactly, all 14 recorded artifact hashes still match disk, and its
raw EDA results support the narrow statement that this particular register
artifact set is clean under the implemented single-clock, single-corner SKY130
methodology.

Those positives do not justify a live-model experiment yet. Three independent
verification-integrity root causes remain:

1. **P0-R1 — SPEF identity/annotation false clean.** SPEF “coverage” is a count
   ratio, not a comparison of actual routed-net identities. A semantically wrong
   SPEF can pass extraction, be mostly ignored by OpenROAD with `STA-0175`
   connectivity warnings, and still earn an authoritative STA PASS from
   plausible no-parasitic slack.
2. **P0-R2 — GateEvidence does not enforce a complete gate-specific proof or
   lineage.** Missing required consumed hashes and report/tool/parser fields are
   accepted. GDSOUT is not an evidence gate. Two organically clean candidates
   can be combined into a hybrid GDS/DRC/LVS generation plus a different
   DEF/SPEF/STA/LEC generation and the production signoff aggregator reports
   clean.
3. **P0-R3 — the model can weaken the PDN structural postcondition.** A PDN
   diagnosis may set `core_ring=false`; the same model-controlled value tells
   the checker not to require a ring. The runner also requests a nonexistent
   `pdn.strap_layers` field, so upper strap presence is never required. A DEF
   with supply rails but no upper distribution can therefore satisfy the
   current structural gate.

There are also three P1 blockers to a meaningful live experiment: the benchmark
live mode actually constructs the scripted fallback, the production prompt
misstates the authorized write surface, and no benchmark currently has both
calibrated real-tool ground truth and an evaluator that grades causal success.

This is not a judgment that the architecture is fundamentally unsalvageable.
The new P0s have small, concrete correction scopes. It is a judgment that the
governing safety condition is not yet met: the deterministic substrate can
still certify the wrong measurement or an incompatible artifact lineage.

### Separation of claims

| Question | Answer |
| --- | --- |
| Safe enough for a controlled live-model experiment now? | **No** |
| Is `reg10` internally clean under the implemented method? | **Yes** |
| Is the method production ASIC signoff complete? | **No** — no MCMM/OCV, comprehensive PVT coverage, IR/EM, or general multi-clock intent |
| Has live runtime-model autonomy been demonstrated? | **No — not tested** |

## 2. Test verification

The normal suite was run from the repository virtual environment:

```text
collected: 502
passed:    502
failed:    0
skipped:   0
xfailed:   0
runtime:   30.50 s
```

Collection alone reported `502 tests collected in 0.11s`.

The claimed `502 passed` baseline is verified. It does not cover the new
negative controls in this report: duplicate/wrong SPEF net identity,
`STA-0175`, empty-but-present GateEvidence fields, organically generated hybrid
candidate lineage, the PDN checker with the ring disabled and no upper straps,
live harness construction, or ground-truth benchmark grading.

VCS metadata is unavailable in this snapshot. `git status`, `git diff`, and
`git log` all report that the directory is not a Git repository, so commit
identity and working-tree cleanliness could not be established.

## 3. Reg10 raw-evidence verification

The preserved run is:

```text
/tmp/claude-1000/-home-xpat-rtl2gdsagi-yosys/
e0c7f0bc-5e69-4f9d-925f-42d79d055d7b/scratchpad/reg10
```

This section distinguishes what the actual run did from what the reusable
verification contracts can guarantee for a future run.

### 3.1 Run and candidate

- `run_state.json` records all 21 stages successful, one attempt each, zero
  rollbacks.
- The final candidate is
  `401a2d020d6f28bdacccc7f10901c083777cd6b09649913771fc5ac425a6215a`.
- Independent canonical reconstruction of the identity object produced that
  exact ID.
- All 14 bound artifact hashes and sizes match their current on-disk contents.
- All 13 preserved checkpoint/output pairs are byte-identical.

Thus the candidate JSON is real content identity for the artifacts it lists,
not merely a label. The limitation is what it omits and the lineage it does not
express.

### 3.2 Raw gate evidence

| Gate | Independently observed raw evidence | Reg10 result |
| --- | --- | --- |
| Simulation | `vvp` output is `TEST PASSED`; `sim_result.txt` says `PASS register_tb.v`; the testbench checks reset, increment, change, wraparound, and reset again | PASS |
| LEC synth | EQY completes gold/gate/combine/partition, proves one partition, and terminates `DONE (PASS, rc=0)` with no contradictory terminal result | PASS |
| PDN | DEF has VPWR/VGND SPECIALNETS, 11 met1 followpin segments, met4/met5 distribution and 51 vias | Structurally populated; IR/EM unverified |
| Placement | Real terminal `Finished with Overflow: 0.099774` after the iteration series | Converged |
| Post-CTS STA | Actual CTS DEF, SDC and TT liberty; setup `+6.9781777887 ns`, hold `+1.2260617313 ns`, no unconstrained endpoints | PASS |
| Routing | Real DRT sequence `9 -> 2 -> 9 -> 0` and terminal completion | PASS |
| Extraction | 18,863-byte SPEF; 35 unique resolved names exactly equal the 35 routed DEF signal-net names; no duplicates, missing, or extra names | Good in this run |
| Signoff STA | Routed DEF and that SPEF are read; no SPEF warnings; setup `+6.9220227065 ns`, hold `+1.1772891883 ns`, both TNS zero | PASS |
| GDS | Hash `8063acda...`; 29 cells, 1,995 elements, expected top, zero unresolved references | Structurally coherent |
| DRC | Required FEOL/BEOL/offgrid/floating-metal switches; 211 unique categories and zero items; exact GDS hash recorded | PASS |
| LVS | Production invocation uses `lvs_sub=VSUBS`; reference and extracted top each have 47 instances; complete 192-circuit DB, zero severity and must-connect records, netlists match | PASS |
| Antenna | OpenROAD raw log reports both 0 net and 0 pin violations; report contains the nonempty completion record | PASS |
| LEC route | Real EQY proof of one partition and coherent `DONE (PASS, rc=0)` | PASS |

The source and run-local RTL hashes match. The self-checking testbench hash is
`7c225435...`, but that hash is not part of the candidate or simulation
GateEvidence.

### 3.3 Exact conclusion about reg10

`reg10` is clean under the implemented one-clock, one-TT-corner methodology on
the evidence that survives. It is not production-signoff proof, and it does not
validate the false-clean paths found with negative controls. In particular, the
real SPEF has exact name-set equality, but the production validator does not
enforce that property.

## 4. GateEvidence audit

### What works

- All ten required record names exist for `reg10`.
- Every non-null recorded report hash and consumed hash currently matches disk
  and the candidate.
- Complete absence of a required gate record is rejected.
- A changed bound GDS or report is detected by re-hashing.
- A consumed hash explicitly naming candidate A is rejected against candidate
  B.
- The five required physical candidate artifacts are required at signoff.

These mechanisms are useful and should be retained.

### P0-R2: exact-schema and lineage validation are missing

`GateEvidence.problems_against()` in
`src/rtl2gdsagi/evidence.py:99` checks only fields that happen to be present.
It never requires:

- the record's `gate` to equal the expected gate;
- a nonempty, current attempt identity;
- the exact gate-specific set of consumed keys;
- the required report key and report hash;
- a known tool identity;
- an approved parser contract;
- the produced artifact and its causal input lineage.

`evidence_for()` at `evidence.py:190` silently omits a required key if it is not
in the ledger. The signoff path at `runner.py:1614` then validates that smaller
map without noticing the omission.

Two defensive production-path tests confirmed the consequence:

1. Ten present PASS records with empty optional fields and empty consumed maps
   were accepted by the actual `_signoff()` aggregator.
2. More decisively, two independent clean full mock candidates were used
   without editing their evidence records: candidate A supplied GDS, DRC, LVS,
   and their organically generated evidence; candidate B supplied routed DEF,
   routed netlist, SPEF, STA, antenna and LEC evidence. The production
   aggregator returned `clean: true` even though the GDS and routed generation
   hashes differed.

The second result is not state tampering disguised as evidence. It demonstrates
that the manifest is an artifact set, not a causal artifact graph.

Specific schema omissions amplify this:

- GDSOUT is absent from `REQUIRED_EVIDENCE`/`CERTIFYING_GATES`; no evidence edge
  binds `routed_def -> final_gds` or requires the GDS integrity verdict.
- STA signoff evidence names `routed_netlist`, but the generated script reads
  `routed_def`, SPEF and SDC.
- LVS evidence binds only final GDS, not the routed schematic netlist,
  generated reference SPICE, extracted netlist, deck, or substrate model.
- Simulation does not bind the testbench that earned PASS.
- Route LEC does not bind its RTL gold input.
- PDN binds its output but not the floorplan from which it was generated.
- STA and LEC raw proof logs have no report keys/hashes and are not candidate
  artifacts.
- Tool identities and parser-contract labels are recorded but never compared
  with an approved contract.

### Required correction

Define an exact immutable evidence schema per gate. Each schema must require the
actual consumed inputs, produced semantic artifact, report/log hash, attempt,
tool build, parser contract, and current-candidate ID. Add GDSOUT evidence and
lineage edges. Reject missing and extra critical keys. Bind testbench content,
both LEC sides, actual STA DEF/SPEF/SDC plus report, LVS schematic/reference/
deck/substrate inputs, and PDK/deck/tool identities. Add the two-candidate
hybrid as a permanent negative regression.

## 5. Candidate-binding audit

The existing candidate ID and all 14 current hashes are mathematically correct.
On-disk mutation of one of those 14 artifacts is detected.

Candidate binding remains incomplete:

- GateEvidence is stored beside, not bound into, the candidate identity.
- The PDK identity is name/root/library/corner rather than hashes of Liberty,
  LEF, cell GDS/CDL/models, extraction rules and approved DRC/LVS decks.
- Candidate tool probes omit OpenROAD/OpenSTA.
- A commit-like container tag is recorded outside candidate identity, not an
  OCI image digest or actual image ID.
- Several verdict-bearing raw logs and generated LVS reference artifacts are
  absent.
- The candidate has no causal edge proving which DEF produced its GDS or which
  reference was compared in LVS.

This is why “all current file hashes match” and “all verification evidence is
for one release candidate” are not equivalent statements.

## 6. Same-stage retry re-test

### Result: stale same-stage output inheritance is closed

The production `_execute()` path calls `_retire_expected_outputs()` before every
attempt (`runner.py:683`, `runner.py:1163`). Defensive retries were exercised for:

- routing (DEF, routed netlist, route report);
- extraction (SPEF);
- GDSOUT (GDS);
- synthesis (netlist and synthesis JSON).

In each case attempt 1 left an output, while attempt 2 returned a superficially
successful tool result without writing a replacement. The old output was moved
to `superseded/`, could not be registered, and the attempt failed. Injecting a
retirement I/O failure raises `Escalation` before the tool is invoked.

This previous P0 is genuinely fixed.

Cross-stage `_retire_stage_outputs()` still logs and continues on a move error,
but the later per-attempt hard retirement prevents the surviving declared
output from being reused. That is a reliability/documentation defect, not the
old same-stage false clean.

## 7. Model write-surface audit

### Strong boundaries now present

Direct calls through the same production diagnosis/validation path, without a
model, established that the deterministic failure class—not a model relabel—
controls authorization.

| Deterministic failure and proposed change | Result |
| --- | --- |
| Routing -> SDC period, testbench, STA corner, extraction corner, guardband, synthesis | Rejected |
| Routing -> floorplan utilization | Accepted; rollback forced to floorplan |
| Hold -> functional RTL, SDC period, testbench | Rejected |
| Hold -> CTS hold margin | Accepted; rollback CTS |
| DRC -> waiver/threshold/skip field | Rejected |
| DRC -> undeclared Tcl/shell field | Rejected by schema |
| Congestion -> placement plus unauthorized synthesis | Rejected atomically |
| Congestion -> placement plus routing | Accepted; earliest affected stage is placement |

There is no model-writable executable name, path, environment map, raw Tcl,
raw shell, arbitrary option dictionary, report path, skip gate, SDC target,
testbench selector, STA corner, extraction corner, or guardband.

### Remaining authority defects

#### P0-R3 — PDN verification intent is coupled to a writable implementation knob

`pdn.core_ring` is agent-writable (`ir.py:225`) and authorized for a PDN
failure. The renderer omits the ring when false (`render.py:437`), while the
runner passes the same value as `expect_ring` to the checker (`runner.py:515`).
The model therefore changes both the design and what evidence is required.

The runner also reads `pdn.strap_layers`, which is not a schema field, so the
checker always receives an empty required strap-layer tuple. A structural
negative control containing VPWR/VGND followpin rails and a via, but no upper
straps or ring, returned `ok=True` when `core_ring=false`. No later IR/EM gate
exists to establish a useful external distribution grid.

This blocks a live model. Freeze the minimum PDN postcondition independently
of model-writable topology, require the actual met4/met5 distribution used by
the renderer for both supplies, and check per-net vertical connectivity. It is
acceptable to continue stating that IR drop, EM and current density are outside
the current method.

#### P1-AUTH-01 — prompt and validator expose different action spaces

`DiagnosisRequest` supplies only the failing stage's IR section. The prompt
calls `describe_section(current)` the only writable schema, but that function
includes locked fields and does not identify `agent_writable`. A signoff hold
failure therefore advertises locked STA fields while withholding the authorized
CTS/placement/routing schemas; DRC advertises a forbidden DRC section while
withholding its authorized implementation sections.

This cannot bypass deterministic validation, but it prevents a meaningful
model experiment: the model is instructed to use fields that code will reject
and must guess the fields code would accept.

Classification: **BLOCKS CONTROLLED LIVE MODEL**.

#### Rollback hint remains broader than the policy comment

The model may propose any stage at or before the failing stage, not only a
stage at or upstream of the deterministic policy target (`runner.py:1049`). A
hold failure can move the target from CTS forward to routing; congestion can
move placement forward to routing. The changed section still forces a rollback
at least as early as its real consumer, so this does not create stale lineage
by itself, but deterministic policy does not fully own responsible-stage
selection as claimed.

Classification: **DOES NOT BLOCK CONTROLLED LIVE MODEL BUT MUST BE DOCUMENTED**
for a same-stage first case; tighten before claiming causal rollback research.

## 8. P0-07 substrate-model verification

Although the latest narrowed review did not require rerunning LVS experiments,
the production path and `reg10` raw artifacts were rechecked because LVS is a
candidate-binding dependency.

- The legacy helper deleted the VNB pin and rewrote its occurrences to ground;
  the old invocation used `lvs_sub=VGND`.
- Production now calls `write_spice(... substrate_net=SUBSTRATE_NET)` with
  `SUBSTRATE_NET = "VSUBS"` and invokes KLayout with `lvs_sub=VSUBS`
  (`runner.py:751-799`).
- `model_substrate()` renames and retains the bulk pin and PININFO entry rather
  than deleting it.
- `reg10` reference and extracted SPICE contain distinct VGND source and VSUBS
  bulk nodes, and VSUBS is promoted at top level.
- No active production occurrence of `lvs_sub=VGND` was found. Remaining text
  occurs in historical documentation, regression descriptions and the explicit
  legacy helper.
- The current DB is structurally complete with 192 cross-references, zero
  severity entries, zero must-connect entries and a real match.

The preserved negative controls are consistent with the production semantics:
changing an NFET bulk connection and restoring the old substrate/ground
conflation both make the real comparison fail. P0-07 itself appears closed.

The new GateEvidence P0 is separate: LVS currently fails to bind all of the
reference-construction inputs that made this correct comparison happen.

## 9. Antenna evidence incident

The incident is independently supported by preserved runs:

- `reg9/stages/18_antenna/antenna.rpt` is zero bytes. It could not be registered
  and therefore could not satisfy evidence.
- `reg10` captures the actual `check_antennas` return value and appends
  `RTL2GDSAGI_ANTENNA_COMPLETE violations=0`; the report is 41 bytes.
- The raw OpenROAD log independently contains both authoritative counts: zero
  net and zero pin violations.

The fix did not relax zero-length artifact registration and did not synthesize
a verdict without invoking `check_antennas`. This is positive evidence that the
ledger/evidence machinery can fail closed when its schema is complete.

## 10. New P0 findings

### P0-R1 — count-only SPEF coverage plus incomplete STA warning handling

Affected code:

- `src/rtl2gdsagi/checks/spef.py:137-186`
- `src/rtl2gdsagi/render.py:305-317`
- `src/rtl2gdsagi/checks/tools.py:486-566`

The extraction validator calculates coverage as:

```text
number of *D_NET records / number of routed DEF nets
```

It does not resolve `*NAME_MAP`, require unique D_NET identities, compare the
actual name sets, or require meaningful per-net CONN/CAP/RES structure.

A defensive negative control with 35 D_NET sections all naming the same real
net was accepted as 35/35 and 100% coverage. The exact pinned OpenROAD build
then exited zero, emitted repeated `STA-0175` messages that the SPEF nodes were
not connected, reached the current annotation marker, and reported plausible
positive no-parasitic setup/hold values. `check_sta()` returned PASS because its
warning contract recognizes `STA-0179` and selected phrases but not this real
annotation/connectivity failure.

Why it matters: the authoritative post-route STA can certify timing that was
not annotated with the routed interconnect.

Required correction:

- resolve NAME_MAP and compare unique SPEF D_NET identities with the routed DEF
  net set;
- reject duplicates, unmapped identities, zero meaningful overlap, incomplete
  sections and insufficient real coverage;
- fail on all relevant SPEF parser/connectivity/annotation diagnostics,
  including `STA-0172`, `STA-0174` and `STA-0175`;
- obtain a deterministic positive annotation-coverage metric rather than using
  a Tcl control-flow marker as annotation proof;
- add a captured-real negative fixture and production runner regression.

The actual `reg10` SPEF passes the stronger proposed set-equality check. No
change to the good artifact is needed.

### P0-R2 — incomplete evidence schema and absent candidate lineage

Affected code:

- `src/rtl2gdsagi/evidence.py:43-58,99-156,176-216`
- `src/rtl2gdsagi/manifest.py:40-58,134-196`
- `src/rtl2gdsagi/runner.py:83-106,1457-1475,1519-1665`

Observed behavior: present-but-empty evidence can certify, GDSOUT has no
semantic evidence record, actual gate inputs/reports are incomplete, and a
hybrid of two clean candidate generations certifies. This is a direct artifact
lineage false clean.

Required correction is the exact per-gate proof/lineage contract described in
Sections 4 and 5.

### P0-R3 — writable PDN topology weakens its own semantic gate

Affected code:

- `src/rtl2gdsagi/ir.py:225-235`
- `src/rtl2gdsagi/render.py:415-459`
- `src/rtl2gdsagi/runner.py:500-526`
- `src/rtl2gdsagi/checks/pdn.py:155-199`

Observed behavior: setting the authorized ring knob false removes both the
implementation and the check, while a nonexistent strap-layer field disables
upper-distribution validation. A rail-only structural negative control passes.

Required correction is an immutable minimum PDN acceptance contract independent
of model-writable topology, with actual configured layer and per-supply
connectivity checks.

## 11. Remaining P1 classification

The classifications below answer only whether an issue independently blocks a
**small, single-clock, trusted-design, one-process, known-tool** first
experiment. Production readiness is not implied.

| ID | Current state | Live-model blocker? | Reason | Required action |
| --- | --- | --- | --- | --- |
| P1-AUTH-01 | Deterministic section allowlists are strong, but prompt shows locked fields and withholds authorized cross-stage schemas | **BLOCKS CONTROLLED LIVE MODEL** | The model cannot be meaningfully evaluated against an action space it is not shown correctly | Build prompt from deterministic failure's authorized sections; include only agent-writable fields, bounds and current values |
| P1-CTS-01 | `target_skew_ns`, `max_fanout`, `balance_levels` are no-ops; parsed skew is not gated; several other schema knobs are also no-ops | **DOES NOT BLOCK CONTROLLED LIVE MODEL BUT MUST BE DOCUMENTED** | Avoid CTS in the first benchmark; STA remains timing authority. No-op fields still waste attempts and corrupt attribution | Remove/freeze no-op fields or implement them before CTS experiments; fingerprint effective rendered behavior |
| P1-GDS-01 | Reader counts BOUNDARY/PATH/SREF at element start, without requiring XY/ENDEL; layer validation skips no-layer files and accepts unknown high layers | **DOES NOT BLOCK CONTROLLED LIVE MODEL BUT MUST BE DOCUMENTED** | Fixed trusted stream-out plus downstream DRC/LVS reduces first-case risk; the model cannot author GDS bytes | Add an element state machine, required records, meaningful mapped geometry and GDSOUT evidence before general certification |
| P1-CP-01 | Per-attempt retirement is correct; checkpoint `produces/consumes` declarations still omit real outputs/inputs, and late in-process rollback can lose routed netlist | **DOES NOT BLOCK CONTROLLED LIVE MODEL BUT MUST BE DOCUMENTED** for a routing-only same-stage case | It false-fails rather than certifies in the observed late rollback; initial case can forbid resume and late-stage rollback | Reconcile StageSpec with actual outputs/dependencies and store/restore copied artifacts; forbid resume initially |
| P1-VERSION-01 | Current environment is known, but no approved-version/parser contract is enforced | **DOES NOT BLOCK CONTROLLED LIVE MODEL BUT MUST BE DOCUMENTED** if an external exact allowlist is imposed | Model cannot change tools; one controlled machine can be frozen, but unknown versions can currently certify | Enforce exact tool/image allowlist in code before authoritative use; record actual execution identity |
| P1-HARNESS-01 | `--diagnosis-source live_model` leaves `agent=None`; Orchestrator converts it to `ScriptedAgent` | **BLOCKS CONTROLLED LIVE MODEL** | The benchmark cannot perform the experiment it labels live | Instantiate the production live agent explicitly; unit-test class/call wiring without a remote call |
| P1-HARNESS-02 | Result evaluator grades mostly process exit; Case 01 is schema-invalid; Cases 02/04 uncalibrated; Case 03's real failure is a layer-range legality error, not claimed congestion | **BLOCKS CONTROLLED LIVE MODEL** | There is no trustworthy calibrated question or causal scoring rule | Calibrate one real case, correct its stated class, and grade failure occurrence, deterministic class, accepted delta, rollback, rerun, metrics and evidence |
| P1-CONTAIN-01 | No shell/raw command/path/env model fields; PDK Docker mount read-only. Native tools inherit host environment and authority; Docker lacks network/resource hardening | **DOES NOT BLOCK CONTROLLED LIVE MODEL BUT MUST BE DOCUMENTED** for trusted register input | Bounded IR prevents the model from selecting commands, but process/tool failure has a larger host impact than necessary | Use an environment allowlist, trusted input only, dedicated run account/container, resource limits and process-group cleanup |
| P1-MCMM-01 | One library context is used; no real MCMM/OCV methodology | **METHODOLOGY LIMITATION ONLY** | Does not affect the narrow question of a controlled remediation experiment | Never call results production signoff; add later as an EDA methodology project |
| P1-MCLOCK-01 | Multiple clocks get default periods; all I/O is assigned to the first; no async groups/generated clocks/CDC intent | **METHODOLOGY LIMITATION ONLY** for a strictly single-clock first case | `reg10` has exactly one clock; general multi-clock designs remain unsupported | Restrict first experiment to reviewed single-clock SDC; do not use OV7670 |

### Blocking P1 count

Three P1 root issues independently block the experiment:

```text
P1-AUTH-01
P1-HARNESS-01
P1-HARNESS-02
```

The new P0s block first and must also be closed.

## 12. Benchmark-harness integrity

### Positive changes

- Diagnosis source is an explicit required choice, not inferred solely from
  ambient credential state.
- Scripted calls remain marked `model=scripted` and do not set
  `autonomy_evidence=true`.
- Run directory deletion is contained below
  `benchmarks/autonomy/runs`; the old arbitrary deletion path is closed.
- The harness returns nonzero for two broad expected-outcome mismatches.

### Blocking defects

1. **Live mode is not live.** `run_case.py` sets no agent object in live mode;
   `Orchestrator(... agent=None)` installs `ScriptedAgent` at `runner.py:154`.
2. **Attribution is insufficient.** A non-scripted model label is enough for
   `autonomy_evidence`; it does not require an accepted delta, safety decision,
   deterministic rollback, real rerun, improvement, final evidence, or
   ground-truth success.
3. **The prompt is not persisted.** The API audit stores the literal placeholder
   `<prompt recorded by agent>`, so a reviewer cannot reconstruct what evidence
   was presented.
4. **The evaluator does not evaluate the case contract.** It does not verify
   that injection caused the expected failure, that the diagnosis named the
   causal stage, that the accepted fields matched ground truth, that the actual
   rollback was correct, or that deterministic metrics improved. The
   `all_refused` outcome is not implemented.
5. **Existing Case 03 is historical scripted evidence.** It shows a real
   OpenROAD error, a scripted delta and a real clean reroute on older code. It
   is not current live-autonomy evidence.

Classification: **BLOCKS CONTROLLED LIVE MODEL**.

## 13. Benchmark calibration

| Case | Current assessment | Suitable now? |
| --- | --- | --- |
| Case 01, floorplan utilization | Injects 0.92 while schema maximum is 0.90; fails validation before claimed downstream causal chain | **No** |
| Case 02, placement density | Schema-valid but no preserved calibration proves the small register reliably fails as stated | **No** |
| Case 03, routing layers | Real failure is `GRT-0056` from an invalid rendered clock-layer range (`met3` minimum above `met2` maximum), not genuine congestion/nonconvergence; historical result is scripted and predates current evidence contract | **No as currently described**; could be recalibrated and relabeled as same-stage configuration-legality repair |
| Case 04, CTS hold | Register baseline hold is strongly positive and hold repair previously found no violations; disabling it is not proven to cause a failure | **No** |
| Case 90, safety | Tests exercise proposals separately, but the benchmark harness does not evaluate `all_refused` | **No as a harness result** |

There is no independently calibrated live benchmark available now.

The smallest credible first case would likely be a corrected Case 03: make the
injection semantically legal at the renderer boundary, establish its exact real
failure class in a fresh scripted control on the current code, and require the
grader to observe that failure, a permitted routing delta, same-stage retry,
real zero-violation reroute, ten valid evidence gates, and current candidate
lineage.

## 14. Tool/parser version policy

Observed environment:

```text
OpenROAD container executable: 41a51eaf4ca2171c92ff38afb91eb37bbd3f36da
container reference: ghcr.io/the-openroad-project/openlane:ff5509f65b17bfa4068d5336495ab1718987ff69
OpenSTA native: 2.0.17
KLayout: 0.30.3
EQY: 0.68
Icarus: 11.0
Yosys: 0.68+56 (7011770a1)
Verilator: 5.050 (v5.050-60-g3d2421f3b)
```

The current corpus meaningfully validates syntax from this environment. The
runtime does not enforce it:

- the OpenLane reference is a tag, not an OCI `@sha256` digest;
- native OpenROAD is preferred if it later appears, silently changing the
  executable path;
- `_tool_identity` labels both OpenROAD and OpenSTA as the container even when
  execution is native;
- candidate tool probes omit OpenROAD/OpenSTA;
- evidence never rejects blank, unknown, changed or unapproved tool/parser
  identities.

Classification for a first run: **DOES NOT BLOCK CONTROLLED LIVE MODEL BUT MUST
BE DOCUMENTED**, only if a wrapper/preflight enforces the exact identities above
and refuses drift. The smallest safe code policy is an approved
`(tool identity, parser contract)` table: unknown authoritative combinations
fail closed; advisory stages may warn.

## 15. Containment assessment

### Bounded model authority

The model cannot choose executable names, raw argv, shell text, arbitrary Tcl,
environment variables, paths, mounts, report paths, or the run root. Commands
are argv lists and no `shell=True` use was found. `cts.root_buffer` is restricted
to an identifier-like regex, although `$` should also be removed because Tcl
will substitute it and cause confusing failures.

OpenROAD's container mounts the PDK read-only and the run directory writable.
These are material positives: the model's accepted action is a bounded IR delta
interpreted by a trusted renderer.

### Residual process authority

- Native EDA and simulation processes inherit the complete host environment.
- Native tools run with the invoking user's filesystem and network authority.
- Docker retains default networking, writable root filesystem and capabilities.
- Neither native nor container paths impose CPU/RAM/PID limits.
- Timeout handling does not establish process-group cleanup for grandchildren;
  EQY/SBY/solvers are the clearest case.
- Native KLayout executes trusted PDK decks with host access; read-only PDK
  enforcement is not a filesystem sandbox there.

For untrusted RTL or testbenches this is a blocker. For the first experiment's
known register RTL/TB and exact generated scripts, it is a documented local
operational risk rather than a route by which the bounded model can weaken a
verdict. Use a dedicated low-privilege environment and an explicit subprocess
environment allowlist.

Classification: **DOES NOT BLOCK CONTROLLED LIVE MODEL BUT MUST BE DOCUMENTED**
inside the strict envelope, after the P0 and harness blockers are fixed.

## 16. Proposed safe live-experiment envelope

This envelope is a future recommendation, not authorization to run now.

Only after P0-R1/R2/R3 and P1-AUTH/HARNESS are closed:

- **Design:** the exact small register reference design and its independently
  hashed, self-checking testbench.
- **Clocking:** exactly one reviewed clock; reviewed fixed SDC; no generated or
  asynchronous clock domains.
- **Timing:** one fixed, known TT corner and nominal extraction; describe the
  result as methodology-limited.
- **PDK:** exact versioned SKY130 tree, content identities recorded; immutable.
- **Tools:** exact versions in Section 14; no native/container substitution;
  unknown identity aborts.
- **Process:** one process, fresh run directory, no resume, no concurrent run.
- **Model role:** diagnosis only; no tool, filesystem or shell access.
- **Write surface:** only fields actually rendered and semantically understood
  for the one calibrated failure. Freeze all verification intent, PDN topology,
  SDC, testbench, STA, extraction, decks, RTL and PDK.
- **Benchmark:** one freshly calibrated same-stage failure whose deterministic
  class and remedy set are established before any model response.
- **Budget:** one diagnosis and at most one bounded retry initially.
- **Evidence:** exact per-gate schemas, candidate lineage, report/log hashes and
  all ten current evidence gates plus GDSOUT.
- **Containment:** dedicated low-privilege local execution, environment
  allowlist, trusted RTL/TB, fixed writable run root, human observation.
- **Claim boundary:** the result answers only whether the model diagnosed and
  safely remediated that injected failure. It is not autonomous chip signoff,
  production readiness, or generalization evidence.

## 17. Final readiness decision

### NOT READY

The current code should not be exposed to a live runtime model even for the
first controlled benchmark. The reason is not lack of production MCMM/OCV or
perfect sandboxing; those can be bounded out of a small experiment. The reason
is that the deterministic substrate still has reachable false-clean paths and
the experiment harness cannot yet execute or grade the proposed live test.

### Minimum exact fixes before another review

1. **Close P0-R1:** validate resolved, unique SPEF net identities and real
   overlap against routed DEF; reject incomplete semantic sections; make STA
   fail on all SPEF connectivity/annotation warnings and require quantitative
   annotation evidence.
2. **Close P0-R2:** enforce exact gate-specific evidence schemas and lineage;
   add GDSOUT evidence; bind actual inputs and logs for simulation, STA, both
   LECs, PDN and LVS; include approved tool/parser/PDK/deck identities; reject
   present-but-incomplete records; add hybrid-generation negative controls.
3. **Close P0-R3:** decouple model-writable PDN implementation choices from an
   immutable minimum structural acceptance contract; require actual upper
   straps and per-supply vertical connectivity.
4. **Fix the prompt/action contract:** show the authorized sections derived
   from the deterministic failure class, only agent-writable fields, their
   bounds and current values. Freeze or remove no-op fields from the first
   experiment's surface.
5. **Fix live harness construction and attribution:** explicitly instantiate
   the production live agent; persist actual presented evidence, response,
   deterministic class, safety decision, accepted delta, derived rollback,
   rerun and before/after metrics. Test wiring without making a remote call.
6. **Calibrate and grade one benchmark:** establish the real failure on current
   code before any live response, correct the case's stated class, and make any
   unmet ground-truth criterion return nonzero.
7. **Freeze the experiment environment:** enforce or externally refuse any
   deviation from the validated tool/image versions; use one process/no resume,
   trusted single-clock register input, fixed SDC/corner, a low-privilege run
   environment and a subprocess environment allowlist.

Once these are verified with new negative controls and one fresh scripted
control run, another pre-autonomy review would be justified.
