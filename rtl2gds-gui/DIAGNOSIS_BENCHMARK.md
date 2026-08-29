# Phase 4 injected-failure benchmark

Date: 2026-08-28

The fixed benchmark manifest is `tests/fixtures/gui_failures/benchmark.json`.
It contains 25 synthetic failure scenarios with explicit expected failure
categories and earliest/root-cause stages. The suite covers frontend,
elaboration, synthesis, placement, timing, routing, physical verification,
power/area, missing evidence, crashes, and timeouts.

## Automated expected-label result

- Injected failures: 25
- Correct root-cause stage: 25
- Root-cause-stage accuracy: 100%
- Required threshold: 80% across at least 20 failures
- Cases removed after implementation: 0

The automated test is
`tests/test_gui_diagnosis.py::test_injected_failure_benchmark_meets_root_stage_threshold`.
It reconstructs a structured `DiagnosisContext` for every fixed fixture and
scores the deterministic `FailureClassifier` result against the manifest.

## Human-grading checkpoint

The expected labels and classifier outputs are visible in the fixed manifest
for independent human review. Automated expected-label accuracy exceeds the
acceptance threshold; formal human grading remains an explicit review
checkpoint and is not represented as having occurred automatically.

The reviewer-facing packet is `DIAGNOSIS_HUMAN_REVIEW.md`. It includes all 25
frozen cases, the structured evidence supplied to diagnosis, the current
validated diagnosis output, blank case-level grading fields, and a blank final
acceptance summary. Its recorded fixture SHA-256 allows a reviewer to confirm
that the packet corresponds to the frozen manifest.

No natural-language provider output affects this score. The benchmark measures
only deterministic failure-category and earliest-stage identification.
