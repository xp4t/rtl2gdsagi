from __future__ import annotations

from pathlib import Path

import pytest

from rtl2gdsagi.ir import IR
from rtl2gdsagi.repair import ActionType, RepairAction, RepairExecutor, RepairPlan
from rtl2gdsagi.safety import ImmutableZones, SafetyViolation
from rtl2gdsagi.stages import StageId


def executor(tmp_path: Path):
    source, work, pdk = tmp_path / "source", tmp_path / "run/work/rtl", tmp_path / "pdk"
    source.mkdir(); work.mkdir(parents=True); pdk.mkdir()
    (source / "top.v").write_text("module top; endmodule\n")
    (work / "top.v").write_text("module top; endmodule\n")
    return RepairExecutor(ir=IR(), zones=ImmutableZones(pdk_root=pdk, rtl_source=source),
                          work_rtl=work), source, work, pdk


def test_floorplan_change_derives_floorplan_rollback(tmp_path):
    ex, *_ = executor(tmp_path)
    result = ex.execute(RepairPlan("abc", (RepairAction(
        ActionType.SET_IR_VALUE, "floorplan.core_utilization", 0.30, "small core"),)))
    assert result.rollback_stage is StageId.FLOORPLAN
    assert result.previous_values["floorplan.core_utilization"] == 0.45


def test_working_rtl_patch_preserves_original_and_requires_lint(tmp_path):
    ex, source, work, _ = executor(tmp_path)
    result = ex.execute(RepairPlan("abc", (RepairAction(
        ActionType.PATCH_WORKING_RTL, "top.v",
        {"old": "module top;", "new": "module top();"}, "syntax repair"),)))
    assert (source / "top.v").read_text() == "module top; endmodule\n"
    assert (work / "top.v").read_text().startswith("module top();")
    assert result.rollback_stage is StageId.LINT


def test_working_rtl_root_alias_resolves_without_fuzzy_search(tmp_path):
    ex, source, work, _ = executor(tmp_path)
    result = ex.execute(RepairPlan("abc", (RepairAction(
        ActionType.PATCH_WORKING_RTL, "rtl/top.v",
        {"old": "module top;", "new": "module top();"}, "syntax repair"),)))
    assert result.changed_files == [str((work / "top.v").resolve())]
    assert (source / "top.v").read_text() == "module top; endmodule\n"


@pytest.mark.parametrize("target", ["../pdk/lib.lef", "/tmp/deck.drc"])
def test_pdk_or_external_mutation_is_rejected(tmp_path, target):
    ex, *_ = executor(tmp_path)
    with pytest.raises(SafetyViolation):
        ex.execute(RepairPlan("abc", (RepairAction(
            ActionType.PATCH_WORKING_RTL, target, {"old": "x", "new": "y"}, "bad"),)))


def test_arbitrary_shell_action_is_unrepresentable(tmp_path):
    ex, *_ = executor(tmp_path)
    with pytest.raises(SafetyViolation):
        ex.execute(RepairPlan("abc", (RepairAction(
            ActionType.SET_PROCESS_ENV, "shell", "rm -rf /", "bad"),)))
