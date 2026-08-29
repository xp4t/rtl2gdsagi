from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QEventLoop, QProcess


GUI_ROOT = Path(__file__).resolve().parents[1] / "rtl2gds-gui"
sys.path.insert(0, str(GUI_ROOT))

from backend.app_controller import AppController  # noqa: E402
from backend.flow_config import (  # noqa: E402
    FlowCommand,
    FlowConfiguration,
    load_flow_configuration,
)
from backend.flow_runner import FlowRunner  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    return QCoreApplication.instance() or QCoreApplication([])


def wait_until(qt_app, predicate, timeout: float = 3.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        qt_app.processEvents(QEventLoop.AllEvents, 20)
        if predicate():
            return
        time.sleep(0.002)
    qt_app.processEvents(QEventLoop.AllEvents, 20)
    assert predicate(), "Qt state did not settle before timeout"


def python_command(source: str, *, stage: str = "Place") -> FlowCommand:
    return FlowCommand(
        stage=stage,
        stage_number=7,
        program=sys.executable,
        arguments=("-u", "-c", source),
        description="Executing a test stage.",
    )


def test_successful_state_transitions(qt_app):
    runner = FlowRunner(FlowConfiguration(commands=(python_command("print('done')"),)))
    statuses = []
    runner.statusChanged.connect(lambda: statuses.append(runner.status))

    assert runner.start() is True
    wait_until(qt_app, lambda: runner.status == "Completed")

    assert statuses[0] == "Starting"
    assert "Running" in statuses
    assert statuses[-1] == "Completed"
    assert runner.currentStage == "Place"
    assert runner.stageNumber == 7
    assert runner.progress == 100
    assert runner.startTime != "—"
    assert len(runner.elapsed.split(":")) == 3
    assert runner.elapsedSeconds >= 0
    assert runner.exitCode == 0
    assert runner.failed is False


def test_incremental_stdout_and_stderr_are_line_buffered(qt_app):
    source = (
        "import sys,time; "
        "sys.stdout.write('partial'); sys.stdout.flush(); time.sleep(0.05); "
        "sys.stdout.write(' line\\nsecond\\n'); sys.stdout.flush(); "
        "sys.stderr.write('problem\\n'); sys.stderr.flush()"
    )
    runner = FlowRunner(FlowConfiguration(commands=(python_command(source),)))
    lines = []
    raw_chunks = []
    runner.outputReceived.connect(lambda stream, line: lines.append((stream, line)))
    runner.rawOutputReceived.connect(lambda stream, text: raw_chunks.append((stream, text)))

    runner.start()
    wait_until(qt_app, lambda: runner.status == "Completed")

    assert ("stdout", "partial line") in lines
    assert ("stdout", "second") in lines
    assert ("stderr", "problem") in lines
    assert "".join(text for stream, text in raw_chunks if stream == "stdout") == "partial line\nsecond\n"


def test_nonzero_exit_sets_failure_state(qt_app):
    runner = FlowRunner(
        FlowConfiguration(commands=(python_command("import sys; print('bad', file=sys.stderr); sys.exit(7)"),))
    )

    runner.start()
    wait_until(qt_app, lambda: runner.status == "Failed")

    assert runner.failed is True
    assert runner.exitCode == 7
    assert "exited with code 7" in runner.failureMessage


def test_cancellation_is_nonblocking(qt_app):
    runner = FlowRunner(
        FlowConfiguration(commands=(python_command("import time; time.sleep(10)"),))
    )
    runner.start()
    wait_until(qt_app, lambda: runner.status == "Running")

    runner.cancel()
    assert runner.status == "Cancelling"
    wait_until(qt_app, lambda: runner.status == "Cancelled")

    assert runner.failed is False
    assert runner.running is False


def test_shutdown_kills_active_child(qt_app):
    runner = FlowRunner(
        FlowConfiguration(commands=(python_command("import time; time.sleep(10)"),))
    )
    runner.start()
    wait_until(qt_app, lambda: runner.status == "Running")

    runner.shutdown()
    wait_until(qt_app, lambda: runner._process.state() == QProcess.NotRunning)

    assert runner.status == "Cancelled"


def test_app_controller_feeds_process_output_to_log_model(qt_app):
    controller = AppController()
    controller.flowController.configure(
        FlowConfiguration(commands=(python_command("print('live process output')"),))
    )

    controller.flowController.start()
    wait_until(qt_app, lambda: controller.flowController.status == "Completed")

    assert controller.logModel.count == 1
    roles = {
        bytes(name).decode(): role
        for role, name in controller.logModel.roleNames().items()
    }
    index = controller.logModel.index(0, 0)
    assert controller.logModel.data(index, roles["level"]) == "INFO"
    assert controller.logModel.data(index, roles["scope"]) == "PLACE"
    assert controller.logModel.data(index, roles["message"]) == "live process output"
    controller.shutdown()


def test_app_controller_parses_live_process_metrics(qt_app):
    controller = AppController()
    controller.flowController.configure(
        FlowConfiguration(commands=(python_command(
            "print('WNS: -0.842 ns'); print('Total congestion: 0.58')"
        ),))
    )

    controller.flowController.start()
    wait_until(qt_app, lambda: controller.flowController.status == "Completed")

    assert controller.metricsModel.wns == pytest.approx(-0.842)
    assert controller.metricsModel.totalCongestion == pytest.approx(0.58)
    assert controller.metricsModel.stageStatus == "Completed"
    controller.shutdown()


def test_json_configuration_resolves_relative_working_directory(tmp_path):
    config_path = tmp_path / "flow.json"
    config_path.write_text(json.dumps({
        "total_stages": 14,
        "commands": [{
            "stage": "Route",
            "stage_number": 10,
            "program": "/bin/true",
            "arguments": [],
            "working_directory": "run",
            "environment": {"FLOW_TEST": "1"},
        }],
    }))

    configuration = load_flow_configuration(config_path)

    assert configuration.total_stages == 14
    assert configuration.commands[0].working_directory == str((tmp_path / "run").resolve())
    assert configuration.commands[0].environment == {"FLOW_TEST": "1"}
