from __future__ import annotations

import json
from dataclasses import replace

import pytest

from rtl2gdsagi.agent.client import ScriptedAgent
from rtl2gdsagi.checks.tools import ToolRun
from rtl2gdsagi.error_knowledge.context import pdn_context
from rtl2gdsagi.error_knowledge.known_fixes import lookup_known_fix
from rtl2gdsagi.error_knowledge.matcher import match_openroad_messages
from rtl2gdsagi.error_knowledge.openroad_catalog import OpenRoadCatalog
from rtl2gdsagi.ir import IR
from rtl2gdsagi.runner import Orchestrator
from rtl2gdsagi.stages import StageId

PDN_LOG = ('[ERROR PDN-0185] Insufficient width (6.27 um) to add straps on layer '
           'met4 in grid "stdcell" with total strap width 8.53 um and offset 2.0 um.\n')


def test_catalog_loads_and_ids_are_unique():
    catalog = OpenRoadCatalog()
    rows = catalog.query(failures_only=True)
    assert len(rows) >= 2500
    assert len({m.canonical_id for m in rows}) == len(rows)
    assert {m.severity for m in rows} <= {"WARN", "ERROR", "CRITICAL"}
    assert {"PDN", "DRT", "CTS", "GPL"} <= {m.subsystem for m in rows}


def test_pdn_0185_resolves_and_unknown_fails_closed():
    catalog = OpenRoadCatalog()
    msg = catalog.require("PDN-0185")
    assert msg.severity == "ERROR"
    assert msg.source_file.endswith("pdn/src/straps.cpp")
    with pytest.raises(KeyError):
        catalog.require("PDN-9999")
    assert match_openroad_messages("[ERROR PDN-9999] invented") == []


def test_pdn_explanation_uses_this_design_context():
    msg = match_openroad_messages(PDN_LOG)[0]
    history = [{"stage": "synthesis", "metrics": {"cells": 18, "area_um2": 31.2}}]
    facts = {"top": "shift_register", "always_blocks": 1}
    context = pdn_context(PDN_LOG, facts=facts, history=history, ir=IR())
    fix = lookup_known_fix(msg, context)
    assert fix is not None
    text = fix.design_context_explanation
    assert "shift_register" in text and "18 mapped cells" in text
    assert "6.27 um" in text and "8.53 um" in text
    assert "functionally implicated" in text
    assert "floorplan" in fix.proposed_delta


def test_auto_known_fix_skips_agent_and_rolls_back_to_floorplan(cfg, toolchain):
    cfg = replace(cfg, repair_policy="auto", klayout_backend="container")
    agent = ScriptedAgent()
    orch = Orchestrator(cfg, agent=agent)
    orch.invoker = toolchain(orch, fail={StageId.PDN: [
        ToolRun(argv=["openroad"], returncode=1, stdout=PDN_LOG, stderr="")
    ]})
    assert orch.run() == 0
    assert agent.calls == []
    assert orch.invoker.stage_calls[StageId.FLOORPLAN] == 2
    verified = json.loads((orch.run_dir / "verified_repairs.json").read_text())
    assert verified[0]["known_error_id"] == "PDN-0185"
    assert verified[0]["verification_scope"] == "physical_signoff"
    assert verified[0]["repair_verified"] is True
    assert verified[0]["physical_signoff_verified"] is True
    repairs = [json.loads(line) for line in (orch.run_dir / "run.jsonl").read_text().splitlines()
               if '"event": "repair_decision"' in line]
    assert repairs[0]["choice"] == "auto"
    drc = json.loads((orch.stage_dir(StageId.DRC) / "drc_summary.json").read_text())
    assert drc["provenance"]["klayout_backend"] == "container"
    assert drc["provenance"]["deck_sha256"]
    assert drc["provenance"]["argv"][0:3] == ["docker", "run", "--rm"]
    assert drc["checked_gds"]["sha256"]


def test_physical_repair_is_promoted_without_simulation(cfg, toolchain, tmp_path):
    rtl = tmp_path / "rtl_without_tb"
    rtl.mkdir()
    (rtl / "widget.v").write_text((cfg.rtl_dir / "widget.v").read_text())
    cfg = replace(cfg, rtl_dir=rtl, repair_policy="auto")
    agent = ScriptedAgent()
    orch = Orchestrator(cfg, agent=agent)
    orch.invoker = toolchain(orch, fail={StageId.PDN: [
        ToolRun(argv=["openroad"], returncode=1, stdout=PDN_LOG, stderr="")
    ]})
    assert orch.run() == 3
    verified = json.loads((orch.run_dir / "verified_repairs.json").read_text())
    assert verified[0]["repair_verified"] is True
    assert verified[0]["functional_spec_verified"] is False
    assert verified[0]["physical_signoff_verified"] is True
    assert verified[0]["logical_identity_verified"] is True
    assert verified[0]["rtl_identity_preserved"] is True
    assert verified[0]["original_working_rtl_sha256"] == verified[0]["verified_working_rtl_sha256"]
    signoff = json.loads((orch.run_dir / "signoff.json").read_text())
    assert signoff["verification"]["sim"] == "skipped"
    assert not signoff["clean"]


def test_unproven_simulation_does_not_poison_physical_repair_scope(cfg, toolchain):
    cfg = replace(cfg, repair_policy="auto")
    orch = Orchestrator(cfg, agent=ScriptedAgent())
    invoker = toolchain(orch, fail={StageId.PDN: [
        ToolRun(argv=["openroad"], returncode=1, stdout=PDN_LOG, stderr="")
    ]})
    invoker.sim_stdout = "testbench exited normally without a verdict\n"
    orch.invoker = invoker
    assert orch.run() == 3
    verified = json.loads((orch.run_dir / "verified_repairs.json").read_text())
    pdn = next(r for r in verified if r.get("known_error_id") == "PDN-0185")
    assert pdn["repair_verified"] is True
    summary = json.loads((orch.run_dir / "verification_summary.json").read_text())
    assert summary["physical_signoff_verified"] is True
    assert summary["logical_identity_verified"] is True
    assert summary["functional_spec_verified"] is False


def test_non_tty_ask_never_reads_stdin(cfg, toolchain):
    def forbidden_input(_prompt):
        raise AssertionError("non-TTY policy attempted to read stdin")
    orch = Orchestrator(cfg, agent=ScriptedAgent(), interactive=False,
                        input_fn=forbidden_input)
    orch.invoker = toolchain(orch, fail={StageId.PDN: [
        ToolRun(argv=["openroad"], returncode=1, stdout=PDN_LOG, stderr="")
    ]})
    assert orch.run() == 3
    assert "manual" in (orch.run_dir / "failure_report.md").read_text().lower()


def test_interactive_prompt_offers_agent_and_manual(cfg, capsys):
    cfg = replace(cfg, repair_policy="ask")
    orch = Orchestrator(cfg, interactive=True, input_fn=lambda _: "2")
    msg = match_openroad_messages(PDN_LOG)[0]
    fix = lookup_known_fix(msg, pdn_context(PDN_LOG, facts={"top": "widget"}, history=[], ir=IR()))
    assert orch._ask_known_repair(type("S", (), {"id": StageId.PDN})(), fix) == "manual"
    shown = capsys.readouterr().out
    assert "Let rtl2gdsagi fix it" in shown and "I will fix it manually" in shown
