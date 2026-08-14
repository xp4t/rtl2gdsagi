"""Characterization tests.

These use small inline designs plus, where available, the real OV7670 RTL on
this machine. Every bug pinned here was found by rendering an SDC and reading
it: a mis-parse does not crash, it silently emits wrong constraints, and a
clock that never gets a create_clock reports falsely clean timing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rtl2gdsagi.characterize import characterize, suggest_starting_ir

OV7670 = Path("/home/xpat/ov7670/rtl")
needs_ov7670 = pytest.mark.skipif(
    not OV7670.is_dir(), reason="OV7670 fixture not present on this machine"
)


def write(tmp_path: Path, name: str, text: str) -> Path:
    d = tmp_path / "rtl"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")
    return d


def test_ansi_port_list_is_parsed_completely(tmp_path):
    """Regression: a \\s comma-continuation swallowed newlines, capturing the
    next line's `input` keyword as a port and dropping the real ports."""
    d = write(tmp_path, "m.v", """
module m (
    input  wire i_clk,
    input  wire i_rst_n,
    input  wire i_start,
    input  wire [7:0] i_data,
    output wire o_done
);
endmodule
""")
    f = characterize(d, "m")
    assert f.inputs == ["i_clk", "i_rst_n", "i_start", "i_data"]
    assert f.outputs == ["o_done"]
    assert "input" not in f.inputs and "output" not in f.outputs


def test_multiple_declarations_on_one_line(tmp_path):
    """Regression: `input wire a, input wire b` lost b entirely."""
    d = write(tmp_path, "m.v",
              "module m (input wire i_clk_a, input wire i_clk_b, output wire y);\n"
              "endmodule\n")
    f = characterize(d, "m")
    assert f.inputs == ["i_clk_a", "i_clk_b"]
    assert f.outputs == ["y"]


def test_multiple_names_on_one_declaration(tmp_path):
    d = write(tmp_path, "m.v", """
module m (input wire a, b, c, output wire y);
endmodule
""")
    f = characterize(d, "m")
    assert f.inputs == ["a", "b", "c"]


@pytest.mark.parametrize(
    "port,is_clock",
    [
        ("i_clk", True), ("clk", True), ("i_pclk", True), ("sys_clock", True),
        ("w_clk25m", True), ("i_top_pclk", True),
        ("i_rst_n", False), ("i_rstn", False), ("reset", False),
        ("aresetn", False), ("i_data", False), ("o_done", False),
    ],
)
def test_clock_and_reset_discrimination(tmp_path, port, is_clock):
    """`i_rstn_clk` contains 'clk' but is a reset. Constraining it as a clock
    invents a domain that does not exist."""
    d = write(tmp_path, "m.v", f"module m (input wire {port});\nendmodule\n")
    f = characterize(d, "m")
    assert bool(f.clocks) is is_clock, f"{port}: clocks={f.clocks} resets={f.resets}"


def test_reset_synchronised_into_a_clock_domain_is_not_a_clock(tmp_path):
    d = write(tmp_path, "m.v", """
module m (input wire i_clk, input wire i_rstn_clk, input wire i_rstn_pclk);
endmodule
""")
    f = characterize(d, "m")
    assert [c["name"] for c in f.clocks] == ["i_clk"]
    assert set(f.resets) == {"i_rstn_clk", "i_rstn_pclk"}


def test_edge_referenced_signal_is_detected_as_a_clock(tmp_path):
    """A clock whose name gives no hint is still found via its edge use."""
    d = write(tmp_path, "m.v", """
module m (input wire strobe, input wire d, output reg q);
    always @(posedge strobe) q <= d;
endmodule
""")
    f = characterize(d, "m")
    assert [c["name"] for c in f.clocks] == ["strobe"]


def test_missing_top_is_reported_not_silently_empty(tmp_path):
    d = write(tmp_path, "m.v", "module m (input wire a);\nendmodule\n")
    f = characterize(d, "nonexistent")
    assert f.warnings and "not found" in f.warnings[0]


def test_design_with_no_clock_warns(tmp_path):
    d = write(tmp_path, "m.v", "module m (input wire a, output wire y);\nendmodule\n")
    f = characterize(d, "m")
    assert f.clocks == []
    assert any("no clock port" in w for w in f.warnings)


def test_comments_do_not_create_phantom_ports(tmp_path):
    d = write(tmp_path, "m.v", """
module m (
    input wire i_clk
    // input wire i_ghost,
    /* input wire i_other, */
);
endmodule
""")
    f = characterize(d, "m")
    assert f.inputs == ["i_clk"]


def test_starting_knobs_scale_with_design_size(tmp_path):
    small = characterize(write(tmp_path / "a", "m.v",
                               "module m(input wire i_clk); endmodule\n"), "m")
    body = "\n".join(f"always @(posedge i_clk) r{i} <= r{i}+1;" for i in range(60))
    big = characterize(write(tmp_path / "b", "m.v",
                             f"module m(input wire i_clk);\n{body}\nendmodule\n"), "m")
    assert (suggest_starting_ir(small)["floorplan"]["core_utilization"]
            <= suggest_starting_ir(big)["floorplan"]["core_utilization"])


def test_multiple_clock_domains_relax_the_skew_target(tmp_path):
    d = write(tmp_path, "m.v", """
module m (input wire i_clk_a, input wire i_clk_b);
endmodule
""")
    f = characterize(d, "m")
    assert f.clock_domains == 2
    assert "cts" in suggest_starting_ir(f)


# ---- against the real design ---------------------------------------------

@needs_ov7670
def test_ov7670_top_has_three_clock_domains():
    """The design is documented as having three asynchronous clock domains."""
    f = characterize(OV7670, "top")
    names = [c["name"] for c in f.clocks]
    assert len(names) == 3, names
    assert set(names) == {"i_top_clk", "w_clk25m", "i_top_pclk"}
    assert f.resets == ["i_top_rst"]


@needs_ov7670
def test_ov7670_modules_are_all_discovered():
    f = characterize(OV7670, "cam_top")
    for m in ("cam_top", "vga_top", "sccb_master", "cam_rom", "vga_driver",
              "cam_capture", "cam_config", "cam_init", "mem_bram", "top"):
        assert m in f.modules, m


@needs_ov7670
def test_ov7670_cam_top_separates_clocks_from_resets():
    f = characterize(OV7670, "cam_top")
    assert [c["name"] for c in f.clocks] == ["i_clk", "i_pclk"]
    assert set(f.resets) == {"i_rstn_clk", "i_rstn_pclk"}
