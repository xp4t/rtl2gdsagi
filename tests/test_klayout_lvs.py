"""LVS verdicts must come from three agreeing signals, not from a log string.

The fixtures are slices of a real 16MB .lvsdb produced by an actual signoff run
on this machine.
"""

from __future__ import annotations

from pathlib import Path

from rtl2gdsagi.artifacts import Artifact
from rtl2gdsagi.checks.klayout_lvs import parse_lvs_report

FIX = Path(__file__).parent / "fixtures" / "klayout"
MATCH_LOG = "INFO : Congratulations! Netlists match."
MISMATCH_LOG = "ERROR : Netlists don't match"


def test_match_with_agreeing_signals_is_clean():
    r = parse_lvs_report(
        FIX / "lvs_match_trimmed.lvsdb",
        log_text=MATCH_LOG, exit_code=0, expected_top="top", deck_trustworthy=True,
    )
    assert r.clean is True
    assert r.xref_circuits > 0
    assert r.top_cell == "top"


def test_log_claiming_match_with_nonzero_exit_is_not_clean():
    """Disagreement between signals is a failure, not a pass."""
    r = parse_lvs_report(
        FIX / "lvs_match_trimmed.lvsdb",
        log_text=MATCH_LOG, exit_code=1, expected_top="top", deck_trustworthy=True,
    )
    assert r.clean is False
    assert any("exited non-zero" in p or "exited 1" in p for p in r.problems)


def test_hardcoded_pass_without_any_comparison_is_rejected():
    """A verdict string with no cross-reference in the database is a printf."""
    r = parse_lvs_report(
        FIX / "lvs_no_comparison.lvsdb",
        log_text=MATCH_LOG, exit_code=0, expected_top="top", deck_trustworthy=True,
    )
    assert r.clean is False
    assert r.xref_circuits == 0
    assert any("hardcoded pass" in p for p in r.problems)


def test_untrustworthy_deck_invalidates_a_match_claim():
    """Even with a full database, a deck with no failure path proves nothing."""
    r = parse_lvs_report(
        FIX / "lvs_match_trimmed.lvsdb",
        log_text=MATCH_LOG, exit_code=0, expected_top="top", deck_trustworthy=False,
    )
    assert r.clean is False
    assert any("no reachable failure path" in p for p in r.problems)


def test_explicit_mismatch_is_not_clean():
    r = parse_lvs_report(
        FIX / "lvs_match_trimmed.lvsdb",
        log_text=MISMATCH_LOG, exit_code=1, expected_top="top", deck_trustworthy=True,
    )
    assert r.clean is False


def test_exit_zero_with_no_verdict_is_not_inferred_as_a_pass():
    r = parse_lvs_report(
        FIX / "lvs_match_trimmed.lvsdb",
        log_text="LVS finished.", exit_code=0, expected_top="top", deck_trustworthy=True,
    )
    assert r.clean is False
    assert any("refusing to infer" in p for p in r.problems)


def test_missing_report_is_not_clean(tmp_path):
    r = parse_lvs_report(
        tmp_path / "absent.lvsdb", log_text=MATCH_LOG, exit_code=0, deck_trustworthy=True,
    )
    assert r.clean is False
    assert any("not written" in p for p in r.problems)


def test_wrong_top_cell_is_rejected():
    r = parse_lvs_report(
        FIX / "lvs_match_trimmed.lvsdb",
        log_text=MATCH_LOG, exit_code=0, expected_top="cam_top", deck_trustworthy=True,
    )
    assert r.clean is False
    assert any("top cell" in p for p in r.problems)


def test_non_lvsdb_file_is_rejected(tmp_path):
    p = tmp_path / "not.lvsdb"
    p.write_text("just some text\n", encoding="utf-8")
    r = parse_lvs_report(p, log_text=MATCH_LOG, exit_code=0, deck_trustworthy=True)
    assert r.clean is False


def test_warnings_are_counted_and_summarised():
    """The real database holds 20k copies of one warning; report it once."""
    r = parse_lvs_report(
        FIX / "lvs_match_trimmed.lvsdb",
        log_text=MATCH_LOG, exit_code=0, expected_top="top", deck_trustworthy=True,
    )
    assert r.warnings > 0
    top_msg, count = r.top_messages(1)[0]
    assert count > 1
    assert "resistor" in top_msg.lower()
    assert len(r.digest().splitlines()) < 30  # stays token-cheap


def test_gds_binding_is_carried(tmp_path):
    gds = tmp_path / "final.gds"
    gds.write_bytes(b"not-a-real-gds")
    art = Artifact.capture("final_gds", gds, stage="gdsout")
    r = parse_lvs_report(
        FIX / "lvs_match_trimmed.lvsdb", log_text=MATCH_LOG, exit_code=0,
        expected_top="top", checked_gds=art, deck_trustworthy=True,
    )
    assert r.to_dict()["checked_gds"]["sha256"] == art.sha256
