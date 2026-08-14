"""Yosys statistics parsing.

Yosys reports cell counts in more than one shape, and which one you get depends
on the design. The compact form is what a *single-module* design produces —
i.e. the first thing anyone writes. Missing it meant an 8-bit register
synthesised perfectly and then failed with "netlist has 0 cells".

All three samples below are copied from real Yosys output.
"""

from __future__ import annotations

import pytest

from rtl2gdsagi.checks.tools import (
    ToolRun,
    _yosys_cell_count,
    _yosys_unmapped,
    check_synthesis,
)
from rtl2gdsagi.checks.verdict import VerdictKind
from rtl2gdsagi.taxonomy import FailureClass

# One flat module: count and area on one line.
FLAT = """
=== widget ===

        +----------Local Count, excluding submodules.
        |        +-Local Area, excluding submodules.
        |        |
       18        - wires
        4        - ports
       22  292.781 cells
        1    5.005   sky130_fd_sc_hd__a21oi_1
        8  200.192   sky130_fd_sc_hd__dfrtp_1

   Chip area for module '\\widget': 292.780800
"""

# Larger design: the area column switches to scientific notation.
SCIENTIFIC = """
=== cam_top ===

      922        - wires
      939 8.56E+03 cells
        1   11.261   sky130_fd_sc_hd__a2111o_1
        4   30.029   sky130_fd_sc_hd__a211oi_1

   Chip area for module '\\cam_top': 8556.956800
"""

# Design with submodules: an explicit labelled total.
LABELLED = """
=== design hierarchy ===

   Number of wires:               1024
   Number of cells:                929
     sky130_fd_sc_hd__nand2_1       12
     sky130_fd_sc_hd__dfrtp_1      100

   Chip area for top module '\\cam_top': 8944.828800
"""


@pytest.mark.parametrize("text,expected", [
    (FLAT, 22),
    (SCIENTIFIC, 939),
    (LABELLED, 929),
])
def test_cell_count_is_read_from_every_yosys_format(text, expected):
    assert _yosys_cell_count(text) == expected


def test_a_single_module_design_synthesises_successfully(tmp_path):
    """The regression: 22 real cells were reported as 0 and failed the stage."""
    netlist = tmp_path / "widget.v"
    netlist.write_text("module widget(); endmodule\n", encoding="utf-8")

    v = check_synthesis(
        ToolRun(argv=[], returncode=0, stdout=FLAT, stderr=""), netlist,
    )
    assert v.kind is VerdictKind.PASS, v.summary
    assert v.metrics["cells"] == 22
    assert v.metrics["area_um2"] == pytest.approx(292.7808)


def test_an_empty_netlist_still_fails(tmp_path):
    netlist = tmp_path / "empty.v"
    netlist.write_text("module widget(); endmodule\n", encoding="utf-8")
    v = check_synthesis(
        ToolRun(argv=[], returncode=0, stdout="=== widget ===\nno cells\n",
                stderr=""),
        netlist,
    )
    assert v.blocks is True
    assert "0 cells" in v.summary


def test_unmapped_cells_are_detected_in_the_compact_format():
    """A $-prefixed cell means logic no foundry cell implements."""
    text = FLAT.replace(
        "        1    5.005   sky130_fd_sc_hd__a21oi_1",
        "        3    0.000   $_DLATCH_P_",
    )
    assert _yosys_unmapped(text) == {"$_DLATCH_P_": 3}


def test_unmapped_cells_are_detected_in_the_labelled_format():
    text = LABELLED.replace(
        "     sky130_fd_sc_hd__nand2_1       12",
        "     $_DLATCH_P_                    12",
    )
    assert _yosys_unmapped(text) == {"$_DLATCH_P_": 12}


def test_mapped_cells_are_not_mistaken_for_unmapped():
    assert _yosys_unmapped(FLAT) == {}
    assert _yosys_unmapped(SCIENTIFIC) == {}


def test_unmapped_cells_fail_the_stage(tmp_path):
    netlist = tmp_path / "n.v"
    netlist.write_text("module widget(); endmodule\n", encoding="utf-8")
    text = FLAT.replace(
        "        1    5.005   sky130_fd_sc_hd__a21oi_1",
        "        3    0.000   $_DLATCH_P_",
    )
    v = check_synthesis(ToolRun(argv=[], returncode=0, stdout=text, stderr=""), netlist)
    assert v.blocks is True
    assert v.failure is FailureClass.SYNTH_ERROR
    assert "unmapped" in v.summary


def test_yosys_error_is_classified_as_elaboration_when_it_mentions_a_module(tmp_path):
    v = check_synthesis(
        ToolRun(argv=[], returncode=1,
                stdout="ERROR: Module `\\missing' referenced but not found\n",
                stderr=""),
        None,
    )
    assert v.failure is FailureClass.ELABORATION


def test_missing_netlist_fails_even_on_a_clean_exit(tmp_path):
    v = check_synthesis(
        ToolRun(argv=[], returncode=0, stdout=FLAT, stderr=""),
        tmp_path / "never_written.v",
    )
    assert v.blocks is True
    assert "wrote no netlist" in v.summary
