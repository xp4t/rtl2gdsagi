from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Availability(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_RUN = "NOT_RUN"
    UNKNOWN = "UNKNOWN"


class Confidence(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Severity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    FAIL = "FAIL"
    CRITICAL = "CRITICAL"


STAGE_ORDER = (
    "import_rtl",
    "elaborate_design",
    "synthesis_logic",
    "sta_pre_cts",
    "floorplan",
    "power_plan_tap",
    "placement",
    "cts",
    "post_cts_sta",
    "routing",
    "signoff_sta",
    "drc",
    "lvs",
    "gds_packaging",
)
KNOWN_STAGES = frozenset(STAGE_ORDER) | {"unknown", ""}


@dataclass(frozen=True, slots=True)
class MetricFact:
    name: str
    value: float | int | str | None
    unit: str
    availability: Availability
    stage: str = ""
    source: str = ""
    timestamp: str = ""


@dataclass(frozen=True, slots=True)
class MetricHistoryFact:
    name: str
    value: float | int | str
    unit: str
    stage: str
    source: str
    timestamp: str
    trend: str


@dataclass(frozen=True, slots=True)
class StageFact:
    stage: str
    status: str
    runtime_seconds: float | None
    source: str
    timestamp: str
    availability: Availability = Availability.AVAILABLE


@dataclass(frozen=True, slots=True)
class GateFact:
    name: str
    status: str
    availability: Availability


@dataclass(frozen=True, slots=True)
class ArtifactFact:
    artifact_type: str
    path: str
    stage: str
    timestamp: str
    exists: bool
    size_bytes: int
    source: str
    availability: Availability


@dataclass(frozen=True, slots=True)
class RuntimeSignal:
    category_hint: str
    stage: str
    message: str
    source: str
    timestamp: str


@dataclass(frozen=True, slots=True)
class DiagnosisEvidence:
    evidence_id: str
    evidence_type: str
    name: str
    value: float | int | str | bool | None
    unit: str
    stage: str
    source: str
    timestamp: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class DetectedFailure:
    failure_id: str
    category: str
    severity: Severity
    stage: str
    earliest_implicated_stage: str
    evidence_ids: tuple[str, ...]
    description: str


@dataclass(frozen=True, slots=True)
class DiagnosisContext:
    run_id: str
    current_stage: str
    failed_stage: str
    stage_statuses: tuple[StageFact, ...]
    metrics: tuple[MetricFact, ...]
    metric_history: tuple[MetricHistoryFact, ...]
    signoff_gates: tuple[GateFact, ...]
    artifacts: tuple[ArtifactFact, ...]
    runtime_signals: tuple[RuntimeSignal, ...]
    detected_failures: tuple[DetectedFailure, ...]
    evidence: tuple[DiagnosisEvidence, ...]
    unavailable_fields: tuple[str, ...]
    timestamp: datetime = field(default_factory=utc_now)

    def with_classification(
        self,
        failures: tuple[DetectedFailure, ...],
        evidence: tuple[DiagnosisEvidence, ...],
    ) -> "DiagnosisContext":
        return replace(self, detected_failures=failures, evidence=evidence)

    def to_dict(self, *, include_timestamp: bool = True) -> dict[str, Any]:
        value = _primitive(asdict(self))
        if not include_timestamp:
            value.pop("timestamp", None)
        return value

    def fingerprint(self) -> str:
        payload = {
            "run_id": self.run_id,
            "current_stage": self.current_stage,
            "failed_stage": self.failed_stage,
            "stages": [(item.stage, item.status) for item in self.stage_statuses],
            "metrics": [
                (item.name, item.value, item.unit, item.availability.value, item.stage, item.source)
                for item in self.metrics
                if item.name != "stage_runtime"
            ],
            "history": [
                (item.name, item.value, item.stage, item.source, item.trend)
                for item in self.metric_history
                if item.name != "stage_runtime"
            ],
            "gates": [(item.name, item.status) for item in self.signoff_gates],
            "artifacts": [
                (item.artifact_type, item.path, item.stage, item.exists, item.size_bytes)
                for item in self.artifacts
            ],
            "signals": [
                (item.category_hint, item.stage, item.message, item.source)
                for item in self.runtime_signals
            ],
            "failures": [
                (item.category, item.stage, item.earliest_implicated_stage, item.evidence_ids)
                for item in self.detected_failures
            ],
            "unavailable": self.unavailable_fields,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class DiagnosisResult:
    summary: str
    primary_failure: str
    root_cause_stage: str
    confidence: Confidence
    evidence_references: tuple[str, ...]
    contributing_factors: tuple[str, ...]
    recommended_checks: tuple[str, ...]
    limitations: tuple[str, ...]
    generated_at: datetime = field(default_factory=utc_now)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "DiagnosisResult":
        if not isinstance(value, Mapping):
            raise ValueError("Diagnosis result must be an object")
        confidence_value = str(value.get("confidence", "")).upper()
        try:
            confidence = Confidence(confidence_value)
        except ValueError as exc:
            raise ValueError("Diagnosis confidence must be LOW, MEDIUM, or HIGH") from exc

        def required_text(snake: str, camel: str) -> str:
            item = value.get(snake, value.get(camel))
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"Diagnosis field '{camel}' must be non-empty text")
            return item.strip()

        def text_tuple(snake: str, camel: str) -> tuple[str, ...]:
            item = value.get(snake, value.get(camel, ()))
            if not isinstance(item, (list, tuple)) or not all(isinstance(part, str) for part in item):
                raise ValueError(f"Diagnosis field '{camel}' must be a list of strings")
            return tuple(part.strip() for part in item if part.strip())

        return cls(
            summary=required_text("summary", "summary"),
            primary_failure=required_text("primary_failure", "primaryFailure"),
            root_cause_stage=required_text("root_cause_stage", "rootCauseStage"),
            confidence=confidence,
            evidence_references=text_tuple("evidence_references", "evidenceReferences"),
            contributing_factors=text_tuple("contributing_factors", "contributingFactors"),
            recommended_checks=text_tuple("recommended_checks", "recommendedChecks"),
            limitations=text_tuple("limitations", "limitations"),
        )

    def to_dict(self) -> dict[str, Any]:
        return _primitive(asdict(self))


@dataclass(frozen=True, slots=True)
class DiagnosisHistoryEntry:
    timestamp: datetime
    fingerprint: str
    detected_failures: tuple[str, ...]
    root_cause_stage: str
    result: DiagnosisResult
    provider_id: str


def _primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _primitive(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_primitive(item) for item in value]
    return value
