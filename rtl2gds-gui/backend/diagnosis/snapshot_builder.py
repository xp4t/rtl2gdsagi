from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .schemas import (
    ArtifactFact,
    Availability,
    DiagnosisContext,
    DiagnosisEvidence,
    GateFact,
    MetricFact,
    MetricHistoryFact,
    RuntimeSignal,
    STAGE_ORDER,
    StageFact,
)


STAGE_ALIASES = {
    "import": "import_rtl",
    "import_rtl": "import_rtl",
    "rtl": "import_rtl",
    "elaborate": "elaborate_design",
    "elaboration": "elaborate_design",
    "elaborate_design": "elaborate_design",
    "synthesis": "synthesis_logic",
    "synthesis_logic": "synthesis_logic",
    "sta_pre_cts": "sta_pre_cts",
    "pre_cts_sta": "sta_pre_cts",
    "floorplan": "floorplan",
    "power_plan": "power_plan_tap",
    "power_plan_tap": "power_plan_tap",
    "place": "placement",
    "placement": "placement",
    "cts": "cts",
    "post_cts_sta": "post_cts_sta",
    "route": "routing",
    "routing": "routing",
    "signoff": "signoff_sta",
    "signoff_sta": "signoff_sta",
    "drc": "drc",
    "lvs": "lvs",
    "gds": "gds_packaging",
    "gds_packaging": "gds_packaging",
}


def canonical_stage(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")
    return STAGE_ALIASES.get(normalized, normalized or "unknown")


def stage_index(stage: str) -> int:
    try:
        return STAGE_ORDER.index(canonical_stage(stage))
    except ValueError:
        return len(STAGE_ORDER)


class DiagnosisSnapshotBuilder:
    """Converts detached runtime model data into an immutable diagnosis snapshot."""

    METRIC_NAMES = (
        "wns",
        "tns",
        "area",
        "power",
        "utilization",
        "total_congestion",
        "peak_congestion",
        "drc_violations",
        "lvs_status",
        "stage_runtime",
    )

    def build(
        self,
        *,
        run_id: str,
        metrics_snapshot: Mapping[str, Any],
        gate_rows: Sequence[Mapping[str, Any]],
        artifact_rows: Sequence[Mapping[str, Any]],
        runtime_signals: Sequence[RuntimeSignal] = (),
    ) -> DiagnosisContext:
        values = metrics_snapshot.get("values", {})
        units = metrics_snapshot.get("units", {})
        histories = metrics_snapshot.get("history", {})
        current_stage = canonical_stage(str(metrics_snapshot.get("current_stage", "")))

        metric_history: list[MetricHistoryFact] = []
        latest_history: dict[str, MetricHistoryFact] = {}
        for name in self.METRIC_NAMES:
            for item in histories.get(name, ()):
                fact = MetricHistoryFact(
                    name=name,
                    value=item.get("value"),
                    unit=str(item.get("unit", units.get(name, ""))),
                    stage=canonical_stage(str(item.get("stage", ""))),
                    source=str(item.get("source", "")),
                    timestamp=str(item.get("timestamp", "")),
                    trend=str(item.get("trend", "unknown")),
                )
                metric_history.append(fact)
                latest_history[name] = fact

        metrics: list[MetricFact] = []
        unavailable: list[str] = []
        for name in self.METRIC_NAMES:
            value = values.get(name)
            latest = latest_history.get(name)
            if value is None:
                availability = Availability.UNAVAILABLE
                unavailable.append(f"metric:{name}")
            else:
                availability = Availability.AVAILABLE
            metrics.append(MetricFact(
                name=name,
                value=value,
                unit=str(units.get(name, latest.unit if latest else "")),
                availability=availability,
                stage=latest.stage if latest else current_stage,
                source=latest.source if latest else "",
                timestamp=latest.timestamp if latest else "",
            ))

        stages = self._stage_facts(metrics_snapshot.get("stage_history", ()))
        failed = sorted(
            (item.stage for item in stages if item.status.upper() in {"FAILED", "FAIL", "CRASHED"}),
            key=stage_index,
        )
        failed_stage = failed[0] if failed else ""

        gates = tuple(self._gate_fact(row) for row in gate_rows)
        for gate in gates:
            if gate.availability != Availability.AVAILABLE:
                unavailable.append(f"gate:{gate.name.lower()}")

        artifacts = tuple(self._artifact_fact(row) for row in artifact_rows)
        evidence = self._base_evidence(metric_history, stages, gates, artifacts, runtime_signals)

        return DiagnosisContext(
            run_id=run_id or "unknown",
            current_stage=current_stage,
            failed_stage=failed_stage,
            stage_statuses=stages,
            metrics=tuple(metrics),
            metric_history=tuple(metric_history),
            signoff_gates=gates,
            artifacts=artifacts,
            runtime_signals=tuple(runtime_signals),
            detected_failures=(),
            evidence=evidence,
            unavailable_fields=tuple(sorted(set(unavailable))),
            timestamp=datetime.now(timezone.utc),
        )

    @staticmethod
    def _stage_facts(history: Sequence[Mapping[str, Any]]) -> tuple[StageFact, ...]:
        latest: dict[str, StageFact] = {}
        for item in history:
            stage = canonical_stage(str(item.get("stage", "")))
            if stage == "unknown" and not item.get("stage"):
                continue
            latest[stage] = StageFact(
                stage=stage,
                status=str(item.get("status", "UNKNOWN")).upper(),
                runtime_seconds=item.get("runtimeSeconds"),
                source=str(item.get("source", "flow")),
                timestamp=str(item.get("timestamp", "")),
            )
        return tuple(sorted(latest.values(), key=lambda item: stage_index(item.stage)))

    @staticmethod
    def _gate_fact(row: Mapping[str, Any]) -> GateFact:
        status = str(row.get("status", "UNKNOWN")).upper()
        availability = (
            Availability.NOT_RUN if status in {"PENDING", "NOT_RUN"}
            else Availability.UNKNOWN if status in {"UNKNOWN", "—", ""}
            else Availability.AVAILABLE
        )
        return GateFact(name=str(row.get("label", "UNKNOWN")).upper(), status=status, availability=availability)

    @staticmethod
    def _artifact_fact(row: Mapping[str, Any]) -> ArtifactFact:
        exists = bool(row.get("exists", False))
        return ArtifactFact(
            artifact_type=str(row.get("artifactType", "artifact")),
            path=str(row.get("path", "")),
            stage=canonical_stage(str(row.get("stage", ""))),
            timestamp=str(row.get("timestamp", "")),
            exists=exists,
            size_bytes=int(row.get("sizeBytes", -1)),
            source=str(row.get("source", "")),
            availability=Availability.AVAILABLE if exists else Availability.UNKNOWN,
        )

    @staticmethod
    def _base_evidence(
        metric_history: Sequence[MetricHistoryFact],
        stages: Sequence[StageFact],
        gates: Sequence[GateFact],
        artifacts: Sequence[ArtifactFact],
        signals: Sequence[RuntimeSignal],
    ) -> tuple[DiagnosisEvidence, ...]:
        evidence: list[DiagnosisEvidence] = []
        for index, item in enumerate(metric_history):
            evidence.append(DiagnosisEvidence(
                evidence_id=f"metric:{item.name}:{index}",
                evidence_type="history_change" if item.trend not in {"initial", "unchanged"} else "metric",
                name=item.name,
                value=item.value,
                unit=item.unit,
                stage=item.stage,
                source=item.source,
                timestamp=item.timestamp,
                detail=item.trend,
            ))
        for item in stages:
            evidence.append(DiagnosisEvidence(
                evidence_id=f"stage:{item.stage}",
                evidence_type="stage_status",
                name=item.stage,
                value=item.status,
                unit="status",
                stage=item.stage,
                source=item.source,
                timestamp=item.timestamp,
                detail=f"Stage status is {item.status}",
            ))
        for item in gates:
            evidence.append(DiagnosisEvidence(
                evidence_id=f"gate:{item.name.lower()}",
                evidence_type="signoff_gate",
                name=item.name.lower(),
                value=item.status,
                unit="status",
                stage=canonical_stage(item.name),
                source="deterministic_gate",
                timestamp="",
                detail=f"Deterministic {item.name} gate is {item.status}",
            ))
        for index, item in enumerate(artifacts):
            evidence.append(DiagnosisEvidence(
                evidence_id=f"artifact:{index}",
                evidence_type="artifact",
                name=item.artifact_type,
                value=item.exists,
                unit="exists",
                stage=item.stage,
                source=item.source,
                timestamp=item.timestamp,
                detail=item.path,
            ))
        for index, item in enumerate(signals):
            evidence.append(DiagnosisEvidence(
                evidence_id=f"parser_event:{index}",
                evidence_type="parser_event",
                name=item.category_hint,
                value=item.message,
                unit="",
                stage=canonical_stage(item.stage),
                source=item.source,
                timestamp=item.timestamp,
                detail=item.message,
            ))
        return tuple(evidence)
