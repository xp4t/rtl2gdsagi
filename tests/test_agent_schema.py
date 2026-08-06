"""Unit tests for agent decision schema validation."""
from __future__ import annotations

import pytest
from agent.schema import AgentDecision, DECISION_TOOL_SCHEMA


class TestAgentDecision:
    def test_valid_continue(self):
        d = AgentDecision({
            "decision": "continue",
            "reasoning": "Timing met.",
            "param_updates": {},
            "confidence": "high",
        })
        assert d.decision == "continue"
        assert d.confidence == "high"

    def test_valid_retune(self):
        d = AgentDecision({
            "decision": "retune",
            "reasoning": "WNS = -0.4 ns",
            "param_updates": {"CLOCK_PERIOD": 12.0},
            "confidence": "medium",
        })
        assert d.decision == "retune"
        assert d.param_updates["CLOCK_PERIOD"] == 12.0

    def test_invalid_decision_raises(self):
        with pytest.raises(ValueError, match="Invalid decision"):
            AgentDecision({
                "decision": "fly_to_moon",
                "reasoning": "why not",
                "param_updates": {},
                "confidence": "high",
            })

    def test_invalid_confidence_raises(self):
        with pytest.raises(ValueError, match="Invalid confidence"):
            AgentDecision({
                "decision": "continue",
                "reasoning": "ok",
                "param_updates": {},
                "confidence": "very_high",
            })

    def test_to_dict_roundtrip(self):
        raw = {
            "decision": "escalate_to_human",
            "reasoning": "DRC failed with 5 violations.",
            "param_updates": {},
            "confidence": "high",
        }
        d = AgentDecision(raw)
        assert d.to_dict() == raw

    def test_tool_schema_has_required_fields(self):
        schema = DECISION_TOOL_SCHEMA
        assert schema["name"] == "make_flow_decision"
        required = schema["input_schema"]["required"]
        for field in ["decision", "reasoning", "param_updates", "confidence"]:
            assert field in required
