"""P0-R1: SPEF coverage is net identity, not a count ratio.

Codex's reproduction: a SPEF containing 35 `*D_NET` sections that **all
resolve to the same routed net**. The old validator computed

    coverage = len(D_NET records) / len(routed DEF nets) = 35/35 = 100%

and accepted it. OpenROAD then read it, emitted `STA-0175` connectivity
warnings, exited zero, and produced plausible positive slack from an analysis
that was effectively unannotated -- and the STA checker returned PASS.

Two independent things were wrong and both are covered here: the extraction
gate compared counts instead of names, and the signoff STA gate proved only
that control flow reached the line after `read_spef`.
"""

from __future__ import annotations

import pytest

from rtl2gdsagi.checks.spef import (
    parse_name_map,
    resolve_net_name,
    validate_spef,
)
from rtl2gdsagi.checks.tools import (
    PARASITIC_DIAGNOSTIC_CODES,
    SPEF_ANNOTATED_MARKER,
    SPEF_COVERAGE_MARKER,
    ToolRun,
    check_sta,
)
from rtl2gdsagi.stages import StageId

ROUTED_NETS = ["i_clk", "i_rst_n", "_00_", "_01_", "_02_"]

HEADER = (
    '*SPEF "ieee 1481-1999"\n'
    '*DESIGN "register"\n'
    "*DIVIDER /\n*DELIMITER :\n*BUS_DELIMITER []\n"
    "*T_UNIT 1 NS\n*C_UNIT 1 PF\n*R_UNIT 1 OHM\n*L_UNIT 1 HENRY\n\n"
)


def _name_map(names):
    return "*NAME_MAP\n" + "".join(
        f"*{i} {n}\n" for i, n in enumerate(names, start=1)) + "\n"


def _d_net(idx, name):
    return (
        f"*D_NET *{idx} 0.00295458\n"
        f"*CONN\n*P {name} I\n*I *130:A I *D sky130_fd_sc_hd__clkbuf_1\n"
        f"*CAP\n1 {name} 0.00147729\n"
        f"*RES\n1 {name} *130:A 45.9483\n"
        f"*END\n"
    )


def write_spef(tmp_path, body, names=ROUTED_NETS, name="x.spef"):
    p = tmp_path / name
    p.write_text(HEADER + _name_map(names) + body)
    return p


def write_def(tmp_path, nets=ROUTED_NETS):
    p = tmp_path / "routed.def"
    body = "".join(f"    - {n} ( inst A )\n" for n in nets)
    p.write_text(f"VERSION 5.8 ;\nDESIGN register ;\n"
                 f"NETS {len(nets)} ;\n{body}END NETS\nEND DESIGN\n")
    return p


def check(tmp_path, body, **kw):
    return validate_spef(write_spef(tmp_path, body, **kw),
                         expected_design="register",
                         routed_def=write_def(tmp_path))


# ---- the control -----------------------------------------------------------

def test_a_correct_spef_passes(tmp_path):
    body = "".join(_d_net(i, n) for i, n in enumerate(ROUTED_NETS, start=1))
    res = check(tmp_path, body)
    assert res.ok, res.problems
    assert res.coverage == 1.0
    assert set(res.resolved_net_names) == set(ROUTED_NETS)
    assert len(res.resolved_net_names) == len(set(res.resolved_net_names))


# ---- Codex's exact false clean --------------------------------------------

def test_every_d_net_describing_the_same_net_is_rejected(tmp_path):
    """THE reproduction: N sections, N routed nets, one real net.

    Under the old count-ratio rule this scored 100% coverage and passed.
    """
    body = "".join(_d_net(1, "i_clk") for _ in ROUTED_NETS)
    res = check(tmp_path, body)

    assert not res.ok
    assert res.duplicates == ("i_clk",)
    assert any("more than one *D_NET" in p for p in res.problems)
    assert any("have no *D_NET" in p for p in res.problems)
    # The count ratio it used to pass on is still 5/5.
    assert res.net_count == len(ROUTED_NETS)
    # But identity coverage is 1 of 5.
    assert res.coverage == pytest.approx(1 / len(ROUTED_NETS))


# ---- the rest of the identity contract ------------------------------------

def test_a_missing_routed_net_is_rejected(tmp_path):
    body = "".join(_d_net(i, n)
                   for i, n in enumerate(ROUTED_NETS, start=1) if n != "_02_")
    res = check(tmp_path, body)
    assert not res.ok
    assert "_02_" in res.missing
    assert any("have no *D_NET" in p for p in res.problems)


def test_a_net_that_is_not_in_this_design_is_rejected(tmp_path):
    names = ROUTED_NETS + ["net_from_another_design"]
    body = "".join(_d_net(i, n) for i, n in enumerate(names, start=1))
    res = check(tmp_path, body, names=names)
    assert not res.ok
    assert "net_from_another_design" in res.extra
    assert any("not routed nets in this design" in p for p in res.problems)


def test_an_unmapped_d_net_identifier_is_rejected(tmp_path):
    """`*D_NET *99` with no `*99` in the NAME_MAP names nothing."""
    body = "".join(_d_net(i, n) for i, n in enumerate(ROUTED_NETS, start=1))
    body += _d_net(99, "mystery")
    res = check(tmp_path, body)
    assert not res.ok
    assert res.unresolved == ("*99",)
    assert any("no *NAME_MAP entry" in p for p in res.problems)


def test_a_zero_net_spef_is_rejected(tmp_path):
    res = check(tmp_path, "")
    assert not res.ok
    assert any("no *D_NET records" in p for p in res.problems)


def test_a_truncated_d_net_is_rejected(tmp_path):
    body = "".join(_d_net(i, n) for i, n in enumerate(ROUTED_NETS, start=1))
    body += "*D_NET *5 0.001\n*CONN\n*P _02_ I\n*CAP\n"      # no *END
    res = check(tmp_path, body)
    assert not res.ok
    assert any("truncated" in p for p in res.problems)


def test_a_net_with_no_connections_is_rejected(tmp_path):
    body = "".join(_d_net(i, n) for i, n in enumerate(ROUTED_NETS[:-1], start=1))
    body += "*D_NET *5 0.001\n*CONN\n*CAP\n1 _02_ 0.0005\n*RES\n*END\n"
    res = check(tmp_path, body)
    assert not res.ok
    assert any("no *CONN entries" in p for p in res.problems)


def test_the_wrong_design_is_rejected(tmp_path):
    p = tmp_path / "other.spef"
    p.write_text(HEADER.replace('"register"', '"something_else"')
                 + _name_map(ROUTED_NETS)
                 + "".join(_d_net(i, n)
                           for i, n in enumerate(ROUTED_NETS, start=1)))
    res = validate_spef(p, expected_design="register",
                        routed_def=write_def(tmp_path))
    assert not res.ok
    assert any("not 'register'" in p_ for p_ in res.problems)


# ---- name-map resolution ---------------------------------------------------

def test_name_map_is_parsed_and_resolved():
    text = HEADER + _name_map(["i_clk", "_00_"]) + _d_net(1, "i_clk")
    nm = parse_name_map(text)
    assert nm == {"1": "i_clk", "2": "_00_"}
    assert resolve_net_name("*2", nm) == "_00_"
    assert resolve_net_name("*7", nm) is None
    assert resolve_net_name("literal_name", nm) == "literal_name"


# ---- the STA half ----------------------------------------------------------

ANNOTATED = (
    f"{SPEF_ANNOTATED_MARKER} /run/x.spef\n"
    f"{SPEF_COVERAGE_MARKER}\n"
    "Found 0 unannotated drivers.\n"
    "Found 0 partially unannotated drivers.\n"
    "=== wns/tns ===\n"
    "setup_wns 0.42\nsetup_tns 0.0\nhold_wns 0.11\nhold_tns 0.0\n"
)


def _run(text, rc=0):
    return ToolRun(argv=["openroad"], returncode=rc, stdout=text, stderr="",
                   duration_s=1.0)


def test_signoff_sta_passes_with_full_annotation():
    v = check_sta(_run(ANNOTATED), StageId.STA_SIGNOFF, expect_parasitics=True)
    assert v.ok, v.summary
    assert v.metrics["unannotated_drivers"] == 0


@pytest.mark.parametrize("code", PARASITIC_DIAGNOSTIC_CODES)
def test_every_parasitic_diagnostic_code_fails_signoff(code):
    """Real captured family, including the STA-0175 Codex saw."""
    text = ANNOTATED.replace(
        f"{SPEF_COVERAGE_MARKER}\n",
        f"[WARNING {code}] parasitic network is not connected to a pin\n"
        f"{SPEF_COVERAGE_MARKER}\n")
    v = check_sta(_run(text), StageId.STA_SIGNOFF, expect_parasitics=True)
    assert not v.ok
    assert code in v.summary or "did not parse cleanly" in v.summary


def test_incomplete_annotation_fails_even_with_no_warning():
    """The quantitative half, independent of any warning text."""
    text = ANNOTATED.replace("Found 0 unannotated drivers.",
                             "Found 34 unannotated drivers.")
    v = check_sta(_run(text), StageId.STA_SIGNOFF, expect_parasitics=True)
    assert not v.ok
    assert "annotation is incomplete" in v.summary
    assert v.metrics.get("unannotated_drivers") == 34


def test_partial_annotation_fails():
    text = ANNOTATED.replace("Found 0 partially unannotated drivers.",
                             "Found 7 partially unannotated drivers.")
    v = check_sta(_run(text), StageId.STA_SIGNOFF, expect_parasitics=True)
    assert not v.ok
    assert "annotation is incomplete" in v.summary


def test_a_marker_without_an_annotation_report_is_not_enough():
    """The old proof: "read_spef returned and the marker printed"."""
    text = (f"{SPEF_ANNOTATED_MARKER} /run/x.spef\n"
            "=== wns/tns ===\nsetup_wns 0.42\nsetup_tns 0.0\n"
            "hold_wns 0.11\nhold_tns 0.0\n")
    v = check_sta(_run(text), StageId.STA_SIGNOFF, expect_parasitics=True)
    assert not v.ok
    assert "no parasitic-annotation report" in v.summary


def test_pre_route_sta_is_unaffected():
    """`expect_parasitics=False` must not start demanding annotation."""
    text = ("=== wns/tns ===\nsetup_wns 0.42\nsetup_tns 0.0\n"
            "hold_wns 0.11\nhold_tns 0.0\n")
    v = check_sta(_run(text), StageId.STA_PRE, expect_parasitics=False)
    assert v.ok, v.summary
