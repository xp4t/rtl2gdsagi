# Replay stratified accounting audit

## Material Passport

Origin: academic-research-suite / experiment-agent, validate mode. Date: 2026-10-13. Verification status: ANALYZED. Internal read-only artifact accounting; no external peer review.

## Draft-ready finding

Excluding the archived timing-passing state timing_1_proposal2 (+1.586 ps setup WNS), the frozen timing replay contains 13 proposal states: 12 fail signoff setup STA and one fails placement with DPL-0036. All 20 reconstructed replay inputs are consistent with archived defaults and logged changes. Separately, seven proposal states match independently retained archived full IR records: three DRC finals, three PDN finals, and timing_1_proposal2. No independent complete IR record was found for the other 13 proposal states in the inspected archival artifacts; retained attempt snapshots contain individual IR sections. The seven full IR matches are exact before adding routing.num_threads=1, which is absent from the archived schema.

## Denominators

| Stratum | States | Frozen outcome |
|---|---:|---|
| All proposals | 20 | 6 certified, 13 signoff setup STA failures, 1 placement failure |
| DRC | 3 | 3 certified |
| PDN | 3 | 3 certified |
| Timing before exclusion | 14 | 13 signoff setup STA failures, 1 placement failure |
| Excluded archived pass | 1 | timing_1_proposal2; frozen signoff setup failure |
| Timing after exclusion | 13 | 12 signoff setup STA failures, 1 placement failure |
| All cohorts after exclusion | 19 | 6 certified, 12 signoff setup STA failures, 1 placement failure |

The placement failure is `timing_3_proposal4` (DPL-0036). It does not provide a signoff timing result for that state. All retained STA failures are setup failures; all have positive hold WNS. Counts refer to proposal states, not native stage executions.

## Twenty-state availability accounting

The reconstruction starts with source18d defaults, then applies characterization seeds, config overrides, logged deltas, and deterministic repair notes in order. In each PDN episode, the logged changes `pdn.strap_offset_um 50.0 -> 21.42` and `floorplan.core_utilization 0.35 -> 0.29` precede the model proposal. The earlier pilot omitted these corrections and explicitly marks itself excluded. Only `frozen_proposal_replay_complete_ir_20261013` outcomes are counted.

All 20 reconstructed states, after the explicit addition of `routing.num_threads=1`, equal the replay YAML IR and retained run_state config IR; every YAML SHA-256 also matches the manifest. Each proposal delta equals its archived runstream delta. This checks reconstruction consistency.

Separately, 447 JSON files in the nine archived episode directories were searched recursively, including superseded snapshots; the two study manifests were also inspected. The seven final cases have 36 complete IR occurrences across signoff and certification/repair summaries. Those copies represent seven proposal case labels and 4 distinct IR dictionaries. All seven raw reconstructed archived IR dictionaries exactly match retained final IR records.

| Proposal state | Independent archived full IR availability | Frozen result |
|---|---|---|
| `drc_1_proposal1` | Exact match: `runs/live_drc_study/drc_1/signoff.json#/ir` | none |
| `drc_2_proposal1` | Exact match: `runs/live_drc_study/drc_2/signoff.json#/ir` | none |
| `drc_3_proposal1` | Exact match: `runs/live_drc_study/drc_3/signoff.json#/ir` | none |
| `pdn_1_proposal1` | Exact match: `runs/live_repair_study/pdn_1/signoff.json#/ir` | none |
| `pdn_2_proposal1` | Exact match: `runs/live_repair_study/pdn_2/signoff.json#/ir` | none |
| `pdn_3_proposal1` | Exact match: `runs/live_repair_study/pdn_3/signoff.json#/ir` | none |
| `timing_1_proposal1` | Not found in inspected archival artifacts | signoff setup sta |
| `timing_1_proposal2` | Exact match: `runs/live_repair_study/timing_1/signoff.json#/ir` | signoff setup sta |
| `timing_2_proposal1` | Not found in inspected archival artifacts | signoff setup sta |
| `timing_2_proposal2` | Not found in inspected archival artifacts | signoff setup sta |
| `timing_2_proposal3` | Not found in inspected archival artifacts | signoff setup sta |
| `timing_3_proposal1` | Not found in inspected archival artifacts | signoff setup sta |
| `timing_3_proposal2` | Not found in inspected archival artifacts | signoff setup sta |
| `timing_3_proposal3` | Not found in inspected archival artifacts | signoff setup sta |
| `timing_3_proposal4` | Not found in inspected archival artifacts | placement DPL-0036 |
| `timing_3_proposal5` | Not found in inspected archival artifacts | signoff setup sta |
| `timing_3_proposal6` | Not found in inspected archival artifacts | signoff setup sta |
| `timing_3_proposal7` | Not found in inspected archival artifacts | signoff setup sta |
| `timing_3_proposal8` | Not found in inspected archival artifacts | signoff setup sta |
| `timing_3_proposal9` | Not found in inspected archival artifacts | signoff setup sta |

The missing records are identified case by case in the table and JSON. Their availability remains unestablished beyond the inspected artifacts. Attempt `effective_ir` snapshots store only `ir_section`, as source18d `runner.py:1929` shows. Combining sections with defaults or runstream deltas is reconstruction, not independent complete-state storage. The JSON contains every inspected section snapshot path and its values.

The archived schema has no `routing.num_threads` key. Consequently, literal effective frozen dictionaries do not equal archived full IR dictionaries key for key. The exact seven matches compare the raw archived reconstruction with the archived record before adding the worker field. A claim that all 20 states independently matched archived full IR is unsupported.

## Archived pass and CTS padding

The archived pass is `timing_1_proposal2`, archived runstream line 195. Its cumulative IR retains synthesis `DELAY0` from proposal 1; proposal 2 sets density 0.55 and padding 1. Its native archived setup WNS is 0.0015860646578364705 ns (+1.5860646578364705 ps), hold WNS 0.343179799846767 ns. Frozen setup WNS is -0.000653699335387172 ns (-0.653699335387172 ps), hold WNS 0.34082815312507253 ns. Both native logs match the corresponding runstream metrics.

Archived CTS/routing scripts omit placement padding; frozen scripts apply `set_placement_padding -global -left 1 -right 1`. Retained controlled padding/thread interventions report:

| CTS padding | Routing padding | Workers | Setup WNS (ps) |
|---|---|---:|---:|
| off | off | 1 | 1.586064658 |
| off | off | 8 | 1.586064658 |
| off | on | 1 | 9.867662522 |
| off | on | 8 | 9.867662522 |
| on | off | 1 | -0.653699335 |
| on | off | 8 | -0.653699335 |
| on | on | 1 | -0.653699335 |
| on | on | 8 | -0.653699335 |

For this recorded state, CTS padding changes the sign under both routing-padding settings; worker counts one/eight agree within each setting. These are existing native results, not experiments run by this audit. Their exact manifest, source identity, native log, script, and configuration paths/digests are in the JSON. This supports a narrow CTS-padding exclusion rationale.

## Timing controls for scripted comparison

| Protected field | Effective timing value |
|---|---|
| `sdc.default_clock_period_ns` | `3.0` |
| `sdc.clock_uncertainty_ns` | `0.25` |
| `sdc.input_delay_frac` | `0.2` |
| `sdc.output_delay_frac` | `0.2` |
| `sdc.output_load_pf` | `0.05` |
| `sta.corners` | `["tt_025C_1v80"]` |
| `sta.derate_setup` | `0.0` |
| `sta.derate_hold` | `0.0` |
| `sta.slack_guardband_ns` | `0.0` |
| `extraction.corner` | `"nom"` |
| `extraction.min_net_coverage` | `0.5` |

All five SDC fields, STA corners/derates/guardband, and extraction targets listed above are `agent_writable=False`. `repair/executor.py:31` rejects unauthorized SET_IR_VALUE targets, `ir.py:373` rejects agent updates, and `safety.py:150` protects SDC targets. None of the 14 timing proposal deltas changes these protected values. Native SDC bytes agree across the three archived timing episodes and all 14 frozen states: period 3.0000 ns, uncertainty 0.2500 ns, input/output delays 0.6000 ns, output load 0.0500 pF. Shared SDC SHA-256: `f5825d3500ceee7248efad76a89a21ce68f0cf63cbd1bcb6b55ebbb9669a954f`.

Actual checker code at archived `checks/tools.py:682` sets `limit = abs(guardband)` and fails required slack if missing, nonfinite, or less than the limit. Here guardband is 0.0 ns, so signoff requires finite setup and hold WNS >= 0.0 ns. Post-CTS gates hold; pre-layout setup is advisory. CTS setup/hold repair margins of 0.05 ns are optimization targets, not the signoff guardband. Thus +1.586 ps passes and -0.654 ps fails.

The initial timing control uses AREA0, resource sharing true, placement density 0.45/padding 2, core utilization 0.30, and the protected values above. Scripted comparisons should declare whether they start from this initial control or a cumulative proposal state, while holding source af31, PDK/corner, constraints, extraction, and worker count fixed. The ongoing 24-state baseline is outside this audit.

| Timing proposal | Logged delta |
|---|---|
| `timing_1_proposal1` | `{"synthesis": {"strategy": "DELAY0"}}` |
| `timing_1_proposal2` | `{"placement": {"padding_sites": 1, "target_density": 0.55}}` |
| `timing_2_proposal1` | `{"synthesis": {"strategy": "DELAY0"}}` |
| `timing_2_proposal2` | `{"cts": {"fix_setup": true}, "placement": {"target_density": 0.4}}` |
| `timing_2_proposal3` | `{"placement": {"target_density": 0.45}}` |
| `timing_3_proposal1` | `{"synthesis": {"strategy": "DELAY1"}}` |
| `timing_3_proposal2` | `{"placement": {"routability_driven": true, "target_density": 0.55}}` |
| `timing_3_proposal3` | `{"synthesis": {"strategy": "DELAY3"}}` |
| `timing_3_proposal4` | `{"placement": {"padding_sites": 4, "target_density": 0.45}}` |
| `timing_3_proposal5` | `{"placement": {"padding_sites": 2, "target_density": 0.4}}` |
| `timing_3_proposal6` | `{"placement": {"padding_sites": 1, "target_density": 0.55}}` |
| `timing_3_proposal7` | `{"placement": {"routability_driven": true, "target_density": 0.45}}` |
| `timing_3_proposal8` | `{"placement": {"routability_driven": true, "target_density": 0.6}}` |
| `timing_3_proposal9` | `{"cts": {"fix_setup": true}, "synthesis": {"share_resources": false}}` |

## Native report and rollback accounting

Each frozen failure was matched against the manifest, runstream, retained native log, and the generated script SHA-256 recorded by its attempt configuration. All four native STA metric values agree exactly; the placement log contains DPL-0036. After failed signoff and default rollback, the failed reports move to `superseded/000`. Final state counters may show zero STA attempts despite a retained failed native check.

All 20 replay runstreams have zero API calls and zero generated configuration updates. No API/manual repair/retry limit one still permits default rollback to repeat native stages. The repeated executions do not create new proposal states.

| Proposal | Setup WNS (ns) or error | Retained native log |
|---|---:|---|
| `timing_1_proposal1` | -0.07915623935920589 | `runs/frozen_proposal_replay_complete_ir_20261013/timing_1_proposal1/stages/14_sta_signoff/superseded/000/attempt_01.log` |
| `timing_1_proposal2` | -0.000653699335387172 | `runs/frozen_proposal_replay_complete_ir_20261013/timing_1_proposal2/stages/14_sta_signoff/superseded/000/attempt_01.log` |
| `timing_2_proposal1` | -0.07915623935920589 | `runs/frozen_proposal_replay_complete_ir_20261013/timing_2_proposal1/stages/14_sta_signoff/superseded/000/attempt_01.log` |
| `timing_2_proposal2` | -0.041820326163549845 | `runs/frozen_proposal_replay_complete_ir_20261013/timing_2_proposal2/stages/14_sta_signoff/superseded/000/attempt_01.log` |
| `timing_2_proposal3` | -0.07915623935920589 | `runs/frozen_proposal_replay_complete_ir_20261013/timing_2_proposal3/stages/14_sta_signoff/superseded/000/attempt_01.log` |
| `timing_3_proposal1` | -0.2713258583495269 | `runs/frozen_proposal_replay_complete_ir_20261013/timing_3_proposal1/stages/14_sta_signoff/superseded/000/attempt_01.log` |
| `timing_3_proposal2` | -0.312995860311291 | `runs/frozen_proposal_replay_complete_ir_20261013/timing_3_proposal2/stages/14_sta_signoff/superseded/000/attempt_01.log` |
| `timing_3_proposal3` | -0.6762770534990955 | `runs/frozen_proposal_replay_complete_ir_20261013/timing_3_proposal3/stages/14_sta_signoff/superseded/000/attempt_01.log` |
| `timing_3_proposal4` | DPL-0036 | `runs/frozen_proposal_replay_complete_ir_20261013/timing_3_proposal4/stages/09_placement/superseded/000/attempt_01.log` |
| `timing_3_proposal5` | -0.4121745283966747 | `runs/frozen_proposal_replay_complete_ir_20261013/timing_3_proposal5/stages/14_sta_signoff/superseded/000/attempt_01.log` |
| `timing_3_proposal6` | -0.3026776692732113 | `runs/frozen_proposal_replay_complete_ir_20261013/timing_3_proposal6/stages/14_sta_signoff/superseded/000/attempt_01.log` |
| `timing_3_proposal7` | -0.2985811682410925 | `runs/frozen_proposal_replay_complete_ir_20261013/timing_3_proposal7/stages/14_sta_signoff/superseded/000/attempt_01.log` |
| `timing_3_proposal8` | -0.34236259241080386 | `runs/frozen_proposal_replay_complete_ir_20261013/timing_3_proposal8/stages/14_sta_signoff/superseded/000/attempt_01.log` |
| `timing_3_proposal9` | -0.34236259241080386 | `runs/frozen_proposal_replay_complete_ir_20261013/timing_3_proposal9/stages/14_sta_signoff/superseded/000/attempt_01.log` |

Archived passing native log: `runs/live_repair_study/timing_1/stages/14_sta_signoff/attempt_01.log`.

## Provenance

| Source path | Python-tree SHA-256 |
|---|---|
| `runs/reviewer_followup_20261013/repair_cohort_source/src` | `18d948815ac6d0af630a5440578304dc9270e1be659c602b5aa7149f40aab22b` |
| `runs/frozen_evaluation_20261013/frozen_source/src` | `af31b39f67827a3375c52bf41f52a727130947f8b5716d80b2680c7de88ca06c` |
| `src` | `af31b39f67827a3375c52bf41f52a727130947f8b5716d80b2680c7de88ca06c` |

These legacy tree identities hash sorted src-relative Python path bytes, NUL, and raw file bytes; they do not cover every resource or tool/environment dependency. Canonical IR digests hash sorted compact JSON (UTF-8, ensure_ascii=False). File byte digests are separately recorded below and throughout the JSON.

| Primary source/evidence path | File SHA-256 |
|---|---|
| `scripts/run_frozen_proposal_replay.py` | `e28d46354daf37eb74cb9d38ae5030d03369019f0d4ea82e5c95234bcd239b15` |
| `scripts/run_live_repair_study.py` | `e183f222d2350458b3b5e46a77819d4bbe94f35aeb5c3bd94714586aac8d2064` |
| `scripts/run_signoff_benchmark.py` | `e657f4f9e5dc4af220efcd7723a5a0153908cf311cc5172583ef990b48c4ef53` |
| `rtl2gdsagi_paper/evidence/repair_study.json` | `8fc957dbfb688bc91c1fe9c22ed3919758873769747fcba64f1b717a18e1508d` |
| `runs/live_repair_study/experiment_manifest.json` | `9a395c5e35cd0f97be3ab4a714fd919e34e7c72c4c26baee921747cbdfcd421f` |
| `runs/live_drc_study/experiment_manifest.json` | `5f8018119b94916484b770c9cd748cd602aa82fbd5f8506aa019ed61dd4f9548` |
| `runs/frozen_proposal_replay_complete_ir_20261013/experiment_manifest.json` | `6f32abd4776e21def1be8acf4c255bb0e4976345c9b45a71b49e64bd985255e9` |
| `runs/frozen_proposal_replay_20261013/experiment_manifest.json` | `11d76eb83b883612c2eaaf05d0089b993a3ada9116aee1bd721000edaba0c2b3` |
| `runs/frozen_evaluation_20261013/experiment_manifest.json` | `f31e0f0c09fd3cffa61db24a5139441ad2b9318ea10a4a9ce9f114c92426fd60` |
| `runs/padding_thread_ablation_20261013/experiment_manifest.json` | `d80ebf48979d984c73e55c25de638915a1c2ffc5f1e2af41c01f117539c1774a` |
| `benchmarks/signoff/alu8_timing_3ns.yaml` | `37cb2aeddf86cc5705d46b40c80fdcecf3028f3d29337e46f1bd1f5658b9c3ea` |
| `rtl2gdsagi_paper/evidence/source_repair_cohort.tar.gz` | `7d7a02efea6c45d5978756906878dab7f94f5c94e5fc7298a66148783713623f` |
| `rtl2gdsagi_paper/evidence/source_frozen_20261013.tar.gz` | `69208729d9e0bc45c2cbcedb920cb8d44c892853364add02b8a61fadd029f899` |

| Independent final IR record | File SHA-256 | Canonical full IR SHA-256 |
|---|---|---|
| `runs/live_drc_study/drc_1/signoff.json#/ir` | `0fce154025c7fe591bf0a0d1793a9b17cc16fdf7817b6e9612bb3ce99d01cefa` | `b159f970afed12a2ad52df72c1f20dfbf246d3718a5c63578fb7dba5dd52b6ab` |
| `runs/live_drc_study/drc_2/signoff.json#/ir` | `14bc22ba7b6b2b461828b4cb74e8c18befd3763e629e659b999bec945fe0d66d` | `b159f970afed12a2ad52df72c1f20dfbf246d3718a5c63578fb7dba5dd52b6ab` |
| `runs/live_drc_study/drc_3/signoff.json#/ir` | `813d1c2dede864b07396b0e51af104d96c22ec8ff4195e51525891642177f869` | `83731c7bc244aafa11a9ece3e01b1fabbc9e41e3361c4d4404fb57ef6351d5dc` |
| `runs/live_repair_study/pdn_1/signoff.json#/ir` | `637fa6ac87d100dd6be7e90ce128040ff40c6fa5146688498b8ebe70b5f35678` | `26433cc3766c9c0cf1da8adef56d5b3039473f37f81bb894003b7d33b0f90c19` |
| `runs/live_repair_study/pdn_2/signoff.json#/ir` | `96bedfc7aab1921f2586a23db7db819c7e16d1aff026c4fffc03e838cac18ce7` | `26433cc3766c9c0cf1da8adef56d5b3039473f37f81bb894003b7d33b0f90c19` |
| `runs/live_repair_study/pdn_3/signoff.json#/ir` | `2b9cc20ab04bd0149717dccaa6b6bc5c6903d4c1b9965f7ca6719b1ce76fc083` | `26433cc3766c9c0cf1da8adef56d5b3039473f37f81bb894003b7d33b0f90c19` |
| `runs/live_repair_study/timing_1/signoff.json#/ir` | `56cad6654eef838d1196fd4c26cb791d2b118ff23aa7c8ae02e6f4da9353ef7a` | `975d413cd6c5fa21e331e102778dccc0971a047bd4e0d5e1bbb96581206012ae` |

Machine-readable companion: [replay_stratified_audit.json](/home/vlsi/rtl2gdsagi/rtl2gdsagi_paper/evidence/replay_stratified_audit.json). It includes the exact twenty-state mapping, reconstructed full states and digests, retained complete IR pointers, scanned archival paths, section snapshots, native script/log bindings, protected values, and all audited file byte digests.

## Limits

- Internal artifact accounting, not external peer review or a new EDA reproducibility run.
- No EDA rerun, model API, formal/tool rerun, literature lookup, manuscript edit, or reading of other new review reports.
- Availability is scoped to the retained JSON artifacts in the nine archived cohort episode directories, including superseded snapshots. Not found does not prove that no other record ever existed.
- Full IR copies in signoff/certification/verified repair summaries represent the same seven final case states; they do not add independent proposal states.
- Section snapshots plus defaults/logged changes support reconstruction but do not establish an independently stored complete IR.
- These are cumulative adaptive proposal states; repeated dictionaries and replicate labels must not be treated as 20 independent statistical samples.
- Failure counts use retained native result_check events before rollback, not final counters reset to zero.
- The pilot replay omitted deterministic PDN corrections and is excluded from all outcome counts.
- Manifest source_sha256 covers Python files only. Individual source and evidence file digests are supplied; this audit does not assert full environment identity.
- Padding attribution is limited to the retained intervention results for this archived timing-passing state.
- The running 24-state scripted baseline is outside this audit; no baseline outcomes are certified here.

This is deterministic accounting; no inferential test, population success-rate claim, or baseline superiority conclusion is made.
