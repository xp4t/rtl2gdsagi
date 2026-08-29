from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot

from ..run_model import DictListModel
from .schemas import DiagnosisContext, DiagnosisEvidence, DiagnosisResult


class DiagnosisModel(QObject):
    """Read-only Qt presentation state for validated diagnoses."""

    changed = Signal()

    STATES = frozenset({"NO_DIAGNOSIS", "ANALYZING", "AVAILABLE", "UNAVAILABLE", "ERROR"})

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._state = "NO_DIAGNOSIS"
        self._message = "No diagnosis available. Diagnosis becomes available when a failure is detected."
        self._summary = ""
        self._primary_failure = ""
        self._root_cause_stage = ""
        self._confidence = ""
        self._provider_id = ""
        self._fingerprint = ""
        self._contributing_factors: list[str] = []
        self._recommended_checks: list[str] = []
        self._limitations: list[str] = []
        self._context: DiagnosisContext | None = None
        self._has_failures = False
        self._evidence = DictListModel(
            [], self,
            role_names=["evidenceType", "name", "value", "stage", "source", "detail", "tone"],
        )
        self._history = DictListModel(
            [], self,
            role_names=["timestamp", "fingerprint", "failures", "rootCause", "provider"],
        )

    state = Property(str, lambda self: self._state, notify=changed)
    message = Property(str, lambda self: self._message, notify=changed)
    summary = Property(str, lambda self: self._summary, notify=changed)
    primaryFailure = Property(str, lambda self: self._display(self._primary_failure), notify=changed)
    primaryFailureCode = Property(str, lambda self: self._primary_failure, notify=changed)
    rootCauseStage = Property(str, lambda self: self._display(self._root_cause_stage), notify=changed)
    rootCauseStageCode = Property(str, lambda self: self._root_cause_stage, notify=changed)
    confidence = Property(str, lambda self: self._confidence, notify=changed)
    providerId = Property(str, lambda self: self._provider_id, notify=changed)
    fingerprint = Property(str, lambda self: self._fingerprint, notify=changed)
    contributingFactors = Property("QStringList", lambda self: list(self._contributing_factors), notify=changed)
    recommendedChecks = Property("QStringList", lambda self: list(self._recommended_checks), notify=changed)
    limitations = Property("QStringList", lambda self: list(self._limitations), notify=changed)
    hasFailures = Property(bool, lambda self: self._has_failures, notify=changed)
    evidenceModel = Property(QObject, lambda self: self._evidence, constant=True)
    historyModel = Property(QObject, lambda self: self._history, constant=True)

    @Property(bool, notify=changed)
    def analyzing(self) -> bool:
        return self._state == "ANALYZING"

    @Property(bool, notify=changed)
    def available(self) -> bool:
        return self._state == "AVAILABLE"

    def set_context(self, context: DiagnosisContext) -> None:
        changed_snapshot = bool(self._fingerprint and self._fingerprint != context.fingerprint())
        self._context = context
        self._has_failures = bool(context.detected_failures)
        if not self._has_failures:
            self.set_no_diagnosis()
        elif changed_snapshot and self._state == "AVAILABLE":
            self.set_no_diagnosis()
        else:
            self.changed.emit()

    @Slot()
    def reset(self) -> None:
        self._context = None
        self._history.clear_rows()
        self.set_no_diagnosis()

    @Slot()
    def set_no_diagnosis(self) -> None:
        self._state = "NO_DIAGNOSIS"
        self._message = "No diagnosis available. Diagnosis becomes available when a failure is detected."
        self._clear_result()
        self._has_failures = bool(self._context and self._context.detected_failures)
        self.changed.emit()

    @Slot(str)
    def set_analyzing(self, fingerprint: str) -> None:
        self._state = "ANALYZING"
        self._message = "Analyzing deterministic failure evidence…"
        self._fingerprint = fingerprint
        self._clear_result(keep_fingerprint=True)
        self.changed.emit()

    @Slot(object, str, str)
    def set_available(self, result: object, fingerprint: str, provider_id: str) -> None:
        if not isinstance(result, DiagnosisResult) or self._context is None:
            self.set_unavailable("Diagnosis unavailable")
            return
        self._state = "AVAILABLE"
        self._message = "Read-only analysis — no changes have been applied."
        self._summary = result.summary
        self._primary_failure = result.primary_failure
        self._root_cause_stage = result.root_cause_stage
        self._confidence = result.confidence.value
        self._provider_id = provider_id
        self._fingerprint = fingerprint
        self._contributing_factors = list(result.contributing_factors)
        self._recommended_checks = list(result.recommended_checks)
        self._limitations = list(result.limitations)
        evidence_map = {item.evidence_id: item for item in self._context.evidence}
        self._evidence.replace_rows([
            self._evidence_row(evidence_map[evidence_id])
            for evidence_id in result.evidence_references
            if evidence_id in evidence_map
        ])
        self._history.append_row({
            "timestamp": result.generated_at.astimezone().strftime("%H:%M:%S"),
            "fingerprint": fingerprint,
            "failures": ", ".join(item.category for item in self._context.detected_failures),
            "rootCause": result.root_cause_stage,
            "provider": provider_id,
        })
        self.changed.emit()

    @Slot(str)
    def set_unavailable(self, message: str = "AI diagnosis unavailable") -> None:
        self._state = "UNAVAILABLE"
        self._message = message or "AI diagnosis unavailable"
        self._clear_result()
        self.changed.emit()

    @Slot(str)
    def set_error(self, message: str = "Diagnosis provider error") -> None:
        self._state = "ERROR"
        self._message = message or "Diagnosis provider error"
        self._clear_result()
        self.changed.emit()

    def context(self) -> DiagnosisContext | None:
        return self._context

    def _clear_result(self, *, keep_fingerprint: bool = False) -> None:
        self._summary = ""
        self._primary_failure = ""
        self._root_cause_stage = ""
        self._confidence = ""
        self._provider_id = ""
        if not keep_fingerprint:
            self._fingerprint = ""
        self._contributing_factors = []
        self._recommended_checks = []
        self._limitations = []
        self._evidence.clear_rows()

    @staticmethod
    def _display(value: str) -> str:
        return value.replace("_", " ").title() if value else "—"

    @staticmethod
    def _evidence_row(item: DiagnosisEvidence) -> dict:
        if item.value is None:
            value = "UNAVAILABLE"
        elif isinstance(item.value, bool):
            value = "AVAILABLE" if item.value else "MISSING"
        else:
            value = str(item.value) + (f" {item.unit}" if item.unit and item.unit not in {"status", "exists"} else "")
        tone = "fail" if item.evidence_type in {"stage_status", "signoff_gate", "missing_data"} else "review"
        return {
            "evidenceType": item.evidence_type.upper(),
            "name": item.name.replace("_", " ").upper(),
            "value": value,
            "stage": item.stage.replace("_", " ").upper(),
            "source": item.source,
            "detail": item.detail,
            "tone": tone,
        }
