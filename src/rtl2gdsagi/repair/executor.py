from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from ..ir import IR, SCHEMA
from ..safety import ImmutableZones, SafetyViolation, SECTION_EARLIEST_STAGE
from ..stages import StageId, stage_index
from .models import ActionType, RepairAction, RepairPlan, RepairResult


class RepairExecutor:
    """Validate and execute typed actions; it never accepts command strings."""

    def __init__(self, *, ir: IR, zones: ImmutableZones, work_rtl: Path,
                 backend_setter: Callable[[str], None] | None = None) -> None:
        self.ir, self.zones, self.work_rtl = ir, zones, Path(work_rtl).resolve()
        self.backend_setter = backend_setter

    def execute(self, plan: RepairPlan) -> RepairResult:
        result = RepairResult(applied=False)
        deltas: dict[str, dict[str, Any]] = {}
        rtl_actions: list[RepairAction] = []
        backend_actions: list[RepairAction] = []
        for action in plan.actions:
            if action.action_type is ActionType.SET_IR_VALUE:
                parts = action.target.split(".")
                if len(parts) != 2 or parts[0] not in SCHEMA:
                    raise SafetyViolation(f"unauthorized IR target {action.target!r}")
                section, field = parts
                if field not in {f.name for f in SCHEMA[section] if f.agent_writable}:
                    raise SafetyViolation(f"IR target {action.target!r} is not agent-writable")
                deltas.setdefault(section, {})[field] = action.value
            elif action.action_type is ActionType.PATCH_WORKING_RTL:
                rtl_actions.append(action)
            elif action.action_type is ActionType.SELECT_TOOL_BACKEND:
                if action.target != "klayout" or action.value not in {"native", "native_isolated", "container"}:
                    raise SafetyViolation(f"unauthorized backend selection {action.target}={action.value}")
                backend_actions.append(action)
            else:
                raise SafetyViolation(f"action {action.action_type.value} is not executable in this context")

        # Validate the complete IR transaction before mutating it.
        probe = IR(self.ir.as_dict())
        probe.apply_delta(deltas, agent=True)
        for section, fields in deltas.items():
            for field, value in fields.items():
                key = f"{section}.{field}"
                result.previous_values[key] = self.ir.get(section, field)
                result.new_values[key] = probe.get(section, field)

        for action in rtl_actions:
            self._validate_rtl_patch(action)
        self.ir.apply_delta(deltas, agent=True)
        for action in rtl_actions:
            path = self._apply_rtl_patch(action)
            result.changed_files.append(str(path))
        for action in backend_actions:
            if self.backend_setter is None:
                raise SafetyViolation("no trusted backend selector is installed")
            self.backend_setter(str(action.value))
            result.previous_values["tool.klayout.backend"] = "native"
            result.new_values["tool.klayout.backend"] = str(action.value)

        stages = [SECTION_EARLIEST_STAGE[s] for s in deltas]
        if rtl_actions:
            stages.append(StageId.LINT)
        if backend_actions:
            stages.append(StageId.GDSOUT)
        result.rollback_stage = min(stages, key=stage_index) if stages else None
        result.rollback_reason = "earliest consumer of: " + ", ".join(
            sorted([*deltas, *("working RTL" for _ in rtl_actions), *("KLayout backend" for _ in backend_actions)]))
        result.actions = [{"action_type": a.action_type.value, "target": a.target,
                           "value": a.value, "reason": a.reason,
                           "expected_effect": a.expected_effect} for a in plan.actions]
        result.applied = True
        return result

    def _validate_rtl_patch(self, action: RepairAction) -> None:
        path = self._resolve_rtl_target(action.target)
        try:
            path.relative_to(self.work_rtl)
        except ValueError:
            raise SafetyViolation(f"RTL patch escapes working copy: {action.target}") from None
        self.zones.check_write(path)
        if not path.is_file() or path.suffix not in {".v", ".sv", ".vh", ".svh"}:
            raise SafetyViolation(f"RTL patch target is not a working RTL file: {path}")
        if not isinstance(action.value, dict) or set(action.value) != {"old", "new"}:
            raise SafetyViolation("RTL patch value must contain exactly old/new strings")
        old = action.value["old"]
        if not isinstance(old, str) or not isinstance(action.value["new"], str) or not old:
            raise SafetyViolation("RTL patch old/new values must be nonempty/string")
        if path.read_text(encoding="utf-8").count(old) != 1:
            raise SafetyViolation("RTL patch old text must occur exactly once")

    def _apply_rtl_patch(self, action: RepairAction) -> Path:
        path = self._resolve_rtl_target(action.target)
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace(action.value["old"], action.value["new"], 1), encoding="utf-8")
        return path

    def _resolve_rtl_target(self, target: str) -> Path:
        """Resolve a confined working-copy path, accepting one explicit alias.

        Model evidence contains paths below a directory named ``rtl``. Some
        models therefore return ``rtl/top.v`` even though ``work_rtl`` is
        already the executor root. The alias is accepted only when the literal
        path does not exist and stripping exactly that first component selects
        one existing file. No general basename search or fuzzy matching is
        performed.
        """
        literal = (self.work_rtl / target).resolve()
        parts = Path(target).parts
        if (
            not literal.exists() and len(parts) > 1 and parts[0] == "rtl"
        ):
            aliased = (self.work_rtl.joinpath(*parts[1:])).resolve()
            if aliased.is_file():
                return aliased
        return literal
