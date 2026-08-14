"""Agent layer: diagnosis only, never verdicts, never tool syntax."""
from .client import (
    Agent, AgentResponse, ClaudeAgent, DiagnosisRequest, ScriptedAgent,
    api_key_present, parse_diagnosis, resolve_model,
)

__all__ = [
    "Agent", "AgentResponse", "ClaudeAgent", "DiagnosisRequest", "ScriptedAgent",
    "api_key_present", "parse_diagnosis", "resolve_model",
]
