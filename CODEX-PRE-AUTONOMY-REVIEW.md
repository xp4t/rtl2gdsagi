# Codex Pre-Autonomy Independent Review

Audit date: 2026-08-14  
Repository snapshot: `/home/xpat/rtl2gdsagi`

This review was performed without changing implementation source, installing packages, running a new full RTL-to-GDS job, or inspecting any runtime-model credential. The five requested documents were read completely before the code and preserved artifacts were inspected. Existing real-tool artifacts were preferred over rerunning expensive stages.

## 1. Executive verdict

**Verdict: NO, IMPORTANT FIXES REQUIRED.**

The repository is materially better than the snapshot described in `results.md`. The routing and antenna parsers now consume the real OpenROAD forms, timing guardband and missing-metric handling were corrected, simulation/LEC skips block certification, CTS Tcl injection through `root_buffer` is closed, 20 fixtures are genuinely captured real output, the release manifest really does re-hash its bound files, and the preserved register run contains substantial real-tool evidence.

It is nevertheless **not ready for a controlled live-model autonomy experiment**. I found **11 P0** paths that can produce false certification or let a future model change what is measured, and **10 P1** correctness/safety defects. Four are sufficient independently to answer the governing question:

1. A diagnosis may change any schema section, including timing intent and testbench selection, while the orchestrator retries only the taxonomy/proposed stage. Deterministic code accepts routing diagnoses that lengthen the clock, select a weaker testbench, or alter STA corners.
2. Same-stage retries do not retire attempt outputs. I reproduced a full clean pipeline in which routing attempt 2 wrote no DEF and the system certified attempt 1's stale DEF under attempt 2's changed IR.
3. Several hard gates still equate tool completion or minimal syntax with semantic proof: PDN accepts a one-byte DEF; extraction accepts a wrong-design, zero-net SPEF; DRC accepts one declared rule; LVS accepts a severely truncated database; LEC accepts explicit error/later-fail contradictions.
4. The claimed clean register LVS contains three explicit top-level `VGND` must-connect messages whose own text says they are errors at chip top level. The parser treats every warning as nonblocking, so the reference result must be withdrawn pending resolution or authoritative adjudication.

The correct current autonomy status is:

```text
live runtime-model autonomy = NOT YET TESTED
```

That status is not itself a defect. The blocker is that the deterministic containment and verification platform is still unsafe to place behind a live diagnostic model.

### Readiness summary

| Area | Confidence | Assessment |
|---|---:|---|
| Exact captured success formats | Moderate-high | The 20 fixtures are authentic and useful |
| Comprehensive fail-closed parsing | Low | 15 verdict-relevant patterns still lack positive captured-real evidence; new false-cleans remain |
| Release manifest | Low-moderate | Real content hashes and re-verification, but incomplete required identity and gate binding |
| Cross-stage rollback, in-process | Moderate | State/history/ledger/file invalidation works in the tested cross-stage path |
| Same-stage retry | Low | Reproducible stale-output certification |
| Model write surface | Unacceptable | Verification intent and unrelated sections remain writable |
| Autonomy harness | Low | Scripted result is honest today; future live attribution and ground-truth grading are not trustworthy |
| Production signoff methodology | Low | Single typical corner, generated constraints, no MCMM/OCV/IR/EM |

### Snapshot and test result

The requested Git snapshot could not be established. `.git/` exists but is empty, and all three commands report that the directory is not a repository:

```text
git status                 fatal: not a git repository
git diff                   not a git repository
git log --oneline -n 20    fatal: not a git repository
```

This means current status, uncommitted changes, and the claimed `382 -> 454` historical delta cannot be independently reconstructed from VCS. The current suite is independently verified:

```text
command     .venv/bin/python -m pytest -q -ra
collected   454
passed      454
failed      0
skipped     0
xfailed     0
runtime     11.45 s
```

`pytest --collect-only -q` independently reported `454 tests collected in 0.09s`. The three claimed new groups also exist at the stated sizes:

```text
tests/test_real_tool_parsers.py   48 collected, 48 passed
tests/test_provenance.py          13 collected
tests/test_autonomy_safety.py     11 collected, 11 passed
```

Current `454` is verified; historical `382` is unverified without history.

## 2. Verification of latest claims

| Claim | Verified? | Evidence | Notes |
|---|---|---|---|
| 454 tests pass | **YES** | Normal pytest run: 454/454 in 11.45 s | Passing tests do not close the findings below |
| 48 real-parser, 13 provenance, 11 safety tests | **YES** | Independent collection of the three files | The safety and provenance suites miss production-path bypasses |
| 29 verdict-bearing regexes | **NO** | AST inventory found 49 compiled regexes under `checks/`; 41 affect a verdict or PASS prerequisite | The claim has no reproducible counting convention |
| 11 checker entry points | **CONVENTION-DEPENDENT** | Ten external-evidence checkers; eleven only if runner-local `_judge_sdc` is included | Publish the convention |
| 25 parsers validated against captured output | **MOSTLY** | 25/41 have a positive captured-real syntax match if two real deck fixtures are credited | Case 03 corroborates one more error form; 15 remain without sidecar-backed positive real evidence |
| 20 real fixtures and 20 sidecars | **YES** | 40 files under `tests/fixtures/real` | Nineteen text/DB fixtures match their sources after documented path substitution; GDS is byte-identical |
| Fixture provenance is sufficient and independent | **PARTIAL** | [test_real_tool_parsers.py:61](/home/xpat/rtl2gdsagi/tests/test_real_tool_parsers.py:61) checks six fields for non-emptiness | Sidecars omit source/fixture hashes, argv, return code, candidate ID, and PDK/deck identity; tests do not assert `expected.verdict` |
| Placement parser now recognizes real Nesterov output | **YES, WITH GAPS** | [_OR_OVERFLOW](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/tools.py:633), real terminal value at [attempt_01.log:105](/home/xpat/rtl2gdsagi/benchmarks/autonomy/runs/case_03_routing_layer_range/stages/09_placement/attempt_01.log:105) | No Nesterov evidence still PASSes; scientific notation is misparsed |
| New placement threshold semantics are correct | **PARTIAL** | IR default 0.15 at [ir.py:244](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/ir.py:244); real terminal 0.099774 | Reasonable empirical advisory, but it is density overflow, not global-route overflow, and the tool stop target is implicit |
| CTS skew parser now uses real output | **PARTIAL** | Real table pattern at [tools.py:669](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/tools.py:669) records 0.03/0.07 ns on the fixture | Missing skew and 9.99 ns both PASS; clock identity/count and `target_skew_ns` are not enforced |
| Release manifest binds GDS/netlists/SPEF/SDC/DEF/config/IR | **MOSTLY** | [BOUND_ARTIFACTS](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/manifest.py:40) and deterministic identity at [manifest.py:124](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/manifest.py:124) | It binds their current bytes when present, but signoff only requires GDS+SDC; RTL, testbench, reports, scripts and full PDK are absent |
| PDK and tool identity are bound | **PARTIAL** | [manifest.py:127](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/manifest.py:127), [_VERSION_PROBES](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/manifest.py:51) | PDK is four strings, not content; OpenROAD/OpenSTA/container identity are missing |
| Bound files are re-hashed at signoff | **YES** | [manifest.verify](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/manifest.py:151); tamper tests at [test_provenance.py:54](/home/xpat/rtl2gdsagi/tests/test_provenance.py:54) | A different-content symlink replacement is caught at verification; small post-verification TOCTOU risk remains |
| Candidate ID is deterministic | **YES** | Sorted canonical JSON at [manifest.py:135](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/manifest.py:135) | `created_at` is correctly excluded |
| Attempt fingerprints include rendered script, PDK and design identity | **PARTIAL** | [fingerprint_attempt](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checkpoints.py:95), runner call at [runner.py:1183](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:1183) | PDK/design are path/structural facts, not content; tool versions, TB contents and actual LVS inputs are missing |
| Rollback removes all stale active outputs | **FALSE** | Cross-stage retirement at [runner.py:924](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:924); retry calls it only if target differs at [runner.py:1261](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:1261) | Same-stage stale output was reproduced and certified |
| Register reaches all 21 real stages with the stated metrics | **NUMERICALLY YES** | Preserved [result.json](/home/xpat/rtl2gdsagi/benchmarks/autonomy/runs/case_03_routing_layer_range/result.json), raw logs and reports | The run is not independently clean because LVS reports three top-level must-connect errors |
| Register is clean under the implemented methodology | **NO** | [lvs.lvsdb:176](/home/xpat/rtl2gdsagi/benchmarks/autonomy/runs/case_03_routing_layer_range/stages/17_lvs/lvs.lvsdb:176) through line 178 | Parser/sidecar share an invalid warning-severity assumption |
| OV7670 is NOT signoff clean | **YES** | Real fixture sidecars identify 11 proved/38 unknown and 1 `m2.x`; [NEXT-PHASE-RESULTS.md:389](/home/xpat/rtl2gdsagi/NEXT-PHASE-RESULTS.md:389) | LEC is from `ov10`, DRC from `ov11`; not one candidate lineage |
| Case 03 proves a real-tool scripted retry | **YES** | [attempt_01.log:21](/home/xpat/rtl2gdsagi/benchmarks/autonomy/runs/case_03_routing_layer_range/stages/12_routing/attempt_01.log:21), [attempt_02.log:170](/home/xpat/rtl2gdsagi/benchmarks/autonomy/runs/case_03_routing_layer_range/stages/12_routing/attempt_02.log:170), [attempt_01_api.json](/home/xpat/rtl2gdsagi/benchmarks/autonomy/runs/case_03_routing_layer_range/stages/12_routing/attempt_01_api.json) | It proves no model autonomy and no cross-stage rollback |
| Case 03 injects routing congestion | **NO** | Renderer creates `clock met3-met2` at [render.py:574](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/render.py:574); OpenROAD reports `GRT-0056` | It is an illegal rendered layer range/Tcl configuration error before routing |
| Case 01 is a schema-valid cross-stage benchmark | **NO** | YAML sets 0.92 at [case_01:8](/home/xpat/rtl2gdsagi/benchmarks/autonomy/case_01_floorplan_utilization.yaml:8); schema maximum is 0.90 at [ir.py:210](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/ir.py:210) | It cannot run as written |
| 6/6 unsafe proposals are structurally rejected | **YES, NARROWLY** | [test_autonomy_safety.py:41](/home/xpat/rtl2gdsagi/tests/test_autonomy_safety.py:41) | Production runner accepts cross-section and semantic verification-intent bypasses absent from these cases |
| Live runtime-model autonomy has been demonstrated | **NO** | Preserved result is `agent: scripted`, `autonomy_evidence: false` | Correct status: NOT YET TESTED |

## 3. New findings

### P0 — false certification or corrupted ground truth

#### P0-01 — Model-write authorization does not match the prompt or rollback graph

**Affected code:** [runner.py:812](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:812), [runner.py:868](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:868), [runner.py:891](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:891), [runner.py:912](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:912), [safety.py:139](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/safety.py:139).

The prompt says the model may write only the failed stage's section, but the response parser and `IR.apply_delta` accept any schema section. `review_diagnosis` is called without `allowed_stage`, the model may choose any implicated stage at or before the failing stage, and the full multi-section delta is applied without computing its earliest causal stage.

Direct deterministic reproductions:

```text
routing + {sdc.default_clock_period_ns: 100}       ACCEPTED
routing + {sim.testbench_glob: one_known_pass_tb} ACCEPTED
setup   + implicated extraction + optimistic STA corner  ACCEPTED
```

For setup/hold, changing `sdc` is blocked, but model-writable `sta.corners`, derates, guardband, extraction corner, and simulation selection remain. [PDKConfig.liberty_for_corner](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/pdk.py:180) silently falls back to the default Liberty for an unknown requested corner.

**Why it matters:** the model can indirectly manufacture PASS by changing verification intent or can change an upstream section while only a downstream stage reruns. Candidate IR/config then describes evidence that was never regenerated. Raw tool text is sent unsanitized into the prompt at [prompts.py:105](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/agent/prompts.py:105), so prompt injection has a concrete impact path.

**Required correction:** freeze user verification intent from model writes; define per-failure/per-stage field allowlists; reject unrelated/multi-section piggyback deltas; deterministically derive rollback from the earliest stage affected by every accepted field; constrain a diagnosis target to the taxonomy's authorized causal window.

#### P0-02 — Same-stage retry certifies stale outputs

**Affected code:** `_execute` does not pre-clear outputs at [runner.py:550](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:550); `_rollback` retires files at [runner.py:924](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:924); same-stage retries skip `_rollback` at [runner.py:1261](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:1261).

Reproduction: routing attempt 1 wrote DEF/netlist/report and returned seven violations; a scripted same-stage delta changed `droute_iters`; attempt 2 emitted a clean terminal routing log but wrote no output. Result:

```text
pipeline rc                0
routing attempts           2
artifact IR fingerprint    d6e27947...  (attempt 1)
current IR fingerprint     dd00454b...  (attempt 2)
same                       false
superseded/ exists         false
signoff clean              true
```

**Required correction:** give each attempt an isolated output directory or retire every expected output before every invocation, including same-stage retries; inability to retire must hard-fail, not warn and continue; register outputs only if creation identity proves they came from the current attempt.

#### P0-03 — Signoff is still status aggregation, not candidate-evidence verification

**Affected code:** [runner.py:1281](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:1281), [runner.py:1330](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:1330), [runner.py:1350](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:1350), [manifest.py:200](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/manifest.py:200).

The manifest re-hashes bound files correctly, but signoff requires only `final_gds` and `sdc`. Missing netlist, routed netlist, DEF, SPEF, design facts, and all report artifacts are allowed. `gate_binding_problems` checks a hash only if a history record happens to contain one. In the preserved run, only DRC and LVS carry `checked_gds_sha256`; STA, antenna, extraction, routing and route LEC carry no dependency hashes.

Direct construction with all gate states marked OK, empty history, and only two registered files containing `not a gds` and `not sdc` produced:

```text
clean true
problems []
bound ['final_gds', 'sdc']
```

That direct construction is not the normal CLI path, but it proves the aggregator cannot independently validate its state. P0-01 and P0-02 provide reachable ways for normal runtime state and evidence to diverge.

**Required correction:** define required artifacts and evidence per gate; bind every report and its exact inputs; require gate candidate/dependency IDs rather than optional hashes; re-parse or cryptographically attest each authoritative result at aggregation; include original RTL/testbench identity and reject any missing required binding.

#### P0-04 — Unconstrained signoff endpoints can certify

**Affected code:** [tools.py:600](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/tools.py:600), [runner.py:1223](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:1223), [runner.py:1290](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:1290).

`check_sta` returns `qor_below_target` with `ok=True` for any nonzero unconstrained endpoint count. `_attempt_stage` accepts any `ok` verdict, and signoff requires explicit `PASS` only for simulation and LEC, not STA. Reproduction with valid positive setup/hold numbers and 99 unconstrained endpoints returned:

```text
kind=qor_below_target  ok=True  unconstrained_endpoints=99
```

The comment assumes such endpoints are constant-driven; no deterministic proof establishes that.

**Required correction:** fail closed at post-CTS/signoff for unconstrained endpoints unless each endpoint has a deterministic, report-bound constant/no-timing-arc proof under an explicit policy.

#### P0-05 — PDN hard gate has no semantic postcondition

**Affected code:** claimed outputs/criteria at [stages.py:227](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/stages.py:227), actual outputs at [runner.py:225](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:225), renderer at [render.py:415](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/render.py:415), generic checker at [tools.py:737](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/tools.py:737).

What constitutes PDN PASS today is: OpenROAD return code zero, no recognized error line, and a nonempty `pdn_def`. The declared `pdn_report` is never mapped or written; `ir_drop_budget_mv` is unused. A one-byte file with an empty log returned `pass: pdn completed`.

**Why it matters:** a grid with missing rails, floating stripes, absent via stacks, disconnected standard-cell/macro PG pins, or no top-level supply connectivity can certify. The register LVS warnings show this is not merely theoretical.

**Required correction:** at minimum, deterministically prove both supply nets exist; followpin rails and required orthogonal straps/vias exist; every standard-cell and macro PG pin is connected through the configured voltage domain to an intended top/domain supply terminal; and no PG component is floating. IR drop/current density/EM are separate analyses and must remain explicitly unverified unless implemented.

#### P0-06 — Extraction accepts meaningless SPEF

**Affected code:** [render.py:646](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/render.py:646), generic output check at [tools.py:737](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/tools.py:737).

A nonempty file is sufficient. A header-only SPEF naming the wrong design and containing zero `*D_NET` records returned `pass: extraction completed`. Truncated and one-byte files do too.

This was also reproduced through the real pinned OpenROAD environment, not only through a unit call. OpenROAD read the preserved register routed DEF/SDC plus a header-only, zero-net SPEF, emitted `[WARNING STA-0179] ... syntax error, unexpected $end`, exited zero, and still printed setup WNS `+6.978177788677701` and hold WNS `+1.226061731288495`—the same values as the no-parasitic/post-CTS analysis. `check_sta` recognizes only `Error:`/`ERROR:` at [tools.py:446](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/tools.py:446), ignores that SPEF parse warning, and returned PASS. A malformed/no-parasitics SPEF can therefore pass both extraction and authoritative signoff timing.

**Required correction:** parse and validate SPEF magic/version/units/design name, finite values, section termination, a nonzero net inventory, and consistency against the exact routed DEF/netlist (with explicit permitted exclusions); require real RCX completion/net-count evidence and bind extraction rules/corner. After `read_spef`, require zero parser/annotation warnings and deterministic nonzero annotation coverage before accepting STA.

#### P0-07 — Reference register LVS contains unhandled top-level connectivity errors

**Affected evidence:** [lvs.lvsdb:176](/home/xpat/rtl2gdsagi/benchmarks/autonomy/runs/case_03_routing_layer_range/stages/17_lvs/lvs.lvsdb:176), [lvs_summary.json:23](/home/xpat/rtl2gdsagi/benchmarks/autonomy/runs/case_03_routing_layer_range/stages/17_lvs/lvs_summary.json:23), parser at [klayout_lvs.py:163](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/klayout_lvs.py:163).

The real database has three severity-`W` messages for CTS clock buffers saying their `VGND` must-connect subnets must be connected further up and that this is an error at chip top level. The parser blocks only severity `E`, and the sidecar itself says PASS. The reference/extracted top subcircuits expose `VGND` but not `VPWR` at [register.reference.spice:168](/home/xpat/rtl2gdsagi/benchmarks/autonomy/runs/case_03_routing_layer_range/stages/17_lvs/register.reference.spice:168) and [register.extracted.cir:3](/home/xpat/rtl2gdsagi/benchmarks/autonomy/runs/case_03_routing_layer_range/stages/17_lvs/register.extracted.cir:3).

**Required correction:** withdraw the register clean label; resolve PG topology/reference-netlist construction, then rerun. If foundry/KLayout semantics establish a benign exception, encode a narrowly version/deck/message-scoped deterministic policy with explicit evidence, never “all warnings pass.”

#### P0-08 — LVS accepts a severely truncated real database

**Affected code:** [klayout_lvs.py:153](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/klayout_lvs.py:153).

The parser requires magic, a top, one `X(` cross-reference, clean exit and a match log, but no complete database grammar/termination. Truncating the 199,053-byte real register database just after its first `X(` at 30,955 bytes returned:

```text
clean=True  xref_circuits=1
```

**Required correction:** reopen/validate the completed database through KLayout or implement full structural/terminal validation; reconcile one coherent terminal comparison result.

#### P0-09 — DRC accepts a partial one-rule run

**Affected code:** [klayout_drc.py:222](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/klayout_drc.py:222).

Runtime requires only a nonempty category list. A valid report containing one dummy category and zero items returned:

```text
clean=True  declared_categories=1  total_violations=0
```

The real reference reports have 211 categories, but count alone is insufficient.

**Required correction:** bind an approved deck content hash and validated tool/image version to an expected category-name inventory/hash; fail on missing, duplicate, or substituted groups.

#### P0-10 — LEC accepts explicit errors and later terminal failure

**Affected code:** [tools.py:338](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/tools.py:338), [tools.py:355](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/tools.py:355), [tools.py:423](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/tools.py:423).

`_EQY_DONE.search()` selects the first terminal outcome, and explicit EQY errors are examined only after the PASS branch. Both reproduced as PASS:

```text
proved partition + ERROR: internal inconsistency + DONE (PASS)
DONE (PASS) followed by DONE (FAIL)
```

**Required correction:** require exactly one final coherent terminal result; reject any explicit error before PASS; reject output after the terminal marker; reconcile partition counts and return code.

#### P0-11 — LVS deck guard does not prove a reachable failure path

**Affected code:** [deck_guard.py:89](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/deck_guard.py:89).

The guard searches for `compare`, a failure phrase and `exit` anywhere. It marks this trustworthy:

```ruby
if false
  if ! compare
    logger.error("Netlists don't match")
    exit(1)
  end
end
logger.info("Netlists match")
```

**Required correction:** pin the approved deck by content identity. Regex token presence is not Ruby control-flow or reachability proof.

### P1 — major correctness, safety or benchmark-integrity defects

#### P1-01 — Placement evidence omission and numeric forms fail open

[tools.py:758](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/tools.py:758) enters placement logic only when a metric matched. No Nesterov output returns PASS. The number regex `[\d.]+` reads `9.9774e-02` as `9.9774`, reads `1.0E-01` as `1.0`, and treats `nan` as no metric/PASS. The main fake pipeline still emits obsolete `Total overflow:` at [tests/conftest.py:343](/home/xpat/rtl2gdsagi/tests/conftest.py:343), so its happy path never exercises the real metric.

Require a version-bound completion marker and finite terminal density-overflow value. Treat metric absence as UNKNOWN/failure for the authoritative completion contract. Rename the advisory: this is placement-density overflow, not global-route overflow.

#### P1-02 — CTS quality fields are telemetry/no-ops

[tools.py:788](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/tools.py:788) records real-shaped skew rows but never compares them to [cts.target_skew_ns](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/ir.py:254). No table and no no-path message PASSes; a real-shaped 9.99 ns skew PASSes. `max_fanout` and `balance_levels` are also unused. The fake pipeline still emits the obsolete `Worst clock skew:` form at [tests/conftest.py:345](/home/xpat/rtl2gdsagi/tests/conftest.py:345).

Do not invent a universal skew gate when no launch/capture pair exists. Require scoped per-clock structural CTS evidence (root, sinks, inserted buffers, connectivity), record why skew is unavailable, compare finite skew where meaningful, and let post-CTS/signoff STA remain timing authority.

#### P1-03 — GDS scanner counts incomplete elements

[gds.py:147](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/gds.py:147) increments the element count on `BOUNDARY` before seeing `LAYER`, `XY` or `ENDEL`. A top containing one incomplete boundary is considered nonempty; with no layers, [runner.py:413](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:413) skips layer-map checking.

Enforce GDS record state and element completeness, require meaningful mapped geometry, and reopen the produced stream with KLayout before certification.

#### P1-04 — Attempt/checkpoint identity and persistence remain incomplete

Positive: the live attempt fingerprint includes section config, consumed input hashes, rendered script and a causal environment. Negative:

- tool/image versions and PDK file contents are absent;
- `rtl_dir` is registered as an unhashed directory and `design_facts` is structural metadata, not an RTL-content hash;
- simulation does not hash testbench contents;
- actual LVS uses routed netlist/CDL/deck, while its StageSpec/fingerprint declares synthesis netlist;
- several renderers consume SDC through the global context without declaring it as an input hash;
- [CheckpointStore.save](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checkpoints.py:150) stores the original artifact path even after copying it, and saves a weaker fingerprint without script/causal environment;
- checkpoint/failure maps are not loaded by `Orchestrator`, so duplicate detection/resume are in-process only;
- retirement errors are warning-only at [runner.py:990](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:990).

Publish a complete causal-input contract per stage; hash source/TB/PDK/deck/CDL/tool identities; store and restore checkpoint copies; persist fingerprints; fail if any declared input/output is missing.

#### P1-05 — No runtime parser-version contract

`ToolRun` has no tool version field at [tools.py:23](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/checks/tools.py:23). The OpenROAD container tag is pinned, which is good, but native tools may vary and the manifest omits OpenROAD/OpenSTA. Fifteen verdict-relevant patterns have no sidecar-backed positive captured-real example after crediting case 03's real OpenROAD error.

Bind authoritative parsers to validated tool/image ranges. Unknown/unvalidated versions should fail closed for hard gates; advisory telemetry may return explicit UNKNOWN, never PASS by omission.

#### P1-06 — Autonomy-result attribution and evidence are not auditable

[run_case.py:120](/home/xpat/rtl2gdsagi/benchmarks/autonomy/run_case.py:120) labels a future result from an ambient credential-presence boolean, not evidence that a model call occurred. A clean/no-diagnosis run can be labeled live. The harness never grades success criteria, always returns zero at [run_case.py:160](/home/xpat/rtl2gdsagi/benchmarks/autonomy/run_case.py:160), and records only five diagnosis fields at [run_case.py:143](/home/xpat/rtl2gdsagi/benchmarks/autonomy/run_case.py:143). Runner audit stores a placeholder prompt at [runner.py:853](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:853).

Use an explicit `scripted`/`live_model` mode. `autonomy_evidence=true` must require an actually recorded non-scripted call, provider/model metadata, request/response or privacy-preserving hashes, structured evidence/delta/safety/target, case/config/source/revision IDs, and a deterministic ground-truth evaluator. Propagate failure via exit status.

#### P1-07 — Benchmark output path can delete arbitrary trees

[run_case.py:78](/home/xpat/rtl2gdsagi/benchmarks/autonomy/run_case.py:78) recursively deletes any user-supplied `--run-dir` with no containment check. A typo can remove the repository, source RTL, or a writable PDK tree.

Resolve and require descendants of a dedicated benchmark-results root; refuse root/repository/RTL/PDK targets; use recoverable or uniquely created directories.

#### P1-08 — Benchmark ground truths are invalid or uncalibrated

Case 01's 0.92 injection is schema-invalid. Case 03 triggers a renderer legality hole, not congestion. Case 04 disables a hold repair that the preserved register route says was a no-op; signoff hold is already +1.177 ns. Cases 02 and 04 have no preserved calibration/control.

Calibrate every case on real tools, preserve control runs, demonstrate the asserted downstream failure, and compare same-stage alternatives before declaring a unique shallowest causal rollback.

#### P1-09 — Multi-clock SDC and corner semantics can misstate timing coverage

[render_sdc](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/render.py:70) assigns all nonclock inputs and all outputs to the first discovered clock, with no domain ownership or asynchronous clock groups. [render_sta](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/render.py:289) reads multiple Liberty files into one analysis rather than true MCMM, and unknown names silently map to the default Liberty.

For controlled experiments, require user-reviewed per-domain timing intent and reject unknown corners. Until MCMM/OCV exists, call the result **clean under the implemented single-corner methodology**, never production signoff.

#### P1-10 — Immutable zones and tool containment are not enforcement boundaries

`ImmutableZones.check_write` is called only while copying RTL at [runner.py:150](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/runner.py:150). Native EDA tools see the host filesystem; the full host environment is inherited at [tools/invoker.py:111](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/tools/invoker.py:111). OpenROAD's PDK mount is correctly read-only at [tools/invoker.py:160](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/tools/invoker.py:160), but the container retains default network/root filesystem/capability/resource behavior, and timeout cleanup does not explicitly kill a process group/container.

Validate `run_root` outside immutable zones before creating it; use an environment allowlist; sandbox native tools or mount inputs read-only in a constrained container; disable unnecessary network/capabilities; set CPU/RAM/PID limits; clean process trees on timeout.

### P2/P3 observations

- A failing current stage generally remains `running` because top-level escalation finishes the run without setting that stage `failed`; `StageState.last_verdict` is omitted from serialization at [state.py:76](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/state.py:76).
- `--resume-from` creates a new orchestrator/ledger rather than loading a prior run; the documented durable checkpoint story is not connected to the CLI.
- Run IDs have one-second precision at [state.py:218](/home/xpat/rtl2gdsagi/src/rtl2gdsagi/state.py:218), and directories use `exist_ok`, allowing concurrent collision.
- The absence of MCMM/OCV/IR/EM is a methodology limitation, not by itself a software bug. The bug is terminology that implies more coverage than exists.
- README mixes historical OV7670 generations (929 and 939 cells, different routing/timing values), says all false-clean paths are closed, and claims the register is clean. Those statements are now false or misleading.
- Missing Git metadata prevents an independently attributable snapshot and historical `382 -> 454` comparison.

## 4. Parser campaign assessment

### Independent inventory and methodology

I counted every `re.compile()` under `src/rtl2gdsagi/checks` with an AST inventory, then traced whether each match can change a `VerdictKind` or satisfy a PASS prerequisite. This avoids both undercounting helper patterns and inflating the number with non-verdict formatting regexes.

```text
compiled regexes under checks/                         49
  checks/tools.py                                      39
  checks/klayout_lvs.py                                 6
  checks/deck_guard.py                                  4

reachable verdict/PASS-prerequisite regexes            41
positive matches in traceable captured-real fixtures   25
additional real case-03 corroboration                    1 (_OR_ERR)
without sidecar-backed positive real evidence           15

external-evidence checker APIs                          10
checker count if runner-local _judge_sdc is included    11
semantic-check-free/effectively weak stages              5
```

The ten external checker APIs are `check_lint`, `check_sim`, `check_synthesis`, `check_lec`, `check_sta`, `check_openroad`, `parse_drc_report`, `parse_lvs_report`, `read_gds`, and `audit_deck`. Calling the total eleven is defensible only if `_judge_sdc` is explicitly included.

The 15 remaining unsupported positive-real classes include Verilator error/warning forms, simulation failure, several Yosys error/cell/latch forms, EQY not-equivalent/error, STA no-clock/unconstrained/error, OpenROAD placement failure, and LVS mismatch. Some have good synthetic negative tests, but they are not independently grounded in captured output.

### Every real fixture

| Tool | Payload(s) inspected | Authenticity result | Semantic limitation |
|---|---|---|---|
| Verilator | `lint_clean.log` | Source-located and path-normalized only | Success only; failure/warning forms not captured |
| Icarus | `sim_pass.log` | Authentic 13-byte `TEST PASSED` output | Text alone does not bind design/TB; preserved register run supplies that context |
| Yosys | `synthesis_ok.log` | Source-located and path-normalized only | Test pairs it with a newly created dummy netlist, not captured output netlist |
| EQY | `lec_pass_1_partition.log`, `lec_fail_unknown_partitions.log` | Both source-located and path-normalized only | No captured contradictory/mismatch/error-terminal example |
| OpenSTA | pre, post-CTS, signoff met logs | All source-located and path-normalized only | Success coverage; no captured parser-warning/no-clock/unconstrained case |
| OpenROAD | antenna clean; CTS skew/no-path; floorplan; placement; two routing logs | All source-located and path-normalized only | CTS clock identities are not checked; placement/CTS absence still PASS |
| KLayout | two DRC DBs, merged GDS, LVS log and DB | GDS byte-identical; text/DB path-normalized only | LVS fixture embeds the erroneous warning-to-PASS assumption; DRC does not bind expected category inventory |

There are exactly **20 payloads and 20 JSON sidecars** spanning 15 stage IDs. All 19 text/database payloads are byte-identical to their preserved source after only the documented scratch/home path substitutions; the GDS is byte-identical. This is a strong result: they are not synthetic snippets labeled “real.”

The provenance is nevertheless self-attested rather than tamper-evident. Sidecars should add source SHA-256, fixture SHA-256, actual argv/return code, capture timestamp, candidate ID, PDK/deck identity and tool image. The test at [test_real_tool_parsers.py:61](/home/xpat/rtl2gdsagi/tests/test_real_tool_parsers.py:61) only requires fields to be nonempty, and no test consumes `expected.verdict`. Most importantly, the LVS sidecar says PASS while the payload itself says three conditions are errors at chip top level. That is the exact implementation/test/fixture shared-assumption failure this campaign was meant to detect.

### Placement overflow forensics

The old parser assumption was wrong. Real OpenROAD prints iterative lines such as:

```text
[NesterovSolve] Iter: ... overflow: ...
[NesterovSolve] Finished with Overflow: 0.099774
```

The corrected implementation collects the series and prefers the explicit final line. For the preserved register run, `0.099774` is real and the parser selects it. It does not mistakenly use the initial roughly `0.65` value.

The threshold needs more precise semantics:

- This value is **global-placement density overflow**, not global-routing overflow.
- OpenROAD's stop target/default is not explicitly rendered, so it is tool-version behavior rather than a project-pinned contract.
- The project limit `0.15` is a soft empirical QoR advisory. It is directionally reasonable for the observed `~0.10` terminal value and should not be presented as a physical legality/signoff threshold.
- The separate `TotalRouteOverflowH2/V2` congestion telemetry is not parsed.
- Missing metric/completion evidence must not fall through to PASS, and numeric parsing must support scientific notation with finite-value checks.

### CTS skew forensics

The old phrase `Worst clock skew:` did not occur in real output. The replacement pattern matches the captured `Latency / CRPR / Skew` table and records worst skew `0.07 ns` across the two fixture rows; this syntax correction is valid for the pinned environment.

What the project actually proves about CTS quality is much weaker:

- `report_clock_skew` may legitimately say no launch/capture paths; this means unavailable, not zero.
- The parser does not retain the clock name or expected clock count.
- Table rows are matched globally rather than scoped beneath a known clock-table header.
- Missing telemetry still PASSes.
- A parsed `9.99 ns` skew still PASSes.
- `cts.target_skew_ns`, `max_fanout`, and `balance_levels` do not affect verdict/rendered behavior as their descriptions imply.

A sound contract should require per-clock structural `report_cts` facts (root, sink count, buffers, connectivity), scope finite skew to the correct clock when a comparable path exists, record explicit unavailable reasons, and rely on post-CTS/signoff STA for timing authority.

### Cross-version policy

The current runtime has no mapping from tool/image version to parser contract. The pinned OpenROAD image is a valuable control, but its identity is not passed into `ToolRun` or the release manifest; native tools can drift.

Recommended policy:

```text
approved tool/image version + fixture-validated parser contract -> authoritative verdict
unknown/unvalidated version -> fail closed for a hard gate
unknown advisory telemetry -> explicit UNKNOWN/warning, never implicit PASS
```

**Parser validation confidence: moderate for the exact captured success formats; low for comprehensive fail-closed certification.**

## 5. PDN assessment

### What currently constitutes PDN PASS?

```text
OpenROAD exit code == 0
AND no recognized [ERROR ...] line
AND pdn_def exists and is nonempty
```

Nothing parses the DEF or OpenDB for power connectivity. The stage declaration promises a `pdn_report` and IR-drop check, but `_outputs_for` emits only `pdn_def`; the renderer runs `pdngen`, writes DEF and exits. `ir_drop_budget_mv` is dead configuration.

### Can a physically useless PDN pass?

**Yes.** A one-byte file passes. So would a syntactically valid DEF with only one supply, no followpin rails, disconnected vertical/horizontal straps, absent via stacks, or macro PG pins not connected to the intended domain. Later DRC does not prove electrical connectivity; current LVS warning handling is demonstrably insufficient.

### Minimum meaningful structural postcondition

A fail-closed minimum can be implemented without pretending to provide IR/EM signoff:

1. Reopen the actual post-PDN database/DEF and prove the expected top and voltage domains.
2. Require both configured power and ground SPECIALNETS.
3. Require standard-cell followpin rails on the intended layer and the configured stripe/ring layers.
4. Verify required inter-layer via stacks and no floating PG components.
5. Traverse every standard-cell and macro PG ITerm to an intended top/domain supply terminal.
6. Emit a structured report containing counts, disconnected objects, layers and hashes of its input database/PDK contract.

IR drop, current density and EM need current/source/activity models and are outside the present methodology. Documentation must say they are unverified.

**Severity: P0**, because the stage is hard, normal runtime certifies a semantically empty result, and the preserved LVS evidence already shows unresolved PG questions.

## 6. Extraction assessment

Current extraction verification is insufficient. The stage accepts any nonempty file after a clean OpenROAD invocation. It does not validate:

- SPEF magic/version/units;
- `*DESIGN` against the configured top;
- nonzero/completed `*D_NET` sections;
- net-name/count coverage against routed DEF/netlist;
- finite R/C values;
- complete termination rather than truncation;
- extraction rule/corner identity;
- actual parasitic annotation coverage in STA.

The real-tool reproduction is decisive: a header-only, zero-net SPEF produced only an OpenROAD warning, positive setup/hold numbers from an effectively unannotated design, and deterministic STA PASS. Therefore presence plus `read_spef` in Tcl is not evidence that parasitics were used.

For the preserved valid register artifact, independently observed evidence is stronger but currently unused:

```text
SPEF *DESIGN    register
SPEF *D_NET     35
routed DEF nets 35
OpenROAD log    extraction completed for the routed design
```

Required minimum: a real SPEF parser with top/units/grammar/finite-value/net-coverage checks; exact routed-candidate binding; expected RCX completion/net-count markers; and a post-read annotation report proving nonzero/high coverage with no SPEF parser warnings. A stale SPEF is substantially mitigated by cross-stage output retirement and manifest hashing only after the same-stage defect and complete identity binding are fixed.

**Severity: P0.**

## 7. Manifest assessment

### What is genuinely enforced

The manifest is not merely decorative JSON:

- It content-hashes seven artifact keys when present: final GDS, routed netlist, synthesis netlist, SPEF, SDC, routed DEF and design facts.
- It hashes effective config and the IR fingerprint.
- Candidate identity uses sorted canonical JSON and excludes `created_at`.
- `verify()` reopens every bound path and recomputes SHA-256.
- Missing or changed bound files are reported.
- In the preserved register run, all seven artifact hashes match current disk contents and candidate ID independently recomputes to `14fe9d5880497d7f12dfcd88b70136df4d06009dfee95753da682a2fa0ed879a`.

Different-content symlink replacement is caught because the current target bytes are rehashed. Path aliasing with identical bytes is not a meaningful identity change. There is a residual local TOCTOU interval between sequential rehash and writing certification; it is low in a single controlled process but not eliminated by snapshotting or file-descriptor pinning.

### What is not enforced

- Signoff requires only final GDS and SDC.
- Absent bound keys are encoded as absent and accepted.
- Gate reports/logs are not bound.
- Gate input hashes are optional; only DRC/LVS record GDS SHA in the reference run.
- The manifest does not bind original RTL or testbench content.
- `design_facts` contains paths/coarse facts, not an RTL tree hash. A logic change preserving coarse facts can keep the same design-facts identity; identical RTL at a different path changes it.
- PDK identity is only name/root/library/corner strings. Liberty, LEF, cell GDS, layer map, RCX rules, CDL/formal models and DRC/LVS decks are not content-hashed; PDK overrides are omitted.
- Tool probes omit OpenROAD, OpenSTA and container image/digest—the tools producing physical and timing evidence.
- `verify()` does not require a bound artifact to remain in the current ledger.
- A fresh manifest is built at signoff, but stale state/ledger from retry or future resume can still be faithfully hashed and mislabeled as current evidence.

### Assessment

The manifest correctly answers “did these named files change after registration?” It does **not** yet answer “did every hard gate prove this exact release candidate with this exact ground truth and tool contract?”

**Manifest confidence: low-moderate.** Useful foundation, insufficient certification mechanism.

## 8. Fingerprint assessment

### Correct behavior

Direct checks confirm:

```text
same config/inputs/script/environment -> same fingerprint
rendered script change               -> different fingerprint
upstream declared artifact hash      -> different fingerprint
timestamps                            -> excluded
```

Hashing the rendered script is a good design choice because it captures cross-section renderer reads that are actually rendered.

### Missing causal inputs

The identity is not yet the effective experiment:

- no tool binary/container identity;
- no PDK/deck/library/model content identity;
- no canonical RTL tree hash;
- no testbench file-content hashes;
- no actual LVS routed-netlist, reference SPICE, CDL or deck hash;
- stage declarations omit SDC for placement/CTS/routing even though rendered Tcl reads it; script includes only its path, not content;
- missing consumed inputs are omitted instead of fatal;
- renderer preview exceptions collapse to an empty script;
- saved checkpoint freshness uses a weaker fingerprint than failed-attempt duplicate detection;
- duplicate-failure state is memory-only.

Cross-stage rollback also drops `design_facts` because characterize is not checkpointed, and `routed_netlist` can be lost because routing's StageSpec declares only `routed_def` while `_outputs_for` produces both. Signoff still accepts this because the missing keys are not required.

### Assessment

Fingerprinting is substantially improved for ordinary in-process retries, but does not yet guarantee either half of the desired invariant:

```text
same effective experiment -> same identity
materially different experiment -> different identity
```

**Fingerprint confidence: moderate for a single normal run, low across ground-truth/tool/source changes or persistence.**

## 9. Rollback assessment

### Cross-stage rollback

The current in-process cross-stage path is mostly sound:

```text
rollback target selected
-> checkpoint DAG invalidated from target
-> active ledger rebuilt from earlier valid checkpoints
-> all target/downstream StageState entries reset
-> target/downstream files moved under superseded/NNN
-> target/downstream history removed
-> execution resumes at target
```

The 13-test provenance file exercises state, history, files and downstream reruns. Inspection confirms active artifact paths do not point into `superseded/` in that case.

### Same-stage retry

The guarantee fails on the most common retry path. A target equal to the failed stage does not call `_rollback`, so outputs remain in place. The full reproduced pipeline certified attempt-1 output under attempt-2 IR when attempt 2 emitted a clean log but no file.

### Additional rollback/persistence gaps

- Failure to move a file logs a warning and continues, leaving a possible active stale file.
- Checkpoint copies are written but `Checkpoint.artifacts` retain original paths, so restore does not use the copies.
- Checkpoints and failed fingerprints are not wired into a persistent orchestrator resume.
- StageSpec/actual output mismatches cause artifacts such as `routed_netlist` to be omitted from checkpoints.
- `design_facts` disappears on cross-stage ledger rebuild.
- `last_verdict` and global verdict history are not persisted.

### Assessment

**Rollback confidence: moderate for a successful in-process cross-stage rollback; unacceptable for same-stage retries; low for process restart/resume.**

## 10. Golden register run

The preserved case-03 directory is real evidence, not a mock run. The table distinguishes numeric/tool execution from certification validity.

| Claim | Independent result | Evidence |
|---|---|---|
| All 21 stages reached; pipeline exit 0 | **Verified as recorded** | [result.json](/home/xpat/rtl2gdsagi/benchmarks/autonomy/runs/case_03_routing_layer_range/result.json) |
| Simulation executed and self-checked | **Verified** | TB checks reset, increment, input change and wrap at [register_tb.v:16](/home/xpat/rtl2gdsagi/examples/register/tb/register_tb.v:16); real log says PASS |
| Synthesis LEC | **Verified for one partition** | EQY proves `register.o_data` and reports terminal PASS at [attempt_01.log:22](/home/xpat/rtl2gdsagi/benchmarks/autonomy/runs/case_03_routing_layer_range/stages/05_lec_synth/attempt_01.log:22) |
| Placement overflow | **Verified** | Real terminal `0.099774` at [placement log:105](/home/xpat/rtl2gdsagi/benchmarks/autonomy/runs/case_03_routing_layer_range/stages/09_placement/attempt_01.log:105) |
| Routing | **Verified** | Attempt 2 real sequence `9 -> 2 -> 9 -> 0` and completion at [attempt_02.log:170](/home/xpat/rtl2gdsagi/benchmarks/autonomy/runs/case_03_routing_layer_range/stages/12_routing/attempt_02.log:170) |
| Extraction artifact | **Verified for this file** | `*DESIGN register`, 35 `*D_NET`; 18,863 bytes; hash matches manifest |
| Signoff STA numbers | **Verified as tool output** | Tcl reads routed DEF and SPEF at [sta_signoff.tcl:8](/home/xpat/rtl2gdsagi/benchmarks/autonomy/runs/case_03_routing_layer_range/stages/14_sta_signoff/sta_signoff.tcl:8); setup +6.9220227, hold +1.1772892 |
| GDS | **Verified structurally** | 135,082 bytes, 29 cells, 1,995 elements, mapped layers, no unresolved references in [gds_summary.json](/home/xpat/rtl2gdsagi/benchmarks/autonomy/runs/case_03_routing_layer_range/stages/15_gdsout/gds_summary.json) |
| DRC | **Verified under current deck invocation** | top `register`, 211 declared categories, zero items; FEOL/BEOL/offgrid/floating-metal flags recorded in [run.jsonl:83](/home/xpat/rtl2gdsagi/benchmarks/autonomy/runs/case_03_routing_layer_range/run.jsonl:83) |
| LVS | **Comparison ran, but clean verdict invalid** | rc 0, explicit match, 192 xrefs, plus three top-level must-connect errors |
| Antenna | **Verified for current syntax** | Real output has 0 net and 0 pin at [attempt_01.log:21](/home/xpat/rtl2gdsagi/benchmarks/autonomy/runs/case_03_routing_layer_range/stages/18_antenna/attempt_01.log:21) |
| Route LEC | **Verified for one partition** | EQY proves `register.o_data` and terminal PASS |
| Manifest bytes/candidate ID | **Verified** | Seven current hashes and canonical candidate recomputation match |

The recorded placement/routing/STA/GDS/DRC/antenna/LEC numbers are genuine. The correct conclusion is **not** “clean.” It is:

> The register design completed all 21 implemented stages with real tools and favorable recorded metrics, but certification is revoked because the LVS database contains unresolved top-level must-connect errors and the PDN/extraction/signoff contracts remain incomplete.

Even after those software/electrical issues are fixed, the strongest honest timing phrase is “clean under the implemented SKY130 single-corner methodology.” There is no MCMM, OCV or reviewed multi-domain signoff intent.

## 11. OV7670 state

The main status statement is correct:

```text
OV7670 = NOT SIGNOFF CLEAN
```

Preserved repository fixtures establish:

- synthesis LEC: 11 partitions proved, 38 unknown/unproved, terminal FAIL;
- simulation: no compatible configured testbench in the preserved run context;
- DRC: one `m2.x` item in a report declaring 212 categories;
- downstream LVS, antenna, route LEC and final signoff were not measured in that run.

Important lineage qualification: LEC evidence is labeled `ov10`; DRC evidence is `ov11`. The repository does not preserve one candidate manifest proving all blockers belong to the same exact generation. Each independently blocks certification, but their combination is a status summary, not a single-run release record.

Documentation is directionally honest in `NEXT-PHASE-RESULTS.md`, but README overstates and mixes generations:

- both 929 and 939 synthesized-cell counts;
- historical route/timing values alongside later runs;
- “everything through GDS” phrasing without the full required verification lineage;
- “nothing reads `i_sda_in`,” although the current RTL samples it; the more supportable statement is that its value appears functionally unobservable at a top output and synthesis removes its fanout.

No OV7670 GDS is certified, and documentation should keep every numeric claim labeled by run/candidate ID.

## 12. Autonomy harness assessment

### Preserved case 03

The stored result is unambiguous and honest:

```text
agent                 scripted
autonomy_evidence     false
diagnosis model       scripted
confidence            0.0
rollbacks             []
```

It cannot reasonably be mistaken for a live-model result today.

### Future attribution weakness

The harness's future label is not tied to an actual runtime-model call. It derives mode from ambient credential presence, records too little evidence, does not grade its own ground truth, and always exits zero. A run with zero diagnoses can therefore acquire a live label. The actual prompt is not persisted.

Required evidence contract:

```text
diagnosis_source = scripted | live_model
actual_model_call_count >= 1 for any live autonomy claim
provider/model/request metadata bound to result
structured evidence + response + accepted delta + safety verdict + rollback target
case/config/source/repository/candidate identities
deterministic ground-truth evaluation
nonzero harness exit when the case fails
```

### What case 03 proves

It proves:

1. a schema-valid-at-field-level injected setting reached a real OpenROAD invocation;
2. real OpenROAD produced `GRT-0056`;
3. deterministic code produced a failure verdict/class;
4. a **scripted** delta passed schema/safety validation;
5. the same stage reran with real tools;
6. terminal route violations reached zero and downstream stages ran.

It does not prove:

- model diagnosis;
- cross-stage causal reasoning;
- rollback or downstream invalidation (`rollbacks` is empty);
- stale-output safety (attempt 1 failed before producing routed output);
- congestion recovery—the failure was `clock met3-met2`, an illegal rendered configuration that should classify as Tcl/config legality.

**Autonomy-harness confidence: low for future claims, high that the preserved result itself is scripted.**

## 13. Case 01 assessment

Case 01 is not currently a legitimate cross-stage benchmark.

1. `floorplan.core_utilization=0.92` violates the schema maximum 0.90, so the case cannot reach a real floorplan.
2. The causal statement is asserted, not calibrated. On a tiny register, a legal high utilization may still route, or placement/routing knobs may solve the observed symptom without a floorplan rollback.
3. There is no preserved control sweep demonstrating:
   - floorplan succeeds;
   - a later stage fails;
   - reducing utilization repairs it;
   - permitted same-stage controls do not provide an equally shallow sufficient fix.

To become research evidence, choose a schema-valid calibrated injection, preserve multiple deterministic controls, establish the downstream failure distribution, and define success as choosing the shallowest sufficient causal target—not merely matching a YAML label.

Case 04 also lacks a valid causal injection for this design: the reference route says no hold violations were found, and signoff hold is strongly positive. Case 02 is plausible but uncalibrated.

## 14. Safety boundary assessment

### Boundaries that are genuinely structural

- Model output is parsed as structured diagnosis/IR, not accepted as a `Verdict` object.
- Unknown schema keys, nonfinite bounded numerics and unsafe cell-name syntax are rejected.
- The previous raw CTS cell-name Tcl injection is closed by a cell-identifier regex.
- Timing guardband now raises the required margin instead of relaxing it.
- SDC changes are blocked for deterministically classified setup/hold failures.
- DRC/LVS/antenna sections do not expose explicit waiver/skip fields.
- Simulation and both LEC gates require explicit PASS for certification; automatic skips block signoff.
- Iteration budget has no model-accessible extension mechanism.
- OpenROAD's container PDK mount is read-only; subprocesses use argv lists rather than `shell=True`.

### Boundaries that are not sufficient

- “The model can write only the current stage” is prompt text, not validator behavior.
- Verification intent remains writable through semantically powerful, innocuously named fields.
- Proposed stage selection is not constrained to the deterministic causal policy window.
- A changed section does not determine rollback.
- Raw adversarial tool/RTL text enters the model prompt.
- Tool processes inherit the full host environment rather than an allowlist.
- Immutable-zone checks do not mediate native tool writes or validate the run root.
- A future result can be labeled live without proof of a call.
- The six proposal cases are narrow: their forward-target check reimplements runner logic in the test instead of invoking production `_diagnose`, and their field-name sweep cannot see semantic weakening.

### Conclusion

The eventual live model's **syntactic** write surface is bounded, but its **semantic** authority is not. Deterministic `Verdict` construction does not compensate for letting the model choose clocks, corners, testbenches, extraction mode or inconsistent rollback. The live-model write surface is not sufficiently restricted for controlled testing.

## 15. Remaining P0/P1

### P0 count: 11

1. P0-01 — cross-section model deltas can weaken/change verification intent and misalign rollback.
2. P0-02 — same-stage stale outputs can be certified under a new attempt/IR.
3. P0-03 — signoff accepts status without complete candidate-bound gate evidence.
4. P0-04 — unconstrained signoff endpoints are advisory and can certify.
5. P0-05 — PDN hard gate is semantically vacuous.
6. P0-06 — malformed/zero-net SPEF passes extraction and real signoff STA.
7. P0-07 — current register LVS ignores three explicit top-level must-connect errors.
8. P0-08 — truncated LVS database after first cross-reference passes.
9. P0-09 — one-category zero-item DRC report passes.
10. P0-10 — LEC PASS can override explicit error/later FAIL.
11. P0-11 — deck guard mistakes unreachable token presence for a real failure path.

### P1 count: 10

1. P1-01 — placement evidence absence/scientific notation fails open; pipeline mock remains obsolete.
2. P1-02 — CTS quality/targets are not enforced.
3. P1-03 — malformed incomplete GDS elements count as geometry.
4. P1-04 — attempt/checkpoint/source/design identity and persistence are incomplete.
5. P1-05 — parser decisions are not bound to validated tool versions.
6. P1-06 — future autonomy attribution/evidence/ground-truth grading is unreliable.
7. P1-07 — arbitrary benchmark run directory can be recursively deleted.
8. P1-08 — cross-stage benchmark cases are invalid or uncalibrated.
9. P1-09 — multi-clock SDC and corner behavior can misstate timing coverage.
10. P1-10 — immutable zones/native/container execution are not complete enforcement boundaries.

## 16. Live-model recommendation

### NOT READY

Do not enable a live runtime diagnostic model yet. The blockers are deterministic-platform defects, not missing model capability.

Exact required actions, in order:

1. **Freeze verification intent.** Remove SDC targets, testbench selection, STA corners/derates/guardband, extraction signoff corner and all gate-selection semantics from the model write surface.
2. **Authorize deltas causally.** Add per-failure/per-stage field allowlists; reject unrelated sections; derive rollback from the earliest changed field; constrain model stage suggestions to a deterministic policy window.
3. **Isolate every attempt.** Use attempt-specific output directories plus atomic promotion, or hard-retire all expected outputs before every invocation. Add a regression reproducing attempt-1 output + attempt-2 no-output for each hard artifact stage.
4. **Repair extraction/STA evidence.** Implement the SPEF semantic/net-coverage parser, RCX completion contract and post-read annotation coverage; fail on SPEF warnings such as `STA-0179`.
5. **Implement a meaningful structural PDN gate.** Prove supply topology and PG connectivity; resolve the three register clock-buffer `VGND` must-connect errors and rerun LVS.
6. **Close parser P0s.** Reconcile final/unique LEC terminal results and errors; validate complete LVS DB structure; pin deck/category inventories; make signoff unconstrained endpoints fail closed; enforce GDS element completeness.
7. **Make signoff candidate-bound.** Require all release artifacts, original RTL/TB identity, reports/logs and exact consumed hashes; require one current PASS evidence record per gate and revalidate it.
8. **Complete ground-truth/tool identity.** Hash PDK decks/libs/LEFs/GDS/maps/RCX/CDL/models; bind OpenROAD/OpenSTA/container identities; add runtime version-parser contracts.
9. **Repair fingerprint/checkpoint persistence.** Canonical RTL/TB tree hashes, complete declared dependencies/outputs, one shared attempt/checkpoint fingerprint, durable failure/history/checkpoint state, and restore from checkpoint copies.
10. **Harden and calibrate the benchmark harness.** Explicit source mode, actual-call proof, complete audit evidence, deterministic success evaluator, contained output root, meaningful exit status, schema-valid real-tool-calibrated cases and controls.
11. **Rerun the register reference from scratch.** Require zero unresolved PG messages, valid SPEF coverage, complete candidate bindings and all adversarial negative regressions before restoring any clean label.
12. **Then run a narrow live experiment.** Start with one pre-calibrated case, no model filesystem/tool access, a small fixed budget, immutable verification intent, complete logging, and human review before any result is used as research evidence.

The absence of production MCMM/OCV/IR/EM does not prohibit controlled orchestration research once the P0/P1 software defects are closed. It does prohibit calling the result manufacturing-qualified or generic signoff.

---

### Final decision record

```text
Verdict:                        NO, IMPORTANT FIXES REQUIRED
P0 count:                       11
P1 count:                       10
New false-clean paths:          11 P0 paths listed above
Parser validation confidence:   MODERATE for captured formats; LOW for comprehensive fail-closed use
Manifest confidence:            LOW-MODERATE
Rollback confidence:            MODERATE cross-stage; LOW/UNACCEPTABLE same-stage
Autonomy-harness confidence:    LOW for future live attribution
Ready for API key locally:      NO
```

No runtime-model autonomy claim is made by this review.
