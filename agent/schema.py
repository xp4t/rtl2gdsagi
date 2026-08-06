"""Strict JSON schema for agent responses — tool-use function calling."""
from __future__ import annotations

from typing import Any

# JSON Schema for the `make_flow_decision` tool that Claude must call.
# The orchestrator validates agent output against this before applying.
DECISION_TOOL_SCHEMA: dict[str, Any] = {
    "name": "make_flow_decision",
    "description": (
        "Make a decision about how to proceed with the current EDA flow stage. "
        "You MUST call this tool — do NOT respond with plain text. "
        "Only suggest param_updates that apply to the current stage."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "decision": {
                "type": "string",
                "enum": ["continue", "retune", "escalate_to_human", "abort"],
                "description": (
                    "continue: results are acceptable, move to next stage. "
                    "retune: adjust parameters and re-run this stage. "
                    "escalate_to_human: results require human judgement. "
                    "abort: fatal issue, stop the run immediately."
                ),
            },
            "reasoning": {
                "type": "string",
                "description": "Short explanation (≤200 chars) of why this decision was made.",
                "maxLength": 200,
            },
            "param_updates": {
                "type": "object",
                "description": (
                    "Key/value pairs of OpenLane2 config params to update before retry. "
                    "Leave empty if decision is not 'retune'. "
                    "Only include params valid for the current stage."
                ),
                "additionalProperties": {"type": ["string", "number", "boolean"]},
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": "Agent's confidence in this decision.",
            },
        },
        "required": ["decision", "reasoning", "param_updates", "confidence"],
        "additionalProperties": False,
    },
}


class AgentDecision:
    """Validated agent decision object."""

    VALID_DECISIONS = {"continue", "retune", "escalate_to_human", "abort"}
    VALID_CONFIDENCE = {"high", "medium", "low"}

    def __init__(self, raw: dict[str, Any]) -> None:
        self.decision   = raw["decision"]
        self.reasoning  = raw.get("reasoning", "")
        self.param_updates = raw.get("param_updates", {})
        self.confidence = raw.get("confidence", "low")
        self._validate()

    def _validate(self) -> None:
        if self.decision not in self.VALID_DECISIONS:
            raise ValueError(f"Invalid decision: {self.decision!r}")
        if self.confidence not in self.VALID_CONFIDENCE:
            raise ValueError(f"Invalid confidence: {self.confidence!r}")
        if not isinstance(self.param_updates, dict):
            raise ValueError("param_updates must be a dict")

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reasoning": self.reasoning,
            "param_updates": self.param_updates,
            "confidence": self.confidence,
        }
