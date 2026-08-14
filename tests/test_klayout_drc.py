"""DRC parser tests, driven by real reports from a SKY130/OpenLane-era signoff.

``drc_dirty_4743.lyrdb`` is the actual KLayout report from a run whose
Innovus ``verify_drc`` said "No DRC violations were found". The Innovus report is
kept alongside it as ``innovus_false_clean.rpt``. If the parser ever calls that
KLayout report clean, the exact bug we are defending against has returned.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rtl2gdsagi.artifacts import Artifact
from rtl2gdsagi.checks.klayout_drc import DRCResult, parse_drc_report

FIX = Path(__file__).parent / "fixtures" / "klayout"

# Ground truth, established by an independent ElementTree pass over the file.
DIRTY_TOTAL = 4743
DIRTY_VIOLATED_CATEGORIES = 12
DECLARED_CATEGORIES = 73
DIRTY_WORST = ("5.7.1 : Minimum Boron spacing violations =  1.5um", 3186)


def test_real_report_is_not_clean():
    """The headline regression: 4743 violations must not read as a pass."""
    r = parse_drc_report(FIX / "drc_dirty_4743.lyrdb", expected_top="top")
    assert r.clean is False
    assert r.total_violations == DIRTY_TOTAL


def test_real_report_counts_match_ground_truth():
    r = parse_drc_report(FIX / "drc_dirty_4743.lyrdb", expected_top="top")
    assert r.total_violations == DIRTY_TOTAL
    assert r.violated_categories == DIRTY_VIOLATED_CATEGORIES
    assert r.declared_categories == DECLARED_CATEGORIES
    assert r.top_cell == "top"


def test_worst_category_is_identified():
    r = parse_drc_report(FIX / "drc_dirty_4743.lyrdb")
    name, count = r.top_categories(1)[0]
    assert (name, count) == DIRTY_WORST


def test_category_counts_sum_to_total():
    """Guards against double-counting or dropping items."""
    r = parse_drc_report(FIX / "drc_dirty_4743.lyrdb")
    assert sum(r.by_category.values()) == r.total_violations


def test_second_real_report_has_its_own_count():
    """A different GDS from the same design gives a genuinely different count."""
    r = parse_drc_report(FIX / "drc_dirty_1626.lyrdb", expected_top="top")
    assert r.clean is False
    assert r.total_violations == 1626
    assert r.violated_categories == 12


def test_counts_are_not_raw_tag_counts():
    """`grep -c '<category>'` overcounts badly; make sure we don't do that."""
    raw = (FIX / "drc_dirty_4743.lyrdb").read_text(encoding="utf-8")
    naive = raw.count("<category>")
    r = parse_drc_report(FIX / "drc_dirty_4743.lyrdb")
    assert naive == DIRTY_TOTAL + DECLARED_CATEGORIES  # 4816, the trap
    assert r.declared_categories == DECLARED_CATEGORIES
    assert r.total_violations == DIRTY_TOTAL


def test_genuinely_clean_report_is_clean():
    """Same 73 rule categories declared, zero items -> a real pass."""
    r = parse_drc_report(FIX / "drc_clean_0.lyrdb", expected_top="top")
    assert r.clean is True
    assert r.total_violations == 0
    assert r.declared_categories == DECLARED_CATEGORIES
    assert "clean" in r.summary().lower()


def test_wrong_top_cell_is_rejected():
    """A report for another layout must not satisfy this design's check."""
    r = parse_drc_report(FIX / "drc_clean_0.lyrdb", expected_top="cam_top")
    assert r.clean is False
    assert any("different layout" in p for p in r.problems)


def test_missing_report_is_not_clean(tmp_path):
    r = parse_drc_report(tmp_path / "nope.lyrdb", expected_top="top")
    assert r.clean is False
    assert any("not written" in p for p in r.problems)


def test_empty_report_is_not_clean(tmp_path):
    p = tmp_path / "empty.lyrdb"
    p.write_text("", encoding="utf-8")
    r = parse_drc_report(p, expected_top="top")
    assert r.clean is False
    assert any("empty" in p_ for p_ in r.problems)


def test_truncated_report_is_not_clean(tmp_path):
    """A crashed deck leaves invalid XML. That is a failure, not a clean run."""
    full = (FIX / "drc_dirty_4743.lyrdb").read_text(encoding="utf-8")
    p = tmp_path / "truncated.lyrdb"
    p.write_text(full[: len(full) // 3], encoding="utf-8")
    r = parse_drc_report(p, expected_top="top")
    assert r.clean is False
    assert any("not valid XML" in x for x in r.problems)


def test_ruleless_deck_is_not_clean(tmp_path):
    """Zero declared categories means the runset checked nothing."""
    p = tmp_path / "ruleless.lyrdb"
    p.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<report-database><top-cell>top</top-cell>"
        "<categories></categories><items></items></report-database>",
        encoding="utf-8",
    )
    r = parse_drc_report(p, expected_top="top")
    assert r.clean is False
    assert any("checked nothing" in x for x in r.problems)


def test_innovus_false_clean_is_not_a_drc_pass():
    """The Innovus text report that hid these violations is not even parseable
    as a KLayout report, so it can never be mistaken for a signoff result."""
    r = parse_drc_report(FIX / "innovus_false_clean.rpt", expected_top="top")
    assert r.clean is False
    assert "No DRC violations were found" in (
        FIX / "innovus_false_clean.rpt"
    ).read_text(encoding="utf-8")


def test_gds_binding_is_recorded(tmp_path):
    """The report cannot say which GDS it read, so we attach that ourselves."""
    gds = tmp_path / "final.gds"
    gds.write_bytes(b"HEADER-not-a-real-gds")
    art = Artifact.capture("final_gds", gds, stage="gdsout", meta={"top_cell": "top"})
    r = parse_drc_report(FIX / "drc_clean_0.lyrdb", expected_top="top", checked_gds=art)
    assert r.checked_gds is not None
    assert r.checked_gds.sha256 == art.sha256
    assert r.to_dict()["checked_gds"]["path"] == str(gds)


def test_original_file_field_is_empty_in_real_reports():
    """Documents *why* the ledger exists: KLayout does not record the input."""
    import xml.etree.ElementTree as ET

    for name in ("drc_dirty_4743.lyrdb", "drc_dirty_1626.lyrdb"):
        root = ET.parse(FIX / name).getroot()
        assert (root.findtext("original-file") or "").strip() == ""


def test_digest_is_compact_and_ordered():
    r = parse_drc_report(FIX / "drc_dirty_4743.lyrdb")
    d = r.violation_digest(limit=5)
    assert "4743" in d
    assert DIRTY_WORST[0] in d
    assert len(d.splitlines()) < 20
    counts = [
        int(line.split()[0])
        for line in d.splitlines()
        if line.startswith("  ") and line.split() and line.split()[0].isdigit()
    ]
    assert counts == sorted(counts, reverse=True)


@pytest.mark.parametrize(
    "fixture,expected",
    [
        ("drc_dirty_4743.lyrdb", 4743),
        ("drc_dirty_1626.lyrdb", 1626),
        ("drc_clean_0.lyrdb", 0),
    ],
)
def test_totals_across_fixtures(fixture, expected):
    assert parse_drc_report(FIX / fixture).total_violations == expected


def test_rule_notes_explain_the_rules_we_have_diagnosed():
    """A rule name like 'm2.x' is opaque; the digest has to say what caused it."""
    res = DRCResult(
        report_path=Path("r.lyrdb"), top_cell="t", generator="g",
        by_category={"m2.x": 1, "li.3": 26, "nwell.2a": 397, "hvtp.1": 58},
        total_violations=482, declared_categories=100,
    )
    named = dict(res.explanations())
    assert set(named) == {"m2.x", "li.3", "nwell.2a", "hvtp.1"}
    assert "port" in named["m2.x"]
    assert "detailed_route" in named["li.3"]
    assert "filler" in named["nwell.2a"]
    digest = res.violation_digest()
    assert "what these usually mean here:" in digest
    for rule in named:
        assert rule in digest


def test_rule_notes_are_absent_when_nothing_matches():
    res = DRCResult(
        report_path=Path("r.lyrdb"), top_cell="t", generator="g",
        by_category={"some.unknown.rule": 2}, total_violations=2,
        declared_categories=100,
    )
    assert res.explanations() == []
    assert "what these usually mean here" not in res.violation_digest()


def test_clean_report_carries_no_notes():
    res = DRCResult(
        report_path=Path("r.lyrdb"), top_cell="t", generator="g",
        by_category={}, total_violations=0, declared_categories=100,
    )
    assert res.clean
    assert res.explanations() == []
