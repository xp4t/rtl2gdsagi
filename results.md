# rtl2gdsagi Independent Engineering Audit

Audit snapshot: 2026-08-13.

This was a read-only review: no source, RTL, PDK, deck, package, or machine-configuration changes were made. Existing tests, CLIs, fixtures, preserved artifacts, and safe parser-level probes were used.

## 1. Executive verdict

**NO.**

The repository contains a substantial and technically interesting RTL-to-GDS orchestration prototype. It has real SKY130/OpenROAD integration, 21 wired stages, deterministic checker classes, structured IR, a centralized diagnosis path, a failure taxonomy, and useful real-run evidence.

It is not fundamentally sound as an autonomous certification system because several independent paths can still produce a deterministic PASS from incomplete, stale, contradictory, or failed evidence. The model cannot directly instantiate a Verdict, but it can alter what gets measured, weaken timing acceptance, select testbenches, override rollback policy, and inject executable Tcl through a schema-valid field.

The decisive failures are:

- signoff can be clean with automatically skipped simulation;
- STA passes with setup or hold evidence missing;
- the model-writable timing “guardband” relaxes timing rather than tightening it;
- DRC ignores the DRC tool’s exit code;
- the routing checker misses OpenROAD’s real Number of violations = N syntax;
- LEC can pass despite nonzero exit status, contradictions, or zero proved partitions;
- final aggregation does not prove a common release-candidate lineage;
- persistent resume is not implemented, and checkpoint restore points to mutable originals;
- the schema contains an unrestricted string that renders as executable Tcl;
- no preserved real run demonstrates live-model remediation, cross-stage rollback, or QoR optimization.

A tiny register example did complete all 21 stages with real tools. The nontrivial OV7670 design did not: its latest preserved run has 14 stages OK, simulation and synthesis LEC skipped, DRC failing, and no downstream LVS/antenna/route-LEC/signoff.

### Scores

| Area | Score | Assessment |
|---|---:|---|
| Architecture | 5/10 | Good conceptual skeleton; critical boundaries are incomplete |
| EDA correctness | 3/10 | Real tools run, but constraints and several stage criteria are inadequate |
| Deterministic verification | 2/10 | Deterministic code owns objects, but numerous deterministic false passes remain |
| Artifact provenance | 2/10 | Some hashes exist; no coherent release-candidate manifest |
| Agent safety | 2/10 | Schema-shaped, but executable strings and verification weakening remain possible |
| Rollback/checkpoint correctness | 2/10 | In-memory mechanism exists; persistence, identity, and restore are defective |
| LLM integration | 2/10 | Reachable structured diagnosis hook; weak validation and no real-run evidence |
| Test quality | 5/10 | Broad and fast regression suite; mocks and shared assumptions dominate |
| Real-tool integration | 6/10 | The strongest part of the project; one tiny full run and substantial OV evidence |
| Autonomous remediation evidence | 0/10 | No preserved model-generated delta, retry, or rollback |
| QoR optimization evidence | 0/10 | No optimizer, DSE, Pareto search, or measured autonomous improvement |
| Reproducibility | 2/10 | Generated files retained, but no root Git revision and older evidence is deleted/mixed |
| Production readiness | 1/10 | Unsafe for certification or unattended deployment |
| Research readiness | 3/10 | Interesting ideas, but guarantees and experimental validation are not ready |

The guarantees genuinely enforced today are narrower than the documentation suggests:

- the model response is not directly deserialized into Verdict;
- unknown IR sections/keys and ordinary out-of-range values are rejected;
- subprocesses use argv lists rather than shell=True;
- OpenROAD’s Docker PDK mount is read-only;
- the normal implementation flow uses a run-local RTL copy;
- missing/empty/malformed DRC reports and zero declared DRC categories fail;
- unresolved GDS references fail;
- the known unconditional-LVS fixture and known antenna syntax have regressions.

The following are only apparent guarantees:

- “the model cannot weaken verification”;
- “all hard checks fail closed”;
- “every report is bound to one final GDS”;
- “simulation is always a certification gate”;
- “resume restores persistent checkpoints”;
- “identical failed work is never repeated”;
- “PDK/source immutability is enforced on every tool”;
- “autonomous backward causal remediation has been demonstrated.”

## 2. What is actually implemented

### Repository reconstruction

The meaningful project tree, excluding virtual environments, caches, and large vendored Yosys/EQY/SBY trees, is:

~~~
rtl2gdsagi/
├── README.md
├── RTL2GDS-AGI-Architecture-Review.md
├── rtl2gdsagi-flowchart.png
├── pyproject.toml
├── setup.sh
├── example.config.yaml
├── examples/
│   ├── counter/{rtl,tb,counter.yaml}
│   └── register/{rtl,tb,register.yaml}
├── src/rtl2gdsagi/
│   ├── cli.py, config.py
│   ├── runner.py, stages.py, state.py
│   ├── ir.py, render.py, characterize.py, pdk.py
│   ├── artifacts.py, checkpoints.py, runlog.py
│   ├── taxonomy.py, safety.py
│   ├── agent/{client.py,prompts.py}
│   ├── checks/
│   │   ├── verdict.py, tools.py
│   │   ├── gds.py
│   │   ├── klayout_drc.py, klayout_lvs.py
│   │   └── deck_guard.py
│   ├── tools/invoker.py
│   ├── spice.py
│   └── resources/formal_pdk_proc.py
└── tests/
    ├── conftest.py
    ├── 16 test_*.py modules
    └── fixtures/klayout/
~~~

The CLI entry point is correctly declared in [pyproject.toml](/home/xpat/rtl2gdsagi/pyproject.toml:18).

The root .git directory is not a usable Git repository. Both git status and git log returned:

~~~
fatal: not a git repository
~~~

Therefore this audit cannot identify a commit, establish a clean/dirty baseline, or prove which source revision generated a given artifact. That is a serious reproducibility limitation.

### Independent counts

Counting methodology:

- source: every Python file below src/rtl2gdsagi, including the formal-PDK resource, excluding bytecode and vendored projects;
- tests: tests/*.py, including conftest.py;
- “code-like” LOC removes blank lines and lines whose first non-whitespace character is #; docstrings remain counted;
- tests collected and executed with the project venv’s pytest;
- stage count taken from both the actual STAGES tuple and rtl2gdsagi stages.

| Metric | Measured |
|---|---:|
| Source physical lines | 8,772 |
| Source nonblank/non-comment-only lines | 7,192 |
| Test physical lines | 3,866 |
| Test nonblank/non-comment-only lines | 2,912 |
| Tests collected | 349 |
| Passed | 349 |
| Failed | 0 |
| Skipped | 0 |
| Xfailed | 0 |
| Runtime | 3.27 s |
| Declared/executable stages | 21 |

Thus “about 7,000 lines of source” is reasonable only as code-like LOC. “About 2,700 test lines” is close but stale. “263 tests” is false for the current snapshot.

### Actual control flow

The success path is:

~~~
CLI
  │  user/config authority
  ▼
RunConfig.build
  ▼
new Orchestrator
  ├── new empty RunState
  ├── new empty ArtifactLedger
  ├── new empty CheckpointStore
  └── default IR
  ▼
prepare
  ├── copy RTL into run/work/rtl
  ├── regex-based characterization
  ├── seed IR
  └── apply user overrides
  ▼
linear 21-stage loop
  ▼
deterministic renderer
  ├── Tcl
  ├── EQY/Yosys scripts
  └── KLayout arguments
  ▼
RealInvoker / MockInvoker
  ▼
tool exit code + logs + expected files
  ▼
deterministic checker/parser
  ▼
Verdict
  ▼
artifact registration + in-memory checkpoint + state transition
  ▼
next stage
~~~

The entry and construction path is visible in [cli.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/cli.py:188), while the always-new state, ledger, checkpoint store, and IR are created in [runner.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:91). RTL copying and characterization are in [runner.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:138), and the main loop is in [runner.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:869).

The failure path is:

~~~
tool/parser failure
  ▼
deterministic Verdict + provisional FailureClass
  ▼
raw summary/evidence/metrics/history
  ▼
single LLM diagnostic service
  │  model chooses:
  │  - failure class
  │  - implicated stage
  │  - confidence
  │  - multi-section IR delta
  ▼
JSON shape validation
  ▼
partial safety review
  ▼
model target OR taxonomy target
  ▼
apply IR delta
  ▼
rollback manager invalidates recorded checkpoints
  ▼
rerun from selected stage
~~~

This is centralized, not a collection of independent stage agents. That part of the intended architecture is real. The relevant code is [runner.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:746).

The authority boundary is weaker than claimed:

- deterministic code creates Verdict;
- the model controls inputs to later deterministic verdicts;
- the model may replace the deterministic failure class;
- the model’s implicated_stage takes precedence over the taxonomy at [runner.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:801);
- model confidence is recorded but has no operational effect;
- the model can submit deltas for any schema section, not just the current or responsible section.

### IR inventory

There are 16 sections and 61 fields. All are agent-writable because no field overrides the schema’s default agent_writable=True.

| Section | Complete field inventory | Actual safety/semantic status |
|---|---|---|
| lint | fail_on_warning=false; waived_rules=[]; timescale=1ns/1ps | Waiver names are free strings; timescale is unused |
| sim | timeout 600; glob *_tb.v; directory ""; plusargs [] | Arbitrary paths/globs and behavioral plusargs; can select no or irrelevant testbench |
| sdc | period 10; uncertainty .25; input/output fraction .2; load .05 | Can weaken constraints; period override ordering is defective |
| synthesis | strategy AREA0; flatten true; fanout 10; adder yosys; sharing and DFF map true | Several fields are no-op or do not implement their documented choice |
| lec | induction 8; timeout 900; solver z3 | Live special path ignores timeout; parser allows vacuous PASS |
| sta | TT corner list; derates 0; guardband 0; max paths 20 | Corners unrestricted; fallback unsafe; guardband weakens verification |
| floorplan | utilization .45; aspect 1; margin 10; IO mode; tap distance 13 | IO mode unused; no semantic floorplan legality gate |
| pdn | width 1.6; pitch 30; offset 2; ring true; drop budget 50 | IR-drop budget is not measured or enforced |
| placement | density .55; effort; displacement 50; routability; padding; overflow | Several fields unused; overflow optional/advisory |
| cts | skew .2; fanout 16; root buffer ""; balance true; hold margin .05; hold repair true | root_buffer is Tcl injection surface; several targets unused |
| routing | layers 1–5; effort; iterations 32; filler and diodes true | Routing effort unused; real violation syntax not parsed |
| extraction | corner nom | Only nonempty SPEF required |
| gdsout | merge mode full | Structural checking useful but incomplete |
| drc | threads 4; deep mode true | No direct waiver field; deep mode unused |
| lvs | threads 4; deep mode true | Live path bypasses tested generic options |
| antenna | threads 4 | Threads unused; report artifact ignored |

Syntactic validation is reasonably good for ordinary types, bounds, enums, and unknown keys. Semantic legality and safety are not.

Notable schema defects:

- NaN and infinities are accepted because range comparisons do not reject non-finite values in [ir.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/ir.py:44).
- Arbitrary strings are accepted without identifier or path policy.
- Boolean strings outside the explicit true set silently become false.
- Cross-section and PDK legality checks are sparse.
- Multiple sections can be changed atomically by one diagnosis.
- No generic environment dictionary or arbitrary command field exists, but CTS root-buffer, simulation paths/globs, plusargs, and unquoted Tcl identifiers are sufficient escape surfaces.

### Dead or disconnected mechanisms

The following exist in code or documentation but are not connected to the runtime guarantee they imply:

- persistent CheckpointStore serialization;
- RunState.load for execution—it is used only by status display;
- freshness and tried-config helpers;
- actual persistent resume;
- checkpoint copies as restore sources;
- runtime RTL syntax repair;
- several RunLog events;
- many schema knobs;
- PDN, CTS, STA, LEC, and signoff report artifacts;
- a QoR optimizer or DSE loop.

## 3. Claim verification

### Core project and README claims

| Claim | Verdict | Evidence | Notes |
|---|---|---|---|
| 21 stages | VERIFIED | [stages.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/stages.py:118) | All are linearly reachable |
| ~7,000 source LOC | MOSTLY VERIFIED | 7,192 code-like; 8,772 physical | Counting convention should be stated |
| ~2,700 test LOC | MOSTLY VERIFIED | 2,912 code-like; 3,866 physical | Stale approximation |
| 263 tests | FALSE/STALE | 349 collected and passed | README is outdated |
| Claude never authors a verdict | PARTIALLY VERIFIED | [verdict.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/verdict.py:38) | Model cannot construct object, but can manipulate conditions |
| Model never emits tool syntax | FALSE | [ir.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/ir.py:208), [render.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/render.py:495) | A valid string becomes executable Tcl |
| Schema-bounded model writes | PARTIALLY VERIFIED | [agent/client.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/agent/client.py:138) | Shape bounded; semantics unsafe |
| Deterministic rendering | PARTIALLY VERIFIED | [render.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/render.py:58) | Unsafe interpolation and set-order clock selection |
| One diagnostic service | VERIFIED | [runner.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:746) | Central and reachable |
| Table-driven rollback | PARTIALLY VERIFIED | [taxonomy.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/taxonomy.py:102) | Model can override target |
| Persistent state/checkpoints | PARTIALLY VERIFIED | [state.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/state.py:157) | Status persists; execution does not resume |
| Resume from checkpoint | FALSE | [runner.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:101) | Starts a new empty orchestrator |
| Identical failure never repeated | PARTIALLY VERIFIED | [checkpoints.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checkpoints.py:95) | In-memory and incomplete |
| Global iteration budget | MISLEADING | [runner.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:759) | Counts diagnoses, not all tool attempts |
| Simulation is a hard gate | FALSE AS CERTIFICATION CLAIM | [stages.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/stages.py:140) | Automatic skip can certify |
| Pre-merge GDS cannot reach signoff | PARTIALLY VERIFIED | [runner.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:420) | Simple dangling references blocked; other stale/hollow paths remain |
| DRC cannot pass with zero rules | PARTIALLY VERIFIED | [klayout_drc.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/klayout_drc.py:231) | Partial category set still passes |
| LVS unconditional success blocked | PARTIALLY VERIFIED | [klayout_lvs.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/klayout_lvs.py:128) | Known fixture fixed; bypasses remain |
| Antenna syntax bug fixed | PARTIALLY VERIFIED | [tools.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/tools.py:657) | Exact format fixed; truncation and duplicates remain |
| Every signoff report agrees on one GDS hash | FALSE | [runner.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:1109) | Only DRC/LVS carry such metric |
| PDK/source/decks are read-only | PARTIALLY VERIFIED | [invoker.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/tools/invoker.py:155) | Native tools not filesystem-sandboxed |
| Full state machine tested | PARTIALLY VERIFIED | mock integration tests | No real-tool rollback/remediation test |
| Real SKY130/OpenROAD execution | VERIFIED | [reg4 run](/tmp/claude-1000/-home-xpat-rtl2gdsagi-yosys/e0c7f0bc-5e69-4f9d-925f-42d79d055d7b/scratchpad/reg4/run.log:1) | Genuine real-tool run |

### Architecture conformance

| Requirement | Actual implementation | Verdict |
|---|---|---|
| Deterministic verdict authority | Direct object boundary exists; evidence/thresholds model-influenceable | PARTIAL/UNSAFE |
| Schema-bounded writes | Typed fields, but raw strings, paths, multi-section deltas, NaN | PARTIAL |
| Deterministic rendering | Mostly templates; Tcl injection and nondeterministic clock selection | PARTIAL |
| Central diagnosis | One reachable path | VERIFIED |
| Table rollback | Table exists; model overrides it | PARTIAL |
| Checkpoint invalidation | Incomplete state/file/history invalidation | PARTIAL |
| Persistent resume | No execution-state load | FALSE |
| Duplicate refusal | In-memory, incomplete, semantic no-ops count as changes | PARTIAL |
| Human escalation | Explicit path exists; confidence ignored | MOSTLY VERIFIED |
| Simulation | Executes if found; no-result and skip weaknesses | UNSAFE |
| Synthesis | Real Yosys flow demonstrated | VERIFIED WITH LIMITS |
| Synthesis LEC | Real tiny proof; parser unsafe; OV unknown | PARTIAL |
| Pre-layout STA | Correctly advisory | VERIFIED, constraints weak |
| Floorplan | Real OpenROAD, mostly exit/output evidence | PARTIAL |
| PDN | No connectivity or IR-drop gate | NOT CONFORMANT |
| Placement/congestion | Metrics optional; fields unused | PARTIAL |
| CTS | Targets not enforced | PARTIAL |
| Post-CTS STA | Missing hold can pass | UNSAFE |
| Routing | Real flow; parser misses actual syntax | UNSAFE |
| Extraction | Nonempty SPEF only | PARTIAL |
| Signoff STA | One TT view and fail-open parser | UNSAFE |
| GDS | Useful structural checks, incomplete | PARTIAL |
| DRC | Exit code and complete rule inventory not proven | UNSAFE |
| LVS | Freshness/database completeness gaps | PARTIAL/UNSAFE |
| Antenna | Truncation/multiple-result bugs | UNSAFE |
| Route LEC | Parser and provenance gaps | PARTIAL/UNSAFE |
| Final aggregation | Status aggregation, not candidate certification | FAIL |

STA, LEC, and antenna should attest to a release-candidate manifest containing exact SDC, RTL, netlists, DEF, SPEF, GDS, libraries, decks, and tool versions. They cannot meaningfully “check the GDS hash” directly.

## 4. Critical findings

### P0 — Can falsely certify an invalid chip

#### P0-01 — Hard gates may be skipped while signoff is clean

Affected code: [stages.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/stages.py:140), [runner.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:895), and [runner.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:1092).

Automatic simulation and synthesis-LEC skips are merely recorded. A synthetic clean run returned exit code 0 and clean:true with simulation skipped.

Correction: define a versioned certification profile requiring explicit PASS for every required gate. SKIPPED, UNKNOWN, or absent evidence must prevent certification.

#### P0-02 — STA can pass missing or weakened timing evidence

Affected code: [tools.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/tools.py:456), [ir.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/ir.py:160).

Reproduced:

- setup-only signoff report → PASS;
- hold-only signoff report → PASS;
- post-CTS report without hold → PASS;
- guardband 5 accepts hold −4 ns;
- NaN guardband bypasses comparisons;
- unconstrained sequential endpoints remain advisory.

The reversed guardband expectation is encoded in [test_sta_grading.py](/home/xpat/rtl2gdsagi/tests/test_sta_grading.py:74).

Correction: require finite values, slack >= positive guardband, complete setup/hold metrics per mandatory view, and classified constraint coverage.

#### P0-03 — Generated SDC is not a valid general signoff constraint model

Affected code: [render.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/render.py:58), [runner.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:156).

Configuration applies after characterization, all IO can be assigned to one arbitrary clock, set iteration is nondeterministic, no-clock designs get a virtual clock, and clock-domain/reset/CDC intent is absent.

Correction: require user-authoritative structured timing intent or reviewed SDC and explicit MCMM views.

#### P0-04 — DRC can pass after tool failure or partial rule execution

Affected code: [runner.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:328), [klayout_drc.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/klayout_drc.py:222).

Reproduced:

- nonzero DRC return plus clean stale fixture → PASS;
- one fabricated empty category → PASS;
- copied/touched unrelated clean report satisfies freshness.

The four SKY130 switches are rendered correctly, which is a positive. Complete rule execution is not proven.

Correction: require rc=0, unique reports, deck hash, exact rule manifest, invocation nonce, and candidate-manifest binding.

#### P0-05 — Routing does not parse real OpenROAD output

Affected code: [tools.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/tools.py:540).

The preserved log uses:

~~~
[INFO DRT-0199] Number of violations = 900.
...
[INFO DRT-0199] Number of violations = 0.
~~~

See [OV9 routing log](/tmp/claude-1000/-home-xpat-rtl2gdsagi-yosys/e0c7f0bc-5e69-4f9d-925f-42d79d055d7b/scratchpad/ov9/stages/12_routing/attempt_01.log:196).

The current regex misses = syntax. Using search after merely changing the regex would incorrectly select the first intermediate result.

Correction: parse all iterations structurally and require a unique terminal completion result.

#### P0-06 — Simulation and LEC can pass without functional proof

Affected code: [runner.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:630), [tools.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/tools.py:320).

Simulation promotes a no-result advisory verdict to hard stage PASS. LEC accepts PASS text before validating process status or contradictory output.

Correction: require a user-owned simulation result protocol, assertion coverage, rc consistency, positive formal coverage, all partitions proved, and GOLD/GATE hashes.

#### P0-07 — Signoff is status aggregation, not candidate certification

Affected code: [runner.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:1071).

Only DRC and LVS emit a checked-GDS metric; absent bindings are accepted, reports are not rehashed/reparsed, and several declared report artifacts do not exist in the ledger.

Correction: create an immutable release-candidate manifest and require each gate to attest to every consumed artifact and tool/deck/library identity.

#### P0-08 — Model output permits Tcl execution and causal-policy bypass

Affected code: [ir.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/ir.py:211), [render.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/render.py:495), [safety.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/safety.py:146).

A render-only probe with a semicolon-bearing root-buffer value generated executable Tcl. No payload was executed during the audit.

The model may also return any failure class, any stage—including a future stage—and unrelated multi-section deltas. Low confidence has no effect.

Correction: make deterministic failure class and causal target policy authoritative; allowlist fields and legal cell identifiers; quote Tcl safely.

#### P0-09 — LVS, antenna, and GDS retain false-clean paths

Reproduced:

- truncated 34-byte LVS database plus match log → PASS;
- unreachable compare plus unconditional match text passes deck audit;
- antenna net-only or pin-only zero → PASS;
- initial antenna 0/0 followed by 4/5 → PASS;
- top GDS referring to a defined but empty leaf → PASS.

Affected code: [klayout_lvs.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/klayout_lvs.py:39), [deck_guard.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/deck_guard.py:89), [tools.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/tools.py:657), and [runner.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:341).

Correction: require complete native reports, trusted deck hashes, exactly one coherent terminal antenna result, and DEF/netlist/GDS correspondence.

### P1 — Major correctness or safety failures

#### P1-01 — Persistent resume and checkpoint restore are not implemented

Every orchestrator creates empty state, IR, ledger, and checkpoint store. Checkpoint save copies files but stores paths to mutable originals; restore re-registers the originals.

Evidence: [checkpoints.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checkpoints.py:138) and [checkpoints.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checkpoints.py:228).

Correction: implement a complete atomic persisted execution snapshot using immutable checkpoint paths, or remove resume claims.

#### P1-02 — Attempt fingerprints omit material causality

Fingerprints omit RTL directory content, tool/container version, PDK/deck/library identity, rendered script, environment, cross-section renderer inputs, and absent declared inputs. Unused fields can produce different hashes for identical commands.

Correction: fingerprint the rendered script/argv and complete candidate manifest.

#### P1-03 — Rollback invalidation leaves stale state and files

Only stages represented by valid checkpoints are reset. Stage directories, stale outputs, skipped states, attempts, and history remain. Failed real runs leave the failing stage RUNNING rather than FAILED.

Correction: use immutable attempt directories and invalidate state, ledger, evidence, files, and candidate history independently.

#### P1-04 — Stage criteria are often tool-completion checks

Floorplan legality, PDN connectivity/IR drop, placement legality, CTS skew/fanout, extraction coverage, route closure, and GDS/DEF correspondence are not fully verified.

Correction: define mandatory typed semantic postconditions for every hard stage.

#### P1-05 — Immutability is not process-level enforcement

Native tools retain host-user access and inherit the entire environment. Dockerized OpenROAD mounts the PDK read-only, but lacks network disablement, resource limits, capability dropping, and explicit process-tree cleanup.

Correction: sandbox all tools with read-only ground truth, minimal environments, disabled network, resource limits, and robust cleanup.

### P2 — Significant reliability issues

- runner.py is a 1,233-line orchestration god object;
- the live LVS path differs from the path directly tested;
- many documented schema knobs are no-op;
- missing outputs are silently skipped;
- empty argv and unhandled stages have default PASS paths;
- raw evidence reaches the model verbatim through [prompts.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/agent/prompts.py:105);
- run IDs have one-second resolution;
- symlinks and TOCTOU windows are not controlled;
- there is no QoR optimizer.

### P3 — Maintainability and documentation

- no usable root Git metadata;
- README mixes incompatible run generations;
- README test count is stale;
- README says seventeen stages but lists sixteen;
- pyflakes reports one unused strategy and two placeholder-free f-strings;
- coverage tooling is unavailable;
- several old raw runs have been deleted.

## 5. False-clean analysis

### Known cases

| Case | Independent result |
|---|---|
| Wrong/pre-merge GDS | Partially fixed. Expected top, readability, invented low layers, nonempty top, and unresolved references are checked. Hollow/stale/wrong binding paths remain. |
| Zero-rule DRC | Partially fixed. Four SKY switches passed and zero categories fail. Partial rules or nonzero tool exit plus stale XML can pass. |
| Unconditional LVS success | Partially fixed. Known fixture blocked. Truncated xref data and unreachable compare remain. |
| Antenna syntax | Exact known format fixed. Missing side, duplicates, and first-match behavior remain. |

### Newly identified paths

| Path | Current behavior |
|---|---|
| Real OpenROAD violations = N | Not parsed |
| STA missing setup or hold | PASS |
| Positive guardband | Relaxes acceptance |
| Non-finite timing threshold | Can bypass comparison |
| DRC nonzero exit | Ignored |
| Partial DRC inventory | PASS |
| LEC nonzero exit plus PASS text | PASS |
| LEC contradiction plus PASS text | PASS |
| LEC zero proved partitions | PASS |
| Non-self-checking simulation | Promoted to PASS |
| No testbench | Automatic skip can certify |
| Stale expected output after rc=0 no-write | Can PASS |
| Truncated LVS DB | Can PASS |
| One-sided antenna summary | Can PASS |
| Hollow GDS hierarchy | Can PASS |
| Unknown STA corner | Silent fallback |
| Missing final report binding | Accepted |

It is not structurally impossible for an LLM response to cause PASS without valid tool evidence. The model cannot directly instantiate Verdict, but it can manipulate thresholds, constraints, testbench selection, corner, Tcl, and stage ordering.

## 6. Timing analysis

### Preserved failing OV run

| Checkpoint | Setup WNS | Hold WNS | Hold TNS |
|---|---:|---:|---:|
| Pre-layout | +5.998711 ns | +0.106542 ns | 0 |
| Post-CTS | +4.862288 ns | +0.058111 ns | 0 |
| Post-route | +4.500397 ns | **−0.124165 ns** | −10.276143 ns |

Evidence:

- [pre-layout](/tmp/claude-1000/-home-xpat-rtl2gdsagi-yosys/e0c7f0bc-5e69-4f9d-925f-42d79d055d7b/scratchpad/ov3/stages/06_sta_pre/attempt_01.log:3531)
- [post-CTS](/tmp/claude-1000/-home-xpat-rtl2gdsagi-yosys/e0c7f0bc-5e69-4f9d-925f-42d79d055d7b/scratchpad/ov3/stages/11_sta_postcts/attempt_01.log:3563)
- [post-route](/tmp/claude-1000/-home-xpat-rtl2gdsagi-yosys/e0c7f0bc-5e69-4f9d-925f-42d79d055d7b/scratchpad/ov3/stages/14_sta_signoff/attempt_01.log:3558)

Degradation:

~~~
pre → signoff:
  setup  -1.498315 ns
  hold   -0.230707 ns

post-CTS → signoff:
  setup  -0.361891 ns
  hold   -0.182276 ns
~~~

The signoff script reads the same-run routed DEF and SPEF, but only one TT Liberty view is used. There is no MCMM or OCV.

All nonclock inputs and outputs are assigned to i_pclk in [cam_top.sdc](/tmp/claude-1000/-home-xpat-rtl2gdsagi-yosys/e0c7f0bc-5e69-4f9d-925f-42d79d055d7b/scratchpad/ov3/stages/03_sdc/cam_top.sdc:6). The worst “hold” path is actually asynchronous-reset removal; see [OV4 signoff log](/tmp/claude-1000/-home-xpat-rtl2gdsagi-yosys/e0c7f0bc-5e69-4f9d-925f-42d79d055d7b/scratchpad/ov4/stages/14_sta_signoff/attempt_01.log:1822).

The negative number is a real OpenSTA result under the generated SDC, but not sufficient evidence of a true silicon defect because timing intent is not credible.

The later hold repair was real numerically but was a Claude Code renderer change followed by a fresh run—not runtime causal remediation. The preserved diagnosis is scripted with confidence 0 and an empty delta: [attempt_01_api.json](/tmp/claude-1000/-home-xpat-rtl2gdsagi-yosys/e0c7f0bc-5e69-4f9d-925f-42d79d055d7b/scratchpad/ov4/stages/14_sta_signoff/attempt_01_api.json:1).

## 7. DRC investigation

Historical raw directories no longer survive. The development transcript reports:

| Experiment | Violations | Distribution |
|---|---:|---|
| Baseline | 440 | nwell.2a 292; hvtp.2 52; nwell.1 48; hvtp.1 48 |
| Taps, unflattened | 601 | 397; 72; 66; 66 |
| Taps plus later flattening | 576 | 378; 66; 66; 66 |
| Raw inv_1 | 0 | none |

Thus “440 → 576 after taps” combines two variants, although the rejection of the tap-only hypothesis remains correct.

### Stronger preserved evidence

Upstream synthesis, floorplan, and CTS hashes are identical across ov7, ov8, and ov9.

| Run | Change | DRC result |
|---|---|---:|
| ov7 | 260 taps, no filler | 580 |
| ov8 | filler insertion | 8 |
| ov9 | route bounds plus changed filler set | 1 |

OV7 distribution:

- nwell.2a 397;
- hvtp.2 66;
- nwell.1 58;
- hvtp.1 58;
- m2.x 1.

Evidence: [ov7 DRC summary](/tmp/claude-1000/-home-xpat-rtl2gdsagi-yosys/e0c7f0bc-5e69-4f9d-925f-42d79d055d7b/scratchpad/ov7/stages/16_drc/drc_summary.json:1).

Adding filler eliminates every well/HVTP category. OV8 leaves seven li.3 plus one m2.x: [ov8 DRC summary](/tmp/claude-1000/-home-xpat-rtl2gdsagi-yosys/e0c7f0bc-5e69-4f9d-925f-42d79d055d7b/scratchpad/ov8/stages/16_drc/drc_summary.json:1).

OV9 leaves one m2.x: [ov9 DRC summary](/tmp/claude-1000/-home-xpat-rtl2gdsagi-yosys/e0c7f0bc-5e69-4f9d-925f-42d79d055d7b/scratchpad/ov9/stages/16_drc/drc_summary.json:1).

Evidence grading:

- Proven for preserved runs: 211 declared categories; taps alone do not close well/HVTP; filler removes those categories.
- Strongly supported: missing row filler/abutment continuity was the root cause.
- Plausible but not isolated: detailed-route bounds removed li.3.
- Unsupported: abnormal row orientation as dominant cause.
- Unproven: Magic streamout would be cleaner or required.
- Limited: one raw-cell zero does not validate all cells and abutments.

## 8. Simulation and LEC

### Simulation

Current Icarus:

~~~
/usr/bin/iverilog
Icarus Verilog 11.0 stable
~~~

The latest OV run still skips simulation because no testbench matched: [OV9 run log](/tmp/claude-1000/-home-xpat-rtl2gdsagi-yosys/e0c7f0bc-5e69-4f9d-925f-42d79d055d7b/scratchpad/ov9/run.log:9).

With the external testbench directory selected:

| Bench | Result |
|---|---|
| mem_bram_tb | Compiles and prints SUCCESS |
| vga_driver_tb | Compiles and prints SUCCESS |
| cam_capture_tb | Elaboration failure |
| cam_init_tb | Nonexistent port |
| debounce_tb | Filename/top mismatch |
| sccb_master_tb | Syntax errors |

top_tb.sv is excluded by the default glob.

The register example has a real self-checking testbench. The runtime does not generate or repair testbenches, which is a useful safety property.

### EQY / LEC

Current EQY:

~~~
/usr/local/bin/eqy
EQY v0.68
~~~

The register example has real one-partition synthesis and route proofs:

- [synthesis LEC](/tmp/claude-1000/-home-xpat-rtl2gdsagi-yosys/e0c7f0bc-5e69-4f9d-925f-42d79d055d7b/scratchpad/reg4/run.log:23)
- [route LEC](/tmp/claude-1000/-home-xpat-rtl2gdsagi-yosys/e0c7f0bc-5e69-4f9d-925f-42d79d055d7b/scratchpad/reg4/run.log:93)

OV7670’s real synthesis LEC failed closed with 11 proved and 38 unknown. Later OV runs skipped both LEC stages. No OV GDS is formally certified.

## 9. Runtime autonomy vs Claude Code development

Exactly 20 preserved attempt API files exist. Every one records:

~~~
model: scripted
confidence: 0
config_delta: {}
response: <scripted>
~~~

No preserved real run demonstrates:

- a live Claude response;
- a model-generated configuration delta;
- a meaningful same-stage retry;
- automatic upstream rollback;
- downstream invalidation and rerun;
- real duplicate avoidance;
- confidence-based experiment or escalation;
- QoR improvement.

Observed development instead followed:

~~~
EDA failure
→ Claude Code reads source/log
→ Claude Code edits renderer/parser
→ fresh run
~~~

Hold repair, filler insertion, routing bounds, DRC hardening, LVS hardening, and antenna parser repairs are developer changes, not runtime autonomy.

## 10. Test-suite assessment

~~~
349 passed in 3.27s
349 collected
0 skipped
0 xfailed
~~~

Approximate classification:

| Category | Tests |
|---|---:|
| Schema/render/config/characterization | 159 |
| Parser/deck/report fixtures | 120 |
| Architecture/safety/agent contracts | 51 |
| Mock state-machine integration | 19 |
| Real-tool tests invoked by pytest | 0 |

Strengths include broad renderer/schema coverage, useful KLayout fixtures, and mock rollback/escalation scenarios.

Weaknesses include excessive fake-tool dependence, fixtures that encode implementation assumptions, reversed guardband expectations, fake colon routing syntax, and no end-to-end real remediation tests.

Important missing negative tests include:

- missing STA analysis and non-finite values;
- DRC nonzero exit plus stale report;
- partial DRC rule inventory;
- real route syntax and multiple iterations;
- nonzero or contradictory LEC PASS;
- zero-partition LEC;
- truncated LVS;
- one-sided/duplicate antenna output;
- no-result simulation;
- automatic skip at signoff;
- future-stage rollback;
- Tcl injection;
- changed artifacts;
- true resume;
- full candidate-lineage mismatch.

The tests provide useful regression confidence, not strong certification confidence.

## 11. Security and safety

### Prompt injection

Raw evidence is included verbatim in [prompts.py](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/agent/prompts.py:105). Logs can contain attacker-controlled source lines, names, paths, and diagnostics.

The model has no direct shell/filesystem tool and only returns diagnosis JSON. That is a real restriction. Impact remains because its output can control executable Tcl, rollback target, timing conditions, and simulation selection.

Required boundary:

~~~
raw artifacts
→ deterministic structured parser
→ normalized facts with trust labels
→ LLM diagnosis
→ strict causal-policy validation
→ allowlisted semantic delta
~~~

### Execution

Positive:

- no shell=True;
- argv lists;
- timeouts;
- read-only OpenROAD PDK mount.

Negative:

- unrestricted Tcl field;
- weak path/identifier quoting;
- full environment inherited;
- no process-group cleanup;
- Docker network enabled;
- no resource/capability/root-filesystem hardening;
- writable extra mounts.

### Safety claims

| Claim | Disposition |
|---|---|
| Cannot rewrite RTL for physical failure | Currently true by absence of RTL edit path |
| Cannot weaken SDC | False |
| Cannot directly waive decks | Mostly true at field level, but evidence paths bypass checks |
| Cannot suppress timing | False through guardband/SDC/corners |
| Cannot edit PDK/decks | Not robustly OS-enforced |
| Cannot extend own budget | True for budget object; budget scope misleading |
| Cannot certify skipped hard gates | False for automatic simulation skip |

## 12. Autonomous-agent assessment

The project is best described as:

> A scripted RTL-to-GDS orchestrator with an agentic diagnosis/rollback prototype.

It is more than a static shell script because it contains an agent loop, centralized diagnosis, causal-policy data, IR deltas, rollback calls, and budgets.

Its preserved demonstrated behavior remains scripted automation. It is not currently:

- an autonomous failure-remediation system;
- an autonomous QoR optimizer;
- a safe autonomous certification system.

Autonomous cross-stage causal remediation has **not** been experimentally demonstrated.

## 13. Research contribution assessment

Potentially interesting ideas include:

- rollback policy represented as data;
- diagnosis separated from deterministic verdict types;
- schema-shaped configuration proposals;
- centralized diagnostics;
- fail-closed report parsing as a research goal;
- artifact-bound signoff as a principle;
- diagnosis-guided physical experiments.

Current ordinary elements include sequential tool orchestration, deterministic templates, retries, JSON state, regex parsing, and fixed OpenROAD repair recipes.

A defensible research claim still needs:

- sound implementation of guarantees;
- immutable candidate lineage;
- multiple nontrivial benchmarks;
- injected failures with known causal truth;
- fixed-script/random/heuristic baselines;
- ablations;
- recovery/cost/QoR/false-certification metrics;
- immutable retained artifacts;
- independent reproduction.

The project should not be called AGI.

## 14. Top 10 next actions

1. Disable or relabel clean:true as experimental completion, not signoff.
2. Build an immutable release-candidate manifest.
3. Make every hard parser complete and fail closed.
4. Remove model authority over verification conditions.
5. Eliminate executable schema strings and constrain causal targets.
6. Replace guessed SDC with reviewed intent and real MCMM.
7. Repair simulation and LEC non-vacuity.
8. Rebuild checkpoint/resume semantics with immutable attempts.
9. Close OV testbench, EQY, li.3, and m2.x blockers using controlled experiments.
10. Only then run benchmarked research evaluation with independent signoff comparison.

## 15. Final answer

### What Claude Code did well

- Built substantial real-tool integration.
- Implemented all 21 stages and a coherent CLI.
- Centralized diagnosis and represented failure policy as data.
- Separated Diagnosis and Verdict types.
- Added useful DRC/LVS/GDS parsers and fixtures.
- Found several genuine false-clean conditions.
- Preserved generated scripts and detailed logs.
- Achieved a real 21-stage register run.
- Drove OV7670 through substantial real physical implementation.
- Used argv execution, atomic state writes, a run-local RTL copy, and read-only Docker PDK mount.

### What Claude Code got wrong

- Equated “model does not instantiate Verdict” with “model cannot cause PASS.”
- Overstated fail-closed verification.
- Implemented status aggregation rather than candidate-bound signoff.
- Exposed executable Tcl through the schema.
- Allowed model override of failure taxonomy and rollback.
- Used guessed and incomplete timing constraints.
- Reversed guardband semantics.
- Allowed automatic functional-verification skips to certify.
- Claimed resume without state restoration.
- Created checkpoint copies restore does not use.
- Mixed historical and current run metrics.
- Presented developer repairs adjacent to runtime-autonomy claims.

### What remains unproven

- Live LLM diagnosis in a real failure;
- same-stage autonomous remediation;
- cross-stage causal rollback;
- safe duplicate avoidance across restarts;
- confidence-aware automation;
- full OV simulation and LEC;
- valid MCMM timing;
- candidate-bound DRC/LVS/antenna/STA/LEC;
- generalization;
- autonomous QoR optimization;
- production reproducibility and sandboxing.

### What would be required before trusting autonomous GDS certification

- zero known P0/P1 false-clean paths;
- a complete immutable release-candidate manifest;
- every hard gate bound to that manifest;
- no skipped/unknown certification;
- validated timing intent and MCMM;
- non-vacuous simulation and formal equivalence;
- complete DRC/LVS/antenna evidence;
- deterministic allowlisted model actions;
- correct persistent checkpoints;
- OS-enforced immutable ground truth;
- independent negative testing and fault injection;
- several nontrivial reproducible designs;
- external signoff cross-checks showing no false clean.

Until those conditions are met, rtl2gdsagi should be treated as a promising experimental orchestration platform—not as an autonomous signoff authority.
