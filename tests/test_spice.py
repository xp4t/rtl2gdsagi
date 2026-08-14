"""Verilog netlist -> SPICE conversion for the LVS reference side.

SPICE subcircuit calls are **positional**, and for SKY130 no two views of a cell
agree on order:

    .SUBCKT sky130_fd_sc_hd__inv_1 A VGND VNB VPB VPWR Y     <- CDL
    module   sky130_fd_sc_hd__inv_1 (Y, A);                   <- blackbox
    module   sky130_fd_sc_hd__inv_1 (Y, A, VPWR, VGND, VPB, VNB);  <- power-pin

Anything that writes ports in Verilog order — `yosys write_spice` included —
miswires every instance while producing a file that looks entirely reasonable.
So the order comes from the CDL and the netlist's *named* connections are placed
into it. These tests pin that, because a silent miswiring would make LVS
meaningless in the most dangerous possible way: it would still run.
"""

from __future__ import annotations

import pytest

from rtl2gdsagi.spice import (
    SpiceConversionError,
    deviceless_cells,
    extract_subckts,
    parse_cdl_pins,
    parse_gate_netlist,
    qualify_device_models,
    to_spice,
)

CDL = """\
.SUBCKT sky130_fd_sc_hd__inv_1 A VGND VNB VPB VPWR Y
MM1 Y A VGND VNB nfet_01v8 m=1 w=0.65 l=0.15
.ENDS sky130_fd_sc_hd__inv_1
.SUBCKT sky130_fd_sc_hd__nand2_1 A B VGND VNB VPB VPWR Y
MM1 Y A VGND VNB nfet_01v8 m=1
.ENDS sky130_fd_sc_hd__nand2_1
.SUBCKT sky130_fd_sc_hd__fill_1 VGND VNB VPB VPWR
.ENDS sky130_fd_sc_hd__fill_1
.SUBCKT sky130_fd_sc_hd__macro_sparecell VGND VNB VPB VPWR LO
XI1 VGND VNB VPB VPWR net59 LO / sky130_fd_sc_hd__inv_1
.ENDS sky130_fd_sc_hd__macro_sparecell
"""

NETLIST = """\
module widget (i_clk, i_data, o_data);
  input i_clk;
  input [1:0] i_data;
  output [1:0] o_data;
  sky130_fd_sc_hd__inv_1 _00_ (.A(i_data[0]), .Y(o_data[0]));
  sky130_fd_sc_hd__nand2_1 _01_ (.A(i_data[0]), .B(i_data[1]), .Y(o_data[1]));
  sky130_fd_sc_hd__fill_1 FILLER_0 ();
endmodule
"""


@pytest.fixture
def cdl(tmp_path):
    p = tmp_path / "cells.cdl"
    p.write_text(CDL, encoding="utf-8")
    return p


@pytest.fixture
def netlist(tmp_path):
    p = tmp_path / "widget.routed.v"
    p.write_text(NETLIST, encoding="utf-8")
    return p


# ---- parsing --------------------------------------------------------------

def test_cdl_pin_order_is_read_verbatim(cdl):
    pins = parse_cdl_pins(cdl)
    assert pins["sky130_fd_sc_hd__inv_1"] == ["A", "VGND", "VNB", "VPB", "VPWR", "Y"]


def test_bus_ports_are_expanded_msb_first(netlist):
    g = parse_gate_netlist(netlist, "widget")
    assert g.ports == ["i_clk", "i_data[1]", "i_data[0]", "o_data[1]", "o_data[0]"]


def test_instances_and_named_connections_are_read(netlist):
    g = parse_gate_netlist(netlist, "widget")
    assert len(g.instances) == 3
    inv = next(i for i in g.instances if i.name == "_00_")
    assert inv.connections == {"A": "i_data[0]", "Y": "o_data[0]"}


def test_a_missing_top_module_is_an_error(netlist):
    with pytest.raises(SpiceConversionError, match="not found"):
        parse_gate_netlist(netlist, "nonexistent")


# ---- the property that matters --------------------------------------------

def test_pins_are_emitted_in_cdl_order_not_verilog_order(cdl, netlist):
    """The whole point. Verilog says (Y, A); the CDL says A VGND VNB VPB VPWR Y."""
    text = to_spice(netlist, "widget", cdl, include_cdl=False)
    line = next(l for l in text.splitlines() if l.startswith("X_00_"))
    assert line == "X_00_ i_data[0] VGND VPWR VPWR o_data[0] sky130_fd_sc_hd__inv_1"


def test_power_pins_are_tied_to_the_supplies(cdl, netlist):
    """The Verilog never mentions VPWR/VGND/VPB; the layout has them all.

    VNB is the exception: the deck declares the substrate global, so the
    extracted cells carry no bulk terminal and neither may the reference.
    """
    text = to_spice(netlist, "widget", cdl, include_cdl=False)
    line = next(l for l in text.splitlines() if l.startswith("X_01_"))
    # CDL order A B VGND VNB VPB VPWR Y, minus the global substrate pin.
    assert line.split()[1:] == [
        "i_data[0]", "i_data[1]", "VGND", "VPWR", "VPWR", "o_data[1]",
        "sky130_fd_sc_hd__nand2_1",
    ]


def test_substrate_pin_is_dropped_from_the_cell_definitions(cdl, netlist):
    """connect_global(sub, ...) means the bulk is not a per-cell terminal.

    Keeping the CDL's VNB pin mismatches every cell in both directions at
    once, which is the failure that tempts people into hardcoding an LVS pass.
    """
    text = to_spice(netlist, "widget", cdl)
    defn = next(l for l in text.splitlines()
                if l.upper().startswith(".SUBCKT SKY130_FD_SC_HD__NAND2_1"))
    assert "VNB" not in defn.split()
    assert "VPB" in defn.split(), "an nwell really is per-cell; VPB must stay"
    body = text.split(defn, 1)[1].split(".ENDS", 1)[0]
    assert "VNB" not in body, "the bulk node has to be rewritten, not left dangling"
    assert "VGND" in body


def test_substrate_pin_is_kept_when_the_caller_asks(cdl, netlist):
    """A deck that extracts the bulk per-cell needs the pin left alone."""
    text = to_spice(netlist, "widget", cdl, substrate_pin="")
    defn = next(l for l in text.splitlines()
                if l.upper().startswith(".SUBCKT SKY130_FD_SC_HD__NAND2_1"))
    assert "VNB" in defn.split()


def test_deviceless_cells_are_omitted_because_extraction_purges_them(cdl, netlist):
    """Fill and well-tap cells are contacts and metal, not one transistor.

    KLayout drops device-less circuits from the extracted layout netlist, so
    keeping them on the reference side leaves circuits with no counterpart and
    the top cell comes back "could not be compared" rather than matching.
    Nothing is lost: a cell with no devices has nothing for LVS to compare, and
    its real job -- nwell continuity -- is checked loudly by DRC instead.
    """
    text = to_spice(netlist, "widget", cdl, include_cdl=False)
    assert not any(l.startswith("XFILLER_0") for l in text.splitlines())
    assert "sky130_fd_sc_hd__fill_1" in text, "the omission must be recorded"
    assert "omitted" in text
    # A cell that does have devices stays.
    assert any(l.startswith("X_00_") for l in text.splitlines())


def test_deviceless_cells_are_kept_when_the_caller_asks(cdl, netlist):
    text = to_spice(netlist, "widget", cdl, include_cdl=False, omit_deviceless=False)
    line = next(l for l in text.splitlines() if l.startswith("XFILLER_0"))
    assert line == "XFILLER_0 VGND VPWR VPWR sky130_fd_sc_hd__fill_1"


def test_deviceless_cells_are_found_from_the_cdl(cdl):
    found = deviceless_cells(cdl)
    assert "sky130_fd_sc_hd__fill_1" in found
    assert "sky130_fd_sc_hd__inv_1" not in found
    # A cell whose body is only a subcircuit call still counts as having content.
    assert "sky130_fd_sc_hd__macro_sparecell" not in found


def test_device_models_are_namespaced_to_match_the_deck(cdl, netlist):
    """The deck extracts into sky130_fd_pr__* classes; the CDL says nfet_01v8."""
    text = to_spice(netlist, "widget", cdl, model_prefix="sky130_fd_pr__")
    card = next(l for l in text.splitlines() if l.startswith("MM1"))
    assert "sky130_fd_pr__nfet_01v8" in card
    # Already-namespaced names are left alone rather than doubled up.
    again = qualify_device_models(card, "sky130_fd_pr__")
    assert "sky130_fd_pr__sky130_fd_pr__" not in again


def test_device_dimensions_get_an_explicit_unit(cdl, netlist):
    """SPICE numbers are metres by convention; the CDL means microns.

    Left bare, KLayout reads w=0.65 as 0.65m and stores 650000um -- wrong by a
    factor of a million against an extracted W of 0.65, so W/L never compare
    equal and no device matches anything.
    """
    text = to_spice(netlist, "widget", cdl)
    card = next(l for l in text.splitlines() if l.startswith("MM1"))
    assert "w=0.65u" in card and "l=0.15u" in card
    bare = to_spice(netlist, "widget", cdl, dimension_unit="")
    assert "w=0.65 " in next(l for l in bare.splitlines() if l.startswith("MM1"))


def test_ground_but_not_power_is_a_top_level_pin(cdl, netlist):
    """Extraction promotes the global substrate net to a top-level pin.

    Power gets no such treatment: with no power pins placed, the supply is an
    internal net that comes back unnamed, so claiming a VPWR port here would
    describe a pin the layout does not have.
    """
    text = to_spice(netlist, "widget", cdl, include_cdl=False)
    subckt = next(l for l in text.splitlines() if l.startswith(".SUBCKT widget"))
    assert subckt.endswith("VGND")
    assert "VPWR" not in subckt.split()


def test_an_unconnected_signal_pin_gets_its_own_net(cdl, tmp_path):
    """Never silently short an open pin to a supply."""
    p = tmp_path / "n.v"
    p.write_text(
        "module widget (o);\n  output o;\n"
        "  sky130_fd_sc_hd__nand2_1 _0_ (.A(o), .Y(o));\n"   # B left open
        "endmodule\n",
        encoding="utf-8",
    )
    text = to_spice(p, "widget", cdl, include_cdl=False)
    line = next(l for l in text.splitlines() if l.startswith("X_0_"))
    assert "_0__B_open" in line


def test_a_cell_missing_from_the_cdl_is_refused(cdl, tmp_path):
    """Unknown pin order means unknown wiring. Fail rather than guess."""
    p = tmp_path / "n.v"
    p.write_text(
        "module widget (o);\n  output o;\n"
        "  some_unknown_cell _0_ (.A(o));\nendmodule\n", encoding="utf-8",
    )
    with pytest.raises(SpiceConversionError, match="no .SUBCKT"):
        to_spice(p, "widget", cdl)


# ---- CDL pruning ----------------------------------------------------------

def test_only_the_cells_in_use_are_included(cdl, netlist):
    text = to_spice(netlist, "widget", cdl)   # hierarchical: cells are defined
    assert "sky130_fd_sc_hd__inv_1" in text
    # The design never instantiates this one, and including it aborts the whole
    # LVS run: its `/` call syntax makes KLayout's reader mis-count pins.
    assert ".SUBCKT sky130_fd_sc_hd__macro_sparecell" not in text


def test_transitively_called_cells_are_pulled_in(cdl):
    """A cell that instantiates others needs those definitions too."""
    text = extract_subckts(cdl, {"sky130_fd_sc_hd__macro_sparecell"})
    assert ".SUBCKT sky130_fd_sc_hd__macro_sparecell" in text
    assert ".SUBCKT sky130_fd_sc_hd__inv_1" in text     # reached via the `/` call


def test_generated_spice_is_self_contained(cdl, netlist):
    """Everything instantiated must also be defined, or LVS cannot resolve it."""
    text = to_spice(netlist, "widget", cdl)
    defined = {l.split()[1] for l in text.splitlines()
               if l.upper().startswith(".SUBCKT")}
    used = {l.split()[-1] for l in text.splitlines() if l.startswith("X")}
    assert used <= defined, f"undefined: {used - defined}"


# ---- flat mode ------------------------------------------------------------

def test_flat_mode_expands_cells_into_transistors(cdl, netlist):
    """Fallback for when hierarchical pin lists cannot be reconciled.

    Extraction merges a cell's bulk pin into the supply when the layout ties
    them inside the cell -- an inverter comes back as `VPB A Y VPWR VGND`, with
    no VNB -- while the CDL always declares both. Whether that happens depends
    on each cell's internal connectivity, so flat transistors sidestep it.
    """
    text = to_spice(netlist, "widget", cdl, flatten=True)
    assert ".SUBCKT sky130_fd_sc_hd__inv_1" not in text     # no cell definitions
    devices = [l for l in text.splitlines() if l.startswith(("M", "m"))]
    assert devices
    # The inverter's transistor, with its formal pins replaced by real nets.
    assert any("i_data[0]" in d and "nfet_01v8" in d for d in devices)


def test_flat_mode_namespaces_internal_nets(cdl, tmp_path):
    """Two instances of one cell must not share its internal nets."""
    p = tmp_path / "n.v"
    p.write_text(
        "module widget (a, y1, y2);\n  input a;\n  output y1;\n  output y2;\n"
        "  sky130_fd_sc_hd__inv_1 _0_ (.A(a), .Y(y1));\n"
        "  sky130_fd_sc_hd__inv_1 _1_ (.A(a), .Y(y2));\n"
        "endmodule\n", encoding="utf-8")
    text = to_spice(p, "widget", cdl, flatten=True)
    names = [l.split()[0] for l in text.splitlines() if l.startswith(("M", "m"))]
    assert len(names) == len(set(names)), "device names collide between instances"
    assert any(n.startswith("M_0_/") for n in names)
    assert any(n.startswith("M_1_/") for n in names)


def test_flat_mode_ties_bulk_to_the_supplies(cdl, netlist):
    text = to_spice(netlist, "widget", cdl, flatten=True)
    inv = next(l for l in text.splitlines() if l.startswith("M_00_/"))
    # MM1 Y A VGND VNB -> the VNB bulk node becomes VGND
    assert inv.split()[1:5] == ["o_data[0]", "i_data[0]", "VGND", "VGND"]
