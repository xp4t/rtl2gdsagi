"""End-to-end orchestration against a fake toolchain.

Exercises the whole state machine: a clean run, per-stage retry, table-driven
rollback to a *distant* stage, escalation instead of looping, duplicate-config
refusal, and the signoff aggregator's GDS binding.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rtl2gdsagi.agent.client import ScriptedAgent
from rtl2gdsagi.checks.tools import ToolRun
from rtl2gdsagi.runner import Orchestrator
from rtl2gdsagi.stages import StageId, Tool
from rtl2gdsagi.state import RunState, StageStatus
from rtl2gdsagi.taxonomy import Diagnosis, FailureClass


def _dirty_drc(toolchain, orch):
    """Wrap the fake toolchain so DRC emits the real 4743-violation report."""
    from conftest import _fresh_copy
    fixtures = Path(__file__).parent / "fixtures" / "klayout"
    inner = toolchain(orch)

    class DirtyDRC:
        stage_calls = inner.stage_calls

        def available(self, tool):
            return inner.available(tool)

        def run(self, tool, argv, *, cwd, timeout_s=3600, env=None, log_path=None):
            r = inner.run(tool, argv, cwd=cwd, timeout_s=timeout_s, env=env,
                          log_path=log_path)
            if Path(cwd).name.endswith("_drc"):
                _fresh_copy(
                    fixtures / "drc_dirty_4743.lyrdb",
                    Path(cwd) / "drc.lyrdb", orch.cfg.top,
                )
            return r

    return DirtyDRC()


def build(cfg, toolchain, *, fail=None, agent=None, budget=None, missing=None):
    orch = Orchestrator(cfg, agent=agent or ScriptedAgent(), global_budget=budget)
    orch.invoker = toolchain(orch, fail=fail, missing=missing)
    return orch


# ---- clean run ------------------------------------------------------------

def test_clean_run_reaches_signoff(cfg, toolchain):
    orch = build(cfg, toolchain)
    assert orch.run() == 0

    state = RunState.load(orch.run_dir)
    assert state.status.value == "ok"
    assert state.stage(StageId.SIGNOFF).status is StageStatus.OK
    for sid in (StageId.SYNTHESIS, StageId.ROUTING, StageId.DRC,
                StageId.LVS, StageId.ANTENNA, StageId.LEC_ROUTE):
        assert state.stage(sid).status is StageStatus.OK, sid


def test_signoff_bundle_binds_every_gate_to_one_gds(cfg, toolchain):
    orch = build(cfg, toolchain)
    assert orch.run() == 0

    bundle = json.loads((orch.run_dir / "signoff.json").read_text())
    assert bundle["clean"] is True
    assert bundle["problems"] == []
    assert bundle["final_gds"]["sha256"]
    assert set(bundle["gates"]) == {
        "drc", "lvs", "antenna", "sta_signoff", "lec_route"
    }
    assert all(v == "ok" for v in bundle["gates"].values())


def test_optional_stage_without_tooling_is_skipped_not_failed(cfg, toolchain):
    """A missing tool is an environment problem, not a design failure.

    The stage is skipped rather than failed -- but see
    test_an_automatically_skipped_gate_still_blocks_signoff: being skipped
    must not let the run certify.
    """
    orch = build(cfg, toolchain, missing={Tool.IVERILOG})
    orch.run()
    assert orch.state.stage(StageId.SIM).status is StageStatus.SKIPPED


def test_an_automatically_skipped_gate_still_blocks_signoff(cfg, toolchain):
    """The false-clean this suite used to assert.

    `sim` is optional so the runner can skip it when iverilog is absent. The
    signoff aggregator looked only at stages the *user* skipped with --skip,
    so an automatic skip went unremarked and the run certified a design that
    had never been simulated. The reason a proof is missing does not make the
    proof exist.
    """
    orch = build(cfg, toolchain, missing={Tool.IVERILOG})
    rc = orch.run()

    assert orch.state.stage(StageId.SIM).status is StageStatus.SKIPPED
    assert rc != 0, "a run that never simulated the design must not certify"

    bundle = json.loads((orch.run_dir / "signoff.json").read_text())
    assert bundle["clean"] is False
    assert any("sim" in p for p in bundle["problems"]), bundle["problems"]


def test_a_gate_that_proved_nothing_does_not_certify(cfg, toolchain, monkeypatch):
    """A testbench that runs but checks nothing grades below target.

    That is enough to keep the flow moving and not enough to sign off, so
    certification looks at the verdict rather than at the stage status --
    which is OK in both cases.
    """
    import conftest
    monkeypatch.setattr(conftest.FakeToolchain, "sim_stdout", "no result here\n")

    orch = build(cfg, toolchain)
    rc = orch.run()

    sim = orch.state.stage(StageId.SIM)
    assert sim.status is StageStatus.OK
    assert sim.last_verdict == "qor_below_target"
    assert rc != 0

    bundle = json.loads((orch.run_dir / "signoff.json").read_text())
    assert bundle["clean"] is False
    assert any("sim" in p for p in bundle["problems"]), bundle["problems"]


def test_source_rtl_is_never_written(cfg, toolchain, design):
    before = {p: p.read_bytes() for p in design.rglob("*.v")}
    orch = build(cfg, toolchain)
    orch.run()
    after = {p: p.read_bytes() for p in design.rglob("*.v")}
    assert before == after
    assert (orch.run_dir / "work" / "rtl" / "widget.v").is_file()


def test_run_log_records_every_stage(cfg, toolchain):
    orch = build(cfg, toolchain)
    orch.run()
    events = orch.log.read_events()
    kinds = {e["event"] for e in events}
    assert {"run_start", "stage_start", "tool_run", "result_check",
            "stage_end", "artifact", "run_end"} <= kinds


# ---- retry within a stage -------------------------------------------------

def test_stage_retries_then_succeeds(cfg, toolchain):
    """Routing fails once with real violations, agent retunes, second try passes."""
    agent = ScriptedAgent(diagnoses=[
        Diagnosis(
            failure=FailureClass.ROUTING,
            evidence="12 violations",
            implicated_stage=StageId.ROUTING,
            confidence=0.8,
            config_delta={"routing": {"droute_iters": 48}},
        )
    ])
    fail = {StageId.ROUTING: [
        ToolRun(argv=[], returncode=0, stdout="Total number of violations: 12\n", stderr="")
    ]}
    orch = build(cfg, toolchain, fail=fail, agent=agent)
    assert orch.run() == 0

    assert orch.state.stage(StageId.ROUTING).attempts == 2
    assert orch.ir.get("routing", "droute_iters") == 48
    assert len(agent.calls) == 1


def test_exhausting_retries_without_a_deeper_target_escalates(cfg, toolchain):
    """CTS has no deeper escalate_to target, so it stops rather than looping.

    Each diagnosis proposes a genuinely different skew target, so every attempt
    is distinct and the stage really does burn its whole retry budget.
    """
    agent = ScriptedAgent(diagnoses=[
        Diagnosis(
            FailureClass.CTS, "clock tree build failed", StageId.CTS, 0.6,
            config_delta={"cts": {"target_skew_ns": 0.3 + 0.1 * i}},
        )
        for i in range(5)
    ])
    fail = {StageId.CTS: [
        ToolRun(argv=[], returncode=1, stdout="",
                stderr="[ERROR CTS-0001] could not build clock tree")
        for _ in range(6)
    ]}
    orch = build(cfg, toolchain, fail=fail, agent=agent)
    assert orch.run() == 3  # escalated

    assert orch.state.stage(StageId.CTS).attempts == cfg.retry_limit
    report = (orch.run_dir / "failure_report.md").read_text()
    assert "cts" in report
    assert "exhausted" in report


def test_remediation_that_changes_nothing_stops_early(cfg, toolchain):
    """A diagnosis with an empty delta means the next attempt is identical.

    Stopping at that point is correct: repeating a byte-identical attempt can
    only waste budget (review 10, duplicate-config refusal).
    """
    agent = ScriptedAgent(diagnoses=[
        Diagnosis(FailureClass.GDS, "streamout failed", StageId.GDSOUT, 0.6)
        for _ in range(5)
    ])
    fail = {StageId.GDSOUT: [
        ToolRun(argv=[], returncode=2, stdout="", stderr="gdsout: top cell not found")
        for _ in range(6)
    ]}
    orch = build(cfg, toolchain, fail=fail, agent=agent)
    assert orch.run() == 3

    # Stopped before spending the third attempt, because it would be identical.
    assert orch.state.stage(StageId.GDSOUT).attempts < cfg.retry_limit
    report = (orch.run_dir / "failure_report.md").read_text()
    assert "identical" in report


# ---- table-driven rollback to a distant stage -----------------------------

def test_routing_failure_rolls_back_to_placement(cfg, toolchain):
    """The mechanism the original diagram could not express (review 2.2)."""
    agent = ScriptedAgent(diagnoses=[
        Diagnosis(
            failure=FailureClass.CONGESTION,
            evidence="overflow concentrated core-wide",
            implicated_stage=StageId.PLACEMENT,
            confidence=0.85,
            config_delta={"placement": {"target_density": 0.40}},
        )
    ])
    fail = {StageId.ROUTING: [
        ToolRun(argv=[], returncode=0, stdout="Total number of violations: 87\n", stderr="")
    ]}
    orch = build(cfg, toolchain, fail=fail, agent=agent)
    assert orch.run() == 0

    # Placement ran twice: once originally, once after the rollback.
    assert orch.invoker.stage_calls[StageId.PLACEMENT] == 2
    assert orch.invoker.stage_calls[StageId.CTS] == 2
    assert orch.ir.get("placement", "target_density") == pytest.approx(0.40)


def test_rollback_invalidates_downstream_checkpoints(cfg, toolchain):
    agent = ScriptedAgent(diagnoses=[
        Diagnosis(
            failure=FailureClass.CONGESTION, evidence="overflow",
            implicated_stage=StageId.FLOORPLAN, confidence=0.9,
            config_delta={"floorplan": {"core_utilization": 0.30}},
        )
    ])
    fail = {StageId.ROUTING: [
        ToolRun(argv=[], returncode=0, stdout="Total number of violations: 99\n", stderr="")
    ]}
    orch = build(cfg, toolchain, fail=fail, agent=agent)
    assert orch.run() == 0

    # Everything from floorplan onward re-ran.
    for sid in (StageId.FLOORPLAN, StageId.PDN, StageId.PLACEMENT,
                StageId.CTS, StageId.ROUTING):
        assert orch.invoker.stage_calls[sid] >= 2, sid
    assert orch.ir.get("floorplan", "core_utilization") == pytest.approx(0.30)


# ---- escalation instead of looping ---------------------------------------

def test_library_failure_escalates_immediately(cfg, toolchain):
    """Review 9.4: a library-integrity problem has no autonomous resolution."""
    fail = {StageId.ROUTING: [
        ToolRun(
            argv=[], returncode=1,
            stdout="[ERROR DRT-0416] Term VDD of _2468_ contains offgrid pin shape\n",
            stderr="",
        )
    ]}
    orch = build(cfg, toolchain, fail=fail)
    assert orch.run() == 3

    report = (orch.run_dir / "failure_report.md").read_text()
    assert "library" in report.lower()
    assert "immutable" in report.lower()
    # It must not have burned retries on something it cannot fix.
    assert orch.state.stage(StageId.ROUTING).attempts == 1


def test_agent_escalation_is_honoured(cfg, toolchain):
    agent = ScriptedAgent(diagnoses=[
        Diagnosis(
            failure=FailureClass.ROUTING, evidence="unclear",
            implicated_stage=None, confidence=0.1,
            reasoning="evidence does not support a confident root cause",
            escalated=True,
        )
    ])
    fail = {StageId.ROUTING: [
        ToolRun(argv=[], returncode=0, stdout="Total number of violations: 5\n", stderr="")
    ]}
    orch = build(cfg, toolchain, fail=fail, agent=agent)
    assert orch.run() == 3
    assert "escalated" in (orch.run_dir / "failure_report.md").read_text().lower()


# ---- safety in the live loop ---------------------------------------------

def test_agent_cannot_weaken_a_signoff_check_mid_run(cfg, toolchain):
    """A diagnosis proposing to touch the DRC section aborts the run."""
    agent = ScriptedAgent(diagnoses=[
        Diagnosis(
            failure=FailureClass.DRC, evidence="violations",
            implicated_stage=StageId.ROUTING, confidence=0.9,
            config_delta={"drc": {"threads": 1}},
        )
    ])
    orch = Orchestrator(cfg, agent=agent)
    orch.invoker = _dirty_drc(toolchain, orch)
    assert orch.run() == 5  # safety violation exit code


def test_budget_exhaustion_stops_the_run(cfg, toolchain):
    agent = ScriptedAgent(diagnoses=[
        Diagnosis(FailureClass.ROUTING, "viol", StageId.ROUTING, 0.5,
                  config_delta={"routing": {"droute_iters": 33 + i}})
        for i in range(10)
    ])
    fail = {StageId.ROUTING: [
        ToolRun(argv=[], returncode=0, stdout="Total number of violations: 7\n", stderr="")
        for _ in range(10)
    ]}
    orch = build(cfg, toolchain, fail=fail, agent=agent, budget=1)
    code = orch.run()
    assert code in (3, 4)
    assert orch.budget.remaining == 0


# ---- real DRC data in the live loop --------------------------------------

def test_dirty_drc_report_fails_the_run(cfg, toolchain):
    """The 4743-violation report must stop the flow, not pass it."""
    orch = Orchestrator(cfg, agent=ScriptedAgent())
    orch.invoker = _dirty_drc(toolchain, orch)
    assert orch.run() != 0
    assert orch.state.stage(StageId.SIGNOFF).status is not StageStatus.OK

    summary = json.loads((orch.stage_dir(StageId.DRC) / "drc_summary.json").read_text())
    assert summary["total_violations"] == 4743
    assert summary["clean"] is False


# ---- resume ---------------------------------------------------------------

def test_state_file_is_valid_json_after_every_transition(cfg, toolchain):
    orch = build(cfg, toolchain)
    orch.run()
    data = json.loads((orch.run_dir / "run_state.json").read_text())
    assert data["version"] == 1
    assert data["status"] == "ok"
    assert "stages" in data and "artifacts" in data


def test_resume_from_skips_earlier_stages(cfg, toolchain):
    from dataclasses import replace
    orch = build(cfg, toolchain)
    orch.run()

    cfg2 = replace(cfg, resume_from=StageId.GDSOUT)
    orch2 = build(cfg2, toolchain)
    # Prior artifacts are not on disk for the new run, so this must fail
    # loudly about the missing input rather than silently "succeeding".
    code = orch2.run()
    assert code != 0
    assert orch2.invoker.stage_calls.get(StageId.SYNTHESIS) is None


def test_any_user_skipped_stage_fails_signoff(cfg, toolchain):
    """--skip measures the flow; it must never yield a clean certification.

    lec_synth is not one of the GDS-bound signoff gates, so without this the
    run could reach a clean signoff.json having never proved the netlist
    matches the RTL.
    """
    from dataclasses import replace

    cfg2 = replace(cfg, skip_stages=frozenset({StageId.LEC_SYNTH}))
    orch = build(cfg2, toolchain)
    code = orch.run()

    assert code != 0
    assert orch.state.stage(StageId.LEC_SYNTH).status is StageStatus.SKIPPED
    bundle = json.loads((orch.run_dir / "signoff.json").read_text())
    assert bundle["clean"] is False
    assert any("skipped at the user's request" in p for p in bundle["problems"])


def test_a_run_with_no_skips_still_signs_off(cfg, toolchain):
    """The guard must not fire on a normal run."""
    orch = build(cfg, toolchain)
    assert orch.run() == 0
    assert json.loads((orch.run_dir / "signoff.json").read_text())["clean"] is True
