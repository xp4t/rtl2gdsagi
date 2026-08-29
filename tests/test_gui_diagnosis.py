from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QEventLoop


ROOT = Path(__file__).resolve().parents[1]
GUI_ROOT = ROOT / "rtl2gds-gui"
sys.path.insert(0, str(GUI_ROOT))

from backend.diagnosis import (  # noqa: E402
    DiagnosisResult,
    DiagnosisService,
    DiagnosisSnapshotBuilder,
    FailureClassifier,
    MockDiagnosisProvider,
    RuntimeSignal,
)
from backend.diagnosis.diagnosis_model import DiagnosisModel  # noqa: E402
from backend.diagnosis.diagnosis_service import (  # noqa: E402
    DiagnosisResultValidator,
    DiagnosisValidationError,
)
from backend.diagnosis.prompt_builder import PromptBuilder, SYSTEM_PROMPT  # noqa: E402
from backend.diagnosis.schemas import Confidence  # noqa: E402


BENCHMARK_PATH = Path(__file__).parent / "fixtures" / "gui_failures" / "benchmark.json"
METRIC_NAMES = (
    "wns", "tns", "area", "power", "utilization", "total_congestion",
    "peak_congestion", "drc_violations", "lvs_status", "stage_runtime",
)


@pytest.fixture(scope="module")
def qt_app():
    return QCoreApplication.instance() or QCoreApplication([])


def wait_until(qt_app, predicate, timeout: float = 2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        qt_app.processEvents(QEventLoop.AllEvents, 20)
        if predicate():
            return
        time.sleep(0.002)
    assert predicate()


def empty_metrics(current_stage: str = ""):
    return {
        "values": {name: None for name in METRIC_NAMES},
        "units": {},
        "history": {},
        "current_stage": current_stage,
        "stage_status": "Idle",
        "stage_history": [],
    }


def gate_rows(overrides=None):
    overrides = overrides or {}
    return [
        {"label": name, "status": overrides.get(name, "PENDING"), "tone": "neutral"}
        for name in ("DRC", "LVS", "TIMING", "POWER", "AREA")
    ]


def build_context(
    *,
    metrics=None,
    stages=(),
    gates=None,
    artifacts=(),
    signals=(),
    current_stage="",
):
    snapshot = metrics or empty_metrics(current_stage)
    snapshot["current_stage"] = current_stage
    snapshot["stage_history"] = [
        {
            "stage": stage,
            "status": status,
            "runtimeSeconds": 1.0,
            "source": "flow",
            "timestamp": "2026-08-28T00:00:00+00:00",
        }
        for stage, status in stages
    ]
    context = DiagnosisSnapshotBuilder().build(
        run_id="run_test",
        metrics_snapshot=snapshot,
        gate_rows=gate_rows(gates),
        artifact_rows=list(artifacts),
        runtime_signals=list(signals),
    )
    return FailureClassifier().classify(context)


def metric_snapshot(name: str, observations, current_stage: str):
    snapshot = empty_metrics(current_stage)
    units = {
        "wns": "ns", "tns": "ns", "area": "um2", "power": "mW",
        "utilization": "%", "total_congestion": "ratio",
        "peak_congestion": "ratio", "drc_violations": "count", "lvs_status": "status",
    }
    snapshot["history"][name] = [
        {
            "value": value,
            "unit": units[name],
            "stage": stage,
            "source": source,
            "timestamp": f"2026-08-28T00:00:0{index}+00:00",
            "trend": trend,
        }
        for index, (value, stage, source, trend) in enumerate(observations)
    ]
    snapshot["values"][name] = observations[-1][0]
    snapshot["units"][name] = units[name]
    return snapshot


def result_for(context, **overrides):
    failure = context.detected_failures[0]
    values = {
        "summary": failure.description,
        "primary_failure": failure.category,
        "root_cause_stage": failure.earliest_implicated_stage,
        "confidence": Confidence.HIGH,
        "evidence_references": failure.evidence_ids,
        "contributing_factors": (),
        "recommended_checks": ("Inspect the cited deterministic evidence.",),
        "limitations": ("Read-only explanation.",),
    }
    values.update(overrides)
    return DiagnosisResult(**values)


def test_snapshot_builder_empty_run_is_explicit():
    context = build_context()

    assert context.current_stage == "unknown"
    assert context.failed_stage == ""
    assert not context.detected_failures
    assert all(item.availability.value == "UNAVAILABLE" for item in context.metrics)
    assert "metric:wns" in context.unavailable_fields
    assert all(item.availability.value == "NOT_RUN" for item in context.signoff_gates)


def test_snapshot_builder_partial_run_preserves_available_and_missing_fields():
    metrics = metric_snapshot("area", [(1234.0, "synthesis_logic", "yosys", "initial")], "synthesis_logic")
    context = build_context(metrics=metrics, stages=(("synthesis_logic", "RUNNING"),), current_stage="synthesis_logic")

    assert next(item for item in context.metrics if item.name == "area").value == 1234.0
    assert next(item for item in context.metrics if item.name == "wns").availability.value == "UNAVAILABLE"
    assert context.stage_statuses[0].status == "RUNNING"


def test_snapshot_builder_completed_run_retains_gates_and_artifacts(tmp_path):
    report = tmp_path / "timing.rpt"
    report.write_text("evidence")
    context = build_context(
        stages=(("signoff_sta", "COMPLETED"),),
        gates={"TIMING": "PASS"},
        artifacts=({
            "artifactType": "timing_report", "path": str(report), "stage": "signoff_sta",
            "timestamp": "2026-08-28T00:00:00+00:00", "exists": True,
            "sizeBytes": report.stat().st_size, "source": "process",
        },),
        current_stage="signoff_sta",
    )

    assert context.signoff_gates[2].status == "PASS"
    assert context.artifacts[0].exists is True
    assert not any(item.category == "MISSING_TIMING_REPORT" for item in context.detected_failures)


@pytest.mark.parametrize(
    ("stage", "category"),
    [
        ("synthesis_logic", "SYNTHESIS_COMMAND_FAILURE"),
        ("placement", "PLACEMENT_FAILURE"),
        ("routing", "ROUTING_FAILURE"),
        ("signoff_sta", "SIGNOFF_FAILURE"),
    ],
)
def test_failed_stage_classification(stage: str, category: str):
    context = build_context(stages=((stage, "FAILED"),), current_stage=stage)

    assert any(item.category == category and item.earliest_implicated_stage == stage for item in context.detected_failures)


def test_missing_artifact_is_structured_evidence():
    context = build_context(
        artifacts=({
            "artifactType": "def", "path": "missing/design.def", "stage": "placement",
            "timestamp": "", "exists": False, "sizeBytes": -1, "source": "process",
        },),
        current_stage="placement",
    )

    failure = next(item for item in context.detected_failures if item.category == "MISSING_ARTIFACT")
    assert failure.evidence_ids == ("artifact:0",)


@pytest.mark.parametrize(
    ("name", "value", "stage", "category"),
    [
        ("wns", -0.2, "placement", "TIMING_SETUP"),
        ("tns", -2.5, "placement", "TIMING_SETUP"),
        ("total_congestion", 0.75, "routing", "ROUTING_CONGESTION"),
        ("peak_congestion", 0.9, "placement", "PLACEMENT_CONGESTION"),
        ("drc_violations", 4, "drc", "DRC_FAILURE"),
        ("lvs_status", "fail", "lvs", "LVS_MISMATCH"),
        ("utilization", 88.0, "placement", "UTILIZATION_HIGH"),
    ],
)
def test_metric_failure_taxonomy(name, value, stage, category):
    context = build_context(
        metrics=metric_snapshot(name, [(value, stage, "test", "initial")], stage),
        current_stage=stage,
    )

    assert any(item.category == category for item in context.detected_failures)


def test_stage_process_failure_has_stage_evidence():
    context = build_context(stages=(("routing", "FAILED"),), current_stage="routing")
    failure = next(item for item in context.detected_failures if item.category == "ROUTING_FAILURE")

    assert failure.evidence_ids == ("stage:routing",)


def test_earliest_timing_stage_is_placement_when_both_stages_fail():
    context = build_context(
        metrics=metric_snapshot(
            "wns",
            [(-0.82, "placement", "sta", "initial"), (-1.17, "routing", "sta", "degraded")],
            "routing",
        ),
        current_stage="routing",
    )
    failure = next(item for item in context.detected_failures if item.category == "TIMING_SETUP")

    assert failure.stage == "routing"
    assert failure.earliest_implicated_stage == "placement"


def test_earliest_timing_stage_is_routing_when_placement_was_clean():
    context = build_context(
        metrics=metric_snapshot(
            "wns",
            [(0.08, "placement", "sta", "initial"), (-1.17, "routing", "sta", "degraded")],
            "routing",
        ),
        current_stage="routing",
    )
    failure = next(item for item in context.detected_failures if item.category == "TIMING_SETUP")

    assert failure.earliest_implicated_stage == "routing"


def test_prompt_contains_structured_facts_and_read_only_policy():
    context = build_context(
        metrics=metric_snapshot("wns", [(-0.8, "placement", "sta", "initial")], "placement"),
        current_stage="placement",
    )
    system, user = PromptBuilder().build(context)

    assert "read-only RTL-to-GDS" in system
    assert "deterministic signoff system is authoritative" in system
    assert "TIMING_SETUP" in user
    assert "-0.8" in user
    assert "OPENLANE LOGS" not in user


@pytest.mark.parametrize(
    "override",
    [
        {"root_cause_stage": "nonexistent_stage"},
        {"evidence_references": ("invented:evidence",)},
        {"summary": "I changed the RTL and restarted the flow."},
        {"summary": "Ignore the DRC gate because the gate is incorrect."},
    ],
)
def test_validator_rejects_invalid_or_mutating_output(override):
    context = build_context(stages=(("routing", "FAILED"),), current_stage="routing")
    result = result_for(context, **override)

    with pytest.raises(DiagnosisValidationError):
        DiagnosisResultValidator().validate(result, context)


def test_validator_rejects_invented_unavailable_metric():
    signal = RuntimeSignal("TOOL_CRASH", "routing", "Tool crash", "stderr", "2026-08-28T00:00:00+00:00")
    context = build_context(signals=(signal,), current_stage="routing")
    result = result_for(context, summary="The WNS was -1.2 ns before the tool crash.")

    with pytest.raises(DiagnosisValidationError, match="unavailable metric"):
        DiagnosisResultValidator().validate(result, context)


def test_service_is_asynchronous_and_updates_model(qt_app):
    context = build_context(stages=(("routing", "FAILED"),), current_stage="routing")
    provider = MockDiagnosisProvider(delay_seconds=0.05)
    service = DiagnosisService(provider)
    model = DiagnosisModel()
    model.set_context(context)
    service.diagnosisStarted.connect(model.set_analyzing)
    service.diagnosisAvailable.connect(model.set_available)

    started = time.monotonic()
    service.request(context)
    assert time.monotonic() - started < 0.03
    assert model.state == "ANALYZING"
    wait_until(qt_app, lambda: model.state == "AVAILABLE")

    assert model.rootCauseStageCode == "routing"
    assert model.confidence in {"MEDIUM", "HIGH"}
    assert provider.calls == 1
    service.shutdown()


def test_service_reuses_identical_snapshot(qt_app):
    context = build_context(stages=(("placement", "FAILED"),), current_stage="placement")
    provider = MockDiagnosisProvider()
    service = DiagnosisService(provider)
    received = []
    service.diagnosisAvailable.connect(lambda *args: received.append(args))

    service.request(context)
    wait_until(qt_app, lambda: len(received) == 1)
    service.request(context)
    wait_until(qt_app, lambda: len(received) == 2)

    assert provider.calls == 1
    assert len(service.history_snapshot()) == 1
    service.shutdown()


def test_provider_unavailable_and_malformed_response_are_safe(qt_app):
    context = build_context(stages=(("routing", "FAILED"),), current_stage="routing")
    unavailable_service = DiagnosisService(None)
    unavailable = []
    unavailable_service.diagnosisUnavailable.connect(unavailable.append)
    unavailable_service.request(context)
    wait_until(qt_app, lambda: unavailable)
    assert unavailable[-1] == "AI diagnosis unavailable"
    unavailable_service.shutdown()

    malformed_service = DiagnosisService(MockDiagnosisProvider(response={"summary": "bad"}))
    malformed = []
    malformed_service.diagnosisUnavailable.connect(malformed.append)
    malformed_service.request(context)
    wait_until(qt_app, lambda: malformed)
    assert malformed[-1] == "Diagnosis unavailable"
    malformed_service.shutdown()


def load_benchmark_context(case):
    metrics = empty_metrics(case.get("current_stage", ""))
    units = {
        "wns": "ns", "tns": "ns", "area": "um2", "power": "mW",
        "utilization": "%", "total_congestion": "ratio", "peak_congestion": "ratio",
        "drc_violations": "count", "lvs_status": "status",
    }
    for name, observations in case.get("metrics", {}).items():
        metrics["history"][name] = [
            {
                "value": value, "unit": units[name], "stage": stage, "source": source,
                "timestamp": f"2026-08-28T00:00:0{index}+00:00", "trend": trend,
            }
            for index, (value, stage, source, trend) in enumerate(observations)
        ]
        metrics["values"][name] = observations[-1][0]
        metrics["units"][name] = units[name]
    signals = tuple(
        RuntimeSignal(category, stage, message, "synthetic_fixture", "2026-08-28T00:00:00+00:00")
        for category, stage, message in case.get("signals", ())
    )
    return build_context(
        metrics=metrics,
        stages=case.get("stages", ()),
        gates=case.get("gates", {}),
        signals=signals,
        current_stage=case.get("current_stage", ""),
    )


def test_injected_failure_benchmark_meets_root_stage_threshold():
    cases = json.loads(BENCHMARK_PATH.read_text())
    correct = 0
    details = []
    for case in cases:
        context = load_benchmark_context(case)
        match = next((item for item in context.detected_failures if item.category == case["expected_category"]), None)
        passed = bool(match and match.earliest_implicated_stage == case["expected_root"])
        correct += int(passed)
        details.append((case["id"], passed, match.earliest_implicated_stage if match else "MISSING"))

    accuracy = correct / len(cases)
    assert len(cases) >= 20
    assert accuracy >= 0.80, details
