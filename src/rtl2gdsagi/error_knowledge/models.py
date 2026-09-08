from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..stages import StageId


class Repairability(str, Enum):
    DETERMINISTIC = "deterministic"
    AGENT_EXECUTABLE = "agent_executable"
    USER_DESIGN_DECISION = "user_design_decision"
    ENVIRONMENT_REPAIRABLE = "environment_repairable"
    NON_REPAIRABLE = "non_repairable"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ToolMessage:
    tool: str
    subsystem: str
    code: int
    severity: str
    raw_message: str
    canonical_id: str
    source_file: str = ""
    source_line: int | None = None
    canonical_message: str = ""
    documentation: str = ""


@dataclass(frozen=True)
class FailureKnowledge:
    key: str
    tool: str
    title: str
    explanation: str
    likely_causes: tuple[str, ...]
    design_context_explanation: str
    repair_class: str
    repairability: Repairability
    allowed_actions: tuple[str, ...]
    earliest_rollback_stage: StageId | None
    confirmation_required: bool = True
    references: tuple[str, ...] = ()
    proposed_delta: dict[str, dict[str, Any]] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
