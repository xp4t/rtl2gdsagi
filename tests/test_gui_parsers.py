from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication


ROOT = Path(__file__).resolve().parents[1]
GUI_ROOT = ROOT / "rtl2gds-gui"
FIXTURES = Path(__file__).parent / "fixtures" / "gui_logs"
sys.path.insert(0, str(GUI_ROOT))

from backend.app_controller import AppController  # noqa: E402
from backend.artifact_model import ArtifactModel  # noqa: E402
from backend.metrics_model import MetricsModel  # noqa: E402
from backend.parsers import ArtifactUpdate, MetricUpdate, ParserPipeline, StageUpdate  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def qt_app():
    return QCoreApplication.instance() or QCoreApplication([])


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


def metric_events(events, name: str):
    return [event for event in events if isinstance(event, MetricUpdate) and event.name == name]


def parse_fragment(name: str, stage: str):
    pipeline = ParserPipeline()
    return pipeline.feed(read_fixture(name), stage=stage) + pipeline.flush()


def model_role_value(model, row: int, role_name: str):
    roles = {bytes(name).decode(): role for role, name in model.roleNames().items()}
    return model.data(model.index(row, 0), roles[role_name])


def test_valid_metric_extraction_across_tool_formats():
    synthesis = parse_fragment("synthesis_fragment.log", "Synthesis Logic")
    placement = parse_fragment("placement_fragment.log", "Placement")

    assert metric_events(synthesis, "area")[-1].value == 12_380_000
    assert metric_events(placement, "utilization")[-1].value == pytest.approx(68.7)
    assert metric_events(placement, "total_congestion")[-1].value == pytest.approx(0.72)
    assert metric_events(placement, "peak_congestion")[-1].value == pytest.approx(0.91)
    assert metric_events(placement, "power")[-1].value == pytest.approx(125.7)
    assert metric_events(placement, "stage_runtime")[-1].value == pytest.approx(922)


def test_malformed_lines_do_not_raise_or_emit_updates():
    pipeline = ParserPipeline()

    assert pipeline.parse_line("WNS: -- unavailable --", stage="Placement") == []
    assert pipeline.parse_line("Total congestion: ???", stage="Placement") == []
    assert pipeline.parse_line("DRC violations: not-a-number", stage="DRC") == []


def test_partial_process_output_is_buffered_incrementally():
    pipeline = ParserPipeline()

    assert pipeline.feed("WN", stage="Placement") == []
    assert pipeline.feed("S: -0.842", stage="Placement") == []
    events = pipeline.feed(" ns\nTNS: -6.11 ns\n", stage="Placement")

    assert metric_events(events, "wns")[0].value == pytest.approx(-0.842)
    assert metric_events(events, "tns")[0].value == pytest.approx(-6.11)


def test_repeated_metric_updates_accumulate():
    events = parse_fragment("timing_fragment.log", "Placement")
    model = MetricsModel()
    for event in events:
        model.applyEvent(event)

    assert len(model.metricHistory("wns")) == 2
    assert len(model.metricHistory("tns")) == 2
    assert model.wns == pytest.approx(-0.842)
    assert model.tns == pytest.approx(-6.11)


def test_metric_improvement_and_degradation_are_classified():
    model = MetricsModel()
    for value in (-1.0, -0.5, -1.2):
        model.applyEvent(MetricUpdate("wns", value, "ns", "placement", "sta"))

    history = model.metricHistory("wns")
    assert [item["trend"] for item in history] == ["initial", "improved", "degraded"]


def test_missing_values_remain_explicitly_unavailable():
    model = MetricsModel()
    pipeline = ParserPipeline()
    events = pipeline.parse_line("No metrics were emitted for this stage", stage="Placement")
    for event in events:
        model.applyEvent(event)

    assert model.wns is None
    assert model.wnsAvailable is False
    assert model_role_value(model, 0, "value") == "—"
    assert model_role_value(model, 0, "context") == "UNAVAILABLE"


def test_malformed_later_value_preserves_previous_known_metric():
    model = MetricsModel()
    pipeline = ParserPipeline()
    valid = pipeline.parse_line("WNS: -0.842 ns", stage="Placement")
    malformed = pipeline.parse_line("WNS: not-a-number", stage="Placement")
    for event in valid + malformed:
        model.applyEvent(event)

    assert model.wns == pytest.approx(-0.842)
    assert len(model.metricHistory("wns")) == 1


def test_drc_violation_count_is_normalized():
    events = parse_fragment("signoff_fragment.log", "DRC")
    drc = metric_events(events, "drc_violations")

    assert len(drc) == 1
    assert drc[0].value == 17
    assert drc[0].unit == "count"
    assert drc[0].source == "drc"


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("LVS PASSED: Netlists match", "pass"),
        ("LVS FAILED: Netlists do not match", "fail"),
    ],
)
def test_lvs_pass_and_fail(line: str, expected: str):
    events = ParserPipeline().parse_line(line, stage="LVS")

    assert metric_events(events, "lvs_status")[0].value == expected


def test_stage_transitions_and_runtime_are_retained():
    model = MetricsModel()
    model.applyEvent(StageUpdate("placement", "Running", 1.5))
    model.applyEvent(StageUpdate("placement", "Completed", 8.25))
    model.applyEvent(StageUpdate("routing", "Running", 0.5))

    assert model.currentStage == "routing"
    assert model.stageStatus == "Running"
    assert model.stageRuntime == pytest.approx(0.5)
    assert [item["status"] for item in model.stageHistory()] == ["Running", "Completed", "Running"]
    assert model.metricHistory("stage_runtime")[0]["value"] == pytest.approx(8.25)


def test_history_retains_stage_source_timestamp_and_spark_data():
    model = MetricsModel()
    model.applyEvent(MetricUpdate("total_congestion", 0.72, "ratio", "placement", "openroad"))
    model.applyEvent(MetricUpdate("total_congestion", 0.58, "ratio", "placement", "openroad"))

    history = model.metricHistory("total_congestion")
    assert history[-1]["stage"] == "placement"
    assert history[-1]["source"] == "openroad"
    assert history[-1]["timestamp"]
    assert history[-1]["trend"] == "improved"
    assert model_role_value(model, 4, "spark")


def test_artifact_index_tracks_structured_metadata(tmp_path):
    artifact = tmp_path / "timing.rpt"
    artifact.write_text("timing evidence")
    events = ParserPipeline().parse_line(f"Writing {artifact}", stage="Signoff STA")
    model = ArtifactModel()
    for event in events:
        model.applyEvent(event)

    assert model.count == 1
    assert model_role_value(model, 0, "artifactType") == "timing_report"
    assert model_role_value(model, 0, "path") == str(artifact)
    assert model_role_value(model, 0, "stage") == "signoff_sta"
    assert model_role_value(model, 0, "exists") is True
    assert model_role_value(model, 0, "sizeBytes") == len("timing evidence")


def test_active_run_backing_model_updates_from_synthetic_event():
    controller = AppController()

    controller.apply_normalized_event(MetricUpdate("wns", -0.842, "ns", "placement", "sta"))
    controller.apply_normalized_event(MetricUpdate("drc_violations", 0, "count", "drc", "drc"))

    assert controller.metricsModel.wns == pytest.approx(-0.842)
    assert model_role_value(controller.metricsModel, 0, "value") == "-0.842"
    assert model_role_value(controller.gateModel, 0, "status") == "PASS"
