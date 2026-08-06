"""Unit tests for StateManager / RunState persistence."""
from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator.state_manager import StateManager
from orchestrator.stages import Stage


def test_new_run_persists(tmp_path):
    sm = StateManager(tmp_path)
    rs = sm.new_run(
        rtl_path="/rtl/alu.v",
        top_module="riscv_alu",
        pdk="sky130hd",
        config_path="config/defaults.yaml",
    )
    assert rs.run_id
    assert (tmp_path / f"{rs.run_id}.json").exists()


def test_save_and_reload(tmp_path):
    sm = StateManager(tmp_path)
    rs = sm.new_run("/rtl/alu.v", "riscv_alu", "sky130hd", "config.yaml")
    rs.current_stage = Stage.SYNTHESIS
    rs.completed_stages.append(Stage.LINT.value)
    rs.stage_results["lint"] = {"status": "pass"}
    sm.save(rs)

    loaded = sm.load_run(rs.run_id)
    assert loaded.current_stage == Stage.SYNTHESIS
    assert Stage.LINT.value in loaded.completed_stages
    assert loaded.stage_results["lint"]["status"] == "pass"


def test_load_missing_raises(tmp_path):
    sm = StateManager(tmp_path)
    with pytest.raises(FileNotFoundError):
        sm.load_run("nonexistent_run_id")


def test_list_runs(tmp_path):
    sm = StateManager(tmp_path)
    rs1 = sm.new_run("/rtl/a.v", "a", "sky130hd", "config.yaml")
    rs2 = sm.new_run("/rtl/b.v", "b", "sky130hd", "config.yaml")
    runs = sm.list_runs()
    assert rs1.run_id in runs
    assert rs2.run_id in runs


def test_atomic_save(tmp_path):
    """Verify that the temp-file rename pattern leaves no .tmp files."""
    sm = StateManager(tmp_path)
    rs = sm.new_run("/rtl/alu.v", "riscv_alu", "sky130hd", "config.yaml")
    sm.save(rs)
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert tmp_files == [], f"Temp files not cleaned up: {tmp_files}"
