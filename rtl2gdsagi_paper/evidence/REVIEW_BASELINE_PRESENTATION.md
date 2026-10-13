# Baseline revision review — PRESENTATION seat

Date: 2026-10-13. Internal presentation verdict: **Minor Revision**. Two localized reporting edits remain; the inspected baseline outcomes do not require new experiments.

criteria_binding_unavailable

calibration_status: NOT_CALIBRATED

This is the PRESENTATION seat within three distinct internal contexts in a shared automated writing workflow. Shared author instructions, manuscript, and evidence do not establish independent external peer review. No other new reviewer reports were read; historical reviews were not used to determine this verdict. The role contract is `/home/vlsi/.codex/plugins/cache/ars-codex/ars-codex/3.23.0/skills/academic-research-suite/ars/academic-paper/agents/peer_reviewer_agent.md`. Only its five generic categorical criteria are applied. No numeric quality score, ranking, venue acceptance, or publication authorization is supplied. Publication remains a separate author-authorized gate.

## Snapshot and read coverage

The requested source hashes match the inspected bytes. SHA-256 bindings:

| Artifact | SHA-256 |
|---|---|
| `main.tex` | `a013da072d36c5794c8d3651285eeff03f26e53bc9957b8af9b69b74f0b88086` |
| `supplement.tex` | `07c80fa0d12d594c651bfd3753f22622acbf6f6119254934fb8011503d294eac` |
| `main.pdf` | `3412d0f4357165fa17973a59f90217f198a7eb64733346946d49fdd3b642c6db` |
| `supplement.pdf` | `43143cb8a1828d6b4a52440141d254b36846314f714a9f7401bbbb32fbe6a1d8` |
| Main PDF text, `pdftotext -layout` stdout | `7f235ec937382c36f6d80696eea2459255a69feefeea211b6860d518cc0b875b` |
| Supplement PDF text, same extraction | `ab6382c814a7803f34dd21c87793d41009e71c1c613122a9226de4fe1f339aef` |

Read the complete current main source (494 lines), supplement source (208 lines), all sixteen distinct directly included generated TeX inputs, and complete extracted text of both PDFs. Rendered every page at 95 dpi and visually inspected all pages in contact sheets; additionally inspected main pages 8–9 and supplement page 4 at 150 dpi. Main page 1 and supplement page 3 were also rendered at 150 dpi, with their visual inspection covered by the full-document sheets. Temporary renders were outside the repository.

Read the baseline launcher, stopping harness, collector, retained extractor, experiment manifest, all 24 CSV rows, relevant retained result events, and failure-log excerpts for all nineteen failed candidates. Ran only the retained extractor's read-only `extract()` function on the five successful candidates. Inspected the citation audit's scope/receipt records and replay audit's reconstruction/stratification records as supporting evidence. No additional EDA execution, paid model call, external message, fresh literature lookup, manuscript edit, or optional broad native audit was performed.

## Five categorical criteria

Criterion source for every row: the role contract's **Five-Dimension Criterion Rubric**, field-general fallback. Judgements concern this seat's inspected presentation and evidence reporting; they do not substitute for a complete technical or literature review.

| Criterion | Judgement | Manuscript evidence and rationale | Uncertainty and decision impact |
|---|---|---|---|
| Originality | NOT_ASSESSED | Main §5, lines 359–389, explicitly acknowledges FlowFixer rechecking, newer AuDoPEDA manifest/proof overlap, and conceptual Nix/Bazel/SLSA relationships without integration, priority, or conformance claims. | Presentation of the contribution is bounded; originality itself was not independently established. No originality-based decision is made. |
| Methodological Rigor | MEETS | Main §3.3, lines 220–235; supplement §4, lines 100–124. The finite sweep, complete certification requirement, stopping intervention, exclusions, and changed-period controls are disclosed. Launcher and harness inspection support this description. | Reporting judgement only; no new native execution or full controller correctness audit. No unresolved methodological reporting blocker found. |
| Evidence Sufficiency | MEETS | Main §4.5 and Table 8; supplement §4; retained CSV/events and five extractor validations. All fixed-target timing candidates have measured failures; unreached checks remain unavailable. | Existing evidence supports the bounded counts. This seat did not repeat verification of all primary design pairs or fault fixtures. P1 concerns the meaning of a displayed statistic, not invented data. |
| Argument Coherence | PARTLY_MEETS | Main abstract, §3.3, §4.5, and §6 consistently separate proposal replay, archived live episodes, scripted candidates, and exploratory episodes. Table 1 omits the newly introduced sweep and its execution-policy qualification. | P2 is a small source-accounting omission, resolved by an explicit row; it does not reverse the conclusions. |
| Writing Quality | PARTLY_MEETS | All table/figure callouts resolve, units and denominators remain visible, and both rendered documents are legible. Table 8's maximum and its surrounding description are insufficiently specific. | P1 and P2 justify Minor Revision. Underfull spacing is cosmetic. No confirmed venue or length rules were supplied. |

## Supported findings

The title and abstract match the main argument: candidate-bound acceptance evidence under frozen Python source `af31b39f67827a3375c52bf41f52a727130947f8b5716d80b2680c7de88ca06c`, with explicitly historical evidence from `18d948815ac6`. Current Python source identity recomputes to that frozen value. The abstract states 0/16 scripted certifications at 3 ns and labels the nine live episodes a recorded case study that was not re-executed on the frozen implementation (main lines 28–48). “Verified repair” is absent from the keyword list. The conclusion repeats the archived/frozen distinction and reports exploratory accumulator outcomes as 0/4 certifications, two policy escalations, and two credit-interrupted episodes with unknown eventual outcomes (main lines 398–408).

Baseline accounting is supported without replacing missing observations with constants:

| Stratum | Declared candidates | Validated outcome |
|---|---:|---|
| Spacing, 10 ns | 4 | Padding 1/2/3 certify; padding 0 has one native DRC marker. |
| PDN, 10 ns | 2 | Offset 2 µm certifies; offset 50 µm fails with PDN-0185 before routed STA or DRC. |
| Timing, fixed 3 ns | 16 | All fail routed setup STA; best measured WNS is `-0.000653699335387172` ns, correctly rounded to `-0.000654` ns. |
| Separate period controls | 2 | 3.25 ns fails at `-0.1419522317648361` ns; 3.50 ns certifies at `+0.06074341201965228` ns. Neither is a repair of the original 3 ns requirement. |

All five successes pass the retained extractor's candidate/artifact checks, gate-lineage checks, certification identity, full 21-stage acceptance, and native signoff metrics. All nineteen failed rows agree with retained result events and relevant native-log excerpts; none has a signoff bundle. PDN failure has `not reached` for routed setup, hold, and DRC. Seventeen routed-STA failures have `not reached` for DRC. The spacing failure has real measured timing and DRC counts. Thus no unreached DRC was silently called clean and no first-failure stage was guessed from a constant.

The launcher declares all 24 configurations before submitting execution jobs. All configuration hashes match the manifest; no `api_call`, `config_generated`, or `repair_applied` event appears in this cohort. The harness subclasses the frozen orchestrator and overrides only `_rollback`; manual policy and retry limit one make this a bounded candidate-acceptance experiment. Native gates and certification paths are inherited. The manuscript explains this distinction (supplement lines 109–118). The retained CLI pilot contains fourteen DRC failures with one marker each; its whole cohort remains excluded. The separately retained bootstrap console records an import failure before EDA, also excluded. The final manifest has 24 declarations and 24 outcomes, rather than selectively combining pilot successes.

The replay wording preserves distinct evidence types: 20/20 trace consistency, seven independent archived complete-IR comparisons before the explicit worker field, and thirteen complete IRs not found in the inspected archive (main lines 199–210; supplement lines 76–89). Excluding `timing_1_proposal2` leaves twelve setup-STA failures and one DPL-0036 placement failure; no routed timing is attributed to the latter (main lines 307–311). The full fourteen-state timing denominator remains displayed. The primary headline remains fourteen design runs/seven repeat pairs and six constructed classes/eighteen consistency executions, with no pooling of these units.

The timing guard is expressly required slack ≥ g, with g = 0 for evaluated runs. Main lines 131–136 distinguish this threshold from clock uncertainty and decline a robustness-margin inference. Table 6's “Not designed for” applies to the audited checker interfaces, as its caption and surrounding §4.2 state; it is not a finding about full OpenLane flows. The earlier inactive wrapper is excluded from the active-checker baseline.

The retained citation audit supplies selected-source receipts for six papers and three official documentation sources, not complete reading of those publications. Its manuscript binding is an earlier `a9962699…` snapshot, so its locators and former 13-reference inventory were not treated as current. The present source has sixteen bibliography entries, each cited, with no missing keys. Current §5 preserves the bounded comparisons and the AuDoPEDA author-manuscript overlap; its bibliography omits the forthcoming DOI that the audit recorded as unresolved. No fresh external source verification is claimed here.

## Issues and exact remedies

No Critical or Major presentation issue was established in this targeted audit.

| ID / severity | Exact anchor | Issue | Minimum remedy and effort |
|---|---|---|---|
| P1 — Minor | Main §4.5, lines 332–333, PDF p.9; `generated/scripted_baseline_table.tex`, lines 2, 4, 6; CSV `spacing_pad0` and `spacing_pad1` | “Table 8 reports all declared configurations” introduces a four-stratum summary, not the 24 per-candidate records. The adjacent “Certified” and “Best setup” columns can also imply that the spacing maximum belongs to a certified candidate: `+5.304609` ns actually belongs to DRC-failed padding 0. The best certified spacing candidate is padding 1 at `+5.289834942028038` ns. The displayed maximum is numerically correct but its selection set is implicit. | Say that Table 8 summarizes all declared strata and point to the 24-row CSV. Define the maximum as the best measured routed setup WNS among all candidates reaching STA, including candidates that fail a later gate; explicitly identify the spacing maximum as DRC-failed padding 0. Preserve the measured value and counts. Update the collector's caption/header source as well as the generated input. Quick wording edit; no experiment needed. |
| P2 — Minor | Main §3.1, lines 157–168, Table 1, PDF p.4; main §3.3, lines 230–235; supplement §1, lines 18–25, and §4, lines 109–118 | The source-accounting table promises assignment of each result but has no row for the new 24-state scripted baseline. The supplement's opening execution ledger also lists the earlier frozen cohorts without the sweep. Readers must reach a later subsection to learn that frozen native checks were run through an external stopping harness. | Add a source-accounting row for the 24 scripted candidates: frozen `af31b39f6782` native executor plus the study-only rollback stopping harness. Add the sweep to the supplement's opening ledger and retain the pointer to §4 for the two excluded cohorts and separate period controls. Quick wording/table edit; no change to source identity or results. |

Optional presentation polish: use ragged-right paragraph columns in Table 6 (`generated/checker_obligations_table.tex`, lines 3–11; main PDF p.8). Current justification stretches “Not designed for” and several obligation labels. Keep the interface-remit caption and “Not assessed” distinction. This is cosmetic, requires only a local render check, and does not bear on the verdict.

## Render, pagination, and build checks

`pdfinfo` confirms **12 main pages and 6 supplement pages**. The full render shows no blank pages, clipped text, overlapping table headers, detached captions, or truncated rows. Main Tables 1–8 and Figure 1, and supplement Tables 1–5 and Figure 1, each have a resolved textual callout. Equation (1) is visible with its definitions. Table 7's two-line headers distinguish archived failed/missing evidence from frozen failed/certified outcomes. Table 8 keeps slower-period controls on a separate row with an explicit caption exclusion. Supplement Figure 1 identifies the archived source and completed-check endpoints; its axis and legend remain readable.

The current logs are **not warning-free**: main has sixteen underfull-box warnings and supplement has two, chiefly table justification, bibliography wrapping, and long artifact paths. Neither log contains an overfull-box warning, undefined-reference/citation warning, or LaTeX error. Their final output records match the inspected PDF page counts and byte sizes. The underfull warnings have no observed clipping consequence. A fresh compilation was not performed, so this is inspection of retained builds, not a new build receipt.

Title/content, abstract/body, question/conclusion, units, keyword scope, callouts, and bibliography-key coverage pass the targeted checks except the two explicitly anchored summary/source-accounting edits. No venue word/page limit, accessibility conformance, link availability, or complete bibliography-integrity certification is assessed. In particular, main lines 410–419 describe the versioned release in present tense; this review does not verify publication or the public release receipt and cannot authorize that separate gate.

## Input and evidence bindings

All directly included generated TeX files were read. Paths below are relative to `rtl2gdsagi_paper/`.

| Input | SHA-256 |
|---|---|
| `generated/live_results.tex` | `e0733c07718806022edd2d279c476877eb90a74850af11ff0740bfe4818402a1` |
| `generated/frozen_macros.tex` | `ce30a277f2c25c664964ca83f9bd789f6c2ec6400e50b1528f39227b645b9775` |
| `generated/scripted_baseline_macros.tex` | `4082eb90a2ce130c31e89f660d7d6b4a5a8371cd4cbb04c40ef1a1d2eb9f2fa2` |
| `generated/qor_table.tex` | `8f105251414597b0189c099be8c26b0da583a195bc9564bfa8e746ddbad2361a` |
| `generated/signoff_table.tex` | `d473ad909c1dbd7f4bac2021a56e1c4b599b27f533d66cd513513e5b22431618` |
| `generated/reproducibility_table.tex` | `045e078a30747062532f3ea5d6b659d468be6eae2b27c4f7f72a3244589d2ba7` |
| `generated/frozen_fault_table.tex` | `fe7b73d818b97d5c22906106011daf0203ddcf0fcb083a720c622912d9ec6209` |
| `generated/checker_obligations_table.tex` | `b81de17bc211317b2ec95908cbbd33c4f34c092019e16d974e0e48cfc385de92` |
| `generated/class_replay_table.tex` | `812ac102c4bf35f6107ec78511ac59925f6b10be095bf744761713c9f118ac42` |
| `generated/scripted_baseline_table.tex` | `63c654cc17aa689e1fdd4c39bdf8d35a6eb9e8793e3c5861e564f48995a81033` |
| `generated/extended_results.tex` | `e1ac173e7ec37fcf86fd81c43e1057b00fa07520b0a3501d5c6410f1bb714e3a` |
| `generated/padding_thread_table.tex` | `fbf1b8db0045131d1169c1e5c09c06c3eb8ee2b7bafccfadfe9772d1502ecae0` |
| `generated/episode_table.tex` | `f61f91ba644c005d38daf5334438fa92dba5c753cb739561159f680d10501845` |
| `generated/configured_drc_controls_table.tex` | `395948f80536d583d4f63a96ce9ee0492506a6ad9e431884e201ddb3820b47bf` |
| `generated/supplement_large_cases.tex` | `c7564653250950d81097b800c759e5202f8437d471de77ded980650490eec9cb` |
| `generated/supplement_history_table.tex` | `dd9903084792355b2561f1667ea3c7353b46afac51d0bacbf5a214e98f8b24a3` |
| `figures/timing_stress.pdf` | `f190f4fc4d3c7a2bf0857d7b310da23dcaacde0da58d26302c9a134fad43f41b` |
| `main.log` | `fc0b3b260565e6d8e8dda1914401c75425d8a953c16459bcae7b93423f3df11e` |
| `supplement.log` | `94ea2241d60b5e3771691cbf0a09a8b03e5574822b7311f9a5b71c791e1d6b87` |
| `evidence/scripted_baseline_metrics.csv` | `c6237b02179bc8785f1b88d3d51294f2094b2bccf2d461cbb51872845510d7b6` |
| `evidence/scripted_baseline.json` | `ee4f4c1e0420f3de2253b9ccf4588df91fe76fa2332bb28de9ab55c447e84c62` |
| `evidence/citation_baseline_audit.json` | `fd81236614c35bd7087bfd7ce9af65cb46eea34b0c582d420eeadd725d6e11cb` |
| `evidence/replay_stratified_audit.json` | `6f40c18f70720990f3c59c5a69a2f6fd0ca0248108bba74f648deec00931da8f` |

Workspace-relative baseline manifest: `runs/scripted_baseline_bounded_20261013/experiment_manifest.json`, SHA-256 `64642e275450739cf69b6afebfcc1d4241fbe5e26d038b56b74f16c7ef53c00c`. Stopping harness: `scripts/run_baseline_candidate.py`, SHA-256 `25a9e50f48f16039e2a2dbc4835d16dcdf9efbf36a1c4c20d8597df69d7c6413`.

Confidence is high for the inspected pagination, source/input bindings, and baseline reporting; narrower for technical correctness beyond the retained validations and selected citation receipts. P1 and P2 are the decision-bearing revision requests. Recheck only their affected text/table renders and bindings after edits; this report requests no new experiments or external review.


## Final scoped closure — 2026-10-13

**Presentation closure: Accept within the inspected scope.** P1 and P2 are resolved; the requested M1–M4 and E1–E3 clarifications are present and supported by the bounded checks below. No unresolved decision-bearing presentation issue remains. This conclusion does not authorize publication or establish venue acceptance.

criteria_binding_unavailable

calibration_status: NOT_CALIBRATED

The entire initial review above, including its verdict, criticism, evidence limits, and historical hashes, is preserved byte-for-byte. Its pre-append SHA-256 is `9ec3c2558a8dc72e0989e9561e89b54e9bf250027669e7014adb3fa7f978f0cb` (17,357 bytes). This closure binds the later files; it does not relabel the earlier review as having inspected them. The same shared-workflow/internal-context disclosure applies. Other seat reports were not read.

### Closed findings and targeted checks

| Item | Current anchor | Closure evidence |
|---|---|---|
| M1 | Main §3.3, lines 222–225, PDF p.5; supplement §4, lines 108–111, pp.3–4 | Both documents describe fixed 0.2 delay fractions and absolute I/O delays changing from 0.60 to 0.65/0.70 ns. Retained SDCs for 3.00/3.25/3.50 ns confirm these values, with uncertainty 0.25 ns and load 0.05 pF unchanged. These are combined requirement changes, not isolated clock-period sensitivity or original-target repairs. |
| M2 | Main §4.5, lines 342–345, p.9; supplement §4, lines 112–114, p.4; collector lines 40–51 | All eight setup off/on pairs are disclosed as outcome-equivalent while all sixteen declared configurations remain counted. The collector asserts pairwise CTS DEF, routed DEF, SPEF hashes and setup/hold WNS equality, and stores eight results. Independently rehashed all three actual artifacts for both members of every pair and compared the stored slacks to the retained state summary. All match. A representative off/on CTS-script comparison also confirms that the on script emits setup repair. This does not infer general setup-repair ineffectiveness. |
| M3 / P1 / E1 | Main §4.5, lines 331–338, p.9; generated baseline table lines 2–6, p.10; collector line 65 | Main now calls Table 8 a summary of declared strata and points to the 24-row CSV. The caption defines the maximum over every candidate reaching routed STA, including later hard failures, and identifies the spacing maximum as DRC-failed padding 0. The two-line header reads “Best setup / all STA (ns).” Collector and rendered input agree. The original maximum and certification counts remain unchanged. |
| M4 / P2 | Main Table 1, line 160, p.4; supplement opening ledger, lines 25–27, p.1 | The 24 scripted states now have an explicit frozen-native-executor plus hashed-stopping-harness entry. The supplement includes this cohort and points to the stopping-policy description. |
| E2 | Supplement §4, lines 127–134, p.4 | Manifest claims are restricted to configuration/harness hashes. Positive candidate/certification identity locators are each successful run's `signoff.json` and `gate_evidence.json`. Checked all five positive bundles: candidate IDs agree across these files and full certification is recorded. All nineteen failed runs lack a signoff bundle; no release certificate is attributed to them. |
| E3 | Main §2.2, lines 131–136; §3.3, lines 231–234, p.5; supplement §4, lines 116–125, p.4 | Diagnosis settings no longer imply universal termination. Main explicitly names the pilot loop caused by date-bearing GDS changing failed-input fingerprints without an IR change. The separate study harness bounds execution while the frozen controller remains unchanged. Both excluded cohorts retain their disclosed status. |

Reread the two final introduction paragraphs (main lines 52–63, p.1). They retain cited OpenROAD/OpenLane infrastructure, evidence bound to the selected implementation and verification inputs, stale/incomplete reports, repair invalidation, all three research questions, and the executable-contract/measured-integration contribution. The shortening introduces no new numeric result or methodological inference.

Table 6's paragraph columns are now ragged right, with the audited-interface qualification retained. Main's CSV filename is breakable and the supplement provides its full evidence path. The shortened supplement artifact-verification paragraph remains on page 6 with preceding content. No new native/model/API experiment, broad native audit, literature check, or manuscript/data edit was performed for closure. The initial retained extractor validations are not represented as new executions.

The outcome inventory remains spacing 3/4, PDN 1/2, fixed 3 ns timing 0/16, and separate period controls 1/2. Best fixed-target setup WNS remains `-0.000653699335387172` ns; controls remain `-0.1419522317648361` and `+0.06074341201965228` ns. The 24-row CSV, execution manifest, and stopping harness have the same hashes as in the initial review. The newly generated pair summary adds reporting verification without enlarging the cohort. The primary seven pairs/fourteen runs, six classes/eighteen consistency executions, archived live cohort, replay stratification, and exploratory outcomes were not broadly re-audited.

### Categorical closure judgements

Source: the same five generic criteria in the role contract; no target-specific binding or arithmetic.

| Criterion | Current judgement | Evidence, limitation, and decision impact |
|---|---|---|
| Originality | NOT_ASSESSED | Unchanged: closure performs no new originality or literature assessment. No decision impact. |
| Methodological Rigor | MEETS | M1, M2 and E3 precisely report controls, observed pair equivalence and stopping limits. Reporting scope only; no controller correctness or native rerun claim. |
| Evidence Sufficiency | MEETS | Actual paired artifacts, retained SDCs, identity locators and unchanged CSV support the affected claims. The initial broad-evidence limits remain. |
| Argument Coherence | MEETS | P2/M4 closes the source-accounting omission; the shortened introduction retains the original questions and contribution. No unresolved scoped issue. |
| Writing Quality | MEETS | P1/M3 closes the maximum/summary ambiguity; affected renders are readable and contain the clarified headers/callouts. No venue-format determination. |

### Final render and packaging limits

Current `pdfinfo` reports **12 main pages and 6 supplement pages** after the final introduction edit. Inspected final main pages 1, 4, 5, 8, 9 and 10 and supplement pages 1, 3, 4 and 6 at 105 dpi; additionally inspected main Table 8 on page 10 at 150 dpi. No clipping, overlapping headers, detached caption, or truncated row was observed on these affected pages. This is a targeted render check, not a repeated full-document audit. PDF hashes were stable across this render operation.

Final retained logs have no overfull boxes, undefined-reference/citation warnings, LaTeX warnings, or error lines. They still contain **11 main and 2 supplement underfull-box notices**; “all warnings zero” is not claimed. The revised Overleaf checker distinguishes these notices in its per-document records and defines its zero-warning field as excluding underfull notices.

The available `fresh_overleaf_build.json` still binds the initial `a013da07…` main source and initial extracted texts. It cannot verify the final package. Rebuilding the ZIP after final inputs and obtaining a matching fresh package receipt remain packaging tasks; no final-ZIP success is asserted here. Publication remains pending a separate author-authorized gate. These availability/package checks do not reopen the closed presentation findings.

### Current file bindings

SHA-256 values below were obtained from the filesystem at closure. Text hashes are `pdftotext -layout` stdout. All sixteen direct generated inputs were compared with the initial bindings: fourteen are unchanged; the two changed inputs are bound below. Historical bindings above remain historical.

| Artifact | Current SHA-256 |
|---|---|
| `main.tex` | `2aa92affa3a4eb7474e1eac7cd859529cbd4ec02f0b39bbc2358fe4388af7c80` |
| `supplement.tex` | `d0e3f9fb656ff7839dd52c19fe8e515c3345db9e06f4f4ac68331e00c1b2717b` |
| `main.pdf` | `d7b1a675203701620c2001ee27d3225d77bb4bd7a19a95600992e1d6cccda751` |
| `supplement.pdf` | `78e0c03002c732f2b6d5bef85f7163de0530b3bccd256b92441f5e69a4bf21fa` |
| `main.log` | `820600fa233806334077b7fd1c8b176f509b009e16fe57b4310a7efa2db6054a` |
| `supplement.log` | `3f769cb1dab6852a7ee3e89b00b96b191d2227a4e6cb5f17a84fd1f690a4ddd3` |
| `generated/scripted_baseline_table.tex` | `0b0bc32bf6545a3efac70eeeaabe7c2bca12afc613ae3f10f595c41b39cd572a` |
| `generated/checker_obligations_table.tex` | `ae928e463c8cb75669e0a1e409469f7c0495bed319c5ef305910b7360067b17b` |
| `evidence/scripted_baseline.json` | `560915dc385b881e04d11165645e51f4ba3990bbd35a7b03e657c3ae15169537` |
| `evidence/scripted_baseline_metrics.csv` | `c6237b02179bc8785f1b88d3d51294f2094b2bccf2d461cbb51872845510d7b6` |
| `evidence/fresh_overleaf_build.json` | `a3a8eed7b033f3d6c709040aaf91cfa487a2523ab7e8f22285ca85ff7a0b92ea` |
| Main PDF extracted text | `a4e69a6d58291d476325ecdade22817456d620d56d03d6466430f70c15e57566` |
| Supplement PDF extracted text | `aed13f3b0a851be4ccb16846545f2dfbbbbb975beb535d525c4801406e8e7ae6` |
| Workspace-relative `scripts/collect_scripted_baseline.py` | `6c2deeea47436485ee26fd369a12ce6517efa5acadadc5fb270d5d2ed3b12277` |
| Workspace-relative `scripts/verify_overleaf_package.py` | `7c23c836cad735f006e849ffdbb54f0b5e2ab1f835e1e1faae7497412b8a7dc2` |
| Workspace-relative `runs/scripted_baseline_bounded_20261013/experiment_manifest.json` | `64642e275450739cf69b6afebfcc1d4241fbe5e26d038b56b74f16c7ef53c00c` |
| Workspace-relative `scripts/run_baseline_candidate.py` | `25a9e50f48f16039e2a2dbc4835d16dcdf9efbf36a1c4c20d8597df69d7c6413` |
