from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot

from .flow_config import FlowCommand, FlowConfiguration, load_flow_configuration
from .flow_runner import FlowRunner


class FlowController(QObject):
    stateChanged = Signal()
    statusChanged = Signal()
    currentStageChanged = Signal()
    progressChanged = Signal()
    startTimeChanged = Signal()
    elapsedChanged = Signal()
    exitCodeChanged = Signal()
    failureChanged = Signal()
    configurationChanged = Signal()

    rawOutputReceived = Signal(str, str)
    outputReceived = Signal(str, str)
    runStarted = Signal()
    runFinished = Signal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        commands: Sequence[FlowCommand] | None = None,
        config_path: str | Path | None = None,
    ) -> None:
        super().__init__(parent)
        if commands is not None and config_path is not None:
            raise ValueError("Provide commands or config_path, not both")
        if config_path is not None:
            configuration = load_flow_configuration(config_path)
        else:
            configuration = FlowConfiguration(commands=tuple(commands or ()))
        self._runner = FlowRunner(configuration, self)

        self._runner.statusChanged.connect(self._forward_status)
        self._runner.currentStageChanged.connect(self.currentStageChanged)
        self._runner.progressChanged.connect(self.progressChanged)
        self._runner.startTimeChanged.connect(self.startTimeChanged)
        self._runner.elapsedChanged.connect(self.elapsedChanged)
        self._runner.exitCodeChanged.connect(self.exitCodeChanged)
        self._runner.failureChanged.connect(self.failureChanged)
        self._runner.configurationChanged.connect(self.configurationChanged)
        self._runner.rawOutputReceived.connect(self.rawOutputReceived)
        self._runner.outputReceived.connect(self.outputReceived)
        self._runner.runStarted.connect(self.runStarted)
        self._runner.runFinished.connect(self.runFinished)

    @Property(str, notify=stateChanged)
    def state(self):
        return self._runner.status

    status = Property(str, lambda self: self._runner.status, notify=statusChanged)
    currentStage = Property(str, lambda self: self._runner.currentStage, notify=currentStageChanged)
    stageDescription = Property(
        str, lambda self: self._runner.stageDescription, notify=currentStageChanged
    )
    stageNumber = Property(int, lambda self: self._runner.stageNumber, notify=currentStageChanged)
    stageCount = Property(int, lambda self: self._runner.stageCount, notify=configurationChanged)
    progress = Property(int, lambda self: self._runner.progress, notify=progressChanged)
    startTime = Property(str, lambda self: self._runner.startTime, notify=startTimeChanged)
    elapsedSeconds = Property(int, lambda self: self._runner.elapsedSeconds, notify=elapsedChanged)
    elapsed = Property(str, lambda self: self._runner.elapsed, notify=elapsedChanged)
    exitCode = Property(int, lambda self: self._runner.exitCode, notify=exitCodeChanged)
    failed = Property(bool, lambda self: self._runner.failed, notify=failureChanged)
    failureMessage = Property(str, lambda self: self._runner.failureMessage, notify=failureChanged)
    running = Property(bool, lambda self: self._runner.running, notify=statusChanged)
    configured = Property(bool, lambda self: self._runner.configured, notify=configurationChanged)

    @Property(str, notify=statusChanged)
    def statusTone(self) -> str:
        tones = {
            "Running": "active",
            "Starting": "active",
            "Paused": "review",
            "Cancelling": "review",
            "Completed": "pass",
            "Failed": "fail",
            "Cancelled": "neutral",
        }
        return tones.get(self._runner.status, "neutral")

    @Property(bool, notify=stateChanged)
    def paused(self):
        return self._runner.status == "Paused"

    @Slot(result=bool)
    def start(self) -> bool:
        return self._runner.start()

    @Slot()
    def pause(self):
        self._runner.pause()

    @Slot()
    def resume(self):
        if self._runner.status == "Paused":
            self._runner.resume()
        elif not self._runner.running:
            self._runner.start()

    @Slot()
    def stop(self):
        self._runner.cancel()

    @Slot()
    def cancel(self):
        self._runner.cancel()

    @Slot()
    def shutdown(self):
        self._runner.shutdown()

    def configure(self, configuration: FlowConfiguration | Sequence[FlowCommand]) -> None:
        self._runner.configure(configuration)

    def _forward_status(self) -> None:
        self.stateChanged.emit()
        self.statusChanged.emit()
