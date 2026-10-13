# Frozen LNCS presentation review

| Field | Recorded value |
|---|---|
| Seat | PRESENTATION |
| Date | 2026-10-13 |
| Guidance | ARS `academic-paper/agents/peer_reviewer_agent.md`, package 3.23.0 |
| Verdict | **Minor Revision, limited to presentation** |
| Criteria | Field-general five categorical criteria; `criteria_binding_unavailable` |
| Calibration | `calibration_status: NOT_CALIBRATED` |
| Execution scope | Separate spawned context sharing the author workspace within the same writing workflow; internal review, without an independent external peer-review or venue-acceptance claim |

The current manuscript clearly distinguishes frozen implementation results, archived proposal origins, fresh proposal-state executions, and incomplete larger episodes. The stale reproducibility table found during this review was corrected while the review was running; its correction is verified and is not an outstanding finding. Remaining issues concern captions and column labels, with no new experiment needed to resolve them.

## Exact reviewed artifacts

All paths below are relative to `/home/vlsi/rtl2gdsagi/rtl2gdsagi_paper`.

| Artifact | Observed SHA-256 |
|---|---|
| `main.tex` | `aa000b982ef658964a94c850c53415b0bbcc8c1db263457b9ff91cb43c546b48` |
| `supplement.tex` | `7ddc69165b429c21c3655e1db7c65f5fc6849db5c948c1273ef469d3a7357ed4` |
| Current `main.pdf` | `9c81288cfa6219f58ac96aa11fb7c3cb60c30546fbdb9e01099adecf029edd79` |
| `supplement.pdf` | `a711bdf17f4ec6b851f6fb568f033be38b2020283e0d4b3039911a71feee511c` |
| Current `evidence/manuscript.txt` | `68ebbb506421c75581efdd9724d2362529fb7ea743cf0017e0720bb8e7b6e376` |
| `evidence/supplement.txt` | `8caa6a1e32bdcedb5984fc4c1371dc31ff61855cba07ad6821d2386f228555cb` |
| `evidence/frozen_results.json` | `41d840d81c4c995a9aa703c88516bcfafec5bb8ebbe02b9638637655b5ead350` |
| `evidence/reproducibility_final.json` | `b9f3f8f7ccc384a471012f4eb200ee0de2cec6ad0ca42a50c9579fa45bee67f4` |
| `evidence/native_fault_injection_frozen.json` | `c87ab6dbf2535f316b04d4202b5935b84f4cc42549b06cc94d6093a4d2c5a00c` |
| Included `figures/timing_stress.pdf` | `f190f4fc4d3c7a2bf0857d7b310da23dcaacde0da58d26302c9a134fad43f41b` |

The supplied main and supplement hashes match the **TeX source files** exactly. The initial progress message comparing them with PDF hashes was a comparison of different artifact types, not a source-binding failure.

Observed Git HEAD was `aec0fda7ee09bd98cc7c8d6965e91120ec4d9062`. Independently recomputing the implementation fingerprint from sorted `src/**/*.py` relative paths, NUL delimiters, and file bytes gives `af31b39f67827a3375c52bf41f52a727130947f8b5716d80b2680c7de88ca06c`. The retained proposal-origin identity is `18d948815ac6d0af630a5440578304dc9270e1be659c602b5aa7149f40aab22b`. The manuscript correctly distinguishes implementation fingerprints from Git commits.

## Actual checks and their limits

- Read the complete main and supplement sources, both complete supplied text extracts, and all 14 distinct generated files included by their `\input` statements. Independently ran `pdftotext -layout` on the reviewed PDFs into temporary storage: both fresh extracts match the current supplied evidence text byte for byte.
- Rendered and visually inspected every page of the initial 10-page main and 5-page supplement. After the correction, rendered and inspected **all 11 current main pages and all 5 supplement pages**. Temporary renders were kept outside the repository. The current report binds to the rebuilt main PDF above.
- Read all 14 primary `run_state.json` files: each has 21 stages with status `ok`. Rehashed 70 retained artifacts across those runs: mapped netlist, routed netlist, routed DEF, SPEF, and raw GDS. Their bytes match the recorded hashes. Recomputed GDS normalization by zeroing only the 24-byte BGNLIB/BGNSTR date payloads: all seven normalized pairs match; all seven routed bundles match; only the register raw-GDS pair matches.
- Cross-checked the recorded frozen replay manifest and class tally: spacing 3/3 certified, PDN 3/3 certified, timing 0/14 certified, with 13 `sta_signoff` failures and one placement failure. The archived timing tally remains 11 native failures plus two unavailable target checks out of 14; unavailable checks are not counted as confirmed failures.
- Checked the retained eight padding/worker observations: both worker counts agree in each padding combination, at +1.586, +9.868, -0.654, and -0.654 ps. The retained comparison records matching mapped netlist/placed DEF and differing CTS/downstream artifacts. The manuscript confines its CTS-effect inference to these executions.
- Checked the frozen fault record: six classes, three entries each, all 18 blocked. Supplement §1 identifies the current recorded spacing-repair episode supplying the post-repair swap artifact. Supplement §3 explicitly excludes the three incorrectly reconstructed pilot PDN states. The corrected replay launcher incorporates curated changes and asserts final-IR equality for archived successful episodes before launching native execution; this review did not rerun that reconstruction procedure.
- Matched every main/supplement table and figure label to a text callout. The 13 bibliography keys exactly match first-citation order; all are cited. Scanned current extracts for unresolved `??`, `[?]`, `TODO`, and `TBD` markers: none found.
- Checked account-detail omission using full reading, page inspection, and targeted term scans. No billing, account-balance, payment, quota, or provider-error narrative is rendered. Author contact addresses and the phrase “Source accounting” are unrelated to provider account details.

No native EDA experiment, model/API experiment, manuscript edit, table-generation command, external message, or publication operation was performed by this seat. Other review reports were not read. The checks above establish presentation and selected artifact consistency; they do not independently certify every native checker or bibliography entry's existence and semantic support.

## Visual inspection ledger

| Current pages | Observations |
|---|---|
| Main 1 | Two-line title, author block, abstract, and keywords are readable and unclipped. The short abstract retains constructed-class and iterative-trajectory qualifications. |
| Main 2–3 | Equation and notation are legible. Figure 1's matrix is readable and called out. Running title fits; continuation across the page boundary is clear. |
| Main 4 | Source-accounting table distinguishes af31 execution from 18d proposal origin. Protocol and replay descriptions remain readable. |
| Main 5 | Tables 2–3 retain clear units, complete seven-design rows, and correct callouts. |
| Main 6 | Corrected Table 4 now agrees with abstract, results, and native hashes: every DEF/SPEF/date-normalized pair is Same; register raw GDS is Same. Caption identifies seven frozen primary pairs and both matching netlists. |
| Main 7 | Tables 5–6 are legible. Repeated fault checks are explicitly consistency executions; OpenLane support is restricted to executed interfaces. No text/table overlap. |
| Main 8 | Tables 7–8 are readable; fresh outcomes, archived unavailable targets, and padding effects are distinguishable. Remaining column-label ambiguities are listed below. |
| Main 9 | Related work and scope are coherent. Ghose et al. appears as an ordinary citation [11], with no special authority or endorsement claim. |
| Main 10–11 | References 1–10 appear on p.10 and 11–13 on p.11. This is a continuous bibliography across an ordinary page break: **no float interrupts it**, and no individual entry is split at that break. URLs and numbered entries are readable. |
| Supplement 1 | Frozen and archived execution ledgers remain distinct; the current swap-fixture repair is explicit. |
| Supplement 2 | Nine archived episodes and timing figure are readable, captioned, and called out. Plot labels, legend, zero line, and terminal trajectories are visible. |
| Supplement 3 | Pilot exclusion and corrected-state reconstruction are clearly stated. Inactive OpenLane configuration is excluded from the active baseline. |
| Supplement 4 | Active DRC controls and all four accumulator outcomes are readable. The latter table preserves 3+3+10+7 = 23 responses, two controller stops, and two incomplete cases. |
| Supplement 5 | Stopping explanations, earlier observations, and artifact verification are legible. Earlier outcomes remain separate from the primary cohorts. |

The rebuilt main has 11 pages rather than the 10 described at intake. Its final page contains three references and substantial white space. This is a pagination observation, not an inferred venue-limit violation. If retaining ten pages is a packaging objective, shorten captions or improve float placement while preserving normal type size; recheck the bibliography afterward.

## Five criterion judgements

Criterion source for every row: the field-general five-dimension rubric in the named ARS peer reviewer guidance. Springer instructions are used only for the requested formatting checks; no venue/track acceptance criteria were supplied.

| Dimension | Judgement | Anchors and rationale | Uncertainty / decision impact |
|---|---|---|---|
| Originality | NOT_ASSESSED | Main §§1,5 describe an executable integration contribution and acknowledge comparable contracts elsewhere. | This presentation seat did not establish literature-wide novelty; no originality verdict. |
| Methodological Rigor | MEETS, within reporting scope | Main §3; supplement §§1,3,5 distinguish execution source, proposal origin, reconstruction exclusion, fixed-state replay, and incomplete outcomes. | Protocol presentation is assessable; experimental design and checker validity were not independently re-executed. No presentation blocker found. |
| Evidence Sufficiency | MEETS, within checked scope | Corrected main Table 4 agrees with rehashed primary artifacts; Tables 5,7,8 agree with retained tallies; supplement Table 3 retains the complete larger denominator. | Selected evidence consistency checked; no exhaustive native-report or citation-support audit. The earlier table contradiction is resolved. |
| Argument Coherence | MEETS | Main §§1,3,4,6 and supplement §§1–6 preserve the chain from evidence obligations to class-specific observations and bounded conclusions. | No population repair-rate or full-flow OpenLane-superiority inference is introduced. No unresolved decision-bearing contradiction. |
| Writing Quality | PARTLY_MEETS | All current pages are readable and callouts/reference numbering are sound; the three caption/header issues below hinder standalone table interpretation. | Local editorial repairs support Minor Revision; they do not require new data or a broad rewrite. |

## Findings and remedies

**Critical: none. Major: none outstanding.** The former Table 4 contradiction is resolved: current generated-file hash `045e078a30747062532f3ea5d6b659d468be6eae2b27c4f7f72a3244589d2ba7`, main p.6. The collector now emits that table from the frozen pair record. This correction is included in the verdict.

| ID / severity | Exact anchor | Issue | Actionable remedy / effort |
|---|---|---|---|
| P1 / Minor | Supplement p.2, Table 1; `generated/episode_table.tex:2` | “The full declared repair denominator” does not identify the archived nine-episode cohort or 18d source in the caption. Readers seeing the table alone can confuse its seven Verified outcomes with frozen replay or the separately retained four larger cases. Surrounding prose is correct. | Caption it as all nine original live episodes on `18d948815ac6`, separate from fresh frozen replay and larger episodes. Keep all rows. Under 10 minutes. |
| P2 / Minor | Main p.8, Table 7; `generated/class_replay_table.tex:4` | “Missing target” and “Certified” omit which execution cohort they describe. The table combines archived and frozen results, making the missing labels material to standalone reading. | Use “Archived missing” and “Frozen certified”, with wrapping as needed. Preserve 11/14 archived failures, 2/14 archived unavailable, and the fresh outcomes. Under 10 minutes. |
| P3 / Minor | Main p.8, Table 8; `generated/padding_thread_table.tex:4` | “Certified” contains counts 2/0, whereas Table 7 presents certification fractions. The caption explains two worker executions, but the denominator is absent from the cells/header. | Use “Certified / 2” or cells 2/2 and 0/2. Keep the one-run-per-worker explanation and the measured slack. Under 10 minutes. |

Suggested editorial checks, without blocking force: subsection headings currently use sentence case, whereas Springer §4.1 describes capitalization of substantive heading words; the title block also does not explicitly mark a corresponding author, as described there. These can be addressed during final formatting once the corresponding author is identified. The requested numbering and caption placement checks comply: numeric citations follow the reference sequence, table captions precede tables, and figure captions follow figures. Springer §4.9 permits citation-order numbering as well as alphabetical numbering; it does not require reordering this correctly matched list. [Springer instructions, §§4.1, 4.5, 4.9](https://cms-resources.apps.public.k8s.springernature.io/springer-cms/rest/v1/content/27852130/data/Instructions%20for%20Authors%20PDF).

## Cross-section disposition and scoped verdict

| Check | Disposition |
|---|---|
| Title, abstract, findings, conclusion | Aligned after the generated Table 4 correction. Abstract's qualifications remain intact. |
| Primary run/repeat outcomes | Fourteen 21-stage records and seven exact routed/date-normalized pairs agree with current presentation. |
| Archived versus fresh timing | Distinct sources and denominators; 11 failed + 2 unavailable remain archived-only, while all 14 fresh timing states fail hard checks. |
| OpenLane presentation | Supported obligations and configured positive/clean controls are shown; the inactive prior pairing is excluded. No full-flow detection or maintainer-endorsement claim. |
| Incomplete accumulator cases | All four remain visible. Neither incomplete case is certified or counted as an eventual algorithmic repair failure. No account-detail explanation is required. |
| Archived material moved to supplement | Original episode table, archived timing figure, earlier-history table, and larger cases are supplementary; current frozen evidence remains central. |
| Floats and bibliography | Pass: no float enters the bibliography. Current bibliography spans pp.10–11 continuously. |
| Exact ten-page expectation | Current observation is 11 main pages and 5 supplement pages. No supplied venue ceiling permits a stronger compliance judgement. |
| Internal review / publication | Internal writing-workflow assistance is disclosed. New frozen-release publication remains for its separate final gate; this report supplies no external peer-review or venue-acceptance certificate. |

**Minor Revision** follows from three local table-caption/header ambiguities. The central generated-table defect is fixed and independently checked against retained bytes. Implement P1–P3 as editorial changes, render the final PDFs, and update the artifact bindings for any changed inputs/PDFs. No additional experiment is required by this presentation review.

Confidence is high for layout, callouts, outcome-label preservation, and the primary artifact comparisons; it is limited for unassessed novelty, full methodological validity, and reference existence/support. The report is restricted to the exact artifacts above.

## Included generated-input hashes

All files were read in full. Shared macro files are listed once.

| `generated/` file | SHA-256 |
|---|---|
| `live_results.tex` | `e0733c07718806022edd2d279c476877eb90a74850af11ff0740bfe4818402a1` |
| `frozen_macros.tex` | `ce30a277f2c25c664964ca83f9bd789f6c2ec6400e50b1528f39227b645b9775` |
| `qor_table.tex` | `8f105251414597b0189c099be8c26b0da583a195bc9564bfa8e746ddbad2361a` |
| `signoff_table.tex` | `d473ad909c1dbd7f4bac2021a56e1c4b599b27f533d66cd513513e5b22431618` |
| `reproducibility_table.tex` | `045e078a30747062532f3ea5d6b659d468be6eae2b27c4f7f72a3244589d2ba7` |
| `frozen_fault_table.tex` | `fe7b73d818b97d5c22906106011daf0203ddcf0fcb083a720c622912d9ec6209` |
| `checker_obligations_table.tex` | `3e112ef5ba00f93919d5f826a34a958d5194a40864b613596385d93f01257520` |
| `class_replay_table.tex` | `4e686c04906ac9e46b1150132298b35eb3dd85fb311886c283942fc5c36632f1` |
| `padding_thread_table.tex` | `d120ff89c7c9d4d2d252e4ea3a5c1afa5d1b46ec8f9ba9f2b70970b3f64f4778` |
| `extended_results.tex` | `e1ac173e7ec37fcf86fd81c43e1057b00fa07520b0a3501d5c6410f1bb714e3a` |
| `episode_table.tex` | `3c20c8925efea9529ad06ef021e2df0e0166304250a09209621f957f9d5cfd54` |
| `configured_drc_controls_table.tex` | `395948f80536d583d4f63a96ce9ee0492506a6ad9e431884e201ddb3820b47bf` |
| `supplement_large_cases.tex` | `09a175eb521c6d1fb6103e2ba5b8057dcbbc5cc9e694e45470d85d2901529a0b` |
| `supplement_history_table.tex` | `dd9903084792355b2561f1667ea3c7353b46afac51d0bacbf5a214e98f8b24a3` |


---

## Final scoped editorial closure — 2026-10-13

**Closure verdict: Accept for the requested PRESENTATION scope.** P1–P3 are resolved against the current delivered inputs, PDFs, and fresh text. The initial review above, including its Minor Revision verdict and historical hashes, is preserved byte for byte. Its pre-append SHA-256 is `f74bbd69a2ce50ec14dd9a0f2c1fe99cad1a1ec794b09f9c4ae69c99f506b0cb`.

`criteria_binding_unavailable` and `calibration_status: NOT_CALIBRATED` remain applicable. This is internal review within the author writing workflow. Author packaging/publication remains its separately authorized final gate; this closure introduces no reviewer-approval requirement for publication.

### Current closure bindings

Hashes below were recomputed from the filesystem during closure. They supersede the earlier PDF/text bindings only for this appended assessment.

| Artifact, relative to the paper directory unless stated | Current SHA-256 |
|---|---|
| `main.tex` | `aa000b982ef658964a94c850c53415b0bbcc8c1db263457b9ff91cb43c546b48` |
| `supplement.tex` | `2e2eb273acffbc28b1be077eec5a533e6fba756a622b0461cf35b59b066327ae` |
| `main.pdf` — 11 pages | `df067d1b98dba094e5288123e94f22e27509c1d78e31f9b944e4065e54b09e44` |
| `supplement.pdf` — 6 pages | `daac9afab3e1b879a0bf58adddaeade7e0a2daa2c3b5aefdfe38e8a55a352b01` |
| `evidence/manuscript.txt` | `3a9899807f0b3ddeec125736d0beb352117464836ae8f14397af8106163b4f43` |
| `evidence/supplement.txt` | `4b6c4dcb5f14a1258a5545bd7dffafcdf0fc0d6f13109445bf7fc36ffb9b0370` |
| `generated/episode_table.tex` | `f61f91ba644c005d38daf5334438fa92dba5c753cb739561159f680d10501845` |
| `generated/class_replay_table.tex` | `812ac102c4bf35f6107ec78511ac59925f6b10be095bf744761713c9f118ac42` |
| `generated/padding_thread_table.tex` | `fbf1b8db0045131d1169c1e5c09c06c3eb8ee2b7bafccfadfe9772d1502ecae0` |
| `evidence/citation_continuity_frozen.json` | `217a7897a655f25536b3f47d283596600768d63ec8fe3bab25c8d3b23b577a3c` |
| `evidence/openlane_invocation_audit.json` | `34170f5f7a776e6b7d73994a1fd9569b5570bd19da8b09ffbfc3098c75c87d68` |
| Repository `scripts/collect_frozen_results.py` | `999d90d5f53a469092195334517e20a5a19d1638bd13813f85377b235ff61b86` |
| `evidence/manuscript_audit.py` | `37b278bfb73fb46565da1bf7131e6d60f25d1d09f897ed8c0f6ed8a2c7eb1941` |
| `evidence/live_results_followup_20261013.json` | `7b043386a39ca23159779d5f876e0d9e240994caedb273039c283051af46b97f` |

The other eleven included generated files match the initial report's hashes, including the corrected `reproducibility_table.tex` (`045e078a30747062532f3ea5d6b659d468be6eae2b27c4f7f72a3244589d2ba7`). Main source is unchanged; its current PDF changes through included generated inputs.

### Verified closure of the named items

| Item | Current evidence and disposition |
|---|---|
| P1 | **Closed.** Supplement p.2, Table 1 explicitly identifies all nine original live repair episodes on `18d948815ac6` and distinguishes archived outcomes from frozen replay and larger episodes. All nine rows remain. |
| P2 | **Closed.** Main p.8, Table 7 uses readable wrapped headers “Archived missing” and “Frozen certified”, alongside “Archived failed” and “Frozen failed”. Archived 11/14 failures and 2/14 unavailable remain separate from fresh 14/14 timing failures and 0/14 certifications. |
| P3 | **Closed.** Main p.8, Table 8 reports 2/2, 2/2, 0/2, 0/2 certifications. Its caption still identifies one execution at each worker count; the four slack values are unchanged. |
| M1, author-supplied closure label | **Verified within presentation/invocation scope.** Supplement p.3, §4 renders `feol=1`, `beol=1`, `offgrid=1`, `seal=1`, `floating_met=0`, the `runs/openlane_invocation_audit/controls_v1/executions/*/command.json` locator, and the exact audit JSON locator. Of 30 retained command files inspected, six direct modern positive/clean commands contain all five literal switches and exactly match recorded audit argument vectors. Paths wrap legibly. Full-flow OpenLane comparison remains explicitly unassessed. |
| S1, author-supplied closure label | **Verified.** Supplement p.3 renders retained EQY revision `v0.68-2-g4a72eb9`. It matches all eight EQY tool-identity occurrences in `live_results_followup_20261013.json` (seven run records and the repair record). This checks version reporting, without re-executing proofs. |
| M2, author-supplied closure label | **Verified as continuity, with its stated limits.** The new JSON binds the unchanged current main hash. All 13 bibliography bodies, bibliography line locators, and all 15 citation occurrences/paragraph contexts match current `main.tex`. Each entry retains prior source/access information and a bounded continuity statement. The original audit bytes still hash to its recorded `d7654fed28b5d0989a3cf0476303ad407756c65ac1996680adb0bda0cf6ba3e0`; only that prior file's digest was checked, without reading its report contents. This is not a fresh external source-resolution or full-body semantic audit. |
| Separate-execution wording | **Verified.** Supplement §1 and the Table 7 caption now say “separate” executions. Unchanged main §3's “independently from RTL” describes executing reconstructed states separately; its following paragraph still identifies collection under native feedback and limits the inference. No statistical independence or independent external peer-review claim is introduced. |
| Stale-table prevention | **Verified for the identified defect.** Collector lines 24–33 regenerate repeat rows from the frozen record. The current manuscript audit, lines 27–33, asserts seven exact pairs and checks each rendered row against its recorded raw-GDS outcome. Independently checking these seven current rows passes: all DEF/SPEF/date-normalized entries are Same and only register raw GDS is Same. The collector and complete audit were inspected, not executed by this seat. |

### Current PDF and scope checks

Both PDFs were freshly extracted with `pdftotext -layout`; each extraction matches its current supplied evidence text byte for byte. Every page of the current **11-page main and 6-page supplement** was rendered and visually inspected. Tables, wrapped headers, literal switches, locators, and EQY revision are readable. Current main and supplement logs contain no Overfull, Undefined, LaTeX Warning, or LaTeX Error markers. Every figure/table label retains a matching callout.

The bibliography remains continuous on main pp.10–11, without an intervening float. Supplement p.6 contains the continuation of artifact verification; its sparse final page is a layout observation, not a newly inferred venue-limit failure. The running title and normal Ghose [11] citation remain intact. The unchanged main source retains the abstract's qualifications and the original thirteen-reference sequence.

Supplement p.4 still retains all four accumulator cases and all 23 responses: two controller stops, two incomplete outcomes, zero certifications. The text and caption preserve unknown eventual repair outcomes for incomplete cases. Page inspection and targeted text scans find no rendered provider account/billing detail; no such narrative is required for closure.

Under the same generic criteria, Writing Quality changes from `PARTLY_MEETS` to **MEETS for this closure scope**, because its three decision-bearing caption/header defects are resolved. Originality remains `NOT_ASSESSED`; the other original criterion judgements and their reporting/evidence limits remain in force. Earlier optional heading/corresponding-author suggestions remain optional and are not closure conditions.

**No unresolved P1–P3 presentation finding remains.** No new experiment, external message, manuscript/generated-file edit, packaging operation, or publication action was performed. Only this report was appended; the prior review was preserved. This scoped acceptance does not establish external independent peer review, scholarly venue acceptance, or comprehensive methodological/citation certification.
