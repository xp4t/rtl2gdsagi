from __future__ import annotations

import codecs
import os
import signal
from collections.abc import Sequence

from PySide6.QtCore import (
    QDateTime,
    QElapsedTimer,
    QObject,
    Property,
    QProcess,
    QProcessEnvironment,
    QTimer,
    Signal,
    Slot,
)

from .flow_config import FlowCommand, FlowConfiguration


class FlowRunner(QObject):
    """Asynchronous, sequential QProcess runner for configured EDA stages."""

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

    ACTIVE_STATUSES = frozenset({"Starting", "Running", "Paused", "Cancelling"})

    def __init__(
        self,
        configuration: FlowConfiguration | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._configuration = configuration or FlowConfiguration()
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.SeparateChannels)
        self._process.started.connect(self._handle_started)
        self._process.readyReadStandardOutput.connect(self._read_stdout)
        self._process.readyReadStandardError.connect(self._read_stderr)
        self._process.errorOccurred.connect(self._handle_error)
        self._process.finished.connect(self._handle_finished)

        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(250)
        self._elapsed_timer.timeout.connect(self._update_elapsed)
        self._clock = QElapsedTimer()

        self._status = "Idle"
        self._current_stage = ""
        self._current_description = ""
        self._current_stage_number = 0
        self._progress = 0
        self._start_time = "—"
        self._elapsed_seconds = 0
        self._exit_code = -1
        self._failed = False
        self._failure_message = ""
        self._command_index = -1
        self._cancel_requested = False
        self._shutdown_requested = False
        self._terminal_emitted = False
        self._stream_buffers = {"stdout": "", "stderr": ""}
        self._decoders = self._new_decoders()

    @staticmethod
    def _new_decoders():
        decoder = codecs.getincrementaldecoder("utf-8")
        return {"stdout": decoder(errors="replace"), "stderr": decoder(errors="replace")}

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @Property(str, notify=currentStageChanged)
    def currentStage(self) -> str:
        return self._current_stage

    @Property(str, notify=currentStageChanged)
    def stageDescription(self) -> str:
        return self._current_description

    @Property(int, notify=currentStageChanged)
    def stageNumber(self) -> int:
        return self._current_stage_number

    @Property(int, notify=configurationChanged)
    def stageCount(self) -> int:
        return self._configuration.total_stages

    @Property(int, notify=progressChanged)
    def progress(self) -> int:
        return self._progress

    @Property(str, notify=startTimeChanged)
    def startTime(self) -> str:
        return self._start_time

    @Property(int, notify=elapsedChanged)
    def elapsedSeconds(self) -> int:
        return self._elapsed_seconds

    @Property(str, notify=elapsedChanged)
    def elapsed(self) -> str:
        hours, remainder = divmod(self._elapsed_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @Property(int, notify=exitCodeChanged)
    def exitCode(self) -> int:
        return self._exit_code

    @Property(bool, notify=failureChanged)
    def failed(self) -> bool:
        return self._failed

    @Property(str, notify=failureChanged)
    def failureMessage(self) -> str:
        return self._failure_message

    @Property(bool, notify=statusChanged)
    def running(self) -> bool:
        return self._status in self.ACTIVE_STATUSES

    @Property(bool, notify=configurationChanged)
    def configured(self) -> bool:
        return bool(self._configuration.commands)

    def configure(
        self,
        configuration: FlowConfiguration | Sequence[FlowCommand],
    ) -> None:
        if self.running:
            raise RuntimeError("Cannot replace flow configuration while a process is active")
        if isinstance(configuration, FlowConfiguration):
            self._configuration = configuration
        else:
            self._configuration = FlowConfiguration(commands=tuple(configuration))
        self.configurationChanged.emit()
        self._reset_execution_state()

    @Slot(result=bool)
    def start(self) -> bool:
        if self.running:
            return False
        if not self._configuration.commands:
            self._set_failure(True, "No flow commands are configured.")
            self._set_status("Failed")
            return False

        self._shutdown_requested = False
        self._cancel_requested = False
        self._terminal_emitted = False
        self._command_index = -1
        self._set_progress(0)
        self._set_exit_code(-1)
        self._set_failure(False, "")
        self._set_start_time(QDateTime.currentDateTime().toString("MMM d HH:mm:ss"))
        self._elapsed_seconds = 0
        self.elapsedChanged.emit()
        self._clock.start()
        self._elapsed_timer.start()
        self.runStarted.emit()
        self._launch_next_command()
        return True

    @Slot()
    def cancel(self) -> None:
        if not self.running or self._status == "Cancelling":
            return
        self._cancel_requested = True
        if self._status == "Paused":
            self._resume_process()
        self._set_status("Cancelling")
        self._process.terminate()
        QTimer.singleShot(3000, self._force_kill)

    @Slot()
    def pause(self) -> None:
        if self._status != "Running" or os.name != "posix":
            return
        try:
            os.kill(self._process.processId(), signal.SIGSTOP)
        except (OSError, ProcessLookupError):
            return
        self._set_status("Paused")

    @Slot()
    def resume(self) -> None:
        if self._status == "Paused":
            self._resume_process()

    @Slot()
    def shutdown(self) -> None:
        """Request immediate child teardown without waiting on the GUI thread."""

        self._shutdown_requested = True
        self._elapsed_timer.stop()
        if self._process.state() != QProcess.NotRunning:
            self._cancel_requested = True
            if self._status == "Paused":
                self._resume_process()
            self._set_status("Cancelling")
            self._process.kill()

    def _reset_execution_state(self) -> None:
        self._command_index = -1
        self._set_status("Idle")
        self._set_current_command(None)
        self._set_progress(0)
        self._set_start_time("—")
        self._elapsed_seconds = 0
        self.elapsedChanged.emit()
        self._set_exit_code(-1)
        self._set_failure(False, "")

    def _launch_next_command(self) -> None:
        self._command_index += 1
        command = self._configuration.commands[self._command_index]
        self._set_current_command(command)
        self._stream_buffers = {"stdout": "", "stderr": ""}
        self._decoders = self._new_decoders()

        environment = QProcessEnvironment.systemEnvironment()
        for key, value in command.environment.items():
            environment.insert(key, value)
        self._process.setProcessEnvironment(environment)
        self._process.setWorkingDirectory(command.working_directory or "")
        self._process.setProgram(command.program)
        self._process.setArguments(list(command.arguments))
        self._set_status("Starting")
        self._process.start()

    def _handle_started(self) -> None:
        self._set_status("Running")

    def _read_stdout(self) -> None:
        self._drain_stream("stdout", bytes(self._process.readAllStandardOutput()))

    def _read_stderr(self) -> None:
        self._drain_stream("stderr", bytes(self._process.readAllStandardError()))

    def _drain_stream(self, stream: str, data: bytes = b"", *, final: bool = False) -> None:
        text = self._decoders[stream].decode(data, final=final)
        if text:
            self.rawOutputReceived.emit(stream, text)
            self._stream_buffers[stream] += text

        buffer = self._stream_buffers[stream]
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            self.outputReceived.emit(stream, line.rstrip("\r"))
        if final and buffer:
            self.outputReceived.emit(stream, buffer.rstrip("\r"))
            buffer = ""
        self._stream_buffers[stream] = buffer

    def _drain_all(self, *, final: bool) -> None:
        self._drain_stream("stdout", bytes(self._process.readAllStandardOutput()), final=final)
        self._drain_stream("stderr", bytes(self._process.readAllStandardError()), final=final)

    def _handle_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        if self._terminal_emitted:
            return
        self._drain_all(final=True)

        if self._cancel_requested:
            self._set_exit_code(exit_code)
            self._finish_run("Cancelled", failed=False)
            return

        if exit_status == QProcess.CrashExit or exit_code != 0:
            message = f"Stage '{self._current_stage}' exited with code {exit_code}."
            self._set_exit_code(exit_code)
            self._set_failure(True, message)
            self._finish_run("Failed", failed=True)
            return

        completed = self._command_index + 1
        self._set_progress(round(completed * 100 / len(self._configuration.commands)))
        if completed < len(self._configuration.commands):
            self._launch_next_command()
            return

        self._set_exit_code(0)
        self._finish_run("Completed", failed=False)

    def _handle_error(self, process_error: QProcess.ProcessError) -> None:
        if self._cancel_requested:
            return
        if process_error != QProcess.FailedToStart or self._terminal_emitted:
            return
        self._drain_all(final=True)
        message = self._process.errorString() or f"Unable to start '{self._process.program()}'."
        self._set_exit_code(-1)
        self._set_failure(True, message)
        self._finish_run("Failed", failed=True)

    def _finish_run(self, status: str, *, failed: bool) -> None:
        self._terminal_emitted = True
        self._elapsed_timer.stop()
        self._update_elapsed()
        self._set_failure(failed, self._failure_message if failed else "")
        self._set_status(status)
        self.runFinished.emit()

    def _force_kill(self) -> None:
        if self._cancel_requested and self._process.state() != QProcess.NotRunning:
            self._process.kill()

    def _resume_process(self) -> None:
        if os.name != "posix":
            return
        try:
            os.kill(self._process.processId(), signal.SIGCONT)
        except (OSError, ProcessLookupError):
            return
        if not self._cancel_requested:
            self._set_status("Running")

    def _update_elapsed(self) -> None:
        if not self._clock.isValid():
            return
        value = self._clock.elapsed() // 1000
        if value != self._elapsed_seconds:
            self._elapsed_seconds = value
            self.elapsedChanged.emit()

    def _set_status(self, value: str) -> None:
        if value != self._status:
            self._status = value
            self.statusChanged.emit()

    def _set_current_command(self, command: FlowCommand | None) -> None:
        if command is None:
            stage, description, number = "", "", 0
        else:
            stage = command.stage
            description = command.description
            number = command.stage_number or self._command_index + 1
        if (
            stage != self._current_stage
            or description != self._current_description
            or number != self._current_stage_number
        ):
            self._current_stage = stage
            self._current_description = description
            self._current_stage_number = number
            self.currentStageChanged.emit()

    def _set_progress(self, value: int) -> None:
        value = max(0, min(100, value))
        if value != self._progress:
            self._progress = value
            self.progressChanged.emit()

    def _set_start_time(self, value: str) -> None:
        if value != self._start_time:
            self._start_time = value
            self.startTimeChanged.emit()

    def _set_exit_code(self, value: int) -> None:
        if value != self._exit_code:
            self._exit_code = value
            self.exitCodeChanged.emit()

    def _set_failure(self, failed: bool, message: str) -> None:
        if failed != self._failed or message != self._failure_message:
            self._failed = failed
            self._failure_message = message
            self.failureChanged.emit()
