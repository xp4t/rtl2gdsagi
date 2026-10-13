# Frozen revision review — METHODS

## Reviewer summary and authority

- Seat: METHODS; fresh review of the current revision using ARS `peer_reviewer_agent.md` (3.23.0).
- **Scoped verdict: Accept for the METHODS assessment**, with the nonblocking reporting recommendations below. This is an internal scholarly assessment, not publication availability, venue acceptance, or independent external peer review.
- `criteria_binding_unavailable`
- `calibration_status: NOT_CALIBRATED`
- Criterion source: the five field-general questions in the supplied ARS peer reviewer guidance. No venue-specific criterion or numerical quality score is inferred from Springer LNCS formatting.
- Provenance: separate spawned review context, sharing the author's workspace within the same writing workflow. Context separation does not establish independent errors or external review. Other review reports were not read. The expressly supplied citation-compliance audit was read as evidence, not as a peer verdict.

The contribution is a candidate-bound release contract supported by constructed fault coverage, fixed-proposal native replay, and artifact repeat checks. Its primary empirical claims are justified at their stated scope. The previously stale Table 4 was corrected during this review; I verified the corrected generated rows and rebuilt PDF/text and do not retain that issue as an unresolved finding.

## Inputs, observations, and actual checks

The supplied main/supplement SHA values identify the **TeX sources** and match exactly. Git HEAD observed was `aec0fda7ee09bd98cc7c8d6965e91120ec4d9062`; the workspace contains uncommitted experiment and manuscript material, so this review is bound to observed bytes rather than a claim that every input is committed. Appendix A records the final source, PDF, text, generated-input, and principal evidence hashes.

I read the complete main source and supplement, both complete saved PDF texts, and all 14 distinct generated files included by the two documents. Fresh `pdftotext -layout` extraction to stdout was byte-identical to `evidence/manuscript.txt` and `evidence/supplement.txt`, including after the Table 4 rebuild. I checked textual figure/caption evidence; I did not perform a pixel-level PDF layout audit.

Read-only checks performed in this review:

1. Recomputed the sorted-path/Python-byte implementation fingerprint for current `src`, the frozen executor source, and the archived proposal-origin source. Current/frozen equal `af31b39f67827a3375c52bf41f52a727130947f8b5716d80b2680c7de88ca06c`; archived equals `18d948815ac6d0af630a5440578304dc9270e1be659c602b5aa7149f40aab22b`. The frozen tar archive contains 50 source/resource files, including two non-Python resources, all byte-identical to current workspace counterparts.
2. Inspected all 14 primary `run_state.json` and `signoff.json` records: every run has 21 successful stages, a clean signoff, and no recorded signoff problems. Rehashed 336 file-valued primary ledger artifacts against recorded digests. Revalidated all seven pairs with the retained implementation-identity function, which also calls production candidate-manifest verification.
3. Independently parsed GDS records and zeroed only the 24-byte payloads of BGNLIB/BGNSTR date records. All seven route bundles (DEF, mapped/routed netlists, SPEF) and date-normalized GDS pairs match. Only the register pair has identical raw GDS. Compared every corrected Table 4 row against these records and confirmed the same rows in the current main PDF text.
4. Independently reconstructed all 20 proposal YAML states from archived IR defaults, characterization/configuration deltas, curated repair notes, and cumulative authorized proposals. All 20 match the final replay configurations; all seven archived successful final IRs match before replay. The three PDN states include offset 50.0→21.42 micrometres and utilization 0.35→0.29. Confirmed the retained excluded 20-state pilot and the separate corrected complete-IR cohort.
5. Inspected raw event streams and terminal states for all 20 final replays. Spacing: three certifications; PDN: three certifications; timing: thirteen `sta_signoff` failures and one placement failure. Proposal configuration file hashes match the manifest. Archived accounting remains eleven timing failures plus two unavailable target checks, with one successful timing state.
6. Checked all eight ablation event streams, source-overlay fingerprints, rendered CTS/routing commands, and overlay diffs. Only the stated CTS/routing padding calls are removed from `render.py`; the both-on overlay equals frozen production source. Verified the retained pinned-binary one-worker query and explicit eight-worker routing command.
7. Inspected all 18 frozen fault records and their blocking reasons, the fixture driver, and current recorded-spacing-repair provenance/clean certification. The swap fixtures use `runs/frozen_recorded_spacing_repair_20261013`, executed on af31 with zero new model calls.
8. Parsed all 24 paired OpenLane DRC control reports, checked categories/marker counts, inspected child `execve` traces, and rehashed 173 input/deck/report/trace/output records. Inspected the deck's runtime switches and public/retained source confirmation; five confirmation records report matching bytes. Freshly opened the pinned public wrapper, primary EQY configuration documentation, MCP4EDA and EDAid landing pages for bounded corroboration.
9. Checked the four accumulator records: responses 3+3+10+7=23, no clean certifications/signoff files, two policy stops and two incomplete cases. Checked retained EQY positive counter/shift PASS and counter-mutant FAIL markers and their split/group configuration. Scanned current citations: 13 bibliography entries, 15 cited-key occurrences, all keys accounted for.

No new native EDA execution, model/experiments API call, publication operation, or external message was performed. Native outcomes above were audited from existing execution records. Only this designated report was written.

## Criterion-bound dimension judgements

| Dimension | Criterion and source | Judgement | Anchored evidence and rationale | Uncertainty / decision impact |
|---|---|---|---|---|
| Originality | ARS: contribution defensible relative to relevant literature | MEETS | Main §§1, 5 distinguish release-candidate identity, parser/invocation obligations, and repeat evidence from native EDA algorithms and existing feedback-driven agents. FlowFixer-EDA is explicitly acknowledged as using patch validation and native feedback. | Literature audit is at metadata/abstract/selected-passage scope; it cannot establish an exhaustive absence of comparable contracts. The manuscript disclaims that absence; no priority or superiority claim is required for this verdict. |
| Methodological Rigor | ARS: design/execution/analysis support the inferences | MEETS | Main §§3.1–3.2, 4.3–4.4; supplement §§1–3. Executor and generator snapshots are separated, full-state reconstruction is checked, native-feedback conditioning is explicit, and factorial interventions hold the stated physical constraints fixed. | Selected synthetic circuits, one corner/tool stack, dependent proposals, and one run per factorial cell limit generalization. Those limits are disclosed rather than used to estimate population performance. No unresolved methodological blocker. |
| Evidence Sufficiency | ARS: material claims have evidence of appropriate type/coverage | MEETS | Raw 14-run ledgers, 20 replay streams, eight ablation streams, 18 fault records, and active checker controls support the reported finite observations. Corrected Table 4 agrees with rehashed artifacts. | This review rechecks records, not new independent native runs. Parser/gate fixtures do not prove all attacks blocked or industrial/foundry qualification; §6 acknowledges that boundary. |
| Argument Coherence | ARS: question→method→finding→implication is traceable | MEETS | Main §§1, 3, 4, 6 consistently answer constructed-fault blocking, fixed proposal-state acceptance, and exact repeat questions. Archived versus frozen timing outcomes are reconciled by the ablation. | No supplied outline was used; structure was reconstructed from the full manuscript. The public-release statement still belongs to the separate final availability gate. |
| Writing Quality | ARS: reasoning precise enough to interpret and verify | MEETS | Main §3.2 and Table 7 separate unavailable archived checks from failures; §4.2 limits OpenLane observations to named interfaces; supplement §5 preserves unknown incomplete outcomes. | Nonblocking improvements to invocation locators, citation-audit continuity, and use of “independent” are listed below. No exact venue length/format authority was supplied. |

## Methods assessment by claim and class

### Frozen protocol and source accounting

Main §3.1 and source Table 1 correctly use af31 as the **executor** for the seven primary pairs, twenty fresh replays, repeated fault checks, and earlier accumulator cohort. Snapshot 18d is the **generator/controller origin** of the nine archived live episodes and their twenty proposals. Its earlier timing certification is not transferred to HEAD. The four declared padding overlays are controlled interventions on af31, not an undisclosed third primary implementation.

The primary configurations reuse selected successful implementation IRs before the frozen rerun. This supports repeatability of those configurations, not an unselected design success rate. The manuscript names small synthetic designs and retains failed scale probes separately. Whole-PDK content identity is explicitly excluded, while the selected decks/map and PDK revision are recorded. Trust in host/controller/native tools remains a stated assumption.

### Conditional replay and hypothetical-gate risk

| Originating class | Verified finite observation | Inferential boundary / strawman risk |
|---|---|---|
| Spacing | Archived and frozen states: 0/3 native failures; frozen 3/3 certified | These are three states from one repeated ALU fixture. They provide no observed false promotion in this class and do not establish a population spacing-repair rate. |
| PDN | Archived and corrected frozen states: 0/3 native failures; frozen 3/3 certified | Curated pre-model changes are essential. The excluded pilot's three failures cannot be attributed to the model or pooled into the final replay. Full-state reconstruction now addresses that confound. |
| Timing | Archived: 11/14 failed, 2/14 target unavailable, 1/14 successful; frozen: 14/14 hard failures, comprising 13 STA and 1 placement | Proposals are dependent intermediate attempts collected under native feedback. A hypothetical gate promoting each state is a deliberately weakened acceptance predicate, not an independently run controller arm or a matched external baseline. |

Main §3.2 and §4.3 already state the necessary conditioning and exclude general model-failure/end-to-end superiority estimates. Re-execution from RTL gives separate native executions, not statistically independent proposal samples. The strongest supported implication is that those timing proposal states lack the required frozen acceptance evidence. Neither the 11/20 archived aggregate nor the 14/14 timing result should become a general LLM failure statistic.

### CTS ablation inference

The raw setup values are +1.5860646578 ps with both padding reapplications off, +9.8676625219 ps with CTS off/routing on, and −0.6536993354 ps with CTS on under either routing-padding setting. Each value is identical at one and eight routing workers. Synthesis and placed DEF hashes match across the CTS intervention; CTS and downstream artifacts differ. Overlay diffs confirm removal of only the named calls.

Thus main §4.4's “effect in these executions” conclusion is supported. Routing padding has an effect when CTS padding is off, so the experiment should not be summarized as routing padding having no effect. Worker count has no observed **slack** effect in this ALU factorial; that does not imply artifact determinism or absence of worker sensitivity for the larger shift register. One run per factorial cell does not establish a general timing law or repeat-variance estimate. The paper's present wording respects these limits.

### Fault coverage and checker scope

All six classes have three recorded blocks on af31. Stale same-top geometry and post-repair substitution are blocked by content/invocation or gate-lineage disagreement. Missing FEOL is blocked by an unapproved deck and a 152-versus-211 inventory mismatch. The synthetic LVS pass is rejected for absent executable compare/circuit cross-references. Removed PDN vias fail a structural check; missing mapping fails a native stream-out layer check.

These are engineered native/parser/ledger coverage fixtures, not eighteen independent attacks or a measured adversarial false-pass rate. The fabricated LVS database and cached-green/nonempty-PDN comparator are intentionally weak predicates. Main §3.2 and Table 5 classify them as obligation coverage and do not present them as complete external-flow behavior. The recorded-repair swap uses the current certified repair, so it is not dependent on an old-controller repair certification.

The audited OpenLane wrapper forwards input/report without modern rule switches; the captured direct modern command passes `feol=1 beol=1 offgrid=1 seal=1 floating_met=0` and the adapter injects the same options. The PDK option `floating_metal` is mapped to deck variable `floating_met`. The legacy deck is an explicit compatible override with built-in FEOL off, BEOL/off-grid on; it is not a demonstrated stock-default selection. Stock `RUN_KLAYOUT_DRC=0` and default Magic behavior are distinct from the executed interfaces. The public [pinned wrapper](https://raw.githubusercontent.com/The-OpenROAD-Project/OpenLane/ff5509f65b17bfa4068d5336495ab1718987ff69/scripts/klayout/run_drc.sh) corroborates the narrow invocation reading.

Reparsed controls give legacy 166 categories/3–0–4 violating markers and modern 220/3–1–4, with paired clean 0–0–0. These raw control inventories are not the primary 211-category normalized contract. Stage return zero despite markers demonstrates that marker reporting and release rejection are different obligations. Main §4.2/Table 6 correctly restrict unsupported candidate/deck/map/lineage obligations to those checker interfaces and label the incompatible KLayout→Netgen no-compare test unassessed. The inactive modern pairing is excluded as an active-DRC baseline. No full OpenLane-flow, comprehensive FEOL, Magic, seal/floating-metal, or foundry comparison follows.

### Literature and incomplete outcomes

The fresh citation audit confirms 13 source identities at its declared reading scope, including seven printed DOIs. The current bibliography has added the four confirmed conference page ranges. ChatEDA follows journal author order/year; ORFS-agent stays the 2025 conference source rather than importing changed 2026 preprint performance; MCP4EDA/AuDoPEDA/ChiBench retain preprint labels; DRVerify is vendor documentation. Related Work makes a bounded integration contribution rather than claiming invention of tool feedback or formal priority over every controller. Primary landing pages for [MCP4EDA](https://arxiv.org/abs/2507.19570) and [EDAid](https://aclanthology.org/2025.naacl-long.83/) corroborate the narrow descriptions; full bodies were not audited here.

Supplement §5/Table 3 retains all four accumulator cases with zero certifications, two policy stops, two incomplete outcomes, and 23 valid responses. Incomplete cases remain unknown eventual outcomes; they are not counted as verified successes or algorithmic failures. The cohort is separate from both nine archived episodes and twenty replay states. No account/billing explanation is required in the paper.

## Findings and actionable recommendations

**Critical: none. Major: none. No unresolved decision-bearing METHODS defect.**

| ID / severity | Precise anchor | Observation | Suggested action / effort |
|---|---|---|---|
| M1 / Minor, nonblocking | Main §4.2, `main.tex:255–256`; supplement §4 | Main says the supplement contains options and commands. Supplement gives option semantics/counts but no literal commands or exact command-file locator. Actual argv/trace evidence exists in the artifact. | Point this sentence to `evidence/openlane_invocation_audit.json` and `runs/openlane_invocation_audit/controls_v1/executions/*/command.json`, or add the five switches plus command locator to supplement §4. Quick reporting edit; no rerun. |
| M2 / Minor, final-gate provenance follow-up | `CITATION_AUDIT_FROZEN.md` “Frozen inputs”; JSON `inputs[0]`, inventory and manuscript locators | The fresh audit freezes older main hash `0bbaad3584623037b5444701f4c0949ab272717c2e4a340515ea11b20db9b76e`, not current `aa000…`. Its old lines and missing-page recommendations therefore do not certify current exact bytes. The source metadata remains useful and the current page additions are visible. | Preserve the original audit and add a final-gate continuity receipt mapping the current bibliography/claim anchors to its per-reference evidence, then bind the rebuilt artifacts. Do not present the old receipt as an audit of the current hash. Moderate bookkeeping; no need to repeat resolved DOI transport solely because prose changed. |
| S1 / Suggestion | Main §2.2, §3.1 and EQY reference | The recorded tool identity is available as `EQY v0.68-2-g4a72eb9`, while the reference uses mutable `/latest/`. Primary [configuration documentation](https://yosyshq.readthedocs.io/projects/eqy/en/latest/config.html) supports split/group semantics but does not prove the local controls. | Add the retained EQY revision to the tool paragraph/reference or a supplement locator. Quick edit. |
| S2 / Suggestion | Main Table 7 caption; supplement §1 | “Independent native executions” can be mistaken for independent proposal samples, although §3.2 explains conditioning. | Prefer “separate executions from RTL”; retain the native-feedback/dependent-trajectory caveat. Quick edit. |
| S3 / Suggestion | Main §5, ChiBench/DRVerify paragraph | “These works” jointly motivates rule intent/coverage, while the citation audit ties the runset rationale specifically to DRVerify. | Attribute the rule-intent/coverage rationale to the vendor white paper and use ChiBench only for RTL tool-testing context. Quick edit; no novelty expansion. |

The initially stale `generated/reproducibility_table.tex` is **resolved**, verified against all seven frozen pairs and rebuilt main PDF/text. The collector now regenerates that table from current pairs. Old conflicting rows are not part of the final verdict or hash binding.

## Cross-section checks and verdict rationale

| Check | Status | Evidence / limit |
|---|---|---|
| Title and abstract match measured scope | Pass | Frozen-source candidate evidence, six classes, seven pairs, class-specific replay. |
| Introduction questions answered in conclusion | Pass | Main §§1/6 track fault coverage, proposal states and exact repeat evidence. |
| Tables/figures referenced and interpretation consistent | Pass after correction | All included table/figure labels referenced; corrected Table 4 matches evidence; archived timing figure remains labeled 18d. Pixel layout not assessed. |
| Citation-key/source accounting | Pass at bounded scope | 13 references, no orphan/uncited keys; source metadata checked against the supplied audit; exact audit continuity is M2. |
| Length/venue acceptance compliance | NOT_ASSESSED | No exact venue criteria or permitted length supplied. |
| Public frozen release availability | Separate final gate | User states publication is pending. No current-release availability/receipt validation is claimed by this review. |

The METHODS verdict is Accept because the principal finite observations are supported and the key inferential limitations are stated. The remaining items are reporting/provenance improvements with existing evidence; they require neither a new comparative controller arm nor new EDA experiments. This recommendation supplies no approval requirement for the already-authorized publication. The separate final gate must bind and check the actual delivered package before its availability is asserted.

Confidence: **High** for local counts, source/reconstruction accounting, corrected repeat hashes and ablation interventions; **moderate** for literature positioning at the audit's restricted reading scope. No independent error model, empirical calibration, comprehensive security certification, or venue-acceptance inference is made.

## Appendix A — final observed SHA-256 binding

These hashes bind this report to the bytes inspected after the generated-table correction. Earlier main PDF/text hashes were superseded during this review and are not the reviewed final package.

| Input relative to `rtl2gdsagi_paper/` | SHA-256 |
|---|---|
| `main.tex` | `aa000b982ef658964a94c850c53415b0bbcc8c1db263457b9ff91cb43c546b48` |
| `supplement.tex` | `7ddc69165b429c21c3655e1db7c65f5fc6849db5c948c1273ef469d3a7357ed4` |
| `main.pdf` | `9c81288cfa6219f58ac96aa11fb7c3cb60c30546fbdb9e01099adecf029edd79` |
| `supplement.pdf` | `a711bdf17f4ec6b851f6fb568f033be38b2020283e0d4b3039911a71feee511c` |
| `evidence/manuscript.txt` | `68ebbb506421c75581efdd9724d2362529fb7ea743cf0017e0720bb8e7b6e376` |
| `evidence/supplement.txt` | `8caa6a1e32bdcedb5984fc4c1371dc31ff61855cba07ad6821d2386f228555cb` |
| `generated/checker_obligations_table.tex` | `3e112ef5ba00f93919d5f826a34a958d5194a40864b613596385d93f01257520` |
| `generated/class_replay_table.tex` | `4e686c04906ac9e46b1150132298b35eb3dd85fb311886c283942fc5c36632f1` |
| `generated/configured_drc_controls_table.tex` | `395948f80536d583d4f63a96ce9ee0492506a6ad9e431884e201ddb3820b47bf` |
| `generated/episode_table.tex` | `3c20c8925efea9529ad06ef021e2df0e0166304250a09209621f957f9d5cfd54` |
| `generated/extended_results.tex` | `e1ac173e7ec37fcf86fd81c43e1057b00fa07520b0a3501d5c6410f1bb714e3a` |
| `generated/frozen_fault_table.tex` | `fe7b73d818b97d5c22906106011daf0203ddcf0fcb083a720c622912d9ec6209` |
| `generated/frozen_macros.tex` | `ce30a277f2c25c664964ca83f9bd789f6c2ec6400e50b1528f39227b645b9775` |
| `generated/live_results.tex` | `e0733c07718806022edd2d279c476877eb90a74850af11ff0740bfe4818402a1` |
| `generated/padding_thread_table.tex` | `d120ff89c7c9d4d2d252e4ea3a5c1afa5d1b46ec8f9ba9f2b70970b3f64f4778` |
| `generated/qor_table.tex` | `8f105251414597b0189c099be8c26b0da583a195bc9564bfa8e746ddbad2361a` |
| `generated/reproducibility_table.tex` | `045e078a30747062532f3ea5d6b659d468be6eae2b27c4f7f72a3244589d2ba7` |
| `generated/signoff_table.tex` | `d473ad909c1dbd7f4bac2021a56e1c4b599b27f533d66cd513513e5b22431618` |
| `generated/supplement_history_table.tex` | `dd9903084792355b2561f1667ea3c7353b46afac51d0bacbf5a214e98f8b24a3` |
| `generated/supplement_large_cases.tex` | `09a175eb521c6d1fb6103e2ba5b8057dcbbc5cc9e694e45470d85d2901529a0b` |
| `figures/timing_stress.pdf` | `f190f4fc4d3c7a2bf0857d7b310da23dcaacde0da58d26302c9a134fad43f41b` |
| `evidence/frozen_results.json` | `41d840d81c4c995a9aa703c88516bcfafec5bb8ebbe02b9638637655b5ead350` |
| `evidence/reproducibility_final.json` | `b9f3f8f7ccc384a471012f4eb200ee0de2cec6ad0ca42a50c9579fa45bee67f4` |
| `evidence/native_fault_injection_frozen.json` | `c87ab6dbf2535f316b04d4202b5935b84f4cc42549b06cc94d6093a4d2c5a00c` |
| `evidence/openlane_invocation_audit.json` | `34170f5f7a776e6b7d73994a1fd9569b5570bd19da8b09ffbfc3098c75c87d68` |
| `evidence/CITATION_AUDIT_FROZEN.md` | `02e7349bc4d2d8464bf594d7d90cb81923ee23a4568c9e4dbdddc0add216a4f4` |
| `evidence/citation_audit_frozen.json` | `d7654fed28b5d0989a3cf0476303ad407756c65ac1996680adb0bda0cf6ba3e0` |

Recorded at 2026-10-13T07:49:16.846678+00:00. Only the designated review report was written.


## Scoped editorial closure — current delivered document bytes

This addendum preserves the original review, verdict and Appendix A unchanged. Its prefix is exactly the original **23,997 bytes**, SHA-256 `99a46e10415ee28d3c35018796d74fa81b755bc944de94cacc1aa632cf94dca8`. Appendix A remains the historical binding for that assessment; the table below binds this closure to the newly inspected files.

**Closure verdict: the listed editorial fixes are verified; the scoped METHODS Accept verdict remains unchanged.** No new decision-bearing METHODS issue was found. `criteria_binding_unavailable` and `calibration_status: NOT_CALIBRATED` remain applicable. This is the same internal writing-workflow review, not independent external review, venue acceptance, or publication approval. Author packaging/publication remains its separately authorized final gate.

### Verified fixes

| Item | Closure status | Current evidence and actual check |
|---|---|---|
| P1: original-episode caption | Closed | `generated/episode_table.tex` and supplement PDF text now identify **all nine original live repair episodes on 18d948815ac6**, explicitly separate from frozen replay/larger episodes. The nine rows and their numerical outcomes are retained. |
| P2: replay-column headers | Closed | `generated/class_replay_table.tex` uses wrapped **Archived failed / Archived missing / Frozen failed / Frozen certified** headers. The current main PDF text contains the corresponding columns. Rows remain spacing 0/3 failures and 3/3 certifications, PDN 0/3 and 3/3, timing archived 11/14 failed plus 2/14 missing and frozen 14/14 failed plus 0/14 certified. |
| P3: factorial denominators | Closed | `generated/padding_thread_table.tex` and the current main PDF text show 2/2, 2/2, 0/2, 0/2 certified. Compared these with the retained frozen manifest: each row contains one run per worker count (1 and 8), with the same recorded slack/outcomes. |
| M1: literal switches and command locators | Closed | Supplement §4 (`supplement.tex:105–110`) now states `feol=1`, `beol=1`, `offgrid=1`, `seal=1`, `floating_met=0`, the exact `executions/*/command.json` location and `evidence/openlane_invocation_audit.json`. These appear in current PDF text. Read the retained direct-modern metal-positive command record and verified its argv equals the audit's control argv and contains all five switches. Existing active-interface/full-flow limits remain explicit. |
| S1: retained EQY revision | Closed | Supplement §4 (`supplement.tex:110–111`) and current PDF text name `v0.68-2-g4a72eb9`. Compared it with the retained primary signoff tool record `EQY v0.68-2-g4a72eb9`. |
| M2: citation-audit continuity | Closed at the requested continuity scope | Read `evidence/citation_continuity_frozen.json`. Its current-main hash equals `aa000…`; its original-audit hash and original-main hash match the preserved source audit. Independently parsed all 13 current bibliography entries: keys, exact entry strings, entry line numbers, citation paragraphs and per-key citation line locators match the receipt. For all 13, prior source records, verified metadata, reference numbers and status equal the original audit. Checked the four added page ranges. No fresh DOI transport or full-body audit is inferred; the receipt expressly preserves the earlier reading limits. |
| S2: execution wording | Closed for the identified caption/supplement sites | Table 7 caption now says **separate native executions**; supplement §1 says **twenty separate recorded-proposal executions**. Both changes are visible in fresh PDF text. Main §3.2's unchanged “run independently from RTL” remains paired with the native-feedback conditioning limitation; no statistical independence claim is inferred. |
| Stale repeat-row prevention | Verified | Read the current collector: it regenerates the repeat table directly from `reproducibility_final.json`. Read `evidence/manuscript_audit.py`: its per-design assertions require the emitted row to match the retained raw-GDS flag and Same DEF/SPEF/date-normalized GDS. Independently compared all seven current rows with frozen records. These regeneration/detection checks are present; I did not execute the collector or whole audit, which write other artifacts. |

The original optional S3 attribution suggestion remains unchanged because `main.tex` is unchanged. It was nonblocking and is not a condition for this scoped closure. No new requirement to edit the main text, supply a billing explanation, rerun native experiments, or seek reviewer permission is introduced.

### Build/text and scope checks

Read the current main/supplement build logs: no `Overfull`, `LaTeX Warning`, `Undefined` or `! LaTeX Error` markers were found; the terminal output records 11 main pages and 6 supplement pages. `pdfinfo` independently reports those page counts. Fresh `pdftotext -layout` extraction to stdout is byte-identical to both current saved text files. Checked the affected table/caption/switch passages in those current texts. No new compilation or pixel-level layout inspection is claimed.

Compared the original binding against current files: the main source, repeat table and principal frozen empirical/citation-audit records are unchanged. Changes are confined, within those bound manuscript inputs, to supplement source, rebuilt PDFs/text, and the three editorial generated tables. The new continuity receipt is bound below. This closure does not certify an Overleaf ZIP, public download, release receipt, or final packaged archive.

No other review report was read. No native experiment, model/experiments API call, publication operation or external message was performed. Only this designated report was appended.

### Closure SHA-256 binding

Paths below are relative to `/home/vlsi/rtl2gdsagi`. Hashes were computed from the current filesystem immediately before appending this closure.

| Current file | SHA-256 |
|---|---|
| `rtl2gdsagi_paper/main.tex` | `aa000b982ef658964a94c850c53415b0bbcc8c1db263457b9ff91cb43c546b48` |
| `rtl2gdsagi_paper/supplement.tex` | `2e2eb273acffbc28b1be077eec5a533e6fba756a622b0461cf35b59b066327ae` |
| `rtl2gdsagi_paper/main.pdf` | `df067d1b98dba094e5288123e94f22e27509c1d78e31f9b944e4065e54b09e44` |
| `rtl2gdsagi_paper/supplement.pdf` | `daac9afab3e1b879a0bf58adddaeade7e0a2daa2c3b5aefdfe38e8a55a352b01` |
| `rtl2gdsagi_paper/evidence/manuscript.txt` | `3a9899807f0b3ddeec125736d0beb352117464836ae8f14397af8106163b4f43` |
| `rtl2gdsagi_paper/evidence/supplement.txt` | `4b6c4dcb5f14a1258a5545bd7dffafcdf0fc0d6f13109445bf7fc36ffb9b0370` |
| `rtl2gdsagi_paper/generated/checker_obligations_table.tex` | `3e112ef5ba00f93919d5f826a34a958d5194a40864b613596385d93f01257520` |
| `rtl2gdsagi_paper/generated/class_replay_table.tex` | `812ac102c4bf35f6107ec78511ac59925f6b10be095bf744761713c9f118ac42` |
| `rtl2gdsagi_paper/generated/configured_drc_controls_table.tex` | `395948f80536d583d4f63a96ce9ee0492506a6ad9e431884e201ddb3820b47bf` |
| `rtl2gdsagi_paper/generated/episode_table.tex` | `f61f91ba644c005d38daf5334438fa92dba5c753cb739561159f680d10501845` |
| `rtl2gdsagi_paper/generated/extended_results.tex` | `e1ac173e7ec37fcf86fd81c43e1057b00fa07520b0a3501d5c6410f1bb714e3a` |
| `rtl2gdsagi_paper/generated/frozen_fault_table.tex` | `fe7b73d818b97d5c22906106011daf0203ddcf0fcb083a720c622912d9ec6209` |
| `rtl2gdsagi_paper/generated/frozen_macros.tex` | `ce30a277f2c25c664964ca83f9bd789f6c2ec6400e50b1528f39227b645b9775` |
| `rtl2gdsagi_paper/generated/live_results.tex` | `e0733c07718806022edd2d279c476877eb90a74850af11ff0740bfe4818402a1` |
| `rtl2gdsagi_paper/generated/padding_thread_table.tex` | `fbf1b8db0045131d1169c1e5c09c06c3eb8ee2b7bafccfadfe9772d1502ecae0` |
| `rtl2gdsagi_paper/generated/qor_table.tex` | `8f105251414597b0189c099be8c26b0da583a195bc9564bfa8e746ddbad2361a` |
| `rtl2gdsagi_paper/generated/reproducibility_table.tex` | `045e078a30747062532f3ea5d6b659d468be6eae2b27c4f7f72a3244589d2ba7` |
| `rtl2gdsagi_paper/generated/signoff_table.tex` | `d473ad909c1dbd7f4bac2021a56e1c4b599b27f533d66cd513513e5b22431618` |
| `rtl2gdsagi_paper/generated/supplement_history_table.tex` | `dd9903084792355b2561f1667ea3c7353b46afac51d0bacbf5a214e98f8b24a3` |
| `rtl2gdsagi_paper/generated/supplement_large_cases.tex` | `09a175eb521c6d1fb6103e2ba5b8057dcbbc5cc9e694e45470d85d2901529a0b` |
| `rtl2gdsagi_paper/figures/timing_stress.pdf` | `f190f4fc4d3c7a2bf0857d7b310da23dcaacde0da58d26302c9a134fad43f41b` |
| `rtl2gdsagi_paper/evidence/frozen_results.json` | `41d840d81c4c995a9aa703c88516bcfafec5bb8ebbe02b9638637655b5ead350` |
| `rtl2gdsagi_paper/evidence/reproducibility_final.json` | `b9f3f8f7ccc384a471012f4eb200ee0de2cec6ad0ca42a50c9579fa45bee67f4` |
| `rtl2gdsagi_paper/evidence/native_fault_injection_frozen.json` | `c87ab6dbf2535f316b04d4202b5935b84f4cc42549b06cc94d6093a4d2c5a00c` |
| `rtl2gdsagi_paper/evidence/openlane_invocation_audit.json` | `34170f5f7a776e6b7d73994a1fd9569b5570bd19da8b09ffbfc3098c75c87d68` |
| `rtl2gdsagi_paper/evidence/CITATION_AUDIT_FROZEN.md` | `02e7349bc4d2d8464bf594d7d90cb81923ee23a4568c9e4dbdddc0add216a4f4` |
| `rtl2gdsagi_paper/evidence/citation_audit_frozen.json` | `d7654fed28b5d0989a3cf0476303ad407756c65ac1996680adb0bda0cf6ba3e0` |
| `rtl2gdsagi_paper/evidence/citation_continuity_frozen.json` | `217a7897a655f25536b3f47d283596600768d63ec8fe3bab25c8d3b23b577a3c` |
| `rtl2gdsagi_paper/main.log` | `dc354a67c8359df7d7b1637554df6b9b97a3be228ec7e17b39770f62456b7bc1` |
| `rtl2gdsagi_paper/supplement.log` | `ea25cedeaa9827166ace438dd1a9d4bb29708f5a2422382102b4a0691a12e624` |
| `scripts/collect_frozen_results.py` | `999d90d5f53a469092195334517e20a5a19d1638bd13813f85377b235ff61b86` |
| `rtl2gdsagi_paper/evidence/manuscript_audit.py` | `37b278bfb73fb46565da1bf7131e6d60f25d1d09f897ed8c0f6ed8a2c7eb1941` |
| `runs/openlane_invocation_audit/controls_v1/executions/modern_direct_pdk_options_metal_positive/command.json` | `7749c0bfb96a4a031ccbe135bc59e3266e6e594bd52cd8a4d153068a4583be95` |

Closure recorded at 2026-10-13T07:55:42.189277+00:00.
