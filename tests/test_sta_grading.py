"""How STA results are graded.

Two things this pins, both found on the real OV7670 run:

* An output tied to a constant (`assign o_pwdn = 0;`) has no timing arc, so
  OpenSTA reports it as an unconstrained endpoint. That is correct and benign,
  and must not hard-fail a design that otherwise meets timing.
* An undefined clock *is* a real gap: every path through it goes unchecked,
  which is exactly the "reports falsely clean timing" failure mode.
"""

from __future__ import annotations

from rtl2gdsagi.checks.tools import ToolRun, check_sta
from rtl2gdsagi.checks.verdict import VerdictKind
from rtl2gdsagi.stages import StageId
from rtl2gdsagi.taxonomy import FailureClass


def sta_out(setup=1.0, hold=0.5, extra="") -> str:
    return (
        "=== check_setup ===\n" + extra +
        "=== setup ===\nno paths\n=== hold ===\nno paths\n=== wns/tns ===\n"
        f"setup_wns {setup}\nsetup_tns 0.0\nhold_wns {hold}\nhold_tns 0.0\n"
    )


def run(text: str, rc: int = 0) -> ToolRun:
    return ToolRun(argv=[], returncode=rc, stdout=text, stderr="")


def test_met_timing_passes():
    v = check_sta(run(sta_out()), StageId.STA_SIGNOFF)
    assert v.kind is VerdictKind.PASS


def test_unconstrained_endpoints_block_the_deciding_gates():
    """An unconstrained endpoint is a path timing never looked at.

    This previously passed as `qor_below_target`, on the reasoning that such
    endpoints are constant-driven and have no timing arc. Nothing checked
    that. The same report shape is produced by an incomplete SDC that simply
    failed to constrain real paths, and the two are indistinguishable from the
    endpoint count alone -- so the gates that decide the design refuse it.
    """
    text = sta_out(extra="Warning: There are 4 unconstrained endpoints.\n"
                         "  o_pwdn\n  o_reset\n  o_sda_out\n  _1670_/D\n")
    for stage in (StageId.STA_POSTCTS, StageId.STA_SIGNOFF):
        v = check_sta(run(text), stage)
        assert v.kind is VerdictKind.FAIL, stage
        assert v.failure is FailureClass.SDC
        assert v.metrics["unconstrained_endpoints"] == 4

    # Pre-layout is explicitly not authoritative, so it stays advisory.
    pre = check_sta(run(text), StageId.STA_PRE)
    assert pre.kind is VerdictKind.QOR_BELOW_TARGET
    assert pre.ok is True and pre.blocks is False


def test_a_fully_constrained_report_still_passes():
    v = check_sta(run(sta_out()), StageId.STA_SIGNOFF)
    assert v.kind is VerdictKind.PASS
    assert v.metrics["unconstrained_endpoints"] == 0


def test_undefined_clock_is_a_hard_sdc_failure():
    text = sta_out(extra="Warning: no clocks defined.\n")
    v = check_sta(run(text), StageId.STA_SIGNOFF)
    assert v.kind is VerdictKind.FAIL
    assert v.failure is FailureClass.SDC
    assert v.blocks is True


def test_negative_hold_after_cts_blocks_and_implicates_cts():
    v = check_sta(run(sta_out(hold=-0.15)), StageId.STA_POSTCTS)
    assert v.failure is FailureClass.HOLD
    assert v.blocks is True


def test_negative_setup_at_signoff_blocks():
    v = check_sta(run(sta_out(setup=-0.4)), StageId.STA_SIGNOFF)
    assert v.failure is FailureClass.SETUP
    assert v.blocks is True


def test_negative_setup_pre_layout_never_blocks():
    """Review 4.9: an estimate is not grounds to stop or roll back."""
    v = check_sta(run(sta_out(setup=-0.4)), StageId.STA_PRE)
    assert v.ok is True
    assert v.kind is VerdictKind.QOR_BELOW_TARGET


def test_guardband_tightens_acceptance_and_never_relaxes_it():
    """A guardband is a margin the design must clear, not an allowance.

    This test previously asserted the opposite -- that a guardband of 0.2
    admitted a setup slack of -0.05 -- which is how the field became a way to
    make failing timing pass. It is model-writable, so "propose a larger
    guardband" would have been a working remedy for a real timing violation.
    """
    ok = check_sta(run(sta_out(setup=0.05)), StageId.STA_SIGNOFF, guardband=0.0)
    assert ok.kind is VerdictKind.PASS

    # Negative slack fails at any guardband; a bigger one must never rescue it.
    for gb in (0.0, 0.2, 5.0):
        v = check_sta(run(sta_out(setup=-0.05)), StageId.STA_SIGNOFF, guardband=gb)
        assert v.kind is VerdictKind.FAIL, f"guardband {gb} accepted negative slack"

    # Positive slack below the guardband also fails: that is what asking for
    # margin means.
    inside = check_sta(run(sta_out(setup=0.1, hold=0.1)), StageId.STA_SIGNOFF,
                       guardband=0.5)
    assert inside.kind is VerdictKind.FAIL
    clear = check_sta(run(sta_out(setup=0.9, hold=0.9)), StageId.STA_SIGNOFF,
                      guardband=0.5)
    assert clear.kind is VerdictKind.PASS


def _without(text: str, prefix: str) -> str:
    return "\n".join(l for l in text.splitlines() if not l.startswith(prefix))


def test_a_missing_timing_number_cannot_pass_its_own_gate():
    """Signoff needs both setup and hold; post-CTS needs hold.

    Each comparison used to be guarded by `is not None`, so a report that
    never mentioned hold skipped the hold gate entirely and passed.
    """
    setup_only = _without(sta_out(setup=1.0), "hold_wns")
    v = check_sta(run(setup_only), StageId.STA_SIGNOFF, guardband=0.0)
    assert v.kind is VerdictKind.FAIL
    assert "hold_wns" in v.summary

    hold_only = _without(sta_out(hold=1.0), "setup_wns")
    v = check_sta(run(hold_only), StageId.STA_SIGNOFF, guardband=0.0)
    assert v.kind is VerdictKind.FAIL
    assert "setup_wns" in v.summary

    # Post-CTS is specifically the hold gate.
    assert check_sta(run(hold_only), StageId.STA_POSTCTS,
                     guardband=0.0).kind is VerdictKind.PASS
    assert check_sta(run(setup_only), StageId.STA_POSTCTS,
                     guardband=0.0).kind is VerdictKind.FAIL


def test_a_non_finite_guardband_is_refused_rather_than_ignored():
    """NaN compares False against everything, silently disabling the check."""
    v = check_sta(run(sta_out(setup=-9.0, hold=-9.0)), StageId.STA_SIGNOFF,
                  guardband=float("nan"))
    assert v.kind is VerdictKind.FAIL
    assert "finite" in v.summary


def test_report_with_no_slack_numbers_is_unusable():
    v = check_sta(run("=== check_setup ===\nnothing here\n"), StageId.STA_SIGNOFF)
    assert v.kind is VerdictKind.FAIL
    assert "unusable" in v.summary


def test_tool_error_is_a_config_problem_not_a_timing_problem():
    v = check_sta(run("Error: sta.tcl, 9 invalid command name \"read_def\"\n", rc=1),
                  StageId.STA_POSTCTS)
    assert v.failure is FailureClass.TCL_CONFIG


def test_timeout_is_an_environment_problem():
    r = ToolRun(argv=[], returncode=124, stdout="", stderr="", timed_out=True)
    assert check_sta(r, StageId.STA_SIGNOFF).failure is FailureClass.TOOL_RUNTIME


# ---- empty-output grading -------------------------------------------------

def test_empty_drc_report_means_zero_violations_not_a_failure(tmp_path):
    """Regression: routing converged to 0 violations, so OpenROAD wrote a
    zero-byte DRC report -- and the stage was failed for it."""
    from rtl2gdsagi.checks.tools import check_openroad, is_report_key

    for key in ("route_drc", "congestion_report", "antenna_report", "drc_report"):
        assert is_report_key(key), key
    for key in ("routed_def", "placement_def", "spef", "routed_netlist"):
        assert not is_report_key(key), key

    outs = {}
    (tmp_path / "r.drc").write_text("")                     # 0 violations
    (tmp_path / "d.def").write_text("DEF content\n")
    outs["route_drc"] = tmp_path / "r.drc"
    outs["routed_def"] = tmp_path / "d.def"

    v = check_openroad(
        ToolRun(argv=[], returncode=0,
                stdout=("[INFO DRT-0199]   Number of violations = 0.\n"
                        "[INFO DRT-0198] Complete detail routing.\n"),
                stderr=""),
        StageId.ROUTING, outputs=outs,
    )
    assert v.ok is True, v.summary


def test_empty_design_database_is_still_a_failure(tmp_path):
    from rtl2gdsagi.checks.tools import check_openroad

    (tmp_path / "d.def").write_text("")                     # empty DEF
    v = check_openroad(
        ToolRun(argv=[], returncode=0, stdout="", stderr=""),
        StageId.ROUTING, outputs={"routed_def": tmp_path / "d.def"},
    )
    assert v.blocks is True
    assert "empty" in v.summary


# ---- antenna grading ------------------------------------------------------

def _ant(text: str):
    from rtl2gdsagi.checks.tools import check_openroad
    return check_openroad(ToolRun(argv=[], returncode=0, stdout=text, stderr=""),
                          StageId.ANTENNA)


def test_real_openroad_antenna_violations_are_detected():
    """The exact strings OpenROAD emits, from a real run on this machine."""
    v = _ant("[INFO ANT-0002] Found 1 net violations.\n"
             "[INFO ANT-0001] Found 1 pin violations.\n")
    assert v.blocks is True
    assert v.failure is FailureClass.ANTENNA
    assert v.metrics["antenna_net_violations"] == 1
    assert v.metrics["antenna_pin_violations"] == 1


def test_zero_antenna_violations_passes():
    v = _ant("[INFO ANT-0002] Found 0 net violations.\n"
             "[INFO ANT-0001] Found 0 pin violations.\n")
    assert v.ok is True


def test_antenna_check_with_no_count_is_not_a_pass():
    """Silence is not a clean result, even if the log mentions antennas."""
    v = _ant("Running check_antennas on the design...\nDone.\n")
    assert v.blocks is True
    assert "refusing to infer" in v.summary
