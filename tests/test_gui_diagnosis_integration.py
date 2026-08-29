from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QEventLoop


ROOT = Path(__file__).resolve().parents[1]
GUI_ROOT = ROOT / "rtl2gds-gui"
sys.path.insert(0, str(GUI_ROOT))

from backend.app_controller import AppController  # noqa: E402
from backend.diagnosis import MockDiagnosisProvider  # noqa: E402
from backend.flow_config import FlowCommand, FlowConfiguration  # noqa: E402
from backend.parsers import MetricUpdate, StageUpdate  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    return QCoreApplication.instance() or QCoreApplication([])


def wait_until(qt_app, predicate, timeout: float = 3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        qt_app.processEvents(QEventLoop.AllEvents, 20)
        if predicate():
            return
        time.sleep(0.002)
    assert predicate()


def model_value(model, row, role_name):
    roles = {bytes(name).decode(): role for role, name in model.roleNames().items()}
    return model.data(model.index(row, 0), roles[role_name])


def test_controller_auto_diagnoses_failed_process_without_changing_gate(qt_app):
    provider = MockDiagnosisProvider()
    controller = AppController(diagnosis_provider=provider)
    controller.flowController.configure(FlowConfiguration(commands=(FlowCommand(
        stage="Placement",
        stage_number=7,
        program=sys.executable,
        arguments=("-u", "-c", "import sys; print('WNS: -0.842 ns'); sys.exit(5)"),
    ),)))

    controller.flowController.start()
    wait_until(qt_app, lambda: controller.flowController.status == "Failed")
    wait_until(qt_app, lambda: controller.diagnosisModel.state == "AVAILABLE")

    assert controller.diagnosisModel.primaryFailureCode in {"PLACEMENT_FAILURE", "TIMING_SETUP"}
    assert controller.diagnosisModel.rootCauseStageCode == "placement"
    assert model_value(controller.gateModel, 2, "status") == "FAIL"
    assert controller.flowController.status == "Failed"
    assert provider.calls >= 1
    controller.shutdown()


def test_controller_gracefully_handles_no_provider(qt_app):
    controller = AppController()
    controller.apply_normalized_event(MetricUpdate("wns", -0.4, "ns", "placement", "sta"))

    wait_until(qt_app, lambda: controller.diagnosisModel.state == "UNAVAILABLE")

    assert controller.diagnosisModel.message == "AI diagnosis unavailable"
    assert controller.metricsModel.wns == pytest.approx(-0.4)
    assert model_value(controller.gateModel, 2, "status") == "FAIL"
    controller.shutdown()


def test_controller_malformed_provider_response_is_unavailable(qt_app):
    controller = AppController(diagnosis_provider=MockDiagnosisProvider(response={"summary": "invalid"}))
    controller.apply_normalized_event(MetricUpdate("drc_violations", 3, "count", "drc", "drc"))

    wait_until(qt_app, lambda: controller.diagnosisModel.state == "UNAVAILABLE")

    assert controller.diagnosisModel.message == "Diagnosis unavailable"
    assert model_value(controller.gateModel, 0, "status") == "FAIL"
    controller.shutdown()


def test_controller_provider_exception_is_error(qt_app):
    controller = AppController(
        diagnosis_provider=MockDiagnosisProvider(error=RuntimeError("provider offline"))
    )
    controller.apply_normalized_event(MetricUpdate("wns", -0.4, "ns", "placement", "sta"))

    wait_until(qt_app, lambda: controller.diagnosisModel.state == "ERROR")

    assert controller.diagnosisModel.message == "Diagnosis provider error"
    assert model_value(controller.gateModel, 2, "status") == "FAIL"
    controller.shutdown()


def test_explicit_analysis_uses_structured_runtime_signal(qt_app):
    provider = MockDiagnosisProvider()
    controller = AppController(diagnosis_provider=provider)
    controller._append_process_output("stderr", "Detailed routing timed out after 7200 seconds")
    controller.analyzeFailure()

    wait_until(qt_app, lambda: controller.diagnosisModel.state == "AVAILABLE")

    assert controller.diagnosisModel.primaryFailureCode == "TIMEOUT"
    assert "timeout" in controller.diagnosisModel.summary.lower() or "timed out" in controller.diagnosisModel.summary.lower()
    controller.shutdown()


def test_diagnosis_history_is_separate_and_run_reset_clears_presentation(qt_app):
    provider = MockDiagnosisProvider()
    controller = AppController(diagnosis_provider=provider)
    controller.apply_normalized_event(StageUpdate("routing", "Failed", 4.0))
    controller.analyzeFailure()
    wait_until(qt_app, lambda: controller.diagnosisModel.state == "AVAILABLE")

    assert controller.diagnosisModel.historyModel.rowCount() == 1
    assert len(controller.metricsModel.stageHistory()) >= 1

    controller._begin_run()
    assert controller.diagnosisModel.state == "NO_DIAGNOSIS"
    assert controller.diagnosisModel.historyModel.rowCount() == 0
    controller.shutdown()
