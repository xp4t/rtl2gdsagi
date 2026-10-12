# Final internal review 1 — numerical evidence and native contracts

criteria_binding_unavailable
calibration_status: NOT_CALIBRATED
Execution: inline, shared-context ARS-guided review, not independent external peer review.
Manuscript SHA-256: 6c144a237a968a8fcdfcc94ccbe050dc2abe11665219f799c7c7473f2a9ed5f3

## Evidence examined

Read the complete manuscript, generated tables and final audit. Revalidated candidate hashes, every gate contract/lineage and certification IDs through the extractor for seven selected designs and their seven repeats. Checked the archived final and repair-cohort source fingerprints, final regression XML, all nine repair rows, native attack rows and isolated EQY controls.

## Claim dispositions

- Abstract/Section 4: 7 designs, 16–1024 mapped cells, all 21 stages. The large completed design is shift1024, not the failed accumulator or ALU bank. Each selected and repeated candidate passes native DRC/LVS/antenna, extracted timing and both equivalence boundaries.
- Native adversarial result: six classes × three replicates, 18 comparator passes and 18 blocks. Actual DRC outputs are zero for stale same-top input, missing FEOL and missing layer map. The fake LVS fixture has zero cross-references. PDN removal leaves zero vias. Post-repair foreign-GDS substitution violates consumed-content identity.
- Repair result: 9 episodes, 7 verified, 2 escalated, 20 real provider calls; 174306 input/50164 output tokens. The proposal comparator has 20 promotions, 11 measured failed rechecks, 2 unavailable target checks. Counts are kept separate and are not pooled with historical API cases.
- Timing: all three ALU injections start at −0.32619152746597474 ns at 3 ns. The successful final native check is +0.0015860646578364705 ns. Native 1.5 ns counter check is −0.7156888617649061 ns and fails. Protected SDC and RTL identity are retained.
- Repeats: six route bundles and six timestamp-neutral GDS pairs match. All seven raw GDS hashes differ. The shift1024 DEF differs only in selecting L1M1_PR_MR versus L1M1_PR at 3651 references; this diagnostic substitution is not added to the reported normalization. Geometry equivalence and a causal threading explanation are not claimed. Netlists/SPEF match for that pair.
- Regression: 954 passes, 15 skips, zero failures/errors. Failed scale and historical transport cases are separately retained.

## Previous blocking findings

The seven-design/large-design requirement is resolved by the fully completed 1024-cell shift register. The 1995-cell accumulator and 2156-cell ALU bank remain failed cases, rather than being silently relabeled as clean. Fresh paired selected flows use source af31b39f6782; the prospective repair cohort uses archived source 18d948815ac6. All tables and full paired hashes are regenerated.

| Criterion | Judgment | Anchor and remaining uncertainty |
|---|---|---|
| Originality | MEETS | Tested, bounded candidate/gate contract contribution; no unsupported priority claim. |
| Methodological rigor | MEETS | Native checks, source identities, comparators and full denominators are declared. |
| Evidence sufficiency | MEETS | Every registered high-impact numerical claim has retained native/audit support. |
| Argument coherence | MEETS | Each research question maps to a measured result and explicit limits. |
| Writing quality | MEETS | Quantities distinguish mapped/die area, episodes/proposals and raw/normalized hashes. |

Disposition: no unresolved numerical or native-contract correction. Public availability is a separate final publication action; its receipt must be verified before delivery. This judgment does not establish manufacturing qualification or venue acceptance.

Final wording check: the no-recheck comparator is explicitly retrospective replay of the same authorized proposals. Model proposals can vary; native tools determine recheck outcomes. Setup/hold table columns explicitly denote slack. These changes preserve all measured quantities and narrow the comparator claim.
