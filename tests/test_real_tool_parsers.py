"""Parser conformance against **captured real EDA tool output**.

Why this file exists
--------------------
The routing parser was wrong for the entire life of the project: OpenROAD
writes ``Number of violations = 900.`` and the regex expected
``violations: 900``. It matched *nothing* in every real log, so routing passed
with no violation evidence at all -- and 349 tests did not notice, because the
mock that fed those tests emitted the same fictional syntax the parser expected.

A parser and its mock can share a false belief and produce a green suite
forever. The only defence is to test against what the tool actually printed.

Every fixture under ``tests/fixtures/real/`` is unmodified real output (paths
sanitised, nothing else), and every one carries a ``.json`` sidecar recording
the tool, version, stage, design, originating run, and the *expected semantic
result*. These tests assert the parser against **that metadata**, so the
expectation is derived from an independent reading of the log rather than from
the parser's own assumptions.

If someone changes a regex back to invented syntax, this suite fails.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rtl2gdsagi.checks import klayout_drc, klayout_lvs
from rtl2gdsagi.checks import gds as gdsread
from rtl2gdsagi.checks.tools import (
    ToolRun,
    check_lec,
    check_lint,
    check_openroad,
    check_sim,
    check_sta,
    check_synthesis,
)
from rtl2gdsagi.checks.verdict import VerdictKind
from rtl2gdsagi.stages import StageId

REAL = Path(__file__).parent / "fixtures" / "real"


def fixture(tool: str, name: str) -> tuple[str, dict]:
    """Real output plus the provenance that says what it should mean."""
    p = REAL / tool / name
    meta = json.loads(p.with_suffix(p.suffix + ".json").read_text())
    return p.read_text(errors="replace"), meta


def run_of(text: str, rc: int = 0) -> ToolRun:
    return ToolRun(argv=[], returncode=rc, stdout=text, stderr="")


# ---- provenance ------------------------------------------------------------

def test_every_real_fixture_declares_its_provenance():
    """A fixture without provenance is just another mock."""
    files = [p for p in REAL.rglob("*") if p.is_file() and p.suffix != ".json"]
    assert files, "no real fixtures captured"
    for f in files:
        side = f.with_suffix(f.suffix + ".json")
        assert side.is_file(), f"{f} has no provenance sidecar"
        meta = json.loads(side.read_text())
        for key in ("tool", "version", "stage", "design", "source_run", "expected"):
            assert meta.get(key) not in (None, ""), f"{f}: missing {key}"


# ---- A5: routing -----------------------------------------------------------

def test_routing_real_log_many_iterations():
    """The reference case. Six iterations, 900 -> 0, real '=' syntax."""
    text, meta = fixture("openroad", "routing_many_iterations.log")
    v = check_openroad(run_of(text), StageId.ROUTING, outputs={})

    assert v.metrics["route_violations"] == meta["expected"]["terminal_violations"]
    assert v.metrics["route_violation_iterations"] == len(
        meta["expected"]["iteration_counts"])
    assert v.kind is VerdictKind.PASS


def test_routing_uses_the_terminal_count_not_the_first():
    """Real log starts at 900 and ends at 0. Picking the first fails a good route."""
    text, meta = fixture("openroad", "routing_many_iterations.log")
    counts = meta["expected"]["iteration_counts"]
    assert counts[0] != counts[-1], "fixture must have a converging series"

    v = check_openroad(run_of(text), StageId.ROUTING, outputs={})
    assert v.metrics["route_violations"] == counts[-1]
    assert v.metrics["route_violations"] != counts[0]


def test_routing_real_log_that_ends_dirty_fails():
    """Same real log with the terminal count edited to be nonzero."""
    text, _ = fixture("openroad", "routing_many_iterations.log")
    dirty = text.replace("Number of violations = 0.", "Number of violations = 3.")
    v = check_openroad(run_of(dirty), StageId.ROUTING, outputs={})
    assert v.kind is VerdictKind.FAIL
    assert v.metrics["route_violations"] == 3


def test_routing_real_log_without_completion_marker_fails_closed():
    """Drop the whole completion line, not just its text.

    The marker is recognised by its message id (DRT-0198) as well as its
    wording, so leaving `[INFO DRT-0198]` behind still -- correctly -- counts
    as completion.
    """
    text, _ = fixture("openroad", "routing_many_iterations.log")
    truncated = "\n".join(
        l for l in text.splitlines()
        if "DRT-0198" not in l and "Complete detail routing" not in l
    )
    v = check_openroad(run_of(truncated), StageId.ROUTING, outputs={})
    assert v.kind is VerdictKind.FAIL
    assert "completion" in v.summary


def test_routing_completion_without_any_count_fails_closed():
    v = check_openroad(
        run_of("[INFO DRT-0198] Complete detail routing.\n"),
        StageId.ROUTING, outputs={})
    assert v.kind is VerdictKind.FAIL
    assert "no violation count" in v.summary


def test_routing_converged_register_log():
    text, meta = fixture("openroad", "routing_converged.log")
    v = check_openroad(run_of(text), StageId.ROUTING, outputs={})
    assert v.kind is VerdictKind.PASS
    assert v.metrics["route_violations"] == meta["expected"]["terminal_violations"]


# ---- A6: antenna -----------------------------------------------------------

def test_antenna_real_clean_log():
    text, meta = fixture("openroad", "antenna_clean.log")
    v = check_openroad(run_of(text), StageId.ANTENNA, outputs={})
    assert v.kind is VerdictKind.PASS
    assert v.metrics["antenna_net_violations"] == meta["expected"]["net_violations"]
    assert v.metrics["antenna_pin_violations"] == meta["expected"]["pin_violations"]


def test_antenna_real_log_with_one_half_removed_fails_closed():
    """Derived from real output: a missing side must not default to zero."""
    text, _ = fixture("openroad", "antenna_clean.log")
    no_pins = "\n".join(l for l in text.splitlines() if "ANT-0001" not in l)
    v = check_openroad(run_of(no_pins), StageId.ANTENNA, outputs={})
    assert v.kind is VerdictKind.FAIL
    assert "pin violation count" in v.summary


def test_antenna_real_log_with_a_later_dirty_result_fails():
    text, _ = fixture("openroad", "antenna_clean.log")
    twice = text + (
        "[INFO ANT-0002] Found 4 net violations.\n"
        "[INFO ANT-0001] Found 5 pin violations.\n"
    )
    v = check_openroad(run_of(twice), StageId.ANTENNA, outputs={})
    assert v.kind is VerdictKind.FAIL
    assert v.metrics["antenna_net_violations"] == 4


# ---- A7: STA ---------------------------------------------------------------

@pytest.mark.parametrize("name,stage", [
    ("sta_pre_met.log", StageId.STA_PRE),
    ("sta_postcts_met.log", StageId.STA_POSTCTS),
    ("sta_signoff_met.log", StageId.STA_SIGNOFF),
])
def test_sta_real_logs_parse_both_slacks(name, stage):
    text, meta = fixture("opensta", name)
    v = check_sta(run_of(text), stage, guardband=0.0)

    assert v.metrics["setup_wns"] is not None, "setup_wns not found in real output"
    assert v.metrics["hold_wns"] is not None, "hold_wns not found in real output"
    assert (v.metrics["setup_wns"] > 0) is meta["expected"]["setup_positive"]
    assert (v.metrics["hold_wns"] > 0) is meta["expected"]["hold_positive"]
    assert v.kind is VerdictKind.PASS


def test_sta_real_signoff_log_with_hold_removed_fails_closed():
    text, _ = fixture("opensta", "sta_signoff_met.log")
    without = "\n".join(l for l in text.splitlines()
                        if not l.startswith("hold_wns"))
    v = check_sta(run_of(without), StageId.STA_SIGNOFF, guardband=0.0)
    assert v.kind is VerdictKind.FAIL
    assert "hold_wns" in v.summary


def test_sta_real_signoff_log_with_setup_removed_fails_closed():
    text, _ = fixture("opensta", "sta_signoff_met.log")
    without = "\n".join(l for l in text.splitlines()
                        if not l.startswith("setup_wns"))
    v = check_sta(run_of(without), StageId.STA_SIGNOFF, guardband=0.0)
    assert v.kind is VerdictKind.FAIL
    assert "setup_wns" in v.summary


@pytest.mark.parametrize("bad", ["nan", "inf", "-inf"])
def test_sta_real_log_with_a_non_finite_slack_fails_closed(bad):
    text, _ = fixture("opensta", "sta_signoff_met.log")
    import re
    mutated = re.sub(r"^hold_wns .*$", f"hold_wns {bad}", text, flags=re.MULTILINE)
    v = check_sta(run_of(mutated), StageId.STA_SIGNOFF, guardband=0.0)
    assert v.kind is VerdictKind.FAIL


def test_sta_guardband_on_a_real_log_tightens_never_relaxes():
    """Real passing log; a guardband above its slack must fail it."""
    text, _ = fixture("opensta", "sta_signoff_met.log")
    ok = check_sta(run_of(text), StageId.STA_SIGNOFF, guardband=0.0)
    assert ok.kind is VerdictKind.PASS

    above = abs(ok.metrics["hold_wns"]) + 1.0
    tightened = check_sta(run_of(text), StageId.STA_SIGNOFF, guardband=above)
    assert tightened.kind is VerdictKind.FAIL, (
        "a larger guardband must never make timing easier to pass")


def test_sta_truncated_real_log_fails_closed():
    text, _ = fixture("opensta", "sta_signoff_met.log")
    v = check_sta(run_of(text[: len(text) // 3]), StageId.STA_SIGNOFF)
    assert v.kind is VerdictKind.FAIL


# ---- A8: EQY ---------------------------------------------------------------

def test_eqy_real_pass_log():
    text, meta = fixture("eqy", "lec_pass_1_partition.log")
    v = check_lec(run_of(text), StageId.LEC_SYNTH)
    assert v.kind is VerdictKind.PASS
    assert v.metrics["partitions_proved"] == meta["expected"]["partitions_proved"]
    assert v.metrics["partitions_unknown"] == meta["expected"]["partitions_unknown"]


def test_eqy_real_failure_log_with_unknown_partitions():
    """OV7670: 11 proved, 38 unknown. Real unproven equivalence."""
    text, meta = fixture("eqy", "lec_fail_unknown_partitions.log")
    v = check_lec(run_of(text), StageId.LEC_SYNTH)
    assert v.kind is VerdictKind.FAIL
    assert v.metrics["partitions_proved"] == meta["expected"]["partitions_proved"]
    assert v.metrics["partitions_unknown"] == meta["expected"]["partitions_unknown"]


def test_eqy_real_pass_log_with_nonzero_exit_is_refused():
    text, _ = fixture("eqy", "lec_pass_1_partition.log")
    v = check_lec(run_of(text, rc=1), StageId.LEC_SYNTH)
    assert v.kind is VerdictKind.FAIL
    assert "exited 1" in v.summary


def test_eqy_real_pass_log_with_an_injected_mismatch_is_refused():
    text, _ = fixture("eqy", "lec_pass_1_partition.log")
    contradictory = text + (
        "EQY x [w] Could not prove equivalence of partition 'w.b' in mode x: "
        "partitions not equivalent\n"
    )
    v = check_lec(run_of(contradictory), StageId.LEC_SYNTH)
    assert v.kind is VerdictKind.FAIL
    assert "contradicts itself" in v.summary


def test_eqy_pass_line_with_no_proved_partition_is_refused():
    """Strip the proof lines from a real log; 'DONE (PASS)' alone proves nothing."""
    text, _ = fixture("eqy", "lec_pass_1_partition.log")
    stripped = "\n".join(
        l for l in text.splitlines()
        if "proved equivalence of partition" not in l.lower()
    )
    v = check_lec(run_of(stripped), StageId.LEC_SYNTH)
    assert v.kind is VerdictKind.FAIL
    assert "no partition was actually proved" in v.summary


def test_eqy_real_log_contains_both_proved_phrasings():
    """Guards the regex against being narrowed back to one wording."""
    text, _ = fixture("eqy", "lec_pass_1_partition.log")
    low = text.lower()
    assert "run: proved equivalence of partition" in low
    assert "successfully proved equivalence of partition" in low


# ---- A9: KLayout DRC -------------------------------------------------------

def test_drc_real_clean_report():
    p = REAL / "klayout" / "drc_clean_register.lyrdb"
    meta = json.loads(p.with_suffix(p.suffix + ".json").read_text())
    res = klayout_drc.parse_drc_report(p, expected_top=meta["design"])

    assert res.total_violations == meta["expected"]["total_violations"]
    assert res.declared_categories > meta["expected"]["declared_categories_gt"]
    assert res.clean is True


def test_drc_real_clean_report_proves_rules_actually_ran():
    """0 violations across 200+ categories is different from 0 categories."""
    p = REAL / "klayout" / "drc_clean_register.lyrdb"
    res = klayout_drc.parse_drc_report(p, expected_top="register")
    assert res.declared_categories > 200, (
        "a clean report must show the deck actually executed its rules")


def test_drc_real_dirty_report():
    p = REAL / "klayout" / "drc_one_m2x_ov7670.lyrdb"
    meta = json.loads(p.with_suffix(p.suffix + ".json").read_text())
    res = klayout_drc.parse_drc_report(p, expected_top="cam_top")

    assert res.total_violations == meta["expected"]["total_violations"]
    assert res.by_category == meta["expected"]["by_category"]
    assert res.clean is False


def test_drc_report_naming_another_top_cell_is_rejected():
    """A report about a different layout is not evidence about this one."""
    p = REAL / "klayout" / "drc_clean_register.lyrdb"
    res = klayout_drc.parse_drc_report(p, expected_top="some_other_top")
    assert res.clean is False
    assert res.problems


def test_drc_truncated_real_report_fails_closed(tmp_path):
    p = REAL / "klayout" / "drc_clean_register.lyrdb"
    cut = tmp_path / "cut.lyrdb"
    cut.write_bytes(p.read_bytes()[: 400])
    res = klayout_drc.parse_drc_report(cut, expected_top="register")
    assert res.clean is False
    assert res.problems


# ---- A10: KLayout LVS ------------------------------------------------------

def test_lvs_real_report_blocks_on_unresolved_must_connect():
    """The register LVS is NOT clean, and the fixture proves why.

    The netlist comparison matches and the log says so. The database also
    carries three entries whose own text reads "must be connected further up
    in the hierarchy - this is an error at chip top level", for all three
    clkbuf_1 instances in the design. Severity W, content error, and top level
    is exactly what was being certified.

    This test previously asserted `clean is True`, and the fixture sidecar
    recorded verdict=pass -- parser, test and fixture all sharing one wrong
    assumption about warning severity. That is the failure mode the real-output
    campaign exists to detect, so it is pinned here in the direction it should
    have had from the start.
    """
    p = REAL / "klayout" / "lvs_match_register.lvsdb"
    meta = json.loads(p.with_suffix(p.suffix + ".json").read_text())
    log, _ = fixture("klayout", "lvs_match_register.log")
    res = klayout_lvs.parse_lvs_report(p, log_text=log, exit_code=0,
                                       expected_top="register")

    assert res.clean is False
    assert meta["expected"]["verdict"] == "fail"
    assert any("must-connect" in problem for problem in res.problems)
    # The comparison itself did run and did match; that is not the issue.
    assert res.log_claims_match is True
    assert res.xref_circuits > 100


def test_only_the_named_condition_blocks_not_severity_w_in_general(tmp_path):
    """The rule is narrow on purpose.

    "Every warning fails" would be its own dishonesty -- it would block real
    designs on cosmetic notes and teach people to ignore the gate. Only the
    must-connect class blocks, because its own message says it is an error at
    the level being certified.

    The real register database happens to carry exactly three warnings and all
    three are must-connect, so the contrast is drawn against a database
    carrying an unrelated warning instead.
    """
    real = (REAL / "klayout" / "lvs_match_register.lvsdb").read_text(errors="replace")
    log, _ = fixture("klayout", "lvs_match_register.log")

    benign = real.replace(
        "Must-connect subnets of VGND of circuit sky130_fd_sc_hd__clkbuf_1 "
        "must be connected further up in the hierarchy - this is an error at "
        "chip top level.",
        "Layer 68/20 has 3 shapes smaller than the resolution and was rounded.",
    )
    p = tmp_path / "benign.lvsdb"
    p.write_text(benign)
    res = klayout_lvs.parse_lvs_report(p, log_text=log, exit_code=0,
                                       expected_top="register")
    assert res.warnings == 3, "the warnings should still be counted"
    assert res.clean is True, f"benign warnings must not block: {res.problems}"


def test_lvs_match_text_alone_is_not_enough(tmp_path):
    """The deck can print 'Netlists match' from an unreachable branch."""
    fake = tmp_path / "empty.lvsdb"
    fake.write_text("#%lvsdb-klayout\n")
    res = klayout_lvs.parse_lvs_report(
        fake, log_text="INFO : Congratulations! Netlists match.\n",
        exit_code=0, expected_top="register")
    assert res.clean is False, "a match string with no cross-reference data"


def test_lvs_truncated_database_fails_closed(tmp_path):
    p = REAL / "klayout" / "lvs_match_register.lvsdb"
    log, _ = fixture("klayout", "lvs_match_register.log")
    cut = tmp_path / "cut.lvsdb"
    cut.write_bytes(p.read_bytes()[:34])
    res = klayout_lvs.parse_lvs_report(cut, log_text=log, exit_code=0,
                                       expected_top="register")
    assert res.clean is False


def test_lvs_nonzero_exit_fails_closed():
    p = REAL / "klayout" / "lvs_match_register.lvsdb"
    log, _ = fixture("klayout", "lvs_match_register.log")
    res = klayout_lvs.parse_lvs_report(p, log_text=log, exit_code=1,
                                       expected_top="register")
    assert res.clean is False


# ---- A11: GDS --------------------------------------------------------------

def test_gds_real_streamed_layout():
    p = REAL / "klayout" / "gds_register_merged.gds"
    meta = json.loads(p.with_suffix(p.suffix + ".json").read_text())
    info = gdsread.read_gds(p)

    assert meta["expected"]["top_cell"] in info.cells
    assert meta["expected"]["top_cell"] in info.root_cells()
    assert not info.unresolved_references
    assert info.total_elements > 0


def test_gds_real_layout_is_not_hollow():
    """Structurally valid but empty must not read as a finished layout.

    The audit's remaining "hollow GDS" concern: a file can parse, declare the
    right top cell and resolve every reference while containing essentially no
    geometry. The real merged layout carries thousands of shapes; a shell does
    not.
    """
    p = REAL / "klayout" / "gds_register_merged.gds"
    info = gdsread.read_gds(p)
    top = info.cell("register")
    assert top is not None
    assert info.total_elements > 100, (
        f"real merged stream-out should be full of geometry, saw "
        f"{info.total_elements}")
    assert len(info.cells) > 1, "a merged GDS contains its standard cells"


def test_gds_real_layout_uses_real_sky130_layers():
    """Catches the streamed-to-invented-layers failure directly."""
    p = REAL / "klayout" / "gds_register_merged.gds"
    info = gdsread.read_gds(p)
    layers = {ld[0] for ld in info.layers}
    assert 67 in layers or 68 in layers, (
        f"expected SKY130 li1/met1 (67/68); saw {sorted(layers)[:12]}")
    assert not {1, 3, 5, 7} & layers, (
        "low invented layer numbers mean the layer map was not applied")


# ---- other stages ----------------------------------------------------------

def test_verilator_real_clean_lint():
    text, meta = fixture("verilator", "lint_clean.log")
    v = check_lint(run_of(text))
    assert v.ok is True
    assert v.metrics["errors"] == meta["expected"]["errors"]


def test_iverilog_real_passing_simulation():
    text, _ = fixture("iverilog", "sim_pass.log")
    v = check_sim(run_of(text), testbench="register_tb.v")
    assert v.kind is VerdictKind.PASS


def test_a_simulation_that_prints_nothing_is_not_a_pass():
    v = check_sim(run_of("no result here\n"), testbench="quiet_tb.v")
    assert v.kind is VerdictKind.QOR_BELOW_TARGET
    assert v.blocks is False


def test_yosys_real_synthesis_log(tmp_path):
    text, meta = fixture("yosys", "synthesis_ok.log")
    netlist = tmp_path / "register.netlist.v"
    netlist.write_text("module register(); endmodule\n")
    v = check_synthesis(run_of(text), netlist)
    assert v.ok is True
    assert v.metrics["cells"] > meta["expected"]["cells_gt"]
    assert v.metrics["latches_inferred"] is meta["expected"]["latches_inferred"]


def test_openroad_real_placement_converged():
    text, meta = fixture("openroad", "placement_converged.log")
    v = check_openroad(run_of(text), StageId.PLACEMENT, outputs={},
                       overflow_limit=0.15)
    assert v.metrics["overflow"] == pytest.approx(meta["expected"]["overflow"])
    assert v.metrics["overflow_converged"] is True
    assert v.kind is VerdictKind.PASS


def test_openroad_placement_that_never_converged_is_flagged():
    """Strip the 'Finished with Overflow' line from real output."""
    text, _ = fixture("openroad", "placement_converged.log")
    unconverged = "\n".join(l for l in text.splitlines()
                            if "Finished with Overflow" not in l)
    v = check_openroad(run_of(unconverged), StageId.PLACEMENT, outputs={},
                       overflow_limit=0.15)
    assert v.kind is VerdictKind.QOR_BELOW_TARGET
    assert "without converging" in v.summary


def test_openroad_placement_overflow_is_terminal_not_initial():
    """The first Nesterov iteration is ~0.65 against a 0.15 limit."""
    text, meta = fixture("openroad", "placement_converged.log")
    v = check_openroad(run_of(text), StageId.PLACEMENT, outputs={},
                       overflow_limit=0.15)
    assert v.metrics["overflow"] < 0.15
    assert v.metrics["overflow_iterations"] > 1
    assert "0.647628" in text, "fixture should contain the high first iteration"


def test_openroad_real_cts_skew_table():
    text, meta = fixture("openroad", "cts_skew_table.log")
    v = check_openroad(run_of(text), StageId.CTS, outputs={})
    assert v.metrics["clock_skew_ns"] == pytest.approx(
        meta["expected"]["clock_skew_ns"])


def test_openroad_cts_without_comparable_paths_records_no_skew():
    """'No launch/capture paths found' must not be recorded as skew 0."""
    text, _ = fixture("openroad", "cts_no_launch_capture_paths.log")
    v = check_openroad(run_of(text), StageId.CTS, outputs={})
    assert v.metrics.get("clock_skew_ns") is None
    assert "no launch/capture" in v.metrics.get("clock_skew_note", "").lower()


def test_openroad_real_floorplan_area():
    text, meta = fixture("openroad", "floorplan_ok.log")
    v = check_openroad(run_of(text), StageId.FLOORPLAN, outputs={})
    assert v.metrics["utilization_pct"] == pytest.approx(
        meta["expected"]["utilization_pct"])
