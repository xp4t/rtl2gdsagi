# Frozen revision review — EVIDENCE seat

Date: 13 October 2026. Guidance: ARS 3.23.0, `ars/academic-paper/agents/peer_reviewer_agent.md`.

`criteria_binding_unavailable`

`calibration_status: NOT_CALIBRATED`

**Final scoped verdict: Accept for the audited evidence claims, after the editorial closure below.** The initial audit supported the substantive results but found a stale reproducibility table requiring a limited correction. That correction is verified in the current generated input. No unresolved decision-bearing evidence finding remains within this seat's scope.

This is a separate review context sharing the author's workspace within the same writing workflow. It is an internal evidence assessment, not independent external peer review, venue acceptance, or publication approval. No exact venue criteria were supplied. The verdict applies to the bounded frozen-source evaluation, not industrial qualification, population repair performance, comparative agent superiority, or comprehensive foundry-rule coverage.

## 1. Artifact binding and initial observations

The supplied initial hashes identify TeX sources, not PDFs. Both matched the files inspected at intake. Git HEAD was `aec0fda7ee09bd98cc7c8d6965e91120ec4d9062`; this is distinct from the implementation source fingerprint.

| Artifact initially read | Observed SHA-256 |
|---|---|
| `main.tex` | `aa000b982ef658964a94c850c53415b0bbcc8c1db263457b9ff91cb43c546b48` |
| `supplement.tex` | `7ddc69165b429c21c3655e1db7c65f5fc6849db5c948c1273ef469d3a7357ed4` |
| `main.pdf` | `fd7d5a6c39cc0be2556a712399a7e845fbacf7b503a65eeb7d185e5e054c3c30` |
| `supplement.pdf` | `a711bdf17f4ec6b851f6fb568f033be38b2020283e0d4b3039911a71feee511c` |
| `evidence/manuscript.txt` | `c348c2470ec43921d498b1155154991682e4d1b3cff9fcfc8cc5744384a0e644` |
| `evidence/supplement.txt` | `8caa6a1e32bdcedb5984fc4c1371dc31ff61855cba07ad6821d2386f228555cb` |

Both initial saved text files matched fresh `pdftotext -layout` extraction byte for byte. I read the full main and supplement sources and their full initial extracted text, including the references. I read every directly included generated TeX input: `live_results`, `frozen_macros`, `qor_table`, `signoff_table`, `reproducibility_table`, `frozen_fault_table`, `checker_obligations_table`, `class_replay_table`, `padding_thread_table`, `extended_results`, `episode_table`, `configured_drc_controls_table`, `supplement_large_cases`, and `supplement_history_table`. The archived macros in `extended_results.tex` retain earlier counts; the main frozen result claims use the frozen macros and current cohorts.

The initial reading found a coherent, appropriately bounded argument: native evidence is accepted only for its selected candidate; repeated constructed faults test declared obligations; fixed proposal states test native-check outcomes. The principal uncertainty was whether summaries and generated tables actually represented the named source and raw cohorts. The checks below resolve that uncertainty for the core claims.

## 2. Evidence checks actually performed

These were read-only inspections, hashing, reconstruction, and validation of retained records. I did not launch EDA experiments, model/API experiments, or a new regression run.

### Source phases and primary implementation

I recomputed the sorted Python-path-and-byte fingerprint for the current `src/`, the primary frozen snapshot, and the archived proposal-generation snapshot. Current and frozen source both equal:

`af31b39f67827a3375c52bf41f52a727130947f8b5716d80b2680c7de88ca06c`.

The archived proposal source equals:

`18d948815ac6d0af630a5440578304dc9270e1be659c602b5aa7149f40aab22b`.

Reading the frozen source tar archive without extraction confirmed the same af31 fingerprint across its 48 Python files; it also contains two non-Python files. The Python fingerprint does not claim to hash the entire installed PDK.

Using `experiment_manifest.json`, `frozen_results.json`, the primary run states, JSONLs, signoff bundles, and gate evidence, I applied the retained extractor's candidate rehash, lineage, gate consistency, and certification-ID checks to **all fourteen primary runs**. Every run completed 21 stages and full certification. Both equivalence boundaries, authoritative simulation, complete SPEF coverage, positive LVS, and zero routing/DRC/antenna violations were present. The mapped-cell range is 16–1,024; the recorded first-pair QoR values agree with the claimed scale and slack values. No new model calls occur in this cohort.

I separately rehashed mapped and routed netlists, routed DEF, SPEF, and raw GDS for every primary pair. I parsed the GDS record structure and normalized only the 24-byte BGNLIB/BGNSTR date payloads using the retained comparison function. Results: **7/7 exact route bundles, 7/7 date-normalized GDS pairs, 1/7 raw GDS pairs**. The supplemental implementation identities also match in all seven pairs. The sole raw-GDS match is register.

For the current shift1024 pair, both routed DEF files hash to `1d84f82313000b2d6f6c58889984b7cbc93b72407ecf476a7477c1b9a2779df8`; both normalized GDS files hash to `b0ff7f92b1948cba53346c1f74e1fb6d22af94532813b659f31ad73bcf69e62c` with 19 date records each. This supports the current one-worker result.

### Complete-state replay and denominators

I reconstructed archived effective IRs from the archived defaults, logged characterization/override deltas, curated numerical changes, and cumulative accepted model deltas. All **twenty** reconstructions match the saved complete replay configurations, with the declared explicit one-worker setting. All **seven archived successful final IRs** match their retained signoff IRs before fresh execution.

The three excluded PDN pilot configurations retain offset 50 µm and default utilization 0.35. The corrected configurations contain the logged curated offset 21.42 µm and utilization 0.29. The old pilot and corrected twenty-state manifests both remain present; the audited final cohort is `runs/frozen_proposal_replay_complete_ir_20261013/`. These exclusions address incomplete reconstruction and are disclosed in supplement §3.

I checked all twenty final configuration hashes, matched trial statuses and failed-check lists to raw run states/JSONLs, and verified that the final replay logs contain no model `api_call` or model `config_generated` events. The six successful runs passed retained signoff validation.

| Originating class | States | Archived confirmed failures | Archived unavailable targets | Fresh native failures | Fresh certifications |
|---|---:|---:|---:|---:|---:|
| Spacing | 3 | 0 | 0 | 0 | 3 |
| PDN | 3 | 0 | 0 | 0 | 3 |
| Timing | 14 | 11 | 2 | 14 | 0 |

Archived failure/target records were checked against their original raw event streams. The remaining archived timing state has a completed passing target. Thus archived timing is **11 failed + 2 unavailable + 1 target pass**, not thirteen confirmed failures. Fresh timing is **13 routed-STA failures + 1 placement failure**, not fourteen completed STA checks. The original nine live episodes retain seven certifications and two escalations, twenty model responses, 174,306 input tokens and 50,164 output tokens, confirmed from their raw API-event records. Episodes and proposal states have different denominators.

Native setup/hold values were matched against retained native STA logs for all 33 primary/final-replay runs that reached routed STA. For failed replay runs, these logs reside in retained `superseded/000/` directories. The placement-failed state has no routed-STA outcome. This inspection does not establish an independently executed no-recheck trajectory; the manuscript correctly treats that comparator as hypothetical acceptance of already recorded states.

### Padding intervention

I checked all eight factorial records, their source fingerprints, configurations, raw routed-STA values and terminal statuses. Overlay differences are confined to deleting the stated CTS and/or routing padding statements in `render.py`; the other Python files match the frozen base. Configurations match apart from worker count, retaining 3 ns, 0.25 ns uncertainty, 0.05 pF load, and one-site placement padding.

Both worker counts give the same slack in each padding cell: off/off +1.586 ps; off/on +9.868 ps; on/off and on/on −0.654 ps. Four runs certify and four fail. Across the CTS intervention with routing padding held on, rehashed mapped netlist and placed DEF agree; CTS DEF, routed netlist, routed DEF and SPEF differ. This supports the stated causal attribution **in these executions**. It does not establish worker insensitivity across other designs or configurations, nor a general guarantee about timing repairs.

### Native faults and configured controls

The frozen fault JSON contains six classes with three blocked executions each. I inspected the launcher, native commands, relevant native logs/reports, and production parser/structural evidence. Degraded DRC reports have zero markers but 152 normalized categories (154 raw), and the copied decks fail approval. Native no-compare LVS prints a match but has zero circuit cross-references and fails the production parser. All three PDN fixtures have zero remaining vias and fail the structural check. Stale-input command paths rehash to the recorded foreign GDS rather than the selected candidate. Missing-map summaries retain geometry on invalid low layer numbers despite zero DRC markers.

The current recorded spacing-repair run passes candidate/gate validation, records one initial DRC marker, zero final markers, one repair verification and zero new model calls. Its GDS hash is `376a7fee1f5844108e11d71a71c36099914269395d15e924573079b906cc27ba`. I recomputed the three post-repair foreign-artifact gate mismatches using its retained candidate and DRC gate. All three block. This supports **18/18 constructed consistency checks**, with six coverage units, not eighteen independent random fault samples.

For the OpenLane invocation audit I rehashed 183 referenced records across the executed controls and five retained/public-source pairs. I parsed all 24 control reports. The inactive prior modern-wrapper pairing remains 0 categories/0 markers and is excluded from the active comparison. Active legacy controls report 166 categories, positive metal/poly/grid counts 3/0/4, and clean counts 0/0/0. Both configured modern paths report 220 categories, positives 3/1/4, and clean counts 0/0/0. Their recorded exits are zero even when markers exist. The manuscript therefore correctly separates marker reporting, release rejection, and candidate/inventory provenance. I did not independently re-execute the retained supply-connectivity/XOR interfaces or assess default Magic/full OpenLane flow coverage.

### Retained incomplete cases and regression record

All four accumulator JSONLs retain 1,995 synthesis cells and no signoff file. Valid response counts are 3, 3, 10 and 7, totaling **23**. Two terminate on the controller's failed-fingerprint policy and two are interrupted/incomplete. The policy records retain budgets 3/24 and 7/24 and the final layer-five/padding-six deltas. The manuscript does not count incomplete outcomes as certifications or eventual algorithmic failures; that is appropriate. No account or billing narrative is required.

The retained pytest XML reports 970 tests, 15 skipped, zero errors/failures, hence 955 passes. Fresh grouped counter/shift PASS markers and the counter-mutant FAIL marker exist. I did not rerun these tests or independently inspect every formal partition proof.

## 3. Generic ARS criterion judgements

Criterion source for each row: the five-dimension field-general rubric in the named ARS peer-reviewer guidance. No numerical score or venue-fit judgement is used.

| Dimension | Judgement | Manuscript anchors and rationale | Uncertainty / decision impact |
|---|---|---|---|
| Originality | NOT_ASSESSED | Main §§1,5 state an executable evidence contract and measured integration; comparable contracts are explicitly not excluded. | This seat did not conduct a fresh literature comparison or read all cited work. No external novelty/venue conclusion follows. |
| Methodological Rigor | MEETS | Main §§3.1–3.2,4.3–4.4; supplement §§1–3. Source phases, complete IR reconstruction, fixed-state comparator and controlled CTS intervention support the bounded inferences. | Repeated constructed cases and shared trajectories do not establish population rates; those limits are stated. No unresolved methodological blocker. |
| Evidence Sufficiency | MEETS | Main §§4.1–4.4; supplement §§3–5. Primary gates, hashes, twenty replay outcomes, eight intervention runs and retained incomplete cases agree with the core claims. | Retained evidence was validated; no new native execution or comprehensive industrial/foundry validation occurred. |
| Argument Coherence | MEETS | Main §§1,3.2,6 connect the three questions to coverage, proposal-state outcomes and repeat artifacts. | The initial Table 4 inconsistency was real and repairable; current closure resolves it. |
| Writing Quality | MEETS after closure | Main Tables 4,7,8 and supplement §§2–4 now identify the correct cohorts, source phases, denominators and native invocation details. | Layout was checked through extracted PDF text and generated source, not a full graphical page inspection or venue-length assessment. |

Specific strengths are the candidate-versus-comparison-identity distinction in main §4.1, explicit source separation in §3.1, the unavailable-target denominator in §4.3, the bounded CTS attribution in §4.4, and the preservation of unknown outcomes in supplement §5.

## 4. Initial finding and actionable resolution

**Initial finding E1 — Minor, main §4.1/Table 4, `generated/reproducibility_table.tex`:** the table showed shift1024 routed DEF/date-normalized GDS as different and register raw GDS as different, while current raw pairs and surrounding text establish seven exact route/date-normalized pairs and one raw match. This was a reporting inconsistency affecting verification of a central result, with a limited remedy: regenerate the table from the current selected cohort and rebuild the PDF/text. It did not require changing data, conclusions, or repeating native runs. **Resolved below.**

No Critical or Major evidence finding was established. No unresolved Minor finding remains after scoped closure. The initial disposition was limited correction of the presentation, with the substantive evidence conclusions supported.

Cross-section checks: title and abstract fit the bounded evaluation; introduction questions are answered in results/conclusion; current table cohorts agree with the reported denominators; the initial stale row is closed. All thirteen bibliography keys appear in citation contexts. Fresh literature/source-content correctness and exact venue length requirements remain outside this evidence assessment.

## 5. Scoped final closure and delivered-byte binding

This closure preserves the audit above. It checks editorial changes against the current delivered artifacts; it does not repeat or expand the native audit.

| Current artifact | Observed SHA-256 |
|---|---|
| `main.tex` — unchanged | `aa000b982ef658964a94c850c53415b0bbcc8c1db263457b9ff91cb43c546b48` |
| `supplement.tex` | `2e2eb273acffbc28b1be077eec5a533e6fba756a622b0461cf35b59b066327ae` |
| `main.pdf` | `df067d1b98dba094e5288123e94f22e27509c1d78e31f9b944e4065e54b09e44` |
| `supplement.pdf` | `daac9afab3e1b879a0bf58adddaeade7e0a2daa2c3b5aefdfe38e8a55a352b01` |
| `evidence/manuscript.txt` | `3a9899807f0b3ddeec125736d0beb352117464836ae8f14397af8106163b4f43` |
| `evidence/supplement.txt` | `4b6c4dcb5f14a1258a5545bd7dffafcdf0fc0d6f13109445bf7fc36ffb9b0370` |
| `evidence/citation_continuity_frozen.json` | `217a7897a655f25536b3f47d283596600768d63ec8fe3bab25c8d3b23b577a3c` |

Fresh layout-text extraction matched both current saved text files exactly, with **11 main pages and 6 supplement pages**. Current source/input inspection confirms:

- **E1:** the repeat table now shows all seven routed DEF/SPEF/date-normalized pairs as Same and only register raw GDS as Same. This agrees with the audited raw files. Collector inspection originally explained the stale-generation gap; the user reports a prevention check was added. I have verified the current rows, not rerun that newly added guard.
- **P1:** the episode caption explicitly names all nine original live episodes on `18d948815ac6` and separates them from frozen replay/larger cases.
- **P2:** wrapped headers distinguish archived failed/missing from frozen failed/certified; the audited counts are unchanged.
- **P3:** factorial certification cells explicitly use 2/2 or 0/2.
- **M1/S1:** supplement §4 includes literal `feol=1`, `beol=1`, `offgrid=1`, `seal=1`, `floating_met=0`, exact `executions/*/command.json` and audit-JSON locators, and retained EQY revision `v0.68-2-g4a72eb9`.
- **M2:** the continuity JSON declares the current main-source hash, thirteen reference mappings/current contexts, the preserved original audit hash, and limited inherited source-reading scopes. I inspected its metadata, row count, first mapping, and the current bibliography/citation keys. I did not read another seat's report, independently verify every inherited mapping conclusion, fetch sources, or perform a new full-body citation audit. This artifact documents continuity, not a fresh external review.
- The supplement and replay table now use “separate” executions. Main source remains the initially bound source; no statistical independence is inferred from separate launches.

**Final decision:** Accept within the EVIDENCE seat's scope. The previously observed table error is closed; no new native work is needed for that correction. Reviewer confidence is high for the audited cohort counts, source reconstruction and artifact identities, and limited for unaudited external novelty, exhaustive citation support, full-flow comparator behavior and industrial generalization.

Public packaging/publication and the release availability receipt remain a separate authorized final gate. This report neither certifies public availability nor introduces another approval requirement. Only this designated report was written for this deliverable; no other review reports were read.
