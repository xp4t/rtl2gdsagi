# METHODS internal review: current scripted-baseline revision

Date: 2026-10-13. Seat: METHODS. Contract: `/home/vlsi/.codex/plugins/cache/ars-codex/ars-codex/3.23.0/skills/academic-research-suite/ars/academic-paper/agents/peer_reviewer_agent.md`.

criteria_binding_unavailable

calibration_status: NOT_CALIBRATED

**Internal disposition: Minor Revision.** The bounded candidate-acceptance findings are supported. Corrections are needed to describe the effective timing constraints, outcome redundancy, and Table 8 summary precisely. These are repairable reporting issues; they do not overturn the observed certifications or require new experiments. No critical or major failure of the current, restricted inference was identified.

This is one of three distinct internal contexts in a shared writing workflow. It is not independent external peer review, and the three contexts are not independent corroboration. Other new reviewer reports were not read; historical reviews were not used as current evidence. Publication is a separate author-authorized gate. This report supplies neither venue acceptance nor a numerical quality score. No paper-blind precommitment or empirical calibration is claimed.

## Read and verification scope

Read all 494 lines of current `main.tex`, all 208 lines of current `supplement.tex`, all sixteen distinct generated TeX inputs actually included by those documents, and complete text extracted directly from both current PDFs with `pdftotext -layout … -`. Main PDF: 12 pages; supplement: 6 pages. Current sources match the two requested SHA-256 values. PDF text confirms the new protocol, Table 8, source separation, limitations, and bibliography appear in the rendered documents. This was a text audit, not a visual inspection of every figure or a fresh compilation.

Read the baseline launcher, stopping harness, collector, and retained signoff extractor; inspected relevant frozen runner/rendering code. Checked all 24 declared configurations against their manifest hashes and exact initial-state-plus-delta definitions, all 24 result histories and CSV metric fields, the failed-stage native logs, and the unpadded DRC report database (one item). Invoked only the extractor's read-only `extract()` function for the five successful runs: candidate/artifact rehashing, gate lineage, certification identity, clean full certification, and all 21 stages validated. No generator entry point was executed.

Checked current and archived frozen Python fingerprints, harness identity, one routing worker, zero acceptance guardband, 0.25 ns uncertainty, 0.05 pF load, and 0.05 ns CTS optimization margins. Compared all eight timing setup-repair off/on pairs: each pair has identical CTS DEF, routed DEF, SPEF, and setup/hold WNS. Inspected rendered SDCs for fixed timing and both slower-period controls.

Read the excluded CLI pilot's retained launcher and spacing history and the excluded bootstrap traceback. Used `citation_baseline_audit.json` for selected-source identity/claim/read-scope evidence and `replay_stratified_audit.json` for reconstruction and exclusion accounting. These audits predate this exact manuscript: their old manuscript locators are not silently transferred. Current claims were matched to the audit content using current locators below. No fresh external literature verification, model calls, EDA runs, full-flow benchmark, broad native-checker reaudit, regression rerun, release verification, publication, or external messages were performed. No author-read declaration is inferred.

## Five categorical criterion judgements

Criterion source in every row: the role contract's field-general five-dimension rubric, restricted to this candidate-bound case study; no venue criteria are supplied.

| Dimension | Judgement | Current evidence and rationale | Uncertainty and decision impact |
|---|---|---|---|
| Originality | MEETS | Main §1, lines 61–70, and §5, lines 349–384, claim executable integration and measured candidate lineage. FlowFixer rechecking and the newer AuDoPEDA patch/snapshot/proof-manifest overlap are acknowledged; generic revalidation priority is expressly disclaimed. | Selected-source scopes do not establish exclusive novelty or absence of comparable controllers. Adequate for the stated integration contribution, not a priority claim. |
| Methodological Rigor | MEETS | Main §3.3, lines 220–235; supplement §4, lines 100–124; launcher lines 42–68; harness lines 13–18. Complete finite grid, declared strata, first-failure stopping, and inherited full certification support the restricted acceptance question. Pilot exclusions are disclosed and retained. | Choices follow knowledge of archived trajectories and a pilot; there is no blinded search, independent episode sample, or matched agent comparison. The period controls also alter derived I/O delays. Finding M1 requires clarification, not a new design. |
| Evidence Sufficiency | PARTLY_MEETS | All 24 CSV rows match retained native result events; all five success bundles validate. Main §4.5, lines 331–346, correctly restricts model-value inference. | Table 8 leaves the best-WNS denominator ambiguous, and the text omits outcome equivalence across setup-repair pairs. M2–M3 are needed for readers to interpret search coverage and successful QoR. No missing result was imputed. |
| Argument Coherence | MEETS | Main §3.2, lines 199–218; §4.3, lines 290–311; §6, lines 386–410. Proposal-state rejection, historical live episodes, fresh scripted acceptance, and primary repeatability answer different, explicitly delimited questions. | Native rejection of adaptive intermediate proposals cannot estimate incremental model value. The manuscript already respects this boundary; preserving it is decision bearing. |
| Writing Quality | PARTLY_MEETS | Sources and both PDF texts communicate the principal counts and limits consistently; all 16 bibliography entries are cited, with no orphan citation keys. | Effective period-control constraints, Table 8's WNS denominator, and the missing baseline row in Table 1 need concise edits (M1, M3, M4). No target word ceiling or venue format binding was supplied. |

## Findings supported by the retained record

- **Finite-grid coverage is complete.** Four spacing states, two PDN states, sixteen fixed-3-ns timing states, and two separately classified slower-period states were declared in the final launcher before its execution pool starts. The manifest contains all 24 completed outcomes and config hashes. This is execution predeclaration for a manually chosen grid, not proof that choices were made before seeing earlier evidence or a formal preregistration. Main §3.3 and §4.5 already identify the finite, manual scope.
- **Acceptance checks remain frozen; stopping changes.** The harness imports the retained frozen source and overrides only `_rollback`. With manual repair and retry limit one, every final candidate has one attempt per reached native stage, no repair/model events, and at most one failed hard check, which ends its native check history. PDN failure terminates through inherited manual-policy behavior. Successful candidates traverse the original full certification path. Thus these are fresh candidate executions through frozen acceptance checks with a study stopping policy, not a measurement of the unchanged CLI's iterative repair behavior.
- **Pilot exclusion is legitimate within that disclosed estimand.** The original CLI spacing history contains 14 DRC failures with one `npc.2` marker each; first and last checked raw GDS hashes differ, and the history repeatedly rolls back to routing without recorded IR repair. The entire pilot, including completed outcomes, is excluded. The separate bootstrap traceback is an `Escalation` import error before EDA; its directory contains no native `run.jsonl` files. Both are retained. This review does not independently establish that every pilot GDS difference consists only of date bytes; that mechanism is the retained protocol explanation. The final sweep is a fresh, separately declared cohort rather than selected pilot successes.
- **Native outcomes support the reported strata.** Spacing certifies padding 1/2/3 and rejects padding 0 at DRC (3/4). PDN rejects offset 50 µm with PDN-0185 and certifies schema offset 2 µm (1/2). All sixteen fixed-3-ns timing states fail routed setup STA, best WNS `−0.000653699335387172` ns. The 3.25 ns control fails at `−0.1419522317648361` ns; the 3.50 ns control certifies at `+0.06074341201965228` ns. The five certifications comprise four unchanged-requirement spacing/PDN candidates and one changed-requirement timing control. Metrics for unreached native stages are `not reached`, including DRC after STA failure and timing after PDN failure.
- **Source accounting is appropriately separated.** Current and retained frozen Python fingerprints equal `af31b39f67827a3375c52bf41f52a727130947f8b5716d80b2680c7de88ca06c`. The nine live episodes remain an `18d948815ac6` case study, explicitly not re-executed live on af31. Primary evidence remains 14 runs/seven exact routed and date-normalized pairs, and six fault classes/18 consistency executions. This review checks their manuscript/generated-table accounting; it does not rerun that existing audit.
- **Replay accounting does not overstate archival availability.** The current text and stratified audit agree: 20/20 trace-consistent reconstructions; only seven independently archived complete IR comparisons before adding `routing.num_threads=1`; the other thirteen were not found in the inspected archive. Removing the CTS-affected `timing_1_proposal2` leaves thirteen timing states: twelve setup-STA failures and one DPL-0036 placement failure whose routed timing was not reached. The original fourteen-state denominator remains visible. This sensitivity removes one known source-dependent pass; it does not validate missing independent full IR records or remove all reconstruction uncertainty.
- **Model value remains unestimated.** Simple scripted configurations are sufficient for these spacing/PDN fixtures. Failure of this selected timing grid establishes neither impossibility of a scripted 3 ns repair nor an LLM advantage. Fixed replay of proposals collected with native feedback is not an independently executed no-recheck agent trajectory. Historical 7/9 live certification cannot be compared as a matched af31 repair rate. Main §4.5 and §6 correctly acknowledge these limits, and the removed “verified repair” keyword does not reappear.
- **Robustness remains bounded.** Main §2.2, lines 131–136, correctly requires necessary slack ≥ `g`, with `g=0`; the CTS 0.05 ns optimization margin and clock uncertainty are separate quantities. Neither the near-zero miss, a small historical positive slack, nor exact repeat hashes establish variation tolerance. One typical corner, trusted host/tools/PDK, constructed faults, and small synthetic circuits leave industrial and multi-corner adequacy unestablished. The four larger accumulator episodes remain 0/4 certifications, with two policy escalations and two credit interruptions of unknown eventual outcome.
- **Related-work comparisons stay within evidence.** The fresh citation audit covers six papers and three official documentation families with differentiated selected-source scopes. FlowFixer support is publisher-indexed abstract evidence; a complete comparative contract audit is unavailable. Newer AuDoPEDA overlap is based on selected author-manuscript passages, not replicated proofs. The unresolved forthcoming conference DOI is omitted from the bibliography; arXiv v2 and the author PDF are separately identified. Nix/Bazel/SLSA are concept comparisons without integration, conformance, or priority claims. Table 6's “Not designed for” concerns the audited checker interfaces, not complete flows. No concrete contradiction justifies repeating the broader native audit.

## Required reporting corrections

Critical: none identified within the current scope. Major: none identified within the current scope. The following are **Minor** findings, each with a minimum remedy that uses existing evidence.

| ID | Exact anchor | Issue and evidence | Minimum remedy | Effort / inference consequence |
|---|---|---|---|---|
| M1 | Main §3.3, lines 227–228; §4.5, lines 342–344; supplement §4, lines 106–107. Rendered files `period_control_3p25/stages/03_sdc/alu8.sdc` and `period_control_3p5/stages/03_sdc/alu8.sdc` under the final baseline directory. | The controls change the period field, but their effective SDC also scales input and output delays: 0.60 ns at 3 ns becomes 0.65 ns at 3.25 ns and 0.70 ns at 3.50 ns, because delay fractions remain 0.2. Their WNS difference is therefore not an isolated clock-period perturbation. Uncertainty and load remain fixed. | State that period controls preserve delay fractions and consequently change absolute interface delays. Keep their certification outside original-target repairs and avoid inferring a continuous feasibility threshold or clock-only sensitivity. | Quick edit; strengthens the already restricted sensitivity interpretation without altering counts. |
| M2 | Main §3.3, lines 223–225; §4.5, lines 340–345; supplement §4, lines 103–105; Table 8 timing row (`generated/scripted_baseline_table.tex:8`). | Sixteen nominal configurations yield eight paired implementation outcomes: in every strategy/density/padding pair, setup repair off/on produces identical CTS DEF, routed DEF, SPEF, and setup/hold WNS. The retained setup-on script does emit `repair_timing -setup -setup_margin 0.0500`; equality is not evidence that the setting was omitted. | Add that all sixteen declared states ran, but this factor produced no observed implementation/timing change in the eight pairs. Describe observed coverage accordingly; do not count these as sixteen distinct achieved timing solutions or infer general setup-repair ineffectiveness. | Quick edit using existing hashes; limits effective search diversity. No additional experiment is required. |
| M3 | Main Table 8 / §4.5; `generated/scripted_baseline_table.tex:6`; collector lines 40–42. | Spacing “Best setup” `+5.304609` ns belongs to `spacing_pad0`, which fails DRC. Best WNS among the three certified spacing candidates is `+5.289834942028038` ns (`spacing_pad1`). The caption says values are measured after routing but does not identify whether failed candidates contribute to “best.” | Prefer a caption explicitly saying best is over all candidates that reached routed STA, including later failures. Alternatively label/report best among certified candidates and preserve the failed-candidate metric in the CSV. | Quick edit; prevents interpreting uncertified QoR as the best certified result. Either denominator is legitimate when labeled. |
| M4 | Main Table 1, lines 160–168; supplement §1, lines 18–35, and §4, lines 113–124. | The new 24-state baseline is absent from the otherwise explicit source-accounting table. A frozen base fingerprint alone does not identify its changed stopping behavior. | Add a row assigning the 24 scripted candidate states to the af31 frozen acceptance implementation plus the hashed study stopping harness; point to supplement §4. Keep the padding interventions and historical live origin distinct. | Quick edit; closes the revision's source/protocol ledger without claiming the stock CLI has the same stopping policy. |

The smallest revision is four localized reporting edits, followed by refreshing affected generated text/PDFs in the author workflow. No new paid calls or experiments are needed to satisfy this METHODS review. Broadening the paper to estimate incremental model value would require a separately designed and author-authorized comparison; it is not a remedy required for this manuscript's current claim.

## Cross-section checks and confidence

| Check | Result | Limit |
|---|---|---|
| Abstract, main §3.3/§4.5, supplement §4, CSV | Consistent | 24 configurations; fixed 3 ns 0/16; slower requirements separate. |
| Native acceptance and stopping description | Consistent | Five full bundles independently revalidated locally; inherited acceptance is distinguished from changed rollback behavior. |
| Source and cohort denominators | Consistent, with M4 omission | af31 fresh execution, 18d historical live origin, replay reconstruction and larger interrupted episodes stay separate. |
| Replay exclusion sensitivity | Consistent | 12 STA + 1 placement after excluding the CTS-affected state; only seven independent full IR comparisons. |
| Period-control sensitivity | Clarification required, M1 | Effective interface delays scale with period. |
| Table 8 QoR and effective timing diversity | Clarification required, M2–M3 | Failed spacing candidate supplies best WNS; eight setup-toggle pairs have equal achieved outcomes. |
| Literature claim overlap and citation keys | Consistent within selected-source audit | 16 cited entries, no orphan keys; no full literature or priority assurance. |
| Target length, venue compliance, public availability | NOT_ASSESSED | No criterion binding; publication and availability verification are separate gates. |

Confidence: **High** for the local 24-state counts, inherited certification validation, and anchored reporting issues; **Medium** for reconstruction and originality interpretations that depend on explicitly limited retained audits. This confidence is qualitative and not calibrated. The generic Minor Revision disposition follows the repairability of M1–M4, not an aggregate of dimension labels.

## Exact artifact binding

Paths below are relative to `/home/vlsi/rtl2gdsagi`. Text hashes are SHA-256 of the exact stdout bytes from `pdftotext -layout <PDF> -`, read in this review; PDF-byte hashes remain the authoritative rendered-artifact binding.

```text
a013da072d36c5794c8d3651285eeff03f26e53bc9957b8af9b69b74f0b88086  rtl2gdsagi_paper/main.tex
07c80fa0d12d594c651bfd3753f22622acbf6f6119254934fb8011503d294eac  rtl2gdsagi_paper/supplement.tex
3412d0f4357165fa17973a59f90217f198a7eb64733346946d49fdd3b642c6db  rtl2gdsagi_paper/main.pdf
43143cb8a1828d6b4a52440141d254b36846314f714a9f7401bbbb32fbe6a1d8  rtl2gdsagi_paper/supplement.pdf
7f235ec937382c36f6d80696eea2459255a69feefeea211b6860d518cc0b875b  main.pdf extracted text (33896 bytes)
ab6382c814a7803f34dd21c87793d41009e71c1c613122a9226de4fe1f339aef  supplement.pdf extracted text (16303 bytes)
e0733c07718806022edd2d279c476877eb90a74850af11ff0740bfe4818402a1  rtl2gdsagi_paper/generated/live_results.tex
ce30a277f2c25c664964ca83f9bd789f6c2ec6400e50b1528f39227b645b9775  rtl2gdsagi_paper/generated/frozen_macros.tex
4082eb90a2ce130c31e89f660d7d6b4a5a8371cd4cbb04c40ef1a1d2eb9f2fa2  rtl2gdsagi_paper/generated/scripted_baseline_macros.tex
8f105251414597b0189c099be8c26b0da583a195bc9564bfa8e746ddbad2361a  rtl2gdsagi_paper/generated/qor_table.tex
d473ad909c1dbd7f4bac2021a56e1c4b599b27f533d66cd513513e5b22431618  rtl2gdsagi_paper/generated/signoff_table.tex
045e078a30747062532f3ea5d6b659d468be6eae2b27c4f7f72a3244589d2ba7  rtl2gdsagi_paper/generated/reproducibility_table.tex
fe7b73d818b97d5c22906106011daf0203ddcf0fcb083a720c622912d9ec6209  rtl2gdsagi_paper/generated/frozen_fault_table.tex
b81de17bc211317b2ec95908cbbd33c4f34c092019e16d974e0e48cfc385de92  rtl2gdsagi_paper/generated/checker_obligations_table.tex
812ac102c4bf35f6107ec78511ac59925f6b10be095bf744761713c9f118ac42  rtl2gdsagi_paper/generated/class_replay_table.tex
63c654cc17aa689e1fdd4c39bdf8d35a6eb9e8793e3c5861e564f48995a81033  rtl2gdsagi_paper/generated/scripted_baseline_table.tex
e1ac173e7ec37fcf86fd81c43e1057b00fa07520b0a3501d5c6410f1bb714e3a  rtl2gdsagi_paper/generated/extended_results.tex
fbf1b8db0045131d1169c1e5c09c06c3eb8ee2b7bafccfadfe9772d1502ecae0  rtl2gdsagi_paper/generated/padding_thread_table.tex
f61f91ba644c005d38daf5334438fa92dba5c753cb739561159f680d10501845  rtl2gdsagi_paper/generated/episode_table.tex
395948f80536d583d4f63a96ce9ee0492506a6ad9e431884e201ddb3820b47bf  rtl2gdsagi_paper/generated/configured_drc_controls_table.tex
c7564653250950d81097b800c759e5202f8437d471de77ded980650490eec9cb  rtl2gdsagi_paper/generated/supplement_large_cases.tex
dd9903084792355b2561f1667ea3c7353b46afac51d0bacbf5a214e98f8b24a3  rtl2gdsagi_paper/generated/supplement_history_table.tex
f190f4fc4d3c7a2bf0857d7b310da23dcaacde0da58d26302c9a134fad43f41b  rtl2gdsagi_paper/figures/timing_stress.pdf
64642e275450739cf69b6afebfcc1d4241fbe5e26d038b56b74f16c7ef53c00c  runs/scripted_baseline_bounded_20261013/experiment_manifest.json
c6237b02179bc8785f1b88d3d51294f2094b2bccf2d461cbb51872845510d7b6  rtl2gdsagi_paper/evidence/scripted_baseline_metrics.csv
fd81236614c35bd7087bfd7ce9af65cb46eea34b0c582d420eeadd725d6e11cb  rtl2gdsagi_paper/evidence/citation_baseline_audit.json
6f40c18f70720990f3c59c5a69a2f6fd0ca0248108bba74f648deec00931da8f  rtl2gdsagi_paper/evidence/replay_stratified_audit.json
25a9e50f48f16039e2a2dbc4835d16dcdf9efbf36a1c4c20d8597df69d7c6413  scripts/run_baseline_candidate.py
1f0e6f1a35896142ac292b9894c352caac56403b3b82dcd1db9352b8b6ba4fa2  scripts/run_scripted_baseline.py
1d304920b24776e4d9e9b2b4584ab2da0871e5c3f8f277c75709961b93c07c54  scripts/collect_scripted_baseline.py
0764e79ca79f10e8a95c45669d62c6a9f341abab20746656eb2d367972df82dd  scripts/extract_signoff_metrics.py
```


## Scoped final closure — 2026-10-13

**METHODS closure: M1–M4 resolved; no remaining required methods revision in this scope.** This append supersedes the initial Minor Revision disposition only for the verified corrections. The initial review, its original locators, and its original hashes remain byte-for-byte intact: initial prefix length 21,361 bytes; SHA-256 `2956bd7ddf8137c2404c0d1d5758da65599f578016abf8c111b30b3d7ff927a8`.

criteria_binding_unavailable

calibration_status: NOT_CALIBRATED

This remains the METHODS context among three distinct internal contexts in the shared writing workflow, not independent external peer review. Other seat reports were not read. Publication remains a separate author-authorized gate; this closure is not venue acceptance.

### Verified correction anchors

| Item | Current source / rendered anchor | Closure evidence |
|---|---|---|
| M1 | `main.tex:222–225`; `supplement.tex:108–111`; main PDF §3.3 and supplement §4 | Both documents now state that fixed 0.2 delay fractions scale absolute I/O delays from 0.60 to 0.65/0.70 ns. Controls are combined requirement changes, excluded from 3 ns repairs; clock-only sensitivity is disclaimed. Resolved. |
| M2 | `main.tex:342–345`; `supplement.tex:112–114`; collector lines 39–49; `scripted_baseline.json` field `setup_toggle_outcome_equivalent_pairs` | All sixteen configurations remain counted. Eight off/on pairs are expressly disclosed as equal in CTS DEF, routed DEF, SPEF, setup and hold WNS. The revised collector checks and retains eight paired hash/metric summaries. Read-only closure checks rehashed all three artifacts for both members of every retained pair and matched the new summary; no native execution occurred. Resolved. |
| M3; associated table-summary clarification | `main.tex:331–332`; `generated/scripted_baseline_table.tex:2–9`; main PDF Table 8, p. 10 | Caption and header define best setup over all candidates reaching routed STA, including later hard failures; the spacing maximum is expressly DRC-failed padding 0. Text now identifies the table as a summary of strata and the CSV as 24 candidate rows. Counts and numbers are unchanged. Resolved. |
| M4; associated source-ledger clarification | `main.tex:160`; `supplement.tex:25–27`; main PDF Table 1, p. 4 | The 24-state cohort is now assigned to frozen native execution plus the hashed stopping harness. Supplement opening supplies the same ledger distinction. The af31 base and separate study stopping policy remain clear in context. Resolved. |
| Successful identity locators / failed-state scope | `supplement.tex:127–134` | Manifest claims are restricted to configuration and harness hashes. Successful identities are located in each run's `signoff.json` and `gate_evidence.json`; failed states have no release certificates. Verified locator existence and candidate-ID agreement for all five successful runs, and absence of `signoff.json` for failed states. This is a locator check, not a repeated full native or certification audit. Resolved. |
| Diagnosis and pilot termination boundary | `main.tex:131–136`, `231–234`; `supplement.tex:116–125` | Three per-stage attempts and 24 diagnosis attempts are settings of recorded live episodes, expressly not a universal termination guarantee. Main text names the unchanged-IR/date-bearing-GDS fingerprint loop and the study harness's stopping role; controller acceptance remains frozen. Entire CLI pilot and bootstrap remain excluded and retained. Resolved. |
| Final introduction shortening | `main.tex:52–63`; main PDF §1 | Reread both paragraphs after the pagination edit. OpenROAD/OpenLane infrastructure citations, selected-implementation/input evidence, omitted-rule/stale-GDS risks, all three questions, and the executable integration contribution remain explicit. No new numeric, source, method, priority, or model-value claim appears in the revised paragraphs. |

These reporting fixes bring Evidence Sufficiency and Writing Quality to **MEETS for the corrected, bounded scope**; Originality, Methodological Rigor and Argument Coherence retain their initial **MEETS** judgements and stated uncertainty. These are the same five generic categorical criteria, without aggregation or empirical calibration. Finite-grid selection, eight equivalent toggle pairs, historical live-source origin, partial independent full-IR availability, zero guardband, single-corner scope, and inability to infer incremental model value remain substantive limits, not findings erased by closure.

### Render and artifact checks

Final filesystem PDFs were checked with `pdfinfo`: main **12 pages**, supplement **6 pages**. These counts were obtained from the final files, not inherited from the initial review. Direct `pdftotext -layout … -` output exactly matches current `evidence/manuscript.txt` and `evidence/supplement.txt`. Visually inspected in-memory rasters of current main PDF Tables 1, 6, and 8 (pp. 4, 8, 10); labels, caption, rows, and revised remit columns are legible without clipping. Table 6 retains its checker-interface qualification. The shortened supplement artifact-verification paragraph was checked in source and current PDF text, not through a full visual page audit.

Current retained TeX logs contain no overfull boxes, LaTeX warnings, undefined-reference/citation notices, or LaTeX errors under the checker's blocking scan. They contain **11 main and 2 supplement underfull-box notices**. The revised Overleaf checker records underfull notices separately and defines its blocking-warning scope; **all warnings zero is not claimed**. Its retained build receipt still binds an earlier revision, and the retained ZIP's affected entries do not match these final inputs. A fresh ZIP rebuild and package verification remain author-workflow delivery steps before claiming final package readiness. No fresh build or ZIP was generated by this METHODS closure.

All sixteen actual generated inputs were hash-checked against the initial review. Fourteen are unchanged; only `scripted_baseline_table.tex` (caption/header) and `checker_obligations_table.tex` (ragged-right column formatting) change. Their final hashes are below. Manifest, 24-row metrics CSV, and stopping harness hashes remain unchanged; the new pair summary/collector changes reporting evidence. The initial full acceptance audit is retained without repetition. No broad native reaudit, regression run, model/API call, EDA experiment, external message, or publication action was performed. Only this closure was appended to the requested report.

### Final closure hash binding

The following current hashes supersede earlier bindings only for these paths. The other fourteen generated-input hashes remain exactly those in the initial binding. Native result counts remain spacing 3/4, PDN 1/2, fixed 3 ns timing 0/16, and slower-period controls 1/2; five certifications in total with the period control kept separate. Paths are relative to `/home/vlsi/rtl2gdsagi`.

```text
2aa92affa3a4eb7474e1eac7cd859529cbd4ec02f0b39bbc2358fe4388af7c80  rtl2gdsagi_paper/main.tex
d0e3f9fb656ff7839dd52c19fe8e515c3345db9e06f4f4ac68331e00c1b2717b  rtl2gdsagi_paper/supplement.tex
d7b1a675203701620c2001ee27d3225d77bb4bd7a19a95600992e1d6cccda751  rtl2gdsagi_paper/main.pdf
78e0c03002c732f2b6d5bef85f7163de0530b3bccd256b92441f5e69a4bf21fa  rtl2gdsagi_paper/supplement.pdf
a4e69a6d58291d476325ecdade22817456d620d56d03d6466430f70c15e57566  rtl2gdsagi_paper/evidence/manuscript.txt
aed13f3b0a851be4ccb16846545f2dfbbbbb975beb535d525c4801406e8e7ae6  rtl2gdsagi_paper/evidence/supplement.txt
0b0bc32bf6545a3efac70eeeaabe7c2bca12afc613ae3f10f595c41b39cd572a  rtl2gdsagi_paper/generated/scripted_baseline_table.tex
ae928e463c8cb75669e0a1e409469f7c0495bed319c5ef305910b7360067b17b  rtl2gdsagi_paper/generated/checker_obligations_table.tex
560915dc385b881e04d11165645e51f4ba3990bbd35a7b03e657c3ae15169537  rtl2gdsagi_paper/evidence/scripted_baseline.json
6c2deeea47436485ee26fd369a12ce6517efa5acadadc5fb270d5d2ed3b12277  scripts/collect_scripted_baseline.py
7c23c836cad735f006e849ffdbb54f0b5e2ab1f835e1e1faae7497412b8a7dc2  scripts/verify_overleaf_package.py
820600fa233806334077b7fd1c8b176f509b009e16fe57b4310a7efa2db6054a  rtl2gdsagi_paper/main.log
3f769cb1dab6852a7ee3e89b00b96b191d2227a4e6cb5f17a84fd1f690a4ddd3  rtl2gdsagi_paper/supplement.log
64642e275450739cf69b6afebfcc1d4241fbe5e26d038b56b74f16c7ef53c00c  runs/scripted_baseline_bounded_20261013/experiment_manifest.json
c6237b02179bc8785f1b88d3d51294f2094b2bccf2d461cbb51872845510d7b6  rtl2gdsagi_paper/evidence/scripted_baseline_metrics.csv
25a9e50f48f16039e2a2dbc4835d16dcdf9efbf36a1c4c20d8597df69d7c6413  scripts/run_baseline_candidate.py
```
