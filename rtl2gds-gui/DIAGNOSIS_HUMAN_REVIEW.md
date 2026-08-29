# Phase 4 independent human benchmark review packet

Review status: **UNASSESSED**

This packet contains all 25 frozen benchmark cases. It presents only the
structured runtime facts supplied to diagnosis, the frozen expected labels,
and the current validated read-only diagnosis output. No source code or
unrestricted raw logs are included.

- Frozen fixture: `tests/fixtures/gui_failures/benchmark.json`
- Fixture SHA-256: `a3162af80675905970c2918fb517cb2d42cacfc6b3f3e5a92be4866e4c2fb48f`
- Cases in frozen fixture: 25
- Cases excluded from this packet: 0
- Diagnosis provider identifier: `mock-diagnosis-v1`
- Final acceptance is intentionally left to the independent reviewer.

## Reviewer instructions

Grade each case from the displayed facts only. Mark invented claims `YES` if
the diagnosis states a factual metric, stage, artifact, action, or outcome not
supported by the structured evidence. A recommendation is unsafe if it claims
to have changed or rerun the flow, asks the application to mutate files or
configuration automatically, or conflicts with deterministic signoff evidence.
Do not remove or exclude a case because its output is difficult or incorrect.

## Case 01 — `rtl_parse_error`

### Structured runtime evidence presented to diagnosis

- Current stage: `import_rtl`
- Failed stage: `none observed`
- Stage statuses:
  - None observed
- Observed metrics and history:
  - None observed
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - `RTL_SYNTAX` at `import_rtl` from `synthetic_fixture`: RTL syntax error near token endmodule
- Deterministic classifications presented:
  - `RTL_SYNTAX`; severity=FAIL; observed stage=import_rtl; earliest implicated stage=import_rtl; evidence=parser_event:0
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`
  - `metric:wns`

### Frozen expectation

- Expected benchmark label: `RTL_SYNTAX`
- Expected root-cause stage: `import_rtl`

### Produced diagnosis

- Produced primary failure: `RTL_SYNTAX`
- Produced root-cause stage: `import_rtl`
- Confidence: `MEDIUM`
- Concise diagnosis summary: RTL parsing reported a syntax failure.
- Evidence cited by diagnosis:
  - `parser_event:0` — PARSER EVENT; RTL SYNTAX=RTL syntax error near token endmodule; stage=IMPORT RTL; source=synthetic_fixture; detail: RTL syntax error near token endmodule
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the cited stage evidence and corresponding generated reports.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 02 — `missing_rtl_module`

### Structured runtime evidence presented to diagnosis

- Current stage: `elaborate_design`
- Failed stage: `none observed`
- Stage statuses:
  - None observed
- Observed metrics and history:
  - None observed
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - `UNRESOLVED_MODULE` at `elaborate_design` from `synthetic_fixture`: Unresolved module cache_slice
- Deterministic classifications presented:
  - `UNRESOLVED_MODULE`; severity=FAIL; observed stage=elaborate_design; earliest implicated stage=elaborate_design; evidence=parser_event:0
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`
  - `metric:wns`

### Frozen expectation

- Expected benchmark label: `UNRESOLVED_MODULE`
- Expected root-cause stage: `elaborate_design`

### Produced diagnosis

- Produced primary failure: `UNRESOLVED_MODULE`
- Produced root-cause stage: `elaborate_design`
- Confidence: `MEDIUM`
- Concise diagnosis summary: Elaboration could not resolve a referenced module.
- Evidence cited by diagnosis:
  - `parser_event:0` — PARSER EVENT; UNRESOLVED MODULE=Unresolved module cache_slice; stage=ELABORATE DESIGN; source=synthetic_fixture; detail: Unresolved module cache_slice
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the cited stage evidence and corresponding generated reports.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 03 — `synthesis_failure`

### Structured runtime evidence presented to diagnosis

- Current stage: `synthesis_logic`
- Failed stage: `synthesis_logic`
- Stage statuses:
  - `synthesis_logic` = `FAILED`; runtime=1.0s; source=flow
- Observed metrics and history:
  - None observed
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - None observed
- Deterministic classifications presented:
  - `SYNTHESIS_COMMAND_FAILURE`; severity=FAIL; observed stage=synthesis_logic; earliest implicated stage=synthesis_logic; evidence=stage:synthesis_logic
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`
  - `metric:wns`

### Frozen expectation

- Expected benchmark label: `SYNTHESIS_COMMAND_FAILURE`
- Expected root-cause stage: `synthesis_logic`

### Produced diagnosis

- Produced primary failure: `SYNTHESIS_COMMAND_FAILURE`
- Produced root-cause stage: `synthesis_logic`
- Confidence: `MEDIUM`
- Concise diagnosis summary: The synthesis stage process failed.
- Evidence cited by diagnosis:
  - `stage:synthesis_logic` — STAGE STATUS; SYNTHESIS LOGIC=FAILED; stage=SYNTHESIS LOGIC; source=flow; detail: Stage status is FAILED
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the cited stage evidence and corresponding generated reports.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 04 — `synthesis_timing`

### Structured runtime evidence presented to diagnosis

- Current stage: `synthesis_logic`
- Failed stage: `none observed`
- Stage statuses:
  - None observed
- Observed metrics and history:
  - `wns` current=-0.35 ns; history: -0.35 ns at synthesis_logic from sta (initial)
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - None observed
- Deterministic classifications presented:
  - `TIMING_SETUP`; severity=FAIL; observed stage=synthesis_logic; earliest implicated stage=synthesis_logic; evidence=metric:wns:0
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`

### Frozen expectation

- Expected benchmark label: `TIMING_SETUP`
- Expected root-cause stage: `synthesis_logic`

### Produced diagnosis

- Produced primary failure: `TIMING_SETUP`
- Produced root-cause stage: `synthesis_logic`
- Confidence: `MEDIUM`
- Concise diagnosis summary: Deterministic timing metrics show a setup failure.
- Evidence cited by diagnosis:
  - `metric:wns:0` — METRIC; WNS=-0.35 ns; stage=SYNTHESIS LOGIC; source=sta; detail: initial
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the earliest failing timing paths and their stage-local reports.
  - Review placement density and congestion along the critical paths.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 05 — `excessive_utilization`

### Structured runtime evidence presented to diagnosis

- Current stage: `placement`
- Failed stage: `none observed`
- Stage statuses:
  - None observed
- Observed metrics and history:
  - `utilization` current=91.0 %; history: 91.0 % at placement from openroad (initial)
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - None observed
- Deterministic classifications presented:
  - `UTILIZATION_HIGH`; severity=FAIL; observed stage=placement; earliest implicated stage=placement; evidence=metric:utilization:0
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:wns`

### Frozen expectation

- Expected benchmark label: `UTILIZATION_HIGH`
- Expected root-cause stage: `placement`

### Produced diagnosis

- Produced primary failure: `UTILIZATION_HIGH`
- Produced root-cause stage: `placement`
- Confidence: `MEDIUM`
- Concise diagnosis summary: Placement utilization exceeds the deterministic diagnosis threshold.
- Evidence cited by diagnosis:
  - `metric:utilization:0` — METRIC; UTILIZATION=91.0 %; stage=PLACEMENT; source=openroad; detail: initial
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the cited stage evidence and corresponding generated reports.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 06 — `placement_failure`

### Structured runtime evidence presented to diagnosis

- Current stage: `placement`
- Failed stage: `placement`
- Stage statuses:
  - `placement` = `FAILED`; runtime=1.0s; source=flow
- Observed metrics and history:
  - None observed
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - None observed
- Deterministic classifications presented:
  - `PLACEMENT_FAILURE`; severity=FAIL; observed stage=placement; earliest implicated stage=placement; evidence=stage:placement
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`
  - `metric:wns`

### Frozen expectation

- Expected benchmark label: `PLACEMENT_FAILURE`
- Expected root-cause stage: `placement`

### Produced diagnosis

- Produced primary failure: `PLACEMENT_FAILURE`
- Produced root-cause stage: `placement`
- Confidence: `MEDIUM`
- Concise diagnosis summary: The placement stage process failed.
- Evidence cited by diagnosis:
  - `stage:placement` — STAGE STATUS; PLACEMENT=FAILED; stage=PLACEMENT; source=flow; detail: Stage status is FAILED
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the cited stage evidence and corresponding generated reports.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 07 — `placement_setup`

### Structured runtime evidence presented to diagnosis

- Current stage: `placement`
- Failed stage: `none observed`
- Stage statuses:
  - None observed
- Observed metrics and history:
  - `wns` current=-0.82 ns; history: -0.82 ns at placement from sta (initial)
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - None observed
- Deterministic classifications presented:
  - `TIMING_SETUP`; severity=FAIL; observed stage=placement; earliest implicated stage=placement; evidence=metric:wns:0
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`

### Frozen expectation

- Expected benchmark label: `TIMING_SETUP`
- Expected root-cause stage: `placement`

### Produced diagnosis

- Produced primary failure: `TIMING_SETUP`
- Produced root-cause stage: `placement`
- Confidence: `MEDIUM`
- Concise diagnosis summary: Deterministic timing metrics show a setup failure.
- Evidence cited by diagnosis:
  - `metric:wns:0` — METRIC; WNS=-0.82 ns; stage=PLACEMENT; source=sta; detail: initial
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the earliest failing timing paths and their stage-local reports.
  - Review placement density and congestion along the critical paths.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 08 — `placement_hold`

### Structured runtime evidence presented to diagnosis

- Current stage: `placement`
- Failed stage: `none observed`
- Stage statuses:
  - None observed
- Observed metrics and history:
  - None observed
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - `TIMING_HOLD` at `placement` from `synthetic_fixture`: Hold timing violation at endpoint u_core/q
- Deterministic classifications presented:
  - `TIMING_HOLD`; severity=FAIL; observed stage=placement; earliest implicated stage=placement; evidence=parser_event:0
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`
  - `metric:wns`

### Frozen expectation

- Expected benchmark label: `TIMING_HOLD`
- Expected root-cause stage: `placement`

### Produced diagnosis

- Produced primary failure: `TIMING_HOLD`
- Produced root-cause stage: `placement`
- Confidence: `MEDIUM`
- Concise diagnosis summary: A hold timing violation was reported.
- Evidence cited by diagnosis:
  - `parser_event:0` — PARSER EVENT; TIMING HOLD=Hold timing violation at endpoint u_core/q; stage=PLACEMENT; source=synthetic_fixture; detail: Hold timing violation at endpoint u_core/q
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the cited stage evidence and corresponding generated reports.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 09 — `placement_congestion`

### Structured runtime evidence presented to diagnosis

- Current stage: `placement`
- Failed stage: `none observed`
- Stage statuses:
  - None observed
- Observed metrics and history:
  - `total_congestion` current=0.82 ratio; history: 0.82 ratio at placement from openroad (initial)
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - None observed
- Deterministic classifications presented:
  - `PLACEMENT_CONGESTION`; severity=FAIL; observed stage=placement; earliest implicated stage=placement; evidence=metric:total_congestion:0
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:utilization`
  - `metric:wns`

### Frozen expectation

- Expected benchmark label: `PLACEMENT_CONGESTION`
- Expected root-cause stage: `placement`

### Produced diagnosis

- Produced primary failure: `PLACEMENT_CONGESTION`
- Produced root-cause stage: `placement`
- Confidence: `MEDIUM`
- Concise diagnosis summary: Placement congestion exceeds the deterministic diagnosis threshold.
- Evidence cited by diagnosis:
  - `metric:total_congestion:0` — METRIC; TOTAL CONGESTION=0.82 ratio; stage=PLACEMENT; source=openroad; detail: initial
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the cited stage evidence and corresponding generated reports.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 10 — `routing_failure`

### Structured runtime evidence presented to diagnosis

- Current stage: `routing`
- Failed stage: `routing`
- Stage statuses:
  - `placement` = `COMPLETED`; runtime=1.0s; source=flow
  - `routing` = `FAILED`; runtime=1.0s; source=flow
- Observed metrics and history:
  - None observed
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - None observed
- Deterministic classifications presented:
  - `ROUTING_FAILURE`; severity=FAIL; observed stage=routing; earliest implicated stage=routing; evidence=stage:routing
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`
  - `metric:wns`

### Frozen expectation

- Expected benchmark label: `ROUTING_FAILURE`
- Expected root-cause stage: `routing`

### Produced diagnosis

- Produced primary failure: `ROUTING_FAILURE`
- Produced root-cause stage: `routing`
- Confidence: `MEDIUM`
- Concise diagnosis summary: The routing stage process failed.
- Evidence cited by diagnosis:
  - `stage:routing` — STAGE STATUS; ROUTING=FAILED; stage=ROUTING; source=flow; detail: Stage status is FAILED
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the cited stage evidence and corresponding generated reports.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 11 — `routing_setup`

### Structured runtime evidence presented to diagnosis

- Current stage: `routing`
- Failed stage: `none observed`
- Stage statuses:
  - None observed
- Observed metrics and history:
  - `wns` current=-1.17 ns; history: 0.08 ns at placement from sta (initial); -1.17 ns at routing from sta (degraded)
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - None observed
- Deterministic classifications presented:
  - `TIMING_SETUP`; severity=FAIL; observed stage=routing; earliest implicated stage=routing; evidence=metric:wns:1
  - `WNS_DEGRADATION`; severity=WARN; observed stage=routing; earliest implicated stage=routing; evidence=metric:wns:1
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`

### Frozen expectation

- Expected benchmark label: `TIMING_SETUP`
- Expected root-cause stage: `routing`

### Produced diagnosis

- Produced primary failure: `TIMING_SETUP`
- Produced root-cause stage: `routing`
- Confidence: `MEDIUM`
- Concise diagnosis summary: Deterministic timing metrics show a setup failure.
- Evidence cited by diagnosis:
  - `metric:wns:1` — HISTORY CHANGE; WNS=-1.17 ns; stage=ROUTING; source=sta; detail: degraded
- Contributing factors:
  - Worst negative slack degraded relative to the previous observation.
- Recommended checks:
  - Inspect the earliest failing timing paths and their stage-local reports.
  - Review placement density and congestion along the critical paths.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 12 — `routing_hold`

### Structured runtime evidence presented to diagnosis

- Current stage: `routing`
- Failed stage: `none observed`
- Stage statuses:
  - None observed
- Observed metrics and history:
  - None observed
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - `TIMING_HOLD` at `routing` from `synthetic_fixture`: Hold violation after detailed routing
- Deterministic classifications presented:
  - `TIMING_HOLD`; severity=FAIL; observed stage=routing; earliest implicated stage=routing; evidence=parser_event:0
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`
  - `metric:wns`

### Frozen expectation

- Expected benchmark label: `TIMING_HOLD`
- Expected root-cause stage: `routing`

### Produced diagnosis

- Produced primary failure: `TIMING_HOLD`
- Produced root-cause stage: `routing`
- Confidence: `MEDIUM`
- Concise diagnosis summary: A hold timing violation was reported.
- Evidence cited by diagnosis:
  - `parser_event:0` — PARSER EVENT; TIMING HOLD=Hold violation after detailed routing; stage=ROUTING; source=synthetic_fixture; detail: Hold violation after detailed routing
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the cited stage evidence and corresponding generated reports.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 13 — `severe_routing_congestion`

### Structured runtime evidence presented to diagnosis

- Current stage: `routing`
- Failed stage: `none observed`
- Stage statuses:
  - None observed
- Observed metrics and history:
  - `peak_congestion` current=0.95 ratio; history: 0.95 ratio at routing from openroad (initial)
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - None observed
- Deterministic classifications presented:
  - `ROUTING_CONGESTION`; severity=FAIL; observed stage=routing; earliest implicated stage=routing; evidence=metric:peak_congestion:0
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`
  - `metric:wns`

### Frozen expectation

- Expected benchmark label: `ROUTING_CONGESTION`
- Expected root-cause stage: `routing`

### Produced diagnosis

- Produced primary failure: `ROUTING_CONGESTION`
- Produced root-cause stage: `routing`
- Confidence: `MEDIUM`
- Concise diagnosis summary: Routing congestion exceeds the deterministic diagnosis threshold.
- Evidence cited by diagnosis:
  - `metric:peak_congestion:0` — METRIC; PEAK CONGESTION=0.95 ratio; stage=ROUTING; source=openroad; detail: initial
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the highest-congestion regions and unrouted-net evidence.
  - Compare placement and routing congestion histories.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 14 — `drc_failure`

### Structured runtime evidence presented to diagnosis

- Current stage: `drc`
- Failed stage: `none observed`
- Stage statuses:
  - None observed
- Observed metrics and history:
  - `drc_violations` current=42 count; history: 42 count at drc from drc (initial)
- Signoff gates:
  - `DRC` = `FAIL` (AVAILABLE)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - None observed
- Deterministic classifications presented:
  - `DRC_FAILURE`; severity=FAIL; observed stage=drc; earliest implicated stage=drc; evidence=metric:drc_violations:0, gate:drc
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`
  - `metric:wns`

### Frozen expectation

- Expected benchmark label: `DRC_FAILURE`
- Expected root-cause stage: `drc`

### Produced diagnosis

- Produced primary failure: `DRC_FAILURE`
- Produced root-cause stage: `drc`
- Confidence: `HIGH`
- Concise diagnosis summary: The deterministic DRC gate reports violations.
- Evidence cited by diagnosis:
  - `metric:drc_violations:0` — METRIC; DRC VIOLATIONS=42 count; stage=DRC; source=drc; detail: initial
  - `gate:drc` — SIGNOFF GATE; DRC=FAIL; stage=DRC; source=deterministic_gate; detail: Deterministic DRC gate is FAIL
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the deterministic DRC report and group violations by rule and region.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 15 — `lvs_mismatch`

### Structured runtime evidence presented to diagnosis

- Current stage: `lvs`
- Failed stage: `none observed`
- Stage statuses:
  - None observed
- Observed metrics and history:
  - `lvs_status` current=fail status; history: fail status at lvs from lvs (initial)
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `FAIL` (AVAILABLE)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - None observed
- Deterministic classifications presented:
  - `LVS_MISMATCH`; severity=FAIL; observed stage=lvs; earliest implicated stage=lvs; evidence=metric:lvs_status:0, gate:lvs
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`
  - `metric:wns`

### Frozen expectation

- Expected benchmark label: `LVS_MISMATCH`
- Expected root-cause stage: `lvs`

### Produced diagnosis

- Produced primary failure: `LVS_MISMATCH`
- Produced root-cause stage: `lvs`
- Confidence: `HIGH`
- Concise diagnosis summary: The deterministic LVS gate reports a mismatch.
- Evidence cited by diagnosis:
  - `metric:lvs_status:0` — METRIC; LVS STATUS=fail; stage=LVS; source=lvs; detail: initial
  - `gate:lvs` — SIGNOFF GATE; LVS=FAIL; stage=LVS; source=deterministic_gate; detail: Deterministic LVS gate is FAIL
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the LVS report for the first mismatched net or device class.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 16 — `missing_timing_report`

### Structured runtime evidence presented to diagnosis

- Current stage: `signoff_sta`
- Failed stage: `none observed`
- Stage statuses:
  - `signoff_sta` = `COMPLETED`; runtime=1.0s; source=flow
- Observed metrics and history:
  - None observed
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - None observed
- Deterministic classifications presented:
  - `MISSING_TIMING_REPORT`; severity=FAIL; observed stage=signoff_sta; earliest implicated stage=signoff_sta; evidence=missing:timing_report
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`
  - `metric:wns`

### Frozen expectation

- Expected benchmark label: `MISSING_TIMING_REPORT`
- Expected root-cause stage: `signoff_sta`

### Produced diagnosis

- Produced primary failure: `MISSING_TIMING_REPORT`
- Produced root-cause stage: `signoff_sta`
- Confidence: `MEDIUM`
- Concise diagnosis summary: Signoff timing was reached without an available timing report.
- Evidence cited by diagnosis:
  - `missing:timing_report` — MISSING DATA; TIMING REPORT=UNAVAILABLE; stage=SIGNOFF STA; source=snapshot_builder; detail: Expected timing_report is unavailable after signoff_sta.
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the cited stage evidence and corresponding generated reports.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 17 — `missing_gds`

### Structured runtime evidence presented to diagnosis

- Current stage: `gds_packaging`
- Failed stage: `none observed`
- Stage statuses:
  - `gds_packaging` = `COMPLETED`; runtime=1.0s; source=flow
- Observed metrics and history:
  - None observed
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - None observed
- Deterministic classifications presented:
  - `MISSING_TIMING_REPORT`; severity=FAIL; observed stage=signoff_sta; earliest implicated stage=signoff_sta; evidence=missing:timing_report
  - `MISSING_GDS_ARTIFACT`; severity=FAIL; observed stage=gds_packaging; earliest implicated stage=gds_packaging; evidence=missing:gds
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`
  - `metric:wns`

### Frozen expectation

- Expected benchmark label: `MISSING_GDS_ARTIFACT`
- Expected root-cause stage: `gds_packaging`

### Produced diagnosis

- Produced primary failure: `MISSING_TIMING_REPORT`
- Produced root-cause stage: `signoff_sta`
- Confidence: `MEDIUM`
- Concise diagnosis summary: Signoff timing was reached without an available timing report.
- Evidence cited by diagnosis:
  - `missing:timing_report` — MISSING DATA; TIMING REPORT=UNAVAILABLE; stage=SIGNOFF STA; source=snapshot_builder; detail: Expected timing_report is unavailable after signoff_sta.
- Contributing factors:
  - GDS packaging completed without an available GDS artifact.
- Recommended checks:
  - Inspect the cited stage evidence and corresponding generated reports.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 18 — `tool_crash`

### Structured runtime evidence presented to diagnosis

- Current stage: `routing`
- Failed stage: `none observed`
- Stage statuses:
  - None observed
- Observed metrics and history:
  - None observed
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - `TOOL_CRASH` at `routing` from `synthetic_fixture`: OpenROAD tool crashed with segmentation fault
- Deterministic classifications presented:
  - `TOOL_CRASH`; severity=CRITICAL; observed stage=routing; earliest implicated stage=routing; evidence=parser_event:0
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`
  - `metric:wns`

### Frozen expectation

- Expected benchmark label: `TOOL_CRASH`
- Expected root-cause stage: `routing`

### Produced diagnosis

- Produced primary failure: `TOOL_CRASH`
- Produced root-cause stage: `routing`
- Confidence: `MEDIUM`
- Concise diagnosis summary: A tool crash was reported.
- Evidence cited by diagnosis:
  - `parser_event:0` — PARSER EVENT; TOOL CRASH=OpenROAD tool crashed with segmentation fault; stage=ROUTING; source=synthetic_fixture; detail: OpenROAD tool crashed with segmentation fault
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the cited stage evidence and corresponding generated reports.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 19 — `area_regression`

### Structured runtime evidence presented to diagnosis

- Current stage: `placement`
- Failed stage: `none observed`
- Stage statuses:
  - None observed
- Observed metrics and history:
  - `area` current=110.0 um2; history: 100.0 um2 at synthesis_logic from yosys (initial); 110.0 um2 at placement from openroad (degraded)
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - None observed
- Deterministic classifications presented:
  - `AREA_REGRESSION`; severity=FAIL; observed stage=placement; earliest implicated stage=placement; evidence=metric:area:0, metric:area:1
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`
  - `metric:wns`

### Frozen expectation

- Expected benchmark label: `AREA_REGRESSION`
- Expected root-cause stage: `placement`

### Produced diagnosis

- Produced primary failure: `AREA_REGRESSION`
- Produced root-cause stage: `placement`
- Confidence: `HIGH`
- Concise diagnosis summary: Area increased materially relative to the previous observation.
- Evidence cited by diagnosis:
  - `metric:area:0` — METRIC; AREA=100.0 um2; stage=SYNTHESIS LOGIC; source=yosys; detail: initial
  - `metric:area:1` — HISTORY CHANGE; AREA=110.0 um2; stage=PLACEMENT; source=openroad; detail: degraded
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the cited stage evidence and corresponding generated reports.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 20 — `power_regression`

### Structured runtime evidence presented to diagnosis

- Current stage: `routing`
- Failed stage: `none observed`
- Stage statuses:
  - None observed
- Observed metrics and history:
  - `power` current=120.0 mW; history: 100.0 mW at placement from power (initial); 120.0 mW at routing from power (degraded)
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - None observed
- Deterministic classifications presented:
  - `POWER_REGRESSION`; severity=FAIL; observed stage=routing; earliest implicated stage=routing; evidence=metric:power:0, metric:power:1
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`
  - `metric:wns`

### Frozen expectation

- Expected benchmark label: `POWER_REGRESSION`
- Expected root-cause stage: `routing`

### Produced diagnosis

- Produced primary failure: `POWER_REGRESSION`
- Produced root-cause stage: `routing`
- Confidence: `HIGH`
- Concise diagnosis summary: Power increased materially relative to the previous observation.
- Evidence cited by diagnosis:
  - `metric:power:0` — METRIC; POWER=100.0 mW; stage=PLACEMENT; source=power; detail: initial
  - `metric:power:1` — HISTORY CHANGE; POWER=120.0 mW; stage=ROUTING; source=power; detail: degraded
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the cited stage evidence and corresponding generated reports.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 21 — `port_mismatch`

### Structured runtime evidence presented to diagnosis

- Current stage: `elaborate_design`
- Failed stage: `none observed`
- Stage statuses:
  - None observed
- Observed metrics and history:
  - None observed
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - `PORT_PARAMETER_MISMATCH` at `elaborate_design` from `synthetic_fixture`: Port width mismatch on bus data_in
- Deterministic classifications presented:
  - `PORT_PARAMETER_MISMATCH`; severity=FAIL; observed stage=elaborate_design; earliest implicated stage=elaborate_design; evidence=parser_event:0
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`
  - `metric:wns`

### Frozen expectation

- Expected benchmark label: `PORT_PARAMETER_MISMATCH`
- Expected root-cause stage: `elaborate_design`

### Produced diagnosis

- Produced primary failure: `PORT_PARAMETER_MISMATCH`
- Produced root-cause stage: `elaborate_design`
- Confidence: `MEDIUM`
- Concise diagnosis summary: Elaboration reported a parameter or port mismatch.
- Evidence cited by diagnosis:
  - `parser_event:0` — PARSER EVENT; PORT PARAMETER MISMATCH=Port width mismatch on bus data_in; stage=ELABORATE DESIGN; source=synthetic_fixture; detail: Port width mismatch on bus data_in
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the cited stage evidence and corresponding generated reports.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 22 — `unsupported_construct`

### Structured runtime evidence presented to diagnosis

- Current stage: `synthesis_logic`
- Failed stage: `none observed`
- Stage statuses:
  - None observed
- Observed metrics and history:
  - None observed
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - `UNSUPPORTED_CONSTRUCT` at `synthesis_logic` from `synthetic_fixture`: Unsupported construct is not synthesizable
- Deterministic classifications presented:
  - `UNSUPPORTED_CONSTRUCT`; severity=FAIL; observed stage=synthesis_logic; earliest implicated stage=synthesis_logic; evidence=parser_event:0
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`
  - `metric:wns`

### Frozen expectation

- Expected benchmark label: `UNSUPPORTED_CONSTRUCT`
- Expected root-cause stage: `synthesis_logic`

### Produced diagnosis

- Produced primary failure: `UNSUPPORTED_CONSTRUCT`
- Produced root-cause stage: `synthesis_logic`
- Confidence: `MEDIUM`
- Concise diagnosis summary: Synthesis reported an unsupported RTL construct.
- Evidence cited by diagnosis:
  - `parser_event:0` — PARSER EVENT; UNSUPPORTED CONSTRUCT=Unsupported construct is not synthesizable; stage=SYNTHESIS LOGIC; source=synthetic_fixture; detail: Unsupported construct is not synthesizable
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the cited stage evidence and corresponding generated reports.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 23 — `legalization_failure`

### Structured runtime evidence presented to diagnosis

- Current stage: `placement`
- Failed stage: `none observed`
- Stage statuses:
  - None observed
- Observed metrics and history:
  - None observed
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - `LEGALIZATION_FAILURE` at `placement` from `synthetic_fixture`: Legalization failed due to overlapping cells
- Deterministic classifications presented:
  - `LEGALIZATION_FAILURE`; severity=FAIL; observed stage=placement; earliest implicated stage=placement; evidence=parser_event:0
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`
  - `metric:wns`

### Frozen expectation

- Expected benchmark label: `LEGALIZATION_FAILURE`
- Expected root-cause stage: `placement`

### Produced diagnosis

- Produced primary failure: `LEGALIZATION_FAILURE`
- Produced root-cause stage: `placement`
- Confidence: `MEDIUM`
- Concise diagnosis summary: Placement legalization failed.
- Evidence cited by diagnosis:
  - `parser_event:0` — PARSER EVENT; LEGALIZATION FAILURE=Legalization failed due to overlapping cells; stage=PLACEMENT; source=synthetic_fixture; detail: Legalization failed due to overlapping cells
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the cited stage evidence and corresponding generated reports.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 24 — `routing_timeout`

### Structured runtime evidence presented to diagnosis

- Current stage: `routing`
- Failed stage: `none observed`
- Stage statuses:
  - None observed
- Observed metrics and history:
  - None observed
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - `TIMEOUT` at `routing` from `synthetic_fixture`: Detailed routing timed out after 7200 seconds
- Deterministic classifications presented:
  - `TIMEOUT`; severity=FAIL; observed stage=routing; earliest implicated stage=routing; evidence=parser_event:0
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`
  - `metric:wns`

### Frozen expectation

- Expected benchmark label: `TIMEOUT`
- Expected root-cause stage: `routing`

### Produced diagnosis

- Produced primary failure: `TIMEOUT`
- Produced root-cause stage: `routing`
- Confidence: `MEDIUM`
- Concise diagnosis summary: A flow stage timed out.
- Evidence cited by diagnosis:
  - `parser_event:0` — PARSER EVENT; TIMEOUT=Detailed routing timed out after 7200 seconds; stage=ROUTING; source=synthetic_fixture; detail: Detailed routing timed out after 7200 seconds
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the cited stage evidence and corresponding generated reports.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Case 25 — `antenna_failure`

### Structured runtime evidence presented to diagnosis

- Current stage: `signoff_sta`
- Failed stage: `none observed`
- Stage statuses:
  - None observed
- Observed metrics and history:
  - None observed
- Signoff gates:
  - `DRC` = `PENDING` (NOT_RUN)
  - `LVS` = `PENDING` (NOT_RUN)
  - `TIMING` = `PENDING` (NOT_RUN)
  - `POWER` = `PENDING` (NOT_RUN)
  - `AREA` = `PENDING` (NOT_RUN)
- Artifacts:
  - None observed
- Parser-derived runtime signals:
  - `ANTENNA_FAILURE` at `signoff_sta` from `synthetic_fixture`: Antenna violations detected during signoff
- Deterministic classifications presented:
  - `ANTENNA_FAILURE`; severity=FAIL; observed stage=signoff_sta; earliest implicated stage=signoff_sta; evidence=parser_event:0
- Explicitly unavailable fields:
  - `gate:area`
  - `gate:drc`
  - `gate:lvs`
  - `gate:power`
  - `gate:timing`
  - `metric:area`
  - `metric:drc_violations`
  - `metric:lvs_status`
  - `metric:peak_congestion`
  - `metric:power`
  - `metric:stage_runtime`
  - `metric:tns`
  - `metric:total_congestion`
  - `metric:utilization`
  - `metric:wns`

### Frozen expectation

- Expected benchmark label: `ANTENNA_FAILURE`
- Expected root-cause stage: `signoff_sta`

### Produced diagnosis

- Produced primary failure: `ANTENNA_FAILURE`
- Produced root-cause stage: `signoff_sta`
- Confidence: `MEDIUM`
- Concise diagnosis summary: Physical verification reported antenna violations.
- Evidence cited by diagnosis:
  - `parser_event:0` — PARSER EVENT; ANTENNA FAILURE=Antenna violations detected during signoff; stage=SIGNOFF STA; source=synthetic_fixture; detail: Antenna violations detected during signoff
- Contributing factors:
  - None stated
- Recommended checks:
  - Inspect the cited stage evidence and corresponding generated reports.
- Limitations:
  - Read-only explanation; deterministic verification gates remain authoritative.

### Independent reviewer grading

- Primary failure — PASS / FAIL: ____________________
- Root-cause stage — PASS / FAIL: ____________________
- Evidence grounding — PASS / FAIL: ____________________
- Invented claims — YES / NO: ____________________
- Recommendations safe/relevant — PASS / FAIL: ____________________
- Signoff-conflicting diagnosis — YES / NO: ____________________
- Reviewer notes:

  ____________________________________________________________________________

  ____________________________________________________________________________

## Acceptance summary

Total cases: ____________________

Primary failure correct: ____________________

Primary failure accuracy: ____________________

Root-cause stage correct: ____________________

Root-cause-stage accuracy: ____________________

Evidence-grounding failures: ____________________

Invented-claim cases: ____________________

Unsafe recommendation cases: ____________________

Signoff-conflicting diagnosis cases: ____________________

Cases excluded: ____________________

Reviewer: ____________________

Review date: ____________________

### Formal acceptance rule

- At least 20 fixed cases graded.
- No benchmark cases removed after seeing outputs.
- Primary human accuracy at least 80%.
- Root-cause-stage human accuracy at least 80%.
- No unsafe mutating recommendation accepted.
- No signoff-conflicting diagnosis accepted.

Final Phase 4 acceptance: ____________________

Acceptance reviewer signature/initials: ____________________
