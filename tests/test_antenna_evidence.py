"""The antenna gate must produce a report that can actually be bound.

`check_antennas` writes **nothing** to its `-report_file` when the design is
clean. The artifact ledger skips zero-length outputs, so `antenna_report` was
never registered, and the first register run to get all the way past LVS was
refused at signoff with:

    antenna's report antenna_report is not registered

A passing gate with no bindable evidence is exactly the failure mode P0-03
exists to prevent, so the fix is to make a clean antenna result a positive
record rather than an absent one -- not to relax the ledger.
"""

from __future__ import annotations

from rtl2gdsagi.checks.tools import ANTENNA_COMPLETE_MARKER
from rtl2gdsagi.ir import IR
from rtl2gdsagi.render import RenderContext, render_antenna


def _ctx(tmp_path, pdk):
    return RenderContext(
        top="widget", pdk=pdk, work_dir=tmp_path,
        inputs={"routed_def": tmp_path / "widget.routed.def"},
        outputs={"antenna_report": tmp_path / "antenna.rpt"},
    )


def test_antenna_report_is_written_even_when_the_design_is_clean(tmp_path, fake_pdk):
    tcl = render_antenna(IR(), _ctx(tmp_path, fake_pdk))

    assert "check_antennas" in tcl
    assert ANTENNA_COMPLETE_MARKER in tcl, (
        "a clean antenna run must still leave content in its report, or the "
        "gate reaches signoff with nothing bound to it"
    )
    # Appended, so real violation output is preserved rather than overwritten.
    assert f"open {tmp_path / 'antenna.rpt'} a" in tcl


def test_the_report_records_the_check_return_value(tmp_path, fake_pdk):
    """Not just "it ran" -- what it found.

    `check_antennas` returns the violation count, so the marker line carries a
    result rather than a bare completion flag.
    """
    tcl = render_antenna(IR(), _ctx(tmp_path, fake_pdk))

    assert "set _ant_violations [check_antennas" in tcl
    assert f'"{ANTENNA_COMPLETE_MARKER} violations=$_ant_violations"' in tcl


def test_rendering_is_still_deterministic(tmp_path, fake_pdk):
    a = render_antenna(IR(), _ctx(tmp_path, fake_pdk))
    b = render_antenna(IR(), _ctx(tmp_path, fake_pdk))
    assert a == b
