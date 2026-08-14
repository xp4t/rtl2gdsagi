"""P0-07: the LVS reference models the substrate as its own node.

The defect
==========

The flow used to build its reference netlist by *deleting* each cell's ``VNB``
bulk pin and rewriting its occurrences to ``VGND``, then telling extraction to
call the substrate ``VGND`` too (``-rd lvs_sub=VGND``). Both sides then agreed
-- but only by sharing a name.

The SKY130 KLayout deck models the substrate as ``sub = polygon_layer``: an
empty layer, no geometry, promoted to a global net. Its ``connect_implicit("*")``
joins same-named parts by name, documented as working "without need for a
physical connection". Naming the substrate ``VGND`` therefore name-joined a
geometry-less node to every cell's labelled ground metal, and KLayout recorded
a must-connect obligation to discharge higher up. Nothing can discharge it,
because there is no geometry to connect with. That produced three permanent,
unfixable LVS failures on the register design.

The fix gives the substrate its own name on both sides, so the bulk terminals
are compared instead of merged away.

These are production gate tests: each one fails if the substrate model
regresses.
"""

from __future__ import annotations

import pytest

from rtl2gdsagi.spice import SUBSTRATE_NET, model_substrate, to_spice

CDL = """\
.SUBCKT sky130_fd_sc_hd__inv_1 A VGND VNB VPB VPWR Y
*.PININFO A:I VGND:G VNB:B VPB:B VPWR:G Y:O
MM1 Y A VGND VNB nfet_01v8 m=1 w=0.65 l=0.15
MM2 Y A VPWR VPB pfet_01v8 m=1 w=1.0 l=0.15
.ENDS sky130_fd_sc_hd__inv_1
"""

NETLIST = """\
module widget (i_a, o_y);
  input i_a;
  output o_y;
  sky130_fd_sc_hd__inv_1 u0 (.A(i_a), .Y(o_y));
endmodule
"""


@pytest.fixture
def cdl(tmp_path):
    p = tmp_path / "cells.cdl"
    p.write_text(CDL)
    return p


@pytest.fixture
def netlist(tmp_path):
    p = tmp_path / "widget.v"
    p.write_text(NETLIST)
    return p


def reference(cdl, netlist, **kw):
    return to_spice(netlist, "widget", cdl, **kw)


# ---- the substrate is a real node -----------------------------------------

def test_the_bulk_pin_survives_as_a_substrate_pin(cdl, netlist):
    """It used to be deleted. That deletion was the root cause of P0-07."""
    out = reference(cdl, netlist, substrate_net=SUBSTRATE_NET)

    defs = [ln for ln in out.splitlines()
            if ln.startswith(".SUBCKT sky130_fd_sc_hd__inv_1")]
    assert defs, "the cell definition is missing entirely"
    assert SUBSTRATE_NET in defs[0].split(), (
        f"the substrate pin is not on the cell definition: {defs[0]!r}"
    )
    assert "VNB" not in defs[0].split(), "the raw CDL bulk name should be renamed"


def test_nfet_bulk_sits_on_the_substrate_not_on_ground(cdl, netlist):
    """The whole point: bulk and ground are different nodes."""
    out = reference(cdl, netlist, substrate_net=SUBSTRATE_NET)

    nfet = [ln for ln in out.splitlines() if "nfet_01v8" in ln]
    assert nfet, "no nfet device card in the reference"
    # M<name> <D> <G> <S> <B> <model> ...
    assert nfet[0].split()[4] == SUBSTRATE_NET, (
        f"nfet bulk is not on the substrate node: {nfet[0]!r}"
    )


def test_the_substrate_is_a_top_level_port(cdl, netlist):
    """Extraction promotes the global substrate to a pin on the top cell.

    If the reference does not declare it, the two top circuits differ by a
    port and the comparison is about the wrong thing.
    """
    out = reference(cdl, netlist, substrate_net=SUBSTRATE_NET)
    top = [ln for ln in out.splitlines() if ln.startswith(".SUBCKT widget")][0]
    assert SUBSTRATE_NET in top.split()
    assert "VGND" in top.split(), "ground is still a top-level port"


def test_substrate_and_ground_are_distinct_names(cdl, netlist):
    """The name collision *is* the defect; assert it cannot come back.

    If SUBSTRATE_NET were ever set to VGND (or VPWR), the deck's implicit
    joining would recreate the unsatisfiable must-connect obligation.
    """
    assert SUBSTRATE_NET not in ("VGND", "VPWR", "VPB", "VNB")

    out = reference(cdl, netlist, substrate_net=SUBSTRATE_NET)
    nfet = [ln for ln in out.splitlines() if "nfet_01v8" in ln][0].split()
    source, bulk = nfet[3], nfet[4]
    assert source == "VGND" and bulk == SUBSTRATE_NET, (
        "source and bulk must be separately identifiable for LVS to compare "
        f"substrate connectivity, got source={source} bulk={bulk}"
    )


# ---- the legacy model, kept reproducible ----------------------------------

def test_legacy_model_deletes_the_pin_and_conflates_the_nodes(cdl, netlist):
    """Documents the old behaviour rather than trusting the report.

    This is what shipped, and what produced the three permanent failures.
    """
    out = reference(cdl, netlist)                     # substrate_net=None

    defs = [ln for ln in out.splitlines()
            if ln.startswith(".SUBCKT sky130_fd_sc_hd__inv_1")][0]
    assert "VNB" not in defs.split()
    assert SUBSTRATE_NET not in defs.split(), "legacy model had no substrate node"

    nfet = [ln for ln in out.splitlines() if "nfet_01v8" in ln][0].split()
    assert nfet[3] == nfet[4] == "VGND", (
        "the legacy model tied bulk to ground, making substrate connectivity "
        "unverifiable by construction"
    )


# ---- the rename helper -----------------------------------------------------

def test_model_substrate_renames_rather_than_removes():
    spice = (
        ".SUBCKT cell A VGND VNB VPB VPWR Y\n"
        "*.PININFO A:I VGND:G VNB:B VPB:B VPWR:G Y:O\n"
        "MM1 Y A VGND VNB nfet_01v8 m=1\n"
        ".ENDS cell\n"
    )
    out = model_substrate(spice, "VNB", "VSUBS")

    assert ".SUBCKT cell A VGND VSUBS VPB VPWR Y" in out
    assert "VSUBS:B" in out, "PININFO must track the rename"
    assert "MM1 Y A VGND VSUBS nfet_01v8 m=1" in out
    assert "VNB" not in out


def test_model_substrate_leaves_similar_names_alone():
    """`VNB` must not match inside `VNBX` or `X.VNB`."""
    spice = ".SUBCKT cell VNBX A\nMM1 A A VNBX VNB nfet m=1\n.ENDS cell\n"
    out = model_substrate(spice, "VNB", "VSUBS")
    assert "VNBX" in out
    assert "MM1 A A VNBX VSUBS nfet m=1" in out


# ---- the production invocation --------------------------------------------

def test_production_lvs_does_not_alias_the_substrate_to_ground():
    """The `-rd lvs_sub=VGND` workaround must not come back.

    Read out of the runner source rather than a rendered command, because the
    argument is built inline and this is the thing that must never regress.
    """
    from pathlib import Path

    import rtl2gdsagi.runner as runner_mod

    src = Path(runner_mod.__file__).read_text()
    assert "lvs_sub=VGND" not in src, (
        "the substrate is aliased to the ground net again; this recreates the "
        "unsatisfiable must-connect obligation that was P0-07"
    )
    assert "lvs_sub={SUBSTRATE_NET}" in src, (
        "the LVS invocation must name the substrate from the same constant the "
        "reference netlist uses, or the two sides model different nodes"
    )
