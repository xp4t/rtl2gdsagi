# ARS internal review pass: METHODS

Date: 14 October 2026. ARS-Codex 3.23.0, academic-paper Phase 6; peer_reviewer_agent.md field-general criteria.

criteria_binding_unavailable
calibration_status: NOT_CALIBRATED

Execution: one of three sequential internal review passes by the same Codex assistant in this writing session. Three initially requested worker contexts produced no completed reports and are not counted. This is author-side internal review, not independent external peer review, a blinded panel, or venue acceptance. No numerical score or ranking is assigned.

## Final revision identity

- `main.tex`: `83cd4ba381f8fbf74aec6ddaacde98c47c5c3357c9cc8021a0432bbe76370436`
- `supplement.tex`: `70973b40eef369a1e42523be13395f1043efb931035aef8594e6d35bb5871242`
- `main.pdf`: `38f73a8425abdc5d0dd7f5b7e3a87a296506ebbc931521a67d9d1e26eb29ec64`
- `supplement.pdf`: `f6445a6dfc48ce4b1fc39f5c0c9694bb18d844470ff0bc5eadeb3bdaf3a64e6a`

Scope: this clarification revision and its retained evidence. Earlier full evaluations and citation audits keep their prior limitations. No new paid model calls, full RTL-to-GDS runs, or signoff certificates are attributed to this review. Public availability is a separate delivery gate.

## Pass 2: execution and inference

The current complete manuscript sources and both new scripts were inspected against frozen render_cts and native check_sta code. The diagnostic executes the eight retained setup-on CTS scripts from their retained placed DEF/SDC, retaining command order and the pinned container. It adds timing markers and snapshots and redirects writers into a new directory. It does not change repair targets, initialize a new live model trajectory, alter production source or overwrite original CTS evidence. All final diagnostic CTS DEF hashes match the originals, strengthening the claim that observation did not change these outcomes.

All eight repair_timing -setup -setup_margin 0.0500 calls are entered and return. Immediate setup WNS is 0.19435609227685544 to 0.27452729755387884 ns, above the target; before/after DEF and netlists match. Frozen scripts set clock RC but not signal RC. RSZ-0014/RSZ-0021 warn of zero capacitance and wire-load fallback. The warranted interpretation is no setup violation under that estimator at the repair point; later extracted routed setup violations do not establish that repair was skipped. This limits the grid's evidence for setup-repair effectiveness; it does not establish a general native repair bug or that a corrected estimator would repair the cases.

Guardband g is a required positive margin, distinct from CTS optimizer margin and 0.25 ns uncertainty. check_sta uses finite slack >=abs(g); post-CTS gates hold and routed STA gates setup and hold. The collector applies all three recorded obligations at 0.05 ns and keeps all other gate outcomes fixed. Historical certificates stay at g=0. It computes threshold eligibility, not native repair success, corner robustness, new model effectiveness or a new certification cohort. Cohorts are not pooled and unavailable timing is not fabricated.

Archived and frozen proposal execution differ in source. The known CTS-padding change reverses one archived narrow pass; the manuscript calls frozen 14/14 source-confounded and does not infer agent superiority from that increase. Intermediate failures remain conditioned on native feedback. The reviewed current-source content fingerprint is unchanged af31b39f6782; archived live generation remains 18d948815ac6.

The recent related-work edit was matched to retained citation_baseline_audit.json's audopeda identity and author-manuscript record. It names Ghose et al.'s ICCAD author manuscript, identifies their manifest/rechecking mechanisms as the subject, and retains the to-appear author PDF rather than claiming its unresolved proceedings DOI is verified. No new full-paper replication or fresh web access is claimed by this pass.

## Criterion-local assessment

| Criterion (ARS field-general rubric) | Assessment | Anchor and limit |
|---|---|---|
| Originality | NOT_ASSESSED | Related-work naming/overlap checked; no priority assessment performed. |
| Methodological rigor | MEETS | Diagnostic scripts, inclusive margin semantics, source-confounded replay and cohort eligibility have bounded interpretations. |
| Evidence sufficiency | MEETS | Native markers and unchanged snapshots support the specific no-op explanation; no corrected-RC experiment is invented. |
| Argument coherence | MEETS | Native routed checks remain acceptance gates despite the earlier estimator limitation. |
| Writing quality | MEETS | Main one-sentence explanation and supplementary warnings make the scope clear. |

Verdict: **Accept within the requested clarification scope**. The signal-RC omission remains a documented limitation of the frozen estimator. Correcting it would create a new implementation/experiment and is outside this revision's existing-results claim.
