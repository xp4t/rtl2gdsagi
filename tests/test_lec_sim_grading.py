"""Grading for formal equivalence and simulation.

Both are graded with a distinction that matters more than it might look:

* LEC: "partitions not equivalent" (the prover produced a counterexample)
  versus "equivalence unknown" (it hit its limit). Both block — unverified is
  unverified — but they are worded differently, and *neither* asserts that the
  design is buggy. This flow still reports counterexamples for sequential logic
  that is known to be correct, so an unqualified "your netlist is wrong" would
  be the worst error message a beginner could receive.

* sim: a testbench that runs to completion without checking anything is neither
  a pass nor a failure. Failing a whole tapeout flow because a testbench does
  not print the word PASS would be absurd; calling it a pass would be a lie.

All strings below are copied from real tool output, not invented.
"""

from __future__ import annotations

import pytest

from rtl2gdsagi.checks.tools import ToolRun, check_lec, check_sim
from rtl2gdsagi.checks.verdict import VerdictKind
from rtl2gdsagi.stages import StageId
from rtl2gdsagi.taxonomy import FailureClass

W = "/tmp/work"


def eqy(*lines: str, rc: int = 0) -> ToolRun:
    body = "\n".join(f"EQY 22:48:49 [{W}] {ln}" for ln in lines)
    return ToolRun(argv=[], returncode=rc, stdout=body, stderr="")


PROVED = "run: Proved equivalence of partition '{}' using strategy 'sat'"
UNKNOWN = ("run: Could not prove equivalence of partition '{}' using "
           "strategy 'sat': equivalence unknown")
NOT_EQUIV = ("run: Could not prove equivalence of partition '{}' using "
             "strategy 'sat': partitions not equivalent")


# ---- LEC ------------------------------------------------------------------

def test_all_partitions_proved_is_a_pass():
    v = check_lec(
        eqy(PROVED.format("top.a"), PROVED.format("top.b"),
            "Successfully proved designs equivalent", "DONE (PASS, rc=0)"),
        StageId.LEC_SYNTH,
    )
    assert v.kind is VerdictKind.PASS
    assert v.metrics["partitions_proved"] == 2


def test_a_reported_counterexample_blocks_without_accusing_the_design():
    v = check_lec(
        eqy(PROVED.format("top.a"), NOT_EQUIV.format("top.b"),
            "DONE (FAIL, rc=2)", rc=2),
        StageId.LEC_SYNTH,
    )
    assert v.blocks is True
    assert v.failure is FailureClass.LEC_MISMATCH
    assert v.metrics["partitions_not_equivalent"] == 1
    assert "NOT established" in v.summary
    # Must not assert the design is buggy: this flow still produces
    # counterexamples on sequential logic that is known to be correct.
    assert "unverified rather than as proof of a bug" in v.summary


def test_prover_giving_up_does_not_claim_the_netlist_is_wrong():
    """The real OV7670 result: 0 not-equivalent, many unknown."""
    v = check_lec(
        eqy(PROVED.format("top.a"), UNKNOWN.format("top.b"),
            UNKNOWN.format("top.c"), "DONE (FAIL, rc=2)", rc=2),
        StageId.LEC_SYNTH,
    )
    assert v.blocks is True                       # equivalence is still unproven
    assert v.metrics["partitions_not_equivalent"] == 0
    assert v.metrics["partitions_unknown"] == 2
    # The wording must not accuse the design.
    assert "not evidence that the netlist is wrong" in v.summary
    assert "reported a counterexample" not in v.summary


def test_a_counterexample_outranks_unknowns():
    """One real mismatch matters more than any number of undecided partitions."""
    v = check_lec(
        eqy(UNKNOWN.format("top.a"), NOT_EQUIV.format("top.b"),
            UNKNOWN.format("top.c"), "DONE (FAIL, rc=2)", rc=2),
        StageId.LEC_SYNTH,
    )
    assert "reported a counterexample" in v.summary


def test_lec_with_no_verdict_is_not_a_pass():
    v = check_lec(eqy("run: Running strategy 'sat' on 'top.a'.."), StageId.LEC_SYNTH)
    assert v.blocks is True
    assert "refusing to assume" in v.summary


def test_lec_config_error_is_not_reported_as_a_design_problem():
    r = ToolRun(argv=[], returncode=1, stdout="",
                stderr="ERROR: unknown option 'depth' in lec.eqy line 5")
    v = check_lec(r, StageId.LEC_SYNTH)
    assert v.failure is FailureClass.TCL_CONFIG
    assert "could not start" in v.summary


def test_lec_failures_escalate_rather_than_being_auto_fixed():
    """No agent may 'fix' an equivalence failure by editing RTL."""
    v = check_lec(eqy(NOT_EQUIV.format("top.b"), "DONE (FAIL, rc=2)", rc=2),
                  StageId.LEC_SYNTH)
    assert v.escalate is True


# ---- simulation -----------------------------------------------------------

def sim(text: str, rc: int = 0) -> ToolRun:
    return ToolRun(argv=[], returncode=rc, stdout=text, stderr="")


def test_explicit_pass_is_a_pass():
    v = check_sim(sim("Running tests...\nALL TESTS PASSED\n"), testbench="a_tb.v")
    assert v.kind is VerdictKind.PASS


@pytest.mark.parametrize("line", [
    "$error: expected 8'h05 got 8'h00",
    "ERROR: data mismatch at time 1200",
    "Assertion failed: addr must be stable",
    "TEST FAILED",
])
def test_explicit_failures_block_and_escalate(line):
    v = check_sim(sim(f"starting\n{line}\n"), testbench="a_tb.v")
    assert v.blocks is True
    assert v.failure is FailureClass.RTL_FUNCTIONAL
    assert v.escalate is True      # a functional bug is a human's call


def test_non_self_checking_testbench_is_below_target_not_failed():
    """It ran clean but checked nothing. That is worth saying, not worth
    stopping a tapeout for."""
    v = check_sim(sim("VCD info: dumpfile dump.vcd opened\n"), testbench="a_tb.v")
    assert v.kind is VerdictKind.QOR_BELOW_TARGET
    assert v.ok is True and v.blocks is False
    assert "not self-checking" in v.summary


def test_nonzero_exit_blocks():
    v = check_sim(sim("", rc=1), testbench="a_tb.v")
    assert v.blocks is True


def test_simulation_timeout_is_an_environment_problem():
    r = ToolRun(argv=[], returncode=124, stdout="", stderr="", timed_out=True)
    assert check_sim(r).failure is FailureClass.TOOL_RUNTIME


def test_the_word_pass_inside_another_word_is_not_a_pass():
    """'bypass'/'passthrough' must not be read as a passing result."""
    v = check_sim(sim("configuring bypass mode\npassthrough enabled\n"),
                  testbench="a_tb.v")
    assert v.kind is VerdictKind.QOR_BELOW_TARGET
