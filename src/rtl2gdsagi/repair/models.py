from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..stages import StageId


class ActionType(str, Enum):
    SET_IR_VALUE = "SET_IR_VALUE"
    PATCH_WORKING_RTL = "PATCH_WORKING_RTL"
    SELECT_TOOL_BACKEND = "SELECT_TOOL_BACKEND"
    SET_PROCESS_ENV = "SET_PROCESS_ENV"
    REGENERATE_SCRIPT = "REGENERATE_SCRIPT"
    CLEAN_STAGE_RUNTIME_STATE = "CLEAN_STAGE_RUNTIME_STATE"
    RUN_HEALTH_PROBE = "RUN_HEALTH_PROBE"


@dataclass(frozen=True)
class RepairAction:
    action_type: ActionType
    target: str
    value: Any
    reason: str
    expected_effect: str = ""


@dataclass(frozen=True)
class RepairPlan:
    failure_fingerprint: str
    actions: tuple[RepairAction, ...]
    known_error_id: str | None = None
    summary: str = ""


@dataclass
class RepairResult:
    applied: bool
    actions: list[dict[str, Any]] = field(default_factory=list)
    rollback_stage: StageId | None = None
    rollback_reason: str = ""
    changed_files: list[str] = field(default_factory=list)
    previous_values: dict[str, Any] = field(default_factory=dict)
    new_values: dict[str, Any] = field(default_factory=dict)
    error: str = ""
