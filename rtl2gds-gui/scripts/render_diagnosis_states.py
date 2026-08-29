from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PySide6.QtCore import QEventLoop, QTimer, QUrl, QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

GUI_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GUI_ROOT))

from backend.app_controller import AppController  # noqa: E402
from backend.diagnosis import MockDiagnosisProvider  # noqa: E402
from backend.flow_config import FlowCommand, FlowConfiguration  # noqa: E402


class StateRenderer:
    """Render the required Phase 4 states and fail on any Qt warning."""

    def __init__(self, output_directory: Path) -> None:
        self.output_directory = output_directory
        self.output_directory.mkdir(parents=True, exist_ok=True)
        self.warnings: list[str] = []
        self.app = QGuiApplication(sys.argv[:1])
        self.app.setApplicationName("RTL2GDSAGI Phase 4 Render Validation")
        self._load_fonts()
        self.provider = MockDiagnosisProvider(delay_seconds=0.3)
        self.controller = AppController(diagnosis_provider=self.provider)
        self.app.aboutToQuit.connect(self.controller.shutdown)
        self.engine = QQmlApplicationEngine()
        self.engine.rootContext().setContextProperty("appController", self.controller)
        self.engine.load(QUrl.fromLocalFile(GUI_ROOT / "qml" / "Main.qml"))
        if not self.engine.rootObjects():
            raise RuntimeError("Main.qml did not create a root object")
        self.window = self.engine.rootObjects()[0]
        self.window.setWidth(1536)
        self.window.setHeight(1024)
        self._step = 0

    def _load_fonts(self) -> None:
        font_directory = GUI_ROOT / "assets" / "fonts"
        for filename in (
            "FiraSans-Regular.ttf",
            "FiraSans-Medium.ttf",
            "FiraSans-SemiBold.ttf",
            "FiraCode-Variable.ttf",
        ):
            if QFontDatabase.addApplicationFont(str(font_directory / filename)) < 0:
                raise RuntimeError(f"Unable to load bundled font: {filename}")

    def capture(self, name: str) -> None:
        self.app.processEvents(QEventLoop.AllEvents, 50)
        target = self.output_directory / f"active-run-{name}.png"
        if not self.window.screen().grabWindow(self.window.winId()).save(str(target)):
            raise RuntimeError(f"Unable to save {target}")

    def run(self) -> int:
        QTimer.singleShot(1000, self.advance)
        exit_code = self.app.exec()
        self.controller.shutdown()
        del self.engine
        if self.warnings:
            for warning in self.warnings:
                print(warning, file=sys.stderr)
            return 2
        return exit_code

    def advance(self) -> None:
        try:
            if self._step == 0:
                self.capture("01-no-process-no-metrics")
                self._start_healthy_flow()
                self._step = 1
                QTimer.singleShot(700, self.advance)
                return
            if self._step == 1:
                self.capture("02-healthy-running")
                self.controller.flowController.stop()
                self._step = 2
                QTimer.singleShot(500, self.advance)
                return
            if self._step == 2:
                self._start_failing_flow()
                self._step = 3
                QTimer.singleShot(700, self.advance)
                return
            if self._step == 3:
                context = self.controller.diagnosis_context_snapshot()
                self.controller.diagnosisModel.set_context(context)
                self.controller.diagnosisModel.set_no_diagnosis()
                self.capture("03-failed-before-diagnosis")
                self.controller.diagnosisModel.set_analyzing(context.fingerprint())
                self._step = 4
                QTimer.singleShot(150, self.advance)
                return
            if self._step == 4:
                self.capture("04-analyzing")
                self._step = 5
                QTimer.singleShot(2000, self.advance)
                return
            if self._step == 5:
                if self.controller.diagnosisModel.state != "AVAILABLE":
                    raise RuntimeError(
                        f"Expected AVAILABLE, got {self.controller.diagnosisModel.state}"
                    )
                self.capture("05-available")
                self.controller.diagnosisModel.set_unavailable("AI diagnosis unavailable")
                self._step = 6
                QTimer.singleShot(150, self.advance)
                return
            if self._step == 6:
                self.capture("06-provider-unavailable")
                self.controller.diagnosisModel.set_unavailable("Diagnosis unavailable")
                self._step = 7
                QTimer.singleShot(150, self.advance)
                return
            if self._step == 7:
                self.capture("07-malformed-provider-response")
                self.controller.diagnosisModel.set_error("Diagnosis provider error")
                self._step = 8
                QTimer.singleShot(150, self.advance)
                return
            self.capture("08-provider-error")
            self.app.quit()
        except Exception as error:  # validation harness must report and terminate
            print(f"render validation failed: {error}", file=sys.stderr)
            self.app.exit(1)

    def _start_healthy_flow(self) -> None:
        self.controller.flowController.configure(FlowConfiguration(commands=(FlowCommand(
            stage="Placement",
            stage_number=7,
            program=sys.executable,
            arguments=(
                "-u",
                "-c",
                "import time; print('WNS: 0.120 ns', flush=True); "
                "print('TNS: 0.000 ns', flush=True); time.sleep(10)",
            ),
        ),)))
        if not self.controller.flowController.start():
            raise RuntimeError("Healthy validation flow did not start")

    def _start_failing_flow(self) -> None:
        self.controller.flowController.configure(FlowConfiguration(commands=(FlowCommand(
            stage="Routing",
            stage_number=10,
            program=sys.executable,
            arguments=(
                "-u",
                "-c",
                "import sys; print('WNS: -1.170 ns', flush=True); "
                "print('TNS: -8.420 ns', flush=True); "
                "print('Peak congestion: 0.91', flush=True); sys.exit(5)",
            ),
        ),)))
        if not self.controller.flowController.start():
            raise RuntimeError("Failing validation flow did not start")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_directory", type=Path)
    arguments = parser.parse_args()
    renderer: StateRenderer | None = None

    def message_handler(message_type, context, message) -> None:
        if renderer is not None and message_type in {
            QtMsgType.QtWarningMsg,
            QtMsgType.QtCriticalMsg,
            QtMsgType.QtFatalMsg,
        }:
            renderer.warnings.append(message)

    qInstallMessageHandler(message_handler)
    renderer = StateRenderer(arguments.output_directory)
    return renderer.run()


if __name__ == "__main__":
    raise SystemExit(main())
