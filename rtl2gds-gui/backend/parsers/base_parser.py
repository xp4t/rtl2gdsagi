from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TypeAlias


MetricValue: TypeAlias = float | int | str | bool


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_stage(stage: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", stage.strip().lower()).strip("_")
    return {"place": "placement", "route": "routing"}.get(value, value or "unknown")


@dataclass(frozen=True, slots=True)
class MetricUpdate:
    name: str
    value: MetricValue
    unit: str
    stage: str
    source: str
    timestamp: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class StageUpdate:
    stage: str
    status: str
    runtime_seconds: float | None = None
    source: str = "flow"
    timestamp: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class ArtifactUpdate:
    artifact_type: str
    path: str
    stage: str
    source: str
    timestamp: datetime = field(default_factory=utc_now)


NormalizedEvent: TypeAlias = MetricUpdate | StageUpdate | ArtifactUpdate


NUMBER_PATTERN = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"


class BaseParser:
    """A fault-isolating line parser that never propagates malformed output."""

    source = "unknown"
    stage_keywords: tuple[str, ...] = ()

    def supports_stage(self, stage: str) -> bool:
        if not self.stage_keywords:
            return True
        normalized = normalize_stage(stage)
        return any(keyword in normalized for keyword in self.stage_keywords)

    def parse(self, line: str, stage: str, stream: str = "stdout") -> list[NormalizedEvent]:
        if not isinstance(line, str) or not line.strip():
            return []
        try:
            return self.parse_line(line, normalize_stage(stage), stream)
        except (ArithmeticError, IndexError, TypeError, ValueError):
            return []

    def parse_line(self, line: str, stage: str, stream: str) -> list[NormalizedEvent]:
        return []

    def metric(
        self,
        name: str,
        value: MetricValue,
        unit: str,
        stage: str,
        *,
        source: str | None = None,
    ) -> MetricUpdate:
        return MetricUpdate(
            name=name,
            value=value,
            unit=unit,
            stage=stage,
            source=source or self.source,
        )

    @staticmethod
    def first_number(patterns: tuple[re.Pattern[str], ...], line: str) -> tuple[float, str] | None:
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                unit = match.groupdict().get("unit") or ""
                return float(match.group("value")), unit
        return None


def parse_duration(value: str, unit: str = "") -> float | None:
    try:
        if ":" in value:
            parts = [float(part) for part in value.split(":")]
            if len(parts) == 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
            if len(parts) == 2:
                return parts[0] * 60 + parts[1]
            return None
        seconds = float(value)
        normalized_unit = unit.lower()
        if normalized_unit.startswith("ms"):
            return seconds / 1000
        if normalized_unit.startswith("min"):
            return seconds * 60
        return seconds
    except (TypeError, ValueError):
        return None
