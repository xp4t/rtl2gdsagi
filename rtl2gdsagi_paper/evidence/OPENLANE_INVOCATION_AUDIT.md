# OpenLane invocation audit

## Material Passport

- Origin Skill: ARS experiment-agent; code_runner_agent role
- Origin Mode: run
- Origin Date: 2026-10-13T06:46:47.618201+00:00
- Verification Status: EXECUTED_BOUNDED_CONTROLS
- Version Label: openlane_invocation_audit_v1
- Delegation: inline execution; native subagent dispatch unavailable. No independent-agent judgement claim.

## Result and intended invocation

Pinned OpenLane and retained native sources match the downloaded official commit bytes. The stock KLayout DRC default is disabled (`RUN_KLAYOUT_DRC=0`); default Magic DRC remains outside this audit. Both installed PDK configs name the modern `_mr.drc` runset and its options, but omit the pinned wrapper's `KLAYOUT_DRC_TECH_SCRIPT`. The native wrapper forwards only input/report, with no rule flags or options translation. There is no confirmed stock active deck/flag pairing for this combination.

The shipped legacy `sky130A.lydrc` is compatible with that wrapper and byte identical across both PDK versions and public dependency-pinned source. Its built-in FEOL=false, BEOL=true, OFFGRID=true settings are exercised using an explicit deck override. This is a demonstrated compatible configuration, not a proven default selection.

The selected PDK's intended modern options are `feol=1 beol=1 offgrid=1 seal=1 floating_metal=0`. Direct runs map `floating_metal` to the deck variable `floating_met`. Native-stage adapter runs inject these values in an audit-only adapter and evaluate the original deck unchanged. The adapter is not stock OpenLane.

## Actual control counts

Categories count emitted report categories, including those with zero markers; it is not a certified rule inventory. Negative controls are nonempty synthetic geometry, clean only within the tested configurations.

| Configuration | Control | Exit | Categories | Markers | Marker categories |
|---|---|---:|---:|---:|---|
| stock_config_forced_stage_probe | metal_positive | 0 | None | None | none |
| prior_modern_native | metal_positive | 0 | 0 | 0 | none |
| legacy_native | metal_positive | 0 | 166 | 3 | m1.1: 2, m1.6: 1 |
| modern_direct_pdk_options | metal_positive | 0 | 220 | 3 | m1.1: 2, m1.6: 1 |
| modern_adapter_native | metal_positive | 0 | 220 | 3 | m1.1: 2, m1.6: 1 |
| prior_modern_native | metal_negative | 0 | 0 | 0 | none |
| legacy_native | metal_negative | 0 | 166 | 0 | none |
| modern_direct_pdk_options | metal_negative | 0 | 220 | 0 | none |
| modern_adapter_native | metal_negative | 0 | 220 | 0 | none |
| prior_modern_native | poly_positive | 0 | 0 | 0 | none |
| legacy_native | poly_positive | 0 | 166 | 0 | none |
| modern_direct_pdk_options | poly_positive | 0 | 220 | 1 | poly.1a: 1 |
| modern_adapter_native | poly_positive | 0 | 220 | 1 | poly.1a: 1 |
| prior_modern_native | poly_negative | 0 | 0 | 0 | none |
| legacy_native | poly_negative | 0 | 166 | 0 | none |
| modern_direct_pdk_options | poly_negative | 0 | 220 | 0 | none |
| modern_adapter_native | poly_negative | 0 | 220 | 0 | none |
| prior_modern_native | grid_positive | 0 | 0 | 0 | none |
| legacy_native | grid_positive | 0 | 166 | 4 | m1_OFFGRID: 4 |
| modern_direct_pdk_options | grid_positive | 0 | 220 | 4 | m1_OFFGRID: 4 |
| modern_adapter_native | grid_positive | 0 | 220 | 4 | m1_OFFGRID: 4 |
| prior_modern_native | grid_negative | 0 | 0 | 0 | none |
| legacy_native | grid_negative | 0 | 166 | 0 | none |
| modern_direct_pdk_options | grid_negative | 0 | 220 | 0 | none |
| modern_adapter_native | grid_negative | 0 | 220 | 0 | none |

## Obligations

SUPPORTED means the exact target rule passed violating/clean controls. NOTSUPPORTED identifies an inactive or absent obligation in the named interface/configuration. NOTASSESSED marks wider or unexecuted coverage. Report detection and process rejection are separate.

| Configuration | Obligation | Classification |
|---|---|---|
| prior_modern_native | report_m1.1 | NOTSUPPORTED |
| prior_modern_native | report_m1.6 | NOTSUPPORTED |
| prior_modern_native | report_poly.1a | NOTSUPPORTED |
| prior_modern_native | report_m1_OFFGRID | NOTSUPPORTED |
| legacy_native | report_m1.1 | SUPPORTED |
| legacy_native | report_m1.6 | SUPPORTED |
| legacy_native | report_poly.1a | NOTSUPPORTED |
| legacy_native | report_m1_OFFGRID | SUPPORTED |
| modern_direct_pdk_options | report_m1.1 | SUPPORTED |
| modern_direct_pdk_options | report_m1.6 | SUPPORTED |
| modern_direct_pdk_options | report_poly.1a | SUPPORTED |
| modern_direct_pdk_options | report_m1_OFFGRID | SUPPORTED |
| modern_adapter_native | report_m1.1 | SUPPORTED |
| modern_adapter_native | report_m1.6 | SUPPORTED |
| modern_adapter_native | report_poly.1a | SUPPORTED |
| modern_adapter_native | report_m1_OFFGRID | SUPPORTED |
| stock_selected_pdk_defaults | active_klayout_drc | NOTSUPPORTED |
| legacy_native | reject_nonzero_klayout_markers | NOTSUPPORTED |
| modern_adapter_native | reject_nonzero_klayout_markers | NOTSUPPORTED |
| audited_run_klayout_drc_interface | bind_consumed_gds_to_selected_candidate | NOTSUPPORTED |
| audited_run_klayout_drc_interface | authenticate_approved_deck_digest | NOTSUPPORTED |
| audited_run_klayout_drc_interface | validate_expected_active_rule_inventory | NOTSUPPORTED |
| audited_run_klayout_drc_interface | detect_omitted_feol_configuration | NOTSUPPORTED |
| audited_run_klayout_drc_interface | validate_streamout_layer_map_provenance | NOTSUPPORTED |
| audited_run_klayout_drc_interface | bind_results_to_later_release_artifact | NOTSUPPORTED |
| wider_scope | all_feol_rules | NOTASSESSED |
| wider_scope | all_beol_rules | NOTASSESSED |
| wider_scope | seal_ring_detection | NOTASSESSED |
| wider_scope | floating_metal_detection | NOTASSESSED |
| wider_scope | density_antenna_lvs_pdn | NOTASSESSED |
| wider_scope | default_magic_drc | NOTASSESSED |
| wider_scope | full_flow_comparative_fault_coverage | NOTASSESSED |

## Why the prior wrapper disabled rules

Prior harness manually sets KLAYOUT_DRC_TECH_SCRIPT to modern sky130A_mr.drc; wrapper passes input/report only, leaving feol/beol/offgrid/seal/floating_met unset and false.

Both installed selected and dependency-pinned PDK configs define KLAYOUT_DRC_RUNSET and KLAYOUT_DRC_OPTIONS, not KLAYOUT_DRC_TECH_SCRIPT; pinned native code has no translator.

Old direct control enables floating_met=true and omits seal; selected PDK options request floating_metal=0 and seal=1. These are different configurations.

Zero categories on a known violating control is an inactive-engine finding. The old study's `not_detected` label is preserved in its original files, with this sidecar qualification; it cannot support an active-checker miss claim.

## Commands, identity, and preservation

- Pinned image: `ghcr.io/the-openroad-project/openlane@sha256:d7e2bdd21e757e3f0b15d6ea08c36d9a96653c31b4fb2fafd4de88c9b6a3f3fa`
- KLayout version: 0.28.2 (actual version stdout retained).
- Run directory: `/home/vlsi/rtl2gdsagi/runs/openlane_invocation_audit/controls_v1`
- Exact argv, stdout, stderr, exit status, timings, hashes: `executions/*/command.json` and `result.json`.
- Actual child process arguments: `cases/*/execve.trace` captured with strace; no checker proc redefined.
- Report XMLs and per-category counts are retained; JSON includes full emitted category inventories.
- Original input/source/control preservation: 855 files; byte identical = True.
- Containers use network=none; repository and both PDKs are read-only; only this run directory is writable.

## Public maintainer-owned confirmation

Confirmation is documentary and source-based. No maintainer was contacted; no personal endorsement is claimed.

- [openlane_run_drc.sh](https://raw.githubusercontent.com/The-OpenROAD-Project/OpenLane/ff5509f65b17bfa4068d5336495ab1718987ff69/scripts/klayout/run_drc.sh): public/retained/image bytes match; SHA256 `92da7961a5a6929bd7b67c93d72c8cfdbf3b741842611e2b96c1d4c361f90ea8`.
- [openlane_klayout.tcl](https://raw.githubusercontent.com/The-OpenROAD-Project/OpenLane/ff5509f65b17bfa4068d5336495ab1718987ff69/scripts/tcl_commands/klayout.tcl): public/retained/image bytes match; SHA256 `285d8b1440b8a9d66379836b26965d329f3db3990badfffb19c73da641316d9e`.
- [openlane_general.tcl](https://raw.githubusercontent.com/The-OpenROAD-Project/OpenLane/ff5509f65b17bfa4068d5336495ab1718987ff69/configuration/general.tcl): public/retained/image bytes match; SHA256 `002fc7d31adc9fc6f6ab5dda069134e4e43836cc3bc081584dd485abd5cade90`.
- [openlane_flow.tcl](https://raw.githubusercontent.com/The-OpenROAD-Project/OpenLane/ff5509f65b17bfa4068d5336495ab1718987ff69/flow.tcl): public/retained/image bytes match; SHA256 `edb5f13711b77a046a704fe180d0691532dd558fa637706f1b1c79897f654bad`.
- [openlane_tool_metadata.yml](https://raw.githubusercontent.com/The-OpenROAD-Project/OpenLane/ff5509f65b17bfa4068d5336495ab1718987ff69/dependencies/tool_metadata.yml): public/retained/image bytes match; SHA256 `d833b89c969a3585b84c7e2438b6af5a00d904a8dfdadb16bbcf51a95dea3252`.
- [openlane_configuration.md](https://raw.githubusercontent.com/The-OpenROAD-Project/OpenLane/ff5509f65b17bfa4068d5336495ab1718987ff69/docs/source/reference/configuration.md): downloaded public source; SHA256 `deff975253be9b768b0cd82de3d5ab08a7cb4545ace64bd316ab5a7c0729969d`.
- [open_pdks_pinned_config.tcl](https://raw.githubusercontent.com/RTimothyEdwards/open_pdks/0fe599b2afb6708d281543108caf8310912f54af/sky130/openlane/config.tcl): downloaded public source; SHA256 `c973405eec9a4a12743d36057149d6f345d6531b29ab440c0705e1513b2a74a3`.
- [open_pdks_selected_config.tcl](https://raw.githubusercontent.com/RTimothyEdwards/open_pdks/bdc9412b3e468c102d01b7cf6337be06ec6e9c9a/sky130/openlane/config.tcl): downloaded public source; SHA256 `c973405eec9a4a12743d36057149d6f345d6531b29ab440c0705e1513b2a74a3`.
- [open_pdks_pinned_sky130.lydrc](https://raw.githubusercontent.com/RTimothyEdwards/open_pdks/0fe599b2afb6708d281543108caf8310912f54af/sky130/klayout/sky130.lydrc): downloaded public source; SHA256 `81cf4f998fc6fb6925ccc8618afba3dc8530058db1d0e31dc1f6ad5299e52372`.

## Enforced scope and limits

Supported geometry obligations apply only to supplied GDS under the named deck/options. Native stage completion does not enforce zero markers. Candidate lineage, approved-deck authenticity, expected active-rule inventory, map provenance, and later artifact binding are absent from this audited interface. The adapter activates the selected PDK options but does not add those obligations or a marker rejection gate.

All-rule coverage, seal/floating-metal discriminating controls, default Magic DRC, LVS/PDN/antenna/density, and full-flow comparative coverage are NOTASSESSED. No full RTL-to-GDS flow was executed and no signoff or full-flow comparative claim follows. Old controls and study files are preserved.
