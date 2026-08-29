from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from .prompt_builder import PromptBuilder
from .schemas import (
    Confidence,
    DiagnosisContext,
    DiagnosisHistoryEntry,
    DiagnosisResult,
    KNOWN_STAGES,
)


class DiagnosisProvider(Protocol):
    provider_id: str

    def diagnose(
        self,
        context: DiagnosisContext,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> DiagnosisResult | Mapping[str, Any]: ...


class DiagnosisValidationError(ValueError):
    pass


class DiagnosisResultValidator:
    """Rejects output that exceeds the read-only deterministic boundary."""

    FORBIDDEN_CLAIMS = (
        re.compile(r"\b(?:i|we)\s+(?:changed|modified|edited|updated|wrote|deleted|applied|restarted|reran|re-ran|executed)\b", re.I),
        re.compile(r"\b(?:files?|rtl|tcl|constraints?|configuration)\s+(?:was|were|have\s+been)\s+(?:changed|modified|edited|updated)\b", re.I),
        re.compile(r"\b(?:apply\s+(?:the\s+)?fix|auto(?:matic)?\s*fix|execute\s+(?:this|the)\s+command|restart\s+the\s+flow|rerun\s+the\s+flow)\b", re.I),
    )
    SIGNOFF_OVERRIDE = (
        re.compile(r"\b(?:override|ignore|bypass)\b.*\b(?:gate|signoff|drc|lvs|sta)\b", re.I),
        re.compile(r"\b(?:gate|signoff|drc|lvs|sta)\b.*\b(?:incorrect|wrong|should\s+(?:pass|fail))\b", re.I),
        re.compile(r"\bfinal\s+verdict\b", re.I),
    )
    METRIC_TOKENS = {
        "wns": re.compile(r"\bwns\b|worst\s+negative\s+slack", re.I),
        "tns": re.compile(r"\btns\b|total\s+negative\s+slack", re.I),
        "area": re.compile(r"\barea\b", re.I),
        "power": re.compile(r"\bpower\b", re.I),
        "utilization": re.compile(r"\b(?:utilization|density)\b", re.I),
        "total_congestion": re.compile(r"\btotal\s+congestion\b", re.I),
        "peak_congestion": re.compile(r"\bpeak\s+congestion\b", re.I),
        "drc_violations": re.compile(r"\bdrc\s+violations?\b", re.I),
        "lvs_status": re.compile(r"\blvs\b", re.I),
    }

    def validate(
        self,
        raw: DiagnosisResult | Mapping[str, Any],
        context: DiagnosisContext,
    ) -> DiagnosisResult:
        try:
            result = raw if isinstance(raw, DiagnosisResult) else DiagnosisResult.from_mapping(raw)
        except (KeyError, TypeError, ValueError) as exc:
            raise DiagnosisValidationError(str(exc)) from exc

        failures = {item.category: item for item in context.detected_failures}
        if result.primary_failure not in failures:
            raise DiagnosisValidationError("Diagnosis references a nonexistent failure")
        deterministic = failures[result.primary_failure]
        if result.root_cause_stage not in KNOWN_STAGES or not result.root_cause_stage:
            raise DiagnosisValidationError("Diagnosis references an invalid stage")
        if result.root_cause_stage != deterministic.earliest_implicated_stage:
            raise DiagnosisValidationError("Diagnosis root stage conflicts with deterministic classification")

        evidence_ids = {item.evidence_id for item in context.evidence}
        if not result.evidence_references or any(item not in evidence_ids for item in result.evidence_references):
            raise DiagnosisValidationError("Diagnosis references nonexistent evidence")

        factual_text = " ".join((result.summary, *result.contributing_factors))
        all_text = " ".join((
            result.summary,
            *result.contributing_factors,
            *result.recommended_checks,
            *result.limitations,
        ))
        if any(pattern.search(all_text) for pattern in self.FORBIDDEN_CLAIMS):
            raise DiagnosisValidationError("Diagnosis claims or requests a prohibited write/action")
        if any(pattern.search(all_text) for pattern in self.SIGNOFF_OVERRIDE):
            raise DiagnosisValidationError("Diagnosis attempts to override deterministic signoff")

        unavailable = {item.name for item in context.metrics if item.value is None}
        for name in unavailable:
            pattern = self.METRIC_TOKENS.get(name)
            if pattern and pattern.search(factual_text) and not re.search(
                rf"(?:{pattern.pattern}).{{0,32}}\b(?:unavailable|unknown|not\s+observed|not\s+run)\b",
                factual_text,
                re.I,
            ):
                raise DiagnosisValidationError(f"Diagnosis invents unavailable metric '{name}'")

        return DiagnosisResult(
            summary=result.summary[:1000],
            primary_failure=result.primary_failure,
            root_cause_stage=result.root_cause_stage,
            confidence=result.confidence,
            evidence_references=tuple(result.evidence_references[:24]),
            contributing_factors=tuple(item[:400] for item in result.contributing_factors[:12]),
            recommended_checks=tuple(item[:400] for item in result.recommended_checks[:12]),
            limitations=tuple(item[:400] for item in result.limitations[:12]),
            generated_at=result.generated_at,
        )


class MockDiagnosisProvider:
    """Deterministic provider used by tests and offline demonstrations."""

    provider_id = "mock-diagnosis-v1"

    def __init__(
        self,
        response: DiagnosisResult | Mapping[str, Any] | None = None,
        *,
        delay_seconds: float = 0.0,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.delay_seconds = delay_seconds
        self.error = error
        self.calls = 0
        self.last_system_prompt = ""
        self.last_user_prompt = ""

    def diagnose(
        self,
        context: DiagnosisContext,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> DiagnosisResult | Mapping[str, Any]:
        self.calls += 1
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        if self.delay_seconds:
            time.sleep(self.delay_seconds)
        if self.error:
            raise self.error
        if self.response is not None:
            return self.response
        primary = context.detected_failures[0]
        factors = tuple(item.description for item in context.detected_failures[1:4])
        checks = self._checks(primary.category)
        return DiagnosisResult(
            summary=primary.description,
            primary_failure=primary.category,
            root_cause_stage=primary.earliest_implicated_stage,
            confidence=Confidence.HIGH if len(primary.evidence_ids) >= 2 else Confidence.MEDIUM,
            evidence_references=primary.evidence_ids or (context.evidence[0].evidence_id,),
            contributing_factors=factors,
            recommended_checks=checks,
            limitations=("Read-only explanation; deterministic verification gates remain authoritative.",),
        )

    @staticmethod
    def _checks(category: str) -> tuple[str, ...]:
        checks = {
            "TIMING_SETUP": (
                "Inspect the earliest failing timing paths and their stage-local reports.",
                "Review placement density and congestion along the critical paths.",
            ),
            "ROUTING_CONGESTION": (
                "Inspect the highest-congestion regions and unrouted-net evidence.",
                "Compare placement and routing congestion histories.",
            ),
            "DRC_FAILURE": ("Inspect the deterministic DRC report and group violations by rule and region.",),
            "LVS_MISMATCH": ("Inspect the LVS report for the first mismatched net or device class.",),
        }
        return checks.get(category, ("Inspect the cited stage evidence and corresponding generated reports.",))


class DiagnosisService(QObject):
    diagnosisStarted = Signal(str)
    diagnosisAvailable = Signal(object, str, str)
    diagnosisUnavailable = Signal(str)
    diagnosisError = Signal(str)
    noDiagnosis = Signal()
    _workerCompleted = Signal(object, str, str, str)

    def __init__(self, provider: DiagnosisProvider | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._provider = provider
        self._prompt_builder = PromptBuilder()
        self._validator = DiagnosisResultValidator()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="rtl2gds-diagnosis")
        self._cache: dict[str, tuple[DiagnosisResult, str]] = {}
        self._history: list[DiagnosisHistoryEntry] = []
        self._latest_fingerprint = ""
        self._inflight: set[str] = set()
        self._shutting_down = False
        self._workerCompleted.connect(self._handle_worker_completed)

    @property
    def provider_id(self) -> str:
        return getattr(self._provider, "provider_id", "unavailable")

    def request(self, context: DiagnosisContext) -> str:
        if not context.detected_failures:
            self.noDiagnosis.emit()
            return ""
        fingerprint = context.fingerprint()
        self._latest_fingerprint = fingerprint
        if fingerprint in self._cache:
            result, provider_id = self._cache[fingerprint]
            QTimer.singleShot(0, lambda: self.diagnosisAvailable.emit(result, fingerprint, provider_id))
            return fingerprint
        if self._provider is None:
            QTimer.singleShot(0, lambda: self.diagnosisUnavailable.emit("AI diagnosis unavailable"))
            return fingerprint
        if fingerprint in self._inflight:
            return fingerprint
        self._inflight.add(fingerprint)
        self.diagnosisStarted.emit(fingerprint)
        system_prompt, user_prompt = self._prompt_builder.build(context)
        self._executor.submit(
            self._run_provider,
            context,
            fingerprint,
            system_prompt,
            user_prompt,
        )
        return fingerprint

    def _run_provider(
        self,
        context: DiagnosisContext,
        fingerprint: str,
        system_prompt: str,
        user_prompt: str,
    ) -> None:
        try:
            raw = self._provider.diagnose(
                context,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            result = self._validator.validate(raw, context)
        except DiagnosisValidationError as exc:
            self._workerCompleted.emit(None, fingerprint, "unavailable", str(exc))
            return
        except Exception as exc:
            self._workerCompleted.emit(None, fingerprint, "error", str(exc))
            return
        self._workerCompleted.emit((result, context), fingerprint, "available", self.provider_id)

    @Slot(object, str, str, str)
    def _handle_worker_completed(self, payload: object, fingerprint: str, status: str, detail: str) -> None:
        self._inflight.discard(fingerprint)
        if self._shutting_down or fingerprint != self._latest_fingerprint:
            return
        if status == "unavailable":
            self.diagnosisUnavailable.emit("Diagnosis unavailable")
            return
        if status == "error":
            self.diagnosisError.emit("Diagnosis provider error")
            return
        result, context = payload
        self._cache[fingerprint] = (result, detail)
        self._history.append(DiagnosisHistoryEntry(
            timestamp=datetime.now(timezone.utc),
            fingerprint=fingerprint,
            detected_failures=tuple(item.category for item in context.detected_failures),
            root_cause_stage=result.root_cause_stage,
            result=result,
            provider_id=detail,
        ))
        self.diagnosisAvailable.emit(result, fingerprint, detail)

    def history_snapshot(self) -> tuple[DiagnosisHistoryEntry, ...]:
        return tuple(self._history)

    @Slot()
    def reset_run(self) -> None:
        self._latest_fingerprint = ""
        self._cache.clear()
        self._history.clear()

    @Slot()
    def shutdown(self) -> None:
        self._shutting_down = True
        self._executor.shutdown(wait=False, cancel_futures=True)
