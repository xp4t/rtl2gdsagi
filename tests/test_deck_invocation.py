"""How the signoff decks are invoked.

The SKY130 KLayout runsets gate their rule groups behind their own switches:

    if $feol == "1" || $feol == "true"   # front-end-of-line rules
    if $beol == "1" || $beol == "true"   # back-end-of-line rules
    if $offgrid == "1" ...
    if $floating_met == "1" ...

Invoked without them the deck loads cleanly, writes a well-formed .lyrdb, and
checks *nothing*. That report has zero declared categories and zero items, which
is indistinguishable from "clean" to anything that just counts violations.

The parser catches it (a ruleless report is not a pass), but the invocation must
be right in the first place. These tests pin both halves.
"""

from __future__ import annotations

from rtl2gdsagi.agent.client import ScriptedAgent
from rtl2gdsagi.checks.klayout_drc import parse_drc_report
from rtl2gdsagi.runner import Orchestrator
from rtl2gdsagi.stages import StageId, Tool


def _argv_for(cfg, toolchain, stage: StageId) -> list[str]:
    orch = Orchestrator(cfg, agent=ScriptedAgent())
    orch.invoker = toolchain(orch)
    orch.run()
    for tool, argv in [(t, a) for t, a in _calls(orch)]:
        if tool is Tool.KLAYOUT and str(stage.value) in " ".join(argv):
            return argv
    # fall back: find by the deck path
    return next(
        argv for tool, argv in _calls(orch)
        if tool is Tool.KLAYOUT and any("drc" in x or "lvs" in x for x in argv)
    )


def _calls(orch):
    inv = orch.invoker
    return getattr(inv, "calls", []) or getattr(getattr(inv, "inner", None), "calls", [])


def _render_argv(cfg, stage: StageId) -> list[str]:
    """Build the argv for one stage without running the flow."""
    from pathlib import Path

    orch = Orchestrator(cfg, agent=ScriptedAgent())
    orch.prepare()
    spec_inputs = {
        "final_gds": Path("/tmp/x.gds"), "netlist": Path("/tmp/x.v"),
        "routed_netlist": Path("/tmp/xr.v"),
    }
    from rtl2gdsagi.stages import get_stage
    spec = get_stage(stage)
    ctx = orch._context(spec)
    ctx.inputs.update(spec_inputs)
    ctx.outputs.update(orch._outputs_for(spec, orch.stage_dir(stage)))
    return orch._argv(spec, None, ctx)


def test_drc_invocation_enables_every_rule_group(cfg):
    argv = " ".join(_render_argv(cfg, StageId.DRC))
    for switch in ("feol=true", "beol=true", "offgrid=true", "floating_met=true"):
        assert switch in argv, f"missing {switch}: the deck would check nothing"


def test_drc_invocation_uses_the_decks_own_variable_names(cfg):
    argv = " ".join(_render_argv(cfg, StageId.DRC))
    assert "top_cell=" in argv and "topcell=" not in argv
    assert "thr=" in argv and "threads=" not in argv
    assert "report=" in argv and "input=" in argv


def test_lvs_invocation_uses_the_decks_own_variable_names(cfg):
    argv = " ".join(_render_argv(cfg, StageId.LVS))
    assert "top_cell=" in argv
    assert "schematic=" in argv and "target_netlist=" in argv
    assert "thr=" in argv


def test_lvs_compares_against_the_post_route_netlist_when_available(cfg):
    """CTS and repair passes change the netlist; LVS must use the final one."""
    argv = " ".join(_render_argv(cfg, StageId.LVS))
    assert "xr.v" in argv, "LVS should prefer routed_netlist over the synth netlist"


def test_a_ruleless_report_is_not_a_pass(tmp_path):
    """What a mis-invoked deck actually produces."""
    p = tmp_path / "noswitches.lyrdb"
    p.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<report-database><description>SKY130 DRC runset</description>"
        "<top-cell>cam_top</top-cell><categories></categories>"
        "<items></items></report-database>",
        encoding="utf-8",
    )
    r = parse_drc_report(p, expected_top="cam_top")
    assert r.total_violations == 0      # looks clean by naive counting
    assert r.clean is False             # but is correctly refused
    assert any("checked nothing" in x for x in r.problems)
