import os
import time

from PySide6.QtCore import QObject, Property, Signal, Slot

from .artifact_model import ArtifactModel
from .checkpoint_model import CheckpointModel
from .diagnosis import (
    DiagnosisModel,
    DiagnosisProvider,
    DiagnosisService,
    DiagnosisSnapshotBuilder,
    FailureClassifier,
    RuntimeEvidenceStore,
)
from .diagnosis.schemas import Severity
from .flow_controller import FlowController
from .log_model import LogModel
from .metrics_model import MetricsModel
from .parsers import ArtifactUpdate, MetricUpdate, ParserPipeline, StageUpdate
from .pipeline_model import PipelineModel
from .run_model import DictListModel, RunModel, RunState
from .strategy_model import StrategyModel


class AppController(QObject):
    currentPageChanged = Signal()

    def __init__(self, parent=None, *, diagnosis_provider: DiagnosisProvider | None = None):
        super().__init__(parent)
        self._current_page = "activeRun"
        self._diagnosis_ready = False
        self._parser_pipeline = ParserPipeline()
        self._runtime_evidence = RuntimeEvidenceStore()
        self._snapshot_builder = DiagnosisSnapshotBuilder()
        self._failure_classifier = FailureClassifier()
        self._metric_stage = ""
        self._stage_started_at: float | None = None
        self._run_state = RunState(self)
        self._pipeline = PipelineModel(self)
        self._metrics = MetricsModel(self)
        self._logs = LogModel(self)
        self._artifacts = ArtifactModel(self)
        self._flow = FlowController(
            config_path=os.environ.get("RTL2GDS_FLOW_CONFIG"),
            parent=self,
        )
        self._flow.runStarted.connect(self._begin_run)
        self._flow.runFinished.connect(self._flush_parser_output)
        self._flow.rawOutputReceived.connect(self._parse_process_output)
        self._flow.outputReceived.connect(self._append_process_output)
        self._flow.statusChanged.connect(self._sync_execution_state)
        self._flow.currentStageChanged.connect(self._sync_execution_state)
        self._flow.elapsedChanged.connect(self._sync_execution_state)
        self._flow.startTimeChanged.connect(self._sync_execution_state)
        self._metrics.metricsChanged.connect(self._sync_gates)
        self._runs = RunModel(self)
        self._checkpoints = CheckpointModel(self)
        self._strategies = StrategyModel(self)
        self._stage_tasks = DictListModel([
            {"code": "7.1", "name": "Init placement", "status": "Done", "duration": "00:01:12", "log": "place_init.log", "tone": "pass"},
            {"code": "7.2", "name": "Global placement", "status": "Done", "duration": "00:14:32", "log": "global_place.log", "tone": "pass"},
            {"code": "7.3", "name": "Legalization", "status": "Done", "duration": "00:07:45", "log": "legalize.log", "tone": "pass"},
            {"code": "7.4", "name": "Optimization (global)", "status": "Running", "duration": "00:15:25", "log": "opt_global.log", "tone": "active"},
            {"code": "7.5", "name": "Optimization (incremental)", "status": "Queued", "duration": "—", "log": "—", "tone": "neutral"},
            {"code": "7.6", "name": "Verify placement", "status": "Queued", "duration": "—", "log": "—", "tone": "neutral"},
        ], self)
        self._gates = DictListModel([
            {"label": "DRC", "status": "PENDING", "tone": "neutral"},
            {"label": "LVS", "status": "PENDING", "tone": "neutral"},
            {"label": "TIMING", "status": "PENDING", "tone": "neutral"},
            {"label": "POWER", "status": "PENDING", "tone": "neutral"},
            {"label": "AREA", "status": "PENDING", "tone": "neutral"},
        ], self)
        self._retune = DictListModel([
            {"parameter": "place_opt_effort", "current": "high", "proposed": "medium", "limits": "medium–very high", "tone": "pass"},
            {"parameter": "target_density", "current": "0.70", "proposed": "0.66", "limits": "0.60–0.75", "tone": "pass"},
            {"parameter": "max_displacement", "current": "0.20", "proposed": "0.30", "limits": "0.10–0.30", "tone": "pass"},
        ], self)
        self._comparison = DictListModel([
            {"metric": "WNS (ns)", "helper": "Higher is better", "before": "-1.324", "after": "-0.842", "delta": "+0.482", "tone": "pass"},
            {"metric": "TNS (ns)", "helper": "Higher is better", "before": "-12.78", "after": "-6.11", "delta": "+6.67", "tone": "pass"},
            {"metric": "TOTAL CONGESTION", "helper": "Lower is better", "before": "0.72", "after": "0.58", "delta": "-0.14", "tone": "pass"},
            {"metric": "PEAK CONGESTION", "helper": "Lower is better", "before": "0.92", "after": "0.71", "delta": "-0.21", "tone": "pass"},
            {"metric": "WIRELENGTH (m)", "helper": "Lower is better", "before": "184.6", "after": "191.8", "delta": "+7.2", "tone": "fail"},
            {"metric": "POWER (mW)", "helper": "Lower is better", "before": "125.7", "after": "128.9", "delta": "+3.2", "tone": "fail"},
        ], self)
        self._retune_regions = DictListModel([
            {"region": "R12", "location": "( 0.12, 0.34 )", "before": "0.89", "after": "0.66", "delta": "-0.23"},
            {"region": "R27", "location": "( 0.58, 0.71 )", "before": "0.84", "after": "0.63", "delta": "-0.21"},
            {"region": "R31", "location": "( 0.33, 0.82 )", "before": "0.81", "after": "0.62", "delta": "-0.19"},
            {"region": "R07", "location": "( 0.09, 0.56 )", "before": "0.76", "after": "0.59", "delta": "-0.17"},
            {"region": "R45", "location": "( 0.77, 0.28 )", "before": "0.74", "after": "0.58", "delta": "-0.16"},
        ], self)
        self._navigation = DictListModel([
            {"route": "activeRun", "label": "FLOW", "detail": "Overview", "icon": "flow", "group": 0, "available": True},
            {"route": "runHistory", "label": "RUNS", "detail": "History", "icon": "runs", "group": 0, "available": True},
            {"route": "newRun", "label": "DESIGNS", "detail": "Hierarchy", "icon": "designs", "group": 0, "available": True},
            {"route": "strategySweep", "label": "COMPARE", "detail": "Diff / Regress", "icon": "compare", "group": 0, "available": True},
            {"route": "retuneReview", "label": "REPORTS", "detail": "Metrics", "icon": "reports", "group": 0, "available": True},
            {"route": "checkpointRecovery", "label": "EVIDENCE", "detail": "Artifacts", "icon": "evidence", "group": 0, "available": True},
            {"route": "config", "label": "CONFIG", "detail": "Parameters", "icon": "config", "group": 1, "available": False},
            {"route": "humanReview", "label": "POLICIES", "detail": "Constraints", "icon": "policies", "group": 1, "available": True},
            {"route": "agents", "label": "AGENTS", "detail": "Claude Ops", "icon": "agents", "group": 1, "available": False},
            {"route": "integrations", "label": "INTEGRATIONS", "detail": "CI / Tools", "icon": "integrations", "group": 1, "available": False},
            {"route": "settings", "label": "SETTINGS", "detail": "Preferences", "icon": "settings", "group": 2, "available": False},
        ], self)
        self._diagnosis = DiagnosisModel(self)
        self._diagnosis_service = DiagnosisService(diagnosis_provider, self)
        self._diagnosis_service.diagnosisStarted.connect(self._diagnosis.set_analyzing)
        self._diagnosis_service.diagnosisAvailable.connect(self._diagnosis.set_available)
        self._diagnosis_service.diagnosisUnavailable.connect(self._diagnosis.set_unavailable)
        self._diagnosis_service.diagnosisError.connect(self._diagnosis.set_error)
        self._diagnosis_service.noDiagnosis.connect(self._diagnosis.set_no_diagnosis)
        self._diagnosis_ready = True
        self._sync_execution_state()
        self._sync_gates()

    @Property(str, notify=currentPageChanged)
    def currentPage(self):
        return self._current_page

    @Slot(str)
    def navigate(self, route):
        known_routes = {"activeRun", "retuneReview", "runHistory", "checkpointRecovery", "newRun", "humanReview", "strategySweep"}
        if route in known_routes and route != self._current_page:
            self._current_page = route
            if route == "activeRun":
                self._sync_execution_state()
            else:
                self._run_state.apply_context(route)
                self._pipeline.apply_context(route)
            self.currentPageChanged.emit()

    @Slot()
    def shutdown(self) -> None:
        self._diagnosis_service.shutdown()
        self._flow.shutdown()

    @Slot(str, str)
    def _append_process_output(self, stream: str, message: str) -> None:
        self._logs.appendProcessOutput(stream, self._flow.currentStage, message)
        signals = self._runtime_evidence.ingest(
            message,
            stage=self._flow.currentStage,
            source=stream,
        )
        if signals:
            self._refresh_diagnosis_context(auto=True)

    @Slot()
    def _begin_run(self) -> None:
        self._logs.clear()
        self._metrics.clear()
        self._artifacts.clear()
        self._parser_pipeline.reset()
        self._runtime_evidence.clear()
        self._diagnosis.reset()
        self._diagnosis_service.reset_run()
        self._metric_stage = ""
        self._stage_started_at = None

    @Slot(str, str)
    def _parse_process_output(self, stream: str, chunk: str) -> None:
        events = self._parser_pipeline.feed(
            chunk,
            stage=self._flow.currentStage,
            stream=stream,
        )
        for event in events:
            self.apply_normalized_event(event)

    @Slot()
    def _flush_parser_output(self) -> None:
        for event in self._parser_pipeline.flush():
            self.apply_normalized_event(event)
        self._refresh_diagnosis_context(auto=True)

    def apply_normalized_event(self, event: object) -> None:
        """Apply a parser/lifecycle event; also used for deterministic injection tests."""

        if isinstance(event, (MetricUpdate, StageUpdate)):
            self._metrics.applyEvent(event)
        elif isinstance(event, ArtifactUpdate):
            self._artifacts.applyEvent(event)

    @Slot()
    def _sync_execution_state(self) -> None:
        self._sync_metric_stage_state()
        if self._current_page != "activeRun":
            return
        self._run_state.apply_execution(
            status=self._flow.status,
            status_tone=self._flow.statusTone,
            elapsed=self._flow.elapsed,
            started=self._flow.startTime,
        )
        self._pipeline.apply_execution(
            self._flow.currentStage,
            self._flow.status,
            self._flow.stageNumber,
        )

    def _sync_metric_stage_state(self) -> None:
        stage = self._flow.currentStage
        now = time.monotonic()
        if stage != self._metric_stage:
            if self._metric_stage and self._stage_started_at is not None:
                self.apply_normalized_event(StageUpdate(
                    stage=self._metric_stage,
                    status="Completed",
                    runtime_seconds=now - self._stage_started_at,
                ))
            self._metric_stage = stage
            self._stage_started_at = now if stage else None
        runtime = now - self._stage_started_at if self._stage_started_at is not None else None
        self.apply_normalized_event(StageUpdate(
            stage=stage,
            status=self._flow.status,
            runtime_seconds=runtime,
        ))

    @Slot()
    def _sync_gates(self) -> None:
        drc = self._metrics.drcViolations
        lvs = self._metrics.lvsStatus
        wns = self._metrics.wns
        tns = self._metrics.tns
        updates = {
            "DRC": (
                ("PENDING", "neutral") if drc is None
                else (("PASS", "pass") if drc == 0 else ("FAIL", "fail"))
            ),
            "LVS": (
                ("PENDING", "neutral") if lvs == "unavailable"
                else (("PASS", "pass") if lvs == "pass" else ("FAIL", "fail"))
            ),
            "TIMING": (
                ("PENDING", "neutral") if wns is None and tns is None
                else (("PASS", "pass") if (wns is None or wns >= 0) and (tns is None or tns >= 0) else ("FAIL", "fail"))
            ),
            "POWER": (("OBSERVED", "active") if self._metrics.powerAvailable else ("PENDING", "neutral")),
            "AREA": (("OBSERVED", "active") if self._metrics.areaAvailable else ("PENDING", "neutral")),
        }
        for row_index, row in enumerate(self._gates._rows):
            status, tone = updates[row["label"]]
            if row["status"] != status or row["tone"] != tone:
                self._gates.update_row(row_index, {"status": status, "tone": tone})
        if self._diagnosis_ready:
            self._refresh_diagnosis_context(auto=True)

    def _build_diagnosis_context(self):
        context = self._snapshot_builder.build(
            run_id=str(self._run_state.execution_snapshot().get("run_id", "unknown")),
            metrics_snapshot=self._metrics.snapshot(),
            gate_rows=self._gates.rows_snapshot(),
            artifact_rows=self._artifacts.rows_snapshot(),
            runtime_signals=self._runtime_evidence.snapshot(),
        )
        return self._failure_classifier.classify(context)

    def _refresh_diagnosis_context(self, *, auto: bool) -> None:
        if not self._diagnosis_ready:
            return
        context = self._build_diagnosis_context()
        self._diagnosis.set_context(context)
        if not auto:
            self._diagnosis_service.request(context)
            return
        has_hard_failure = any(
            item.severity in {Severity.FAIL, Severity.CRITICAL}
            for item in context.detected_failures
        )
        gate_failed = any(row["status"] == "FAIL" for row in self._gates._rows)
        if has_hard_failure and (gate_failed or self._flow.status == "Failed"):
            self._diagnosis_service.request(context)

    @Slot()
    def analyzeFailure(self) -> None:
        self._refresh_diagnosis_context(auto=False)

    def diagnosis_context_snapshot(self):
        return self._build_diagnosis_context()

    runState = Property(QObject, lambda self: self._run_state, constant=True)
    flowController = Property(QObject, lambda self: self._flow, constant=True)
    pipelineModel = Property(QObject, lambda self: self._pipeline, constant=True)
    metricsModel = Property(QObject, lambda self: self._metrics, constant=True)
    logModel = Property(QObject, lambda self: self._logs, constant=True)
    runModel = Property(QObject, lambda self: self._runs, constant=True)
    checkpointModel = Property(QObject, lambda self: self._checkpoints, constant=True)
    strategyModel = Property(QObject, lambda self: self._strategies, constant=True)
    navigationModel = Property(QObject, lambda self: self._navigation, constant=True)
    stageTaskModel = Property(QObject, lambda self: self._stage_tasks, constant=True)
    gateModel = Property(QObject, lambda self: self._gates, constant=True)
    retuneModel = Property(QObject, lambda self: self._retune, constant=True)
    artifactModel = Property(QObject, lambda self: self._artifacts, constant=True)
    comparisonModel = Property(QObject, lambda self: self._comparison, constant=True)
    retuneRegionModel = Property(QObject, lambda self: self._retune_regions, constant=True)
    diagnosisModel = Property(QObject, lambda self: self._diagnosis, constant=True)
