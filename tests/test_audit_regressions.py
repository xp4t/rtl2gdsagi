"""Regressions for the false-clean paths found by the 2026-08-13 audit.

Every test here fails against the behaviour that shipped before the audit
remediation. They are grouped by the audit's own finding IDs so a reader can
go from a claim in `results.md` to the thing that now prevents it.

The shared property under test is always the same one:

    absence of a recognised failure is not evidence of success.

A parser that cannot find the number it grades on, a tool that exited nonzero,
a report that only states half the answer, a proof that proved nothing -- each
of those is *unknown*, and unknown must never read as PASS.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rtl2gdsagi.agent.client import ScriptedAgent
from rtl2gdsagi.checks.tools import ToolRun, check_lec, check_openroad
from rtl2gdsagi.checks.verdict import VerdictKind
from rtl2gdsagi.ir import IR, SchemaViolation
from rtl2gdsagi.runner import Orchestrator
from rtl2gdsagi.stages import StageId
from rtl2gdsagi.taxonomy import Diagnosis, FailureClass
from rtl2gdsagi.state import StageStatus


def run(text: str, rc: int = 0) -> ToolRun:
    return ToolRun(argv=[], returncode=rc, stdout=text, stderr="")


# ---- P0-05: routing did not parse OpenROAD's real syntax -------------------

#: Captured verbatim from a real OV7670 detailed-route log.
REAL_ROUTE_LOG = """\
[INFO DRT-0195] Start 1st optimization iteration.
[INFO DRT-0199]   Number of violations = 900.
[INFO DRT-0195] Start 2nd optimization iteration.
[INFO DRT-0199]   Number of violations = 739.
[INFO DRT-0195] Start 5th optimization iteration.
[INFO DRT-0199]   Number of violations = 0.
[INFO DRT-0198] Complete detail routing.
Total number of vias = 7353.
"""


def test_real_openroad_violation_syntax_is_parsed():
    """OpenROAD writes '= 900.', not ': 900'.

    The original pattern required a digit immediately after whitespace, so it
    matched nothing at all in a real log: no count was recorded and routing
    passed with no violation evidence whatsoever.
    """
    v = check_openroad(run(REAL_ROUTE_LOG), StageId.ROUTING, outputs={})
    assert v.kind is VerdictKind.PASS
    assert v.metrics["route_violations"] == 0
    assert v.metrics["route_violation_iterations"] == 3


def test_the_terminal_iteration_decides_not_the_first():
    """Each iteration prints a count; only the last one is the result.

    Simply making the regex match would have selected 900 -- the first,
    worst, intermediate value -- and failed a route that actually converged.
    """
    v = check_openroad(run(REAL_ROUTE_LOG), StageId.ROUTING, outputs={})
    assert v.ok is True

    unconverged = REAL_ROUTE_LOG.replace(
        "[INFO DRT-0199]   Number of violations = 0.",
        "[INFO DRT-0199]   Number of violations = 38.",
    )
    bad = check_openroad(run(unconverged), StageId.ROUTING, outputs={})
    assert bad.kind is VerdictKind.FAIL
    assert bad.metrics["route_violations"] == 38


def test_routing_without_any_violation_count_fails_closed():
    log = "[INFO DRT-0198] Complete detail routing.\n"
    v = check_openroad(run(log), StageId.ROUTING, outputs={})
    assert v.kind is VerdictKind.FAIL
    assert "no violation count" in v.summary


def test_routing_that_never_completed_fails_closed():
    """A count from an aborted route describes nothing."""
    partial = "[INFO DRT-0199]   Number of violations = 0.\n"
    v = check_openroad(run(partial), StageId.ROUTING, outputs={})
    assert v.kind is VerdictKind.FAIL
    assert "completion" in v.summary


# ---- P0-09: one-sided and repeated antenna results -------------------------

def test_antenna_needs_both_halves_of_the_answer():
    """A missing side used to default to zero, so half a report read as clean."""
    nets_only = "[INFO ANT-0002] Found 0 net violations.\n"
    v = check_openroad(run(nets_only), StageId.ANTENNA, outputs={})
    assert v.kind is VerdictKind.FAIL
    assert "pin violation count" in v.summary

    pins_only = "[INFO ANT-0001] Found 0 pin violations.\n"
    v = check_openroad(run(pins_only), StageId.ANTENNA, outputs={})
    assert v.kind is VerdictKind.FAIL
    assert "net violation count" in v.summary


def test_a_later_antenna_result_cannot_be_hidden_by_an_earlier_clean_one():
    """check_antennas may run twice; the first match used to win."""
    log = (
        "[INFO ANT-0002] Found 0 net violations.\n"
        "[INFO ANT-0001] Found 0 pin violations.\n"
        "[INFO ANT-0002] Found 4 net violations.\n"
        "[INFO ANT-0001] Found 5 pin violations.\n"
    )
    v = check_openroad(run(log), StageId.ANTENNA, outputs={})
    assert v.kind is VerdictKind.FAIL
    assert v.metrics["antenna_net_violations"] == 4
    assert v.metrics["antenna_pin_violations"] == 5


def test_a_clean_antenna_report_still_passes():
    log = ("[INFO ANT-0002] Found 0 net violations.\n"
           "[INFO ANT-0001] Found 0 pin violations.\n")
    assert check_openroad(run(log), StageId.ANTENNA, outputs={}).kind is VerdictKind.PASS


# ---- P0-06: equivalence claimed on contradictory evidence ------------------

PROOF = (
    "EQY [w] run: Proved equivalence of partition 'w.a' using strategy 'sat'\n"
    "EQY [w] Successfully proved equivalence of partition w.a\n"
    "EQY [w] Successfully proved designs equivalent\n"
    "EQY [w] DONE (PASS, rc=0)\n"
)


def test_a_real_proof_still_passes():
    v = check_lec(run(PROOF), StageId.LEC_SYNTH)
    assert v.kind is VerdictKind.PASS
    assert v.metrics["partitions_proved"] == 1


def test_lec_pass_text_with_a_nonzero_exit_is_refused():
    v = check_lec(run(PROOF, rc=1), StageId.LEC_SYNTH)
    assert v.kind is VerdictKind.FAIL
    assert "exited 1" in v.summary


def test_lec_pass_text_alongside_a_mismatch_is_refused():
    contradictory = PROOF + (
        "EQY [w] Could not prove equivalence of partition 'w.b' in mode x: "
        "partitions not equivalent\n"
    )
    v = check_lec(run(contradictory), StageId.LEC_SYNTH)
    assert v.kind is VerdictKind.FAIL
    assert "contradicts itself" in v.summary


def test_lec_pass_text_alongside_an_unknown_is_refused():
    contradictory = PROOF + (
        "EQY [w] Could not prove equivalence of partition 'w.b' in mode x: "
        "equivalence unknown\n"
    )
    assert check_lec(run(contradictory), StageId.LEC_SYNTH).kind is VerdictKind.FAIL


def test_lec_that_proved_no_partitions_is_not_a_proof():
    """'DONE (PASS)' with nothing proved is an empty run, not equivalence."""
    vacuous = "EQY [w] Successfully proved designs equivalent\nEQY [w] DONE (PASS, rc=0)\n"
    v = check_lec(run(vacuous), StageId.LEC_SYNTH)
    assert v.kind is VerdictKind.FAIL
    assert "no partition was actually proved" in v.summary


def test_both_eqy_phrasings_count_as_a_proved_partition():
    """EQY prints the same fact two ways; only one was being matched."""
    only_successfully = (
        "EQY [w] Successfully proved equivalence of partition w.a\n"
        "EQY [w] Successfully proved designs equivalent\n"
        "EQY [w] DONE (PASS, rc=0)\n"
    )
    v = check_lec(run(only_successfully), StageId.LEC_SYNTH)
    assert v.kind is VerdictKind.PASS
    assert v.metrics["partitions_proved"] == 1


# ---- P0-08: executable strings and non-finite bounds in the schema ---------

@pytest.mark.parametrize("payload", [
    "buf; exec touch /tmp/pwned",
    "buf} ; puts hi ; {",
    "$(id)",
    "[exec id]",
    "two words",
    "buf\nputs hi",
])
def test_a_cell_name_field_cannot_carry_tcl(payload):
    """cts.root_buffer is interpolated straight into the CTS script.

    Tcl treats ';' as a command separator, so an unrestricted string field is
    an execution surface regardless of how the prompt is worded.
    """
    with pytest.raises(SchemaViolation):
        IR().update("cts", {"root_buffer": payload})


def test_a_legitimate_cell_name_is_still_accepted():
    ir = IR()
    ir.update("cts", {"root_buffer": "sky130_fd_sc_hd__clkbuf_16"})
    assert ir.get("cts", "root_buffer") == "sky130_fd_sc_hd__clkbuf_16"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_numbers_are_rejected_by_the_schema(value):
    """NaN compares False against every bound, so it defeats range checks."""
    with pytest.raises(SchemaViolation):
        IR().update("sta", {"slack_guardband_ns": value})


# ---- P0-04: DRC read a clean report out of a failed tool run ---------------

def _clean_report_but_tool_failed(toolchain, orch):
    """Let the mock write its clean DRC report, then report a crash."""
    inner = toolchain(orch)

    class CrashingDRC:
        stage_calls = inner.stage_calls

        def available(self, tool):
            return inner.available(tool)

        def run(self, tool, argv, *, cwd, timeout_s=3600, env=None, log_path=None):
            r = inner.run(tool, argv, cwd=cwd, timeout_s=timeout_s, env=env,
                          log_path=log_path)
            if Path(cwd).name.endswith("_drc"):
                return ToolRun(argv=argv, returncode=1, stdout=r.stdout,
                               stderr="terminate called after throwing")
            return r

    return CrashingDRC()


def test_drc_cannot_pass_when_the_tool_exited_nonzero(cfg, toolchain):
    """The exit code was not even passed to the DRC judge.

    A crashed KLayout next to a clean report -- from an earlier attempt, or
    written before the crash -- was read as a clean design.
    """
    orch = Orchestrator(cfg, agent=ScriptedAgent())
    orch.invoker = _clean_report_but_tool_failed(toolchain, orch)
    rc = orch.run()

    assert rc != 0
    assert orch.state.stage(StageId.DRC).status is not StageStatus.OK
    report = (orch.run_dir / "failure_report.md").read_text()
    assert "drc" in report


# ---- P0-01/P0-06: certification on missing or vacuous verification ---------

def test_signoff_bundle_records_the_verification_it_relied_on(cfg, toolchain):
    """A clean bundle must be able to show what was actually proved."""
    orch = Orchestrator(cfg, agent=ScriptedAgent())
    orch.invoker = toolchain(orch)
    assert orch.run() == 0

    bundle = json.loads((orch.run_dir / "signoff.json").read_text())
    assert bundle["clean"] is True
    assert bundle["verification"]["sim"] == "ok"
    assert bundle["verification"]["lec_synth"] == "ok"


# ---- P0-08: model authority over rollback and classification ---------------

def test_a_proposed_rollback_to_a_later_stage_is_refused(cfg, toolchain):
    """`implicated_stage` used to win outright, including pointing forward.

    Resuming *after* the stage that just failed leaves every stage in between
    un-rerun, so the signoff gates would grade artifacts nobody regenerated.
    """
    agent = ScriptedAgent(diagnoses=[
        Diagnosis(
            failure=FailureClass.ROUTING,
            evidence="87 violations",
            implicated_stage=StageId.SIGNOFF,   # forward: skip DRC/LVS/antenna
            confidence=0.9,
            config_delta={"routing": {"droute_iters": 48}},
        )
    ])
    fail = {StageId.ROUTING: [
        ToolRun(argv=[], returncode=0,
                stdout=("[INFO DRT-0199]   Number of violations = 87.\n"
                        "[INFO DRT-0198] Complete detail routing.\n"),
                stderr="")
    ]}
    orch = Orchestrator(cfg, agent=agent)
    orch.invoker = toolchain(orch, fail=fail)
    orch.run()

    # Routing was re-run rather than jumped past, and the gates after it all
    # actually executed.
    assert orch.invoker.stage_calls[StageId.ROUTING] == 2
    for sid in (StageId.DRC, StageId.LVS, StageId.ANTENNA):
        assert orch.state.stage(sid).status is StageStatus.OK, sid


def test_timing_cannot_be_fixed_by_relaxing_the_clock():
    """Lengthening the period moves the target instead of fixing the design.

    The SDC_TARGETS token and the SDC class already named this, but the `sdc`
    IR section was never mapped in the section guard, so for a setup or hold
    failure the check never fired -- and the sdc fields are model-writable.
    """
    from rtl2gdsagi.safety import SafetyViolation, review_diagnosis

    relax = Diagnosis(
        failure=FailureClass.SETUP,
        evidence="signoff setup WNS -0.4ns",
        implicated_stage=StageId.SDC,
        confidence=0.9,
        config_delta={"sdc": {"default_clock_period_ns": 100.0}},
    )
    with pytest.raises(SafetyViolation):
        review_diagnosis(relax)


def test_reclassifying_a_failure_cannot_unlock_a_forbidden_section():
    """Forbidden IR sections follow the deterministic class, not the model's.

    A hold violation may not be answered by rewriting the timing constraints.
    Relabelling it as something more permissive used to hand those sections
    back, because the safety review read the class off the model's own reply.
    """
    from rtl2gdsagi.safety import SafetyViolation, review_diagnosis

    dodge = Diagnosis(
        failure=FailureClass.CONGESTION,       # the model's claim
        evidence="looks like congestion to me",
        implicated_stage=StageId.PLACEMENT,
        confidence=0.9,
        config_delta={"sdc": {"default_clock_period_ns": 100.0}},
    )
    # Believing the model's own label: allowed.
    review_diagnosis(dodge)
    # Judged against what actually happened: refused.
    with pytest.raises(SafetyViolation):
        review_diagnosis(dodge, policy_failure=FailureClass.HOLD)


# ---- P0-03 (partial): SDC reference clock was chosen from a set -------------

def test_the_sdc_reference_clock_is_stable_across_processes():
    """Identical inputs must render identical SDC.

    The reference clock used by every set_input_delay/set_output_delay was
    taken as `next(iter(clock_names))` from a *set*. Python randomises string
    hashing per process, so on a multi-clock design the answer changed between
    runs of the same design -- three different clocks in six processes when
    measured. Timing results are not comparable across runs if the constraints
    are not.
    """
    import subprocess
    import sys

    snippet = (
        "from rtl2gdsagi.ir import IR\n"
        "from rtl2gdsagi.render import render_sdc\n"
        "class C:\n"
        "    facts = {'clocks': [{'name': 'i_pclk', 'period_ns': 10.0},\n"
        "                        {'name': 'i_clk', 'period_ns': 10.0},\n"
        "                        {'name': 'sys_clock', 'period_ns': 10.0},\n"
        "                        {'name': 'ref_clk', 'period_ns': 10.0}],\n"
        "             'inputs': ['d_in'], 'outputs': ['q_out']}\n"
        "print([l for l in render_sdc(IR(), C()).splitlines()\n"
        "       if 'set_input_delay' in l][0])\n"
    )
    seen = {
        subprocess.run([sys.executable, "-c", snippet],
                       capture_output=True, text=True, check=True).stdout.strip()
        for _ in range(6)
    }
    assert len(seen) == 1, f"SDC differed between processes: {seen}"
    assert "i_pclk" in seen.pop(), "expected the first declared clock"
