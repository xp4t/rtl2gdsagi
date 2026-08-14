"""The routing renderer must emit a legal layer range for every legal IR.

`set_routing_layers -clock met{max(lo, 3)}-met{hi}` produced `met3-met2`
whenever `max_layer` was below 3. `max_layer` is agent-writable over 1..12, so
a schema-valid IR could drive the renderer to emit a command OpenROAD rejects
outright:

    [ERROR GRT-0056] In argument -clock_layers, min routing layer is greater
                     than max routing layer.

This is a renderer correctness bug in its own right -- an operator setting
`max_layer: 2` gets a malformed argument rather than a two-layer design -- and
is fixed independently of any benchmark. It is deliberately NOT the basis of an
autonomy benchmark: an illegal tool argument is a configuration defect, not a
physical implementation failure.
"""

from __future__ import annotations

import re

import pytest

from rtl2gdsagi.ir import IR, SCHEMA
from rtl2gdsagi.render import RenderContext, render_routing

_RANGE = re.compile(r"-(signal|clock) met(\d+)-met(\d+)")

BOUNDS = next(f for f in SCHEMA["routing"] if f.name == "max_layer")


def _tcl(tmp_path, pdk, **routing):
    ctx = RenderContext(
        top="widget", pdk=pdk, work_dir=tmp_path,
        inputs={k: tmp_path / k for k in ("cts_def", "sdc", "netlist")},
        outputs={k: tmp_path / k for k in
                 ("routed_def", "routed_netlist", "route_drc",
                  "congestion_report", "route_report")},
    )
    return render_routing(IR({"routing": routing}), ctx)


@pytest.mark.parametrize("max_layer", range(int(BOUNDS.lo), int(BOUNDS.hi) + 1))
def test_every_legal_max_layer_renders_a_legal_range(tmp_path, fake_pdk, max_layer):
    tcl = _tcl(tmp_path, fake_pdk, max_layer=max_layer)
    found = _RANGE.findall(tcl)
    assert found, "no routing layer range was rendered"
    for which, lo, hi in found:
        assert int(lo) <= int(hi), (
            f"max_layer={max_layer} renders an inverted -{which} range "
            f"met{lo}-met{hi}, which OpenROAD rejects with GRT-0056"
        )


@pytest.mark.parametrize("max_layer", [1, 2])
def test_the_clock_range_stays_inside_the_signal_range(tmp_path, fake_pdk, max_layer):
    tcl = _tcl(tmp_path, fake_pdk, max_layer=max_layer)
    ranges = {w: (int(lo), int(hi)) for w, lo, hi in _RANGE.findall(tcl)}
    slo, shi = ranges["signal"]
    clo, chi = ranges["clock"]
    assert slo <= clo <= chi <= shi, (
        f"clock met{clo}-met{chi} escapes signal met{slo}-met{shi}"
    )


def test_the_default_configuration_is_unchanged(tmp_path, fake_pdk):
    """The fix must not move the normal case."""
    tcl = _tcl(tmp_path, fake_pdk)
    assert "-signal met1-met5 -clock met3-met5" in tcl.replace("\n", " ").replace("  ", " ")


def test_min_above_max_is_still_refused(tmp_path, fake_pdk):
    with pytest.raises(ValueError, match="exceeds max_layer"):
        _tcl(tmp_path, fake_pdk, min_layer=4, max_layer=2)
