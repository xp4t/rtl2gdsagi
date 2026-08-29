from __future__ import annotations

import json

from .schemas import DiagnosisContext


SYSTEM_PROMPT = """You are a read-only RTL-to-GDS failure-diagnosis assistant.

You may explain likely causes and recommend investigation steps.
You must not claim to have modified the design.
You must not instruct the application to automatically change files or flow parameters.
The deterministic signoff system is authoritative.
Never override or reinterpret a PASS/FAIL gate as a different final verdict.

Clearly distinguish:
- observed facts
- deterministic classifications
- hypotheses
- recommended human investigation

Return only the requested structured diagnosis fields. Never emit shell commands, TCL,
configuration changes, file edits, automatic fixes, or instructions to rerun the flow."""


class PromptBuilder:
    """Builds bounded prompts exclusively from structured diagnosis facts."""

    def build(self, context: DiagnosisContext) -> tuple[str, str]:
        payload = {
            "runId": context.run_id,
            "currentStage": context.current_stage,
            "failedStage": context.failed_stage or "UNKNOWN",
            "detectedFailures": [
                {
                    "id": item.failure_id,
                    "category": item.category,
                    "severity": item.severity.value,
                    "stage": item.stage,
                    "earliestImplicatedStage": item.earliest_implicated_stage,
                    "evidenceIds": list(item.evidence_ids),
                }
                for item in context.detected_failures
            ],
            "stageStatuses": [
                {
                    "stage": item.stage,
                    "status": item.status,
                    "runtimeSeconds": item.runtime_seconds,
                    "availability": item.availability.value,
                }
                for item in context.stage_statuses
            ],
            "metrics": [
                {
                    "name": item.name,
                    "value": item.value,
                    "unit": item.unit,
                    "stage": item.stage,
                    "source": item.source,
                    "availability": item.availability.value,
                }
                for item in context.metrics
            ],
            "recentMetricHistory": [
                {
                    "name": item.name,
                    "value": item.value,
                    "unit": item.unit,
                    "stage": item.stage,
                    "source": item.source,
                    "trend": item.trend,
                }
                for item in context.metric_history[-32:]
            ],
            "signoffGates": [
                {"name": item.name, "status": item.status, "availability": item.availability.value}
                for item in context.signoff_gates
            ],
            "artifacts": [
                {
                    "type": item.artifact_type,
                    "path": item.path,
                    "stage": item.stage,
                    "exists": item.exists,
                    "sizeBytes": item.size_bytes,
                    "availability": item.availability.value,
                }
                for item in context.artifacts[:64]
            ],
            "evidence": [
                {
                    "id": item.evidence_id,
                    "type": item.evidence_type,
                    "name": item.name,
                    "value": item.value,
                    "unit": item.unit,
                    "stage": item.stage,
                    "source": item.source,
                    "detail": item.detail,
                }
                for item in context.evidence[:96]
            ],
            "unavailableFields": list(context.unavailable_fields),
            "requiredResultFields": [
                "summary",
                "primaryFailure",
                "rootCauseStage",
                "confidence",
                "evidenceReferences",
                "contributingFactors",
                "recommendedChecks",
                "limitations",
            ],
        }
        user_prompt = (
            "Explain the deterministic failures below for human review. "
            "Do not alter any deterministic verdict.\n\n"
            + json.dumps(payload, indent=2, sort_keys=True)
        )
        return SYSTEM_PROMPT, user_prompt
