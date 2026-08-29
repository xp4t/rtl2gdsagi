from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from numbers import Real

from PySide6.QtCore import Property, Signal, Slot

from .parsers import MetricUpdate, StageUpdate
from .run_model import DictListModel


class MetricsModel(DictListModel):
    """Normalized runtime metric state plus the existing seven-card view model."""

    metricsChanged = Signal()

    CARD_DEFINITIONS = (
        ("wns", "WNS (ns)"),
        ("tns", "TNS (ns)"),
        ("area", "AREA (µm²)"),
        ("utilization", "UTILIZATION"),
        ("total_congestion", "TOTAL CONG."),
        ("peak_congestion", "PEAK CONG."),
        ("power", "POWER (mW)"),
    )
    METRIC_NAMES = frozenset({
        "wns", "tns", "area", "power", "utilization", "total_congestion",
        "peak_congestion", "drc_violations", "lvs_status", "stage_runtime",
    })
    ALIASES = {
        "density": "utilization",
        "congestion": "total_congestion",
        "drc": "drc_violations",
        "lvs": "lvs_status",
        "runtime": "stage_runtime",
    }
    LOWER_IS_BETTER = frozenset({
        "area", "power", "total_congestion", "peak_congestion",
        "drc_violations", "stage_runtime",
    })
    HIGHER_IS_BETTER = frozenset({"wns", "tns"})

    def __init__(self, parent=None):
        rows = [
            {"label": label, "value": "—", "context": "UNAVAILABLE", "tone": "neutral", "spark": ""}
            for _, label in self.CARD_DEFINITIONS
        ]
        super().__init__(rows, parent)
        self._values: dict[str, object | None] = {name: None for name in self.METRIC_NAMES}
        self._units: dict[str, str] = {}
        self._history: dict[str, list[dict]] = defaultdict(list)
        self._current_stage = ""
        self._stage_status = "Idle"
        self._stage_history: list[dict] = []
        self._last_stage_state: tuple[str, str] | None = None

    wns = Property(object, lambda self: self._values["wns"], notify=metricsChanged)
    tns = Property(object, lambda self: self._values["tns"], notify=metricsChanged)
    area = Property(object, lambda self: self._values["area"], notify=metricsChanged)
    power = Property(object, lambda self: self._values["power"], notify=metricsChanged)
    utilization = Property(object, lambda self: self._values["utilization"], notify=metricsChanged)
    totalCongestion = Property(object, lambda self: self._values["total_congestion"], notify=metricsChanged)
    peakCongestion = Property(object, lambda self: self._values["peak_congestion"], notify=metricsChanged)
    drcViolations = Property(object, lambda self: self._values["drc_violations"], notify=metricsChanged)
    lvsStatus = Property(str, lambda self: str(self._values["lvs_status"] or "unavailable"), notify=metricsChanged)
    stageRuntime = Property(object, lambda self: self._values["stage_runtime"], notify=metricsChanged)
    stageStatus = Property(str, lambda self: self._stage_status, notify=metricsChanged)
    currentStage = Property(str, lambda self: self._current_stage, notify=metricsChanged)

    @Property(bool, notify=metricsChanged)
    def wnsAvailable(self) -> bool:
        return self._values["wns"] is not None

    @Property(bool, notify=metricsChanged)
    def tnsAvailable(self) -> bool:
        return self._values["tns"] is not None

    @Property(bool, notify=metricsChanged)
    def areaAvailable(self) -> bool:
        return self._values["area"] is not None

    @Property(bool, notify=metricsChanged)
    def powerAvailable(self) -> bool:
        return self._values["power"] is not None

    @Property(bool, notify=metricsChanged)
    def utilizationAvailable(self) -> bool:
        return self._values["utilization"] is not None

    @Property(bool, notify=metricsChanged)
    def totalCongestionAvailable(self) -> bool:
        return self._values["total_congestion"] is not None

    @Property(bool, notify=metricsChanged)
    def peakCongestionAvailable(self) -> bool:
        return self._values["peak_congestion"] is not None

    @Property(bool, notify=metricsChanged)
    def drcViolationsAvailable(self) -> bool:
        return self._values["drc_violations"] is not None

    @Property(bool, notify=metricsChanged)
    def lvsStatusAvailable(self) -> bool:
        return self._values["lvs_status"] is not None

    @Slot(object)
    def applyEvent(self, event: object) -> None:
        if isinstance(event, MetricUpdate):
            self._apply_metric(event)
        elif isinstance(event, StageUpdate):
            self._apply_stage(event)

    @Slot()
    def clear(self) -> None:
        self._values = {name: None for name in self.METRIC_NAMES}
        self._units.clear()
        self._history.clear()
        self._current_stage = ""
        self._stage_status = "Idle"
        self._stage_history.clear()
        self._last_stage_state = None
        self._refresh_cards()
        self.metricsChanged.emit()

    @Slot(str, result="QVariantList")
    def metricHistory(self, name: str) -> list[dict]:
        normalized = self.ALIASES.get(name, name)
        return [dict(item) for item in self._history.get(normalized, ())]

    @Slot(result="QVariantList")
    def stageHistory(self) -> list[dict]:
        return [dict(item) for item in self._stage_history]

    def snapshot(self) -> dict:
        """Export detached deterministic state for diagnosis construction."""

        return {
            "values": deepcopy(self._values),
            "units": dict(self._units),
            "history": deepcopy(dict(self._history)),
            "current_stage": self._current_stage,
            "stage_status": self._stage_status,
            "stage_history": deepcopy(self._stage_history),
        }

    def _apply_metric(self, event: MetricUpdate) -> None:
        name = self.ALIASES.get(event.name, event.name)
        if name not in self.METRIC_NAMES:
            return
        value = self._normalize_value(name, event.value)
        if value is None:
            return
        previous = self._values[name]
        trend = self._trend(name, previous, value)
        self._values[name] = value
        self._units[name] = event.unit
        self._history[name].append({
            "value": value,
            "unit": event.unit,
            "stage": event.stage,
            "source": event.source,
            "timestamp": self._timestamp_text(event.timestamp),
            "trend": trend,
        })
        self._refresh_card(name)
        self.metricsChanged.emit()

    def _apply_stage(self, event: StageUpdate) -> None:
        state = (event.stage, event.status)
        changed = False
        if event.stage != self._current_stage:
            self._current_stage = event.stage
            changed = True
        if event.status != self._stage_status:
            self._stage_status = event.status
            changed = True
        if event.runtime_seconds is not None:
            runtime = max(0.0, float(event.runtime_seconds))
            if runtime != self._values["stage_runtime"]:
                self._values["stage_runtime"] = runtime
                self._units["stage_runtime"] = "s"
                changed = True
        if state != self._last_stage_state:
            self._stage_history.append({
                "stage": event.stage,
                "status": event.status,
                "runtimeSeconds": event.runtime_seconds,
                "source": event.source,
                "timestamp": self._timestamp_text(event.timestamp),
            })
            if event.status.lower() in {"completed", "failed", "cancelled"} and event.runtime_seconds is not None:
                self._history["stage_runtime"].append({
                    "value": float(event.runtime_seconds),
                    "unit": "s",
                    "stage": event.stage,
                    "source": event.source,
                    "timestamp": self._timestamp_text(event.timestamp),
                    "trend": "initial",
                })
            self._last_stage_state = state
            changed = True
        if changed:
            self.metricsChanged.emit()

    def _refresh_cards(self) -> None:
        for name, _ in self.CARD_DEFINITIONS:
            self._refresh_card(name)

    def _refresh_card(self, name: str) -> None:
        card_index = next((index for index, definition in enumerate(self.CARD_DEFINITIONS) if definition[0] == name), None)
        if card_index is None:
            return
        history = self._history.get(name, [])
        if not history:
            self.update_row(card_index, {"value": "—", "context": "UNAVAILABLE", "tone": "neutral", "spark": ""})
            return
        current = history[-1]
        context = (
            f"PREV  {self._format_value(name, history[-2]['value'])}"
            if len(history) > 1
            else f"SOURCE  {str(current['source']).upper()}"
        )
        self.update_row(card_index, {
            "value": self._format_value(name, current["value"]),
            "context": context,
            "tone": self._tone(name, current["value"]),
            "spark": self._spark(history),
        })

    @staticmethod
    def _normalize_value(name: str, value: object) -> float | int | str | None:
        if name == "lvs_status":
            if not isinstance(value, str):
                return None
            normalized = value.strip().lower()
            return normalized if normalized in {"pass", "fail", "unknown"} else None
        if isinstance(value, bool) or not isinstance(value, Real):
            return None
        numeric = float(value)
        if numeric != numeric or numeric in {float("inf"), float("-inf")}:
            return None
        if name == "drc_violations":
            return max(0, int(numeric))
        return numeric

    def _trend(self, name: str, previous: object, value: object) -> str:
        if previous is None or not isinstance(previous, Real) or not isinstance(value, Real):
            return "initial"
        if value == previous:
            return "unchanged"
        improving = value > previous if name in self.HIGHER_IS_BETTER else value < previous
        if name not in self.HIGHER_IS_BETTER | self.LOWER_IS_BETTER:
            return "changed"
        return "improved" if improving else "degraded"

    @staticmethod
    def _format_value(name: str, value: object) -> str:
        if not isinstance(value, Real):
            return str(value).upper()
        numeric = float(value)
        if name in {"wns", "tns"}:
            return f"{numeric:+.3f}"
        if name == "area":
            return f"{numeric / 1_000_000:.2f}M" if abs(numeric) >= 1_000_000 else f"{numeric:,.0f}"
        if name == "utilization":
            return f"{numeric:.1f}%"
        if name in {"total_congestion", "peak_congestion"}:
            return f"{numeric:.2f}"
        if name == "power":
            return f"{numeric:.1f}"
        if name in {"drc_violations", "stage_runtime"}:
            return f"{numeric:.0f}"
        return f"{numeric:g}"

    @staticmethod
    def _tone(name: str, value: object) -> str:
        if not isinstance(value, Real):
            return "live"
        numeric = float(value)
        if name in {"wns", "tns"}:
            return "pass" if numeric >= 0 else "fail"
        if name in {"total_congestion", "peak_congestion"} and numeric >= 0.7:
            return "review"
        return "live"

    @staticmethod
    def _spark(history: list[dict]) -> str:
        values = [float(item["value"]) for item in history[-8:] if isinstance(item["value"], Real)]
        if len(values) < 2:
            return ""
        minimum, maximum = min(values), max(values)
        if minimum == maximum:
            return ",".join("5" for _ in values)
        return ",".join(str(1 + round((value - minimum) * 8 / (maximum - minimum))) for value in values)

    @staticmethod
    def _timestamp_text(timestamp: datetime | object) -> str:
        return timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp)
