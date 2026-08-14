"""P0-R3: the PDN postcondition is immutable and model-independent.

Codex's reproduction: `pdn.core_ring` is agent-writable. The renderer omits the
ring when it is false, and the runner passed that same value to the checker as
`expect_ring`. So a PDN diagnosis changed both the implementation *and* the
definition of an acceptable implementation. The runner also read
`pdn.strap_layers`, which is not a schema field, so the required strap-layer
tuple was always empty. A DEF with supply rails, no upper distribution and one
via therefore returned `ok=True`.

The postcondition now lives in `checks.pdn.PDNContract`, outside model-writable
IR, and requires met4+met5 distribution and a full via ladder for **both**
supplies.
"""

from __future__ import annotations

import pytest

from rtl2gdsagi.checks.pdn import (
    SKY130_MINIMUM_PDN,
    PDNContract,
    check_pdn_def,
    via_prefix,
)

RAIL = "      NEW met1 480 + SHAPE FOLLOWPIN ( 10120 {y} ) ( 38640 {y} )"
LADDER = [
    "      NEW met1 0 + SHAPE STRIPE ( 12120 38080 ) via2_3_1600_480_1_5_320_320",
    "      NEW met2 0 + SHAPE STRIPE ( 12120 38080 ) via3_4_1600_480_1_4_400_400",
    "      NEW met3 0 + SHAPE STRIPE ( 12120 38080 ) via4_5_1600_480_1_4_400_400",
    "      NEW met4 0 + SHAPE STRIPE ( 12120 12880 ) via5_6_1600_1600_1_1_1600_1600",
]


def _net(name, use, *, rails=True, met4=True, met5=True, ring=False,
         ladder=True, extra=()):
    out = [f"    - {name} ( * {name} ) + USE {use}"]
    if met5:
        out.append("      + ROUTED met5 1600 + SHAPE STRIPE "
                   "( 4020 12880 ) ( 44740 12880 )")
    if met4:
        out.append("      NEW met4 1600 + SHAPE STRIPE "
                   "( 12120 4780 ) ( 12120 44180 )")
    if rails:
        out += [RAIL.format(y=y) for y in (10880, 16320, 21760)]
    if ring:
        out.append("      NEW met4 1600 + SHAPE RING ( 4820 4780 ) ( 4820 44180 )")
    if ladder:
        out += LADDER
    out += list(extra)
    return out


def write_def(tmp_path, nets, name="pdn.def"):
    body = ["VERSION 5.8 ;", "DESIGN register ;", f"SPECIALNETS {len(nets)} ;"]
    for n in nets:
        body += n
    body += ["END SPECIALNETS", "END DESIGN"]
    p = tmp_path / name
    p.write_text("\n".join(x if x.endswith(";") or x.startswith(" ") else x
                           for x in body) + "\n")
    return p


def good(tmp_path, **kw):
    return write_def(tmp_path, [
        _net("VPWR", "POWER", **kw), _net("VGND", "GROUND", **kw)])


# ---- the contract is satisfiable at all --------------------------------

def test_a_complete_grid_passes(tmp_path):
    res = check_pdn_def(good(tmp_path))
    assert res.ok, res.problems


# ---- the reproduction --------------------------------------------------

def test_rails_only_with_a_via_is_rejected(tmp_path):
    """Codex's exact negative control: rails + a via, no upper distribution.

    This returned ok=True when `core_ring=false`.
    """
    d = write_def(tmp_path, [
        _net("VPWR", "POWER", met4=False, met5=False, ladder=False,
             extra=["      NEW met1 0 + SHAPE STRIPE ( 12120 38080 ) "
                    "via2_3_1600_480_1_5_320_320"]),
        _net("VGND", "GROUND", met4=False, met5=False, ladder=False,
             extra=["      NEW met1 0 + SHAPE STRIPE ( 12120 38080 ) "
                    "via2_3_1600_480_1_5_320_320"]),
    ])
    res = check_pdn_def(d)
    assert not res.ok
    assert any("no STRIPE geometry on met4" in p for p in res.problems)


def test_the_model_cannot_switch_off_the_obligation(tmp_path):
    """There is no argument by which a caller relaxes the requirement.

    The old signature accepted `expect_ring` and `strap_layers` straight from
    the IR. Requiring a keyword-only `contract` object means the runner cannot
    accidentally hand model state to the checker.
    """
    import inspect

    sig = inspect.signature(check_pdn_def)
    assert "expect_ring" not in sig.parameters
    assert "strap_layers" not in sig.parameters
    assert set(sig.parameters) == {"path", "contract"}

    # And the runner does not read those IR fields any more.
    from pathlib import Path

    import rtl2gdsagi.runner as runner_mod

    src = Path(runner_mod.__file__).read_text()
    assert "check_pdn_def(Path(ctx.out(\"pdn_def\")), contract=SKY130_MINIMUM_PDN)" in src
    assert 'expect_ring=bool(s[' not in src
    assert 'strap_layers=tuple(' not in src


def test_core_ring_false_does_not_weaken_anything(tmp_path):
    """A ring-less DEF is still held to the full distribution contract."""
    assert SKY130_MINIMUM_PDN.require_ring is False
    without = check_pdn_def(good(tmp_path, ring=False))
    assert without.ok, without.problems

    # ... but turning the ring off cannot rescue a grid missing distribution.
    broken = write_def(tmp_path, [
        _net("VPWR", "POWER", met4=False, ring=False),
        _net("VGND", "GROUND", met4=False, ring=False),
    ], name="broken.def")
    assert not check_pdn_def(broken).ok


# ---- per-supply requirements -------------------------------------------

@pytest.mark.parametrize("supply,use", [("VPWR", "POWER"), ("VGND", "GROUND")])
def test_distribution_is_required_for_each_supply_separately(
        tmp_path, supply, use):
    """Distributing only one supply is not a power network."""
    nets = []
    for name, u in (("VPWR", "POWER"), ("VGND", "GROUND")):
        full = name != supply
        nets.append(_net(name, u, met4=full, met5=full))
    res = check_pdn_def(write_def(tmp_path, nets))
    assert not res.ok
    assert any(supply in p and "STRIPE" in p for p in res.problems)


def test_a_broken_layer_transition_is_rejected(tmp_path):
    """Drop met3->met4 and the upper straps float above the rails."""
    partial = [v for v in LADDER if not v.count("via4_5")]
    nets = [
        _net("VPWR", "POWER", ladder=False, extra=partial),
        _net("VGND", "GROUND", ladder=False, extra=partial),
    ]
    res = check_pdn_def(write_def(tmp_path, nets))
    assert not res.ok
    assert any("met3-to-met4" in p for p in res.problems)


def test_a_via_ladder_present_on_only_one_supply_is_rejected(tmp_path):
    nets = [
        _net("VPWR", "POWER"),
        _net("VGND", "GROUND", ladder=False),
    ]
    res = check_pdn_def(write_def(tmp_path, nets))
    assert not res.ok
    assert any("VGND" in p and "via" in p for p in res.problems)


def test_missing_rails_still_rejected(tmp_path):
    nets = [_net("VPWR", "POWER", rails=False), _net("VGND", "GROUND")]
    res = check_pdn_def(write_def(tmp_path, nets))
    assert not res.ok
    assert any("FOLLOWPIN" in p for p in res.problems)


# ---- the via naming table ----------------------------------------------

def test_via_prefix_matches_the_pinned_openroad_naming():
    assert via_prefix("met1", "met2") == "via2_3_"
    assert via_prefix("met4", "met5") == "via5_6_"
    with pytest.raises(KeyError):
        via_prefix("met1", "metX")


def test_the_contract_is_frozen():
    with pytest.raises(Exception):
        SKY130_MINIMUM_PDN.require_ring = True  # type: ignore[misc]


def test_contract_defaults_match_what_the_renderer_builds():
    """If the renderer's layers change, this test is the tripwire."""
    c = PDNContract()
    assert c.rail_layer == "met1"
    assert c.distribution_layers == ("met4", "met5")
    assert c.via_ladder[0] == ("met1", "met2")
    assert c.via_ladder[-1] == ("met4", "met5")
