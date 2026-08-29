from __future__ import annotations

import re
from datetime import datetime, timezone
from numbers import Real
from typing import Iterable

from .schemas import (
    DetectedFailure,
    DiagnosisContext,
    DiagnosisEvidence,
    RuntimeSignal,
    Severity,
)
from .snapshot_builder import canonical_stage, stage_index


FAILURE_DESCRIPTIONS = {
    "RTL_SYNTAX": "RTL parsing reported a syntax failure.",
    "UNRESOLVED_MODULE": "Elaboration could not resolve a referenced module.",
    "ELABORATION_FAILURE": "Design elaboration failed.",
    "PORT_PARAMETER_MISMATCH": "Elaboration reported a parameter or port mismatch.",
    "SYNTHESIS_COMMAND_FAILURE": "The synthesis stage process failed.",
    "UNSUPPORTED_CONSTRUCT": "Synthesis reported an unsupported RTL construct.",
    "INFERRED_RESOURCE_ISSUE": "Synthesis reported an inferred-resource problem.",
    "SYNTHESIS_CONSTRAINT_ISSUE": "Synthesis reported a constraint problem.",
    "UTILIZATION_HIGH": "Placement utilization exceeds the deterministic diagnosis threshold.",
    "PLACEMENT_FAILURE": "The placement stage process failed.",
    "LEGALIZATION_FAILURE": "Placement legalization failed.",
    "DENSITY_ISSUE": "Placement density is excessive.",
    "MACRO_PLACEMENT_ISSUE": "Macro placement evidence indicates a failure.",
    "TIMING_SETUP": "Deterministic timing metrics show a setup failure.",
    "TIMING_HOLD": "A hold timing violation was reported.",
    "WNS_DEGRADATION": "Worst negative slack degraded relative to the previous observation.",
    "TNS_DEGRADATION": "Total negative slack degraded relative to the previous observation.",
    "PLACEMENT_CONGESTION": "Placement congestion exceeds the deterministic diagnosis threshold.",
    "ROUTING_FAILURE": "The routing stage process failed.",
    "ROUTING_CONGESTION": "Routing congestion exceeds the deterministic diagnosis threshold.",
    "UNROUTED_NETS": "Routing reported unrouted nets.",
    "DRC_FAILURE": "The deterministic DRC gate reports violations.",
    "LVS_MISMATCH": "The deterministic LVS gate reports a mismatch.",
    "ANTENNA_FAILURE": "Physical verification reported antenna violations.",
    "SIGNOFF_FAILURE": "A signoff stage process failed.",
    "MISSING_TIMING_REPORT": "Signoff timing was reached without an available timing report.",
    "MISSING_GDS_ARTIFACT": "GDS packaging completed without an available GDS artifact.",
    "MISSING_ARTIFACT": "A referenced flow artifact is not available on disk.",
    "AREA_REGRESSION": "Area increased materially relative to the previous observation.",
    "POWER_REGRESSION": "Power increased materially relative to the previous observation.",
    "TOOL_CRASH": "A tool crash was reported.",
    "TIMEOUT": "A flow stage timed out.",
    "MALFORMED_PARSER_INPUT": "Tool output could not be parsed reliably.",
    "STAGE_TERMINATED": "A stage terminated unexpectedly.",
}


class RuntimeEvidenceStore:
    """Extracts bounded structured failure signals; it never retains full logs."""

    PATTERNS = (
        ("RTL_SYNTAX", re.compile(r"\b(?:rtl\s+)?(?:syntax|parse)\s+error\b", re.I)),
        ("UNRESOLVED_MODULE", re.compile(r"\b(?:unresolved|unknown|cannot\s+find)\s+module\b|module\s+.*not\s+found", re.I)),
        ("PORT_PARAMETER_MISMATCH", re.compile(r"\b(?:port|parameter)\b.*\b(?:mismatch|does\s+not\s+match|unknown)\b", re.I)),
        ("ELABORATION_FAILURE", re.compile(r"\belaborat(?:ion|e).*\b(?:fail|error)\b", re.I)),
        ("UNSUPPORTED_CONSTRUCT", re.compile(r"\bunsupported\s+(?:rtl\s+)?construct\b|not\s+synthesizable", re.I)),
        ("INFERRED_RESOURCE_ISSUE", re.compile(r"\binferred\b.*\b(?:latch|memory|resource)\b.*\b(?:error|failed|unsupported)\b", re.I)),
        ("SYNTHESIS_CONSTRAINT_ISSUE", re.compile(r"\b(?:synthesis\s+)?constraint\b.*\b(?:error|invalid|missing|failed)\b", re.I)),
        ("LEGALIZATION_FAILURE", re.compile(r"\blegaliz(?:ation|e).*\b(?:fail|error|unable)\b", re.I)),
        ("MACRO_PLACEMENT_ISSUE", re.compile(r"\bmacro\s+placement\b.*\b(?:fail|overlap|error)\b", re.I)),
        ("TIMING_HOLD", re.compile(r"\bhold\b.*\b(?:violation|slack\s*[:=]\s*-)\b", re.I)),
        ("TIMING_SETUP", re.compile(r"\bsetup\b.*\b(?:violation|slack\s*[:=]\s*-)\b", re.I)),
        ("UNROUTED_NETS", re.compile(r"\b(?:unrouted|unconnected)\s+nets?\b", re.I)),
        ("ANTENNA_FAILURE", re.compile(r"\bantenna\b.*\b(?:violation|fail|error)\b", re.I)),
        ("TOOL_CRASH", re.compile(r"\b(?:segmentation\s+fault|core\s+dumped|tool\s+crash(?:ed)?|fatal\s+signal)\b", re.I)),
        ("TIMEOUT", re.compile(r"\b(?:timed?\s+out|timeout)\b", re.I)),
        ("MALFORMED_PARSER_INPUT", re.compile(r"\b(?:malformed|unparseable|parser\s+error)\b", re.I)),
        ("STAGE_TERMINATED", re.compile(r"\bstage\b.*\bterminated\s+unexpectedly\b|unexpected\s+termination", re.I)),
    )

    def __init__(self, max_signals: int = 256) -> None:
        self._signals: list[RuntimeSignal] = []
        self._max_signals = max_signals

    def ingest(self, line: str, *, stage: str, source: str) -> tuple[RuntimeSignal, ...]:
        if not isinstance(line, str):
            return ()
        text = " ".join(line.strip().split())[:240]
        if not text:
            return ()
        found: list[RuntimeSignal] = []
        for category, pattern in self.PATTERNS:
            if not pattern.search(text):
                continue
            signal = RuntimeSignal(
                category_hint=category,
                stage=canonical_stage(stage),
                message=text,
                source=source,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            identity = (signal.category_hint, signal.stage, signal.message)
            if not any((item.category_hint, item.stage, item.message) == identity for item in self._signals):
                self._signals.append(signal)
                found.append(signal)
        if len(self._signals) > self._max_signals:
            self._signals = self._signals[-self._max_signals:]
        return tuple(found)

    def snapshot(self) -> tuple[RuntimeSignal, ...]:
        return tuple(self._signals)

    def clear(self) -> None:
        self._signals.clear()


class FailureClassifier:
    """Authoritative deterministic failure taxonomy and root-stage selection."""

    CONGESTION_TOTAL_LIMIT = 0.70
    CONGESTION_PEAK_LIMIT = 0.80
    UTILIZATION_LIMIT = 80.0
    REGRESSION_FRACTION = 0.05

    SIGNAL_SEVERITY = {
        "TOOL_CRASH": Severity.CRITICAL,
        "TIMEOUT": Severity.FAIL,
        "MALFORMED_PARSER_INPUT": Severity.WARN,
    }

    def classify(self, context: DiagnosisContext) -> DiagnosisContext:
        evidence = list(context.evidence)
        failures: list[DetectedFailure] = []

        def add(
            category: str,
            stage: str,
            evidence_ids: Iterable[str],
            *,
            earliest: str | None = None,
            severity: Severity = Severity.FAIL,
        ) -> None:
            normalized_stage = canonical_stage(stage)
            root = canonical_stage(earliest or stage)
            identity = (category, normalized_stage, root)
            if any((item.category, item.stage, item.earliest_implicated_stage) == identity for item in failures):
                return
            valid_ids = tuple(dict.fromkeys(item for item in evidence_ids if any(e.evidence_id == item for e in evidence)))
            failures.append(DetectedFailure(
                failure_id=f"failure:{category.lower()}:{normalized_stage}",
                category=category,
                severity=severity,
                stage=normalized_stage,
                earliest_implicated_stage=root,
                evidence_ids=valid_ids,
                description=FAILURE_DESCRIPTIONS.get(category, category.replace("_", " ").title()),
            ))

        # Structured parser signals carry deterministic categorical facts.
        for index, signal in enumerate(context.runtime_signals):
            add(
                signal.category_hint,
                signal.stage,
                (f"parser_event:{index}",),
                severity=self.SIGNAL_SEVERITY.get(signal.category_hint, Severity.FAIL),
            )

        stage_failures = {
            "import_rtl": "RTL_SYNTAX",
            "elaborate_design": "ELABORATION_FAILURE",
            "synthesis_logic": "SYNTHESIS_COMMAND_FAILURE",
            "floorplan": "PLACEMENT_FAILURE",
            "placement": "PLACEMENT_FAILURE",
            "cts": "PLACEMENT_FAILURE",
            "routing": "ROUTING_FAILURE",
            "signoff_sta": "SIGNOFF_FAILURE",
            "drc": "DRC_FAILURE",
            "lvs": "LVS_MISMATCH",
            "gds_packaging": "SIGNOFF_FAILURE",
        }
        for stage in context.stage_statuses:
            if stage.status.upper() in {"FAILED", "FAIL", "CRASHED"}:
                add(stage_failures.get(stage.stage, "STAGE_TERMINATED"), stage.stage, (f"stage:{stage.stage}",))

        metric_map = {item.name: item for item in context.metrics}
        history = context.metric_history

        timing_names = [name for name in ("wns", "tns") if self._numeric(metric_map.get(name)) is not None and self._numeric(metric_map.get(name)) < 0]
        if timing_names:
            timing_evidence = [
                item for item in evidence
                if item.name in timing_names and isinstance(item.value, Real) and float(item.value) < 0
            ]
            earliest = min((item.stage for item in timing_evidence), key=stage_index, default=context.current_stage)
            observed = max((item.stage for item in timing_evidence), key=stage_index, default=context.current_stage)
            add("TIMING_SETUP", observed, (item.evidence_id for item in timing_evidence), earliest=earliest)

        for name, category in (("wns", "WNS_DEGRADATION"), ("tns", "TNS_DEGRADATION")):
            relevant = [item for item in history if item.name == name]
            if relevant and relevant[-1].trend == "degraded":
                ids = [item.evidence_id for item in evidence if item.name == name and item.stage == relevant[-1].stage]
                add(category, relevant[-1].stage, ids[-1:], severity=Severity.WARN)

        utilization = self._numeric(metric_map.get("utilization"))
        if utilization is not None and utilization >= self.UTILIZATION_LIMIT:
            item = metric_map["utilization"]
            add("UTILIZATION_HIGH", item.stage or "placement", self._metric_ids(evidence, "utilization"))

        total = self._numeric(metric_map.get("total_congestion"))
        peak = self._numeric(metric_map.get("peak_congestion"))
        if (total is not None and total >= self.CONGESTION_TOTAL_LIMIT) or (peak is not None and peak >= self.CONGESTION_PEAK_LIMIT):
            metric = metric_map["peak_congestion"] if peak is not None and peak >= self.CONGESTION_PEAK_LIMIT else metric_map["total_congestion"]
            category = "ROUTING_CONGESTION" if stage_index(metric.stage) >= stage_index("routing") else "PLACEMENT_CONGESTION"
            ids = self._metric_ids(evidence, "total_congestion") + self._metric_ids(evidence, "peak_congestion")
            add(category, metric.stage or context.current_stage, ids)

        drc = self._numeric(metric_map.get("drc_violations"))
        drc_gate = next((item for item in context.signoff_gates if item.name == "DRC"), None)
        if (drc is not None and drc > 0) or (drc_gate and drc_gate.status == "FAIL"):
            add("DRC_FAILURE", "drc", self._metric_ids(evidence, "drc_violations") + ["gate:drc"])

        lvs = metric_map.get("lvs_status")
        lvs_gate = next((item for item in context.signoff_gates if item.name == "LVS"), None)
        if (lvs and str(lvs.value).lower() == "fail") or (lvs_gate and lvs_gate.status == "FAIL"):
            add("LVS_MISMATCH", "lvs", self._metric_ids(evidence, "lvs_status") + ["gate:lvs"])

        for name, category in (("area", "AREA_REGRESSION"), ("power", "POWER_REGRESSION")):
            relevant = [item for item in history if item.name == name and isinstance(item.value, Real)]
            if len(relevant) >= 2 and float(relevant[-2].value) != 0:
                change = (float(relevant[-1].value) - float(relevant[-2].value)) / abs(float(relevant[-2].value))
                if change >= self.REGRESSION_FRACTION:
                    ids = self._metric_ids(evidence, name)
                    add(category, relevant[-1].stage, ids[-2:])

        reached = max((stage_index(item.stage) for item in context.stage_statuses), default=-1)
        available_types = {item.artifact_type for item in context.artifacts if item.exists}
        if reached >= stage_index("signoff_sta") and "timing_report" not in available_types:
            missing_id = self._missing_evidence(evidence, "timing_report", "signoff_sta")
            add("MISSING_TIMING_REPORT", "signoff_sta", (missing_id,))
        gds_completed = any(item.stage == "gds_packaging" and item.status == "COMPLETED" for item in context.stage_statuses)
        if gds_completed and "gds" not in available_types:
            missing_id = self._missing_evidence(evidence, "gds", "gds_packaging")
            add("MISSING_GDS_ARTIFACT", "gds_packaging", (missing_id,))
        for index, artifact in enumerate(context.artifacts):
            if not artifact.exists:
                add("MISSING_ARTIFACT", artifact.stage, (f"artifact:{index}",), severity=Severity.WARN)

        severity_rank = {Severity.CRITICAL: 0, Severity.FAIL: 1, Severity.WARN: 2, Severity.INFO: 3}
        failures.sort(key=lambda item: (severity_rank[item.severity], stage_index(item.earliest_implicated_stage), item.category))
        return context.with_classification(tuple(failures), tuple(evidence))

    @staticmethod
    def _numeric(metric) -> float | None:
        if metric is None or isinstance(metric.value, bool) or not isinstance(metric.value, Real):
            return None
        return float(metric.value)

    @staticmethod
    def _metric_ids(evidence: list[DiagnosisEvidence], name: str) -> list[str]:
        return [item.evidence_id for item in evidence if item.name == name and item.evidence_type in {"metric", "history_change"}]

    @staticmethod
    def _missing_evidence(evidence: list[DiagnosisEvidence], name: str, stage: str) -> str:
        evidence_id = f"missing:{name}"
        if not any(item.evidence_id == evidence_id for item in evidence):
            evidence.append(DiagnosisEvidence(
                evidence_id=evidence_id,
                evidence_type="missing_data",
                name=name,
                value=None,
                unit="",
                stage=stage,
                source="snapshot_builder",
                timestamp="",
                detail=f"Expected {name} is unavailable after {stage}.",
            ))
        return evidence_id
