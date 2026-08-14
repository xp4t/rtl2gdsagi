"""Structural verification of the power distribution network.

What "PDN passed" used to mean, in full:

    OpenROAD exited 0, no [ERROR ...] line, and pdn_def is not empty.

A one-byte file satisfied all three. So would a DEF with one supply and no
rails, or straps that connect to nothing. That matters more than it sounds: a
grid that reaches no cell is invisible to DRC (spacing is fine), invisible to
STA (timing does not model supply), and shows up only in LVS, whose warnings
this project was until recently treating as non-blocking.

This module proves the things a DEF can actually be asked:

* both configured supply nets exist as SPECIALNETS with the right USE;
* standard-cell rails exist as FOLLOWPIN geometry, on the expected layer;
* the configured straps and ring exist on their configured layers;
* the grid is vertically connected -- vias tie the rail layer up through the
  strap layers rather than floating above them;
* nothing declared is left with no geometry at all.

**It does not verify IR drop, electromigration or current density.** Those need
current and activity models this project does not have, and no amount of DEF
reading substitutes for them. They are unverified, and the summary says so.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_SPECIALNETS = re.compile(r"^SPECIALNETS\s+(\d+)\s*;(.*?)^END SPECIALNETS",
                          re.S | re.M)
#: `- VGND ( * VGND ) + USE GROUND` -- the net and how it is used.
_NET_HEAD = re.compile(r"^\s*-\s+(\S+)\s*(.*?)(?=^\s*-\s+\S+\s*\(|\Z)",
                       re.S | re.M)
_USE = re.compile(r"\+\s*USE\s+(\w+)")
#: `NEW met1 480 + SHAPE FOLLOWPIN ( x y ) ( x y )`
_SEGMENT = re.compile(
    r"(?:ROUTED|NEW)\s+(\w+)\s+(\d+)\s*\+\s*SHAPE\s+(\w+)", re.I)
#: A via placement inside a special net: `NEW met1 0 + SHAPE STRIPE ( x y ) VIANAME`
_VIA = re.compile(r"\(\s*-?\d+\s+-?\d+\s*\)\s+([A-Za-z]\w*)")


# ---------------------------------------------------------------------------
# The immutable minimum contract
# ---------------------------------------------------------------------------
#
# P0-R3: the checker used to be told what to require by the same IR fields the
# model is allowed to write. `pdn.core_ring=false` removed the ring from the
# rendered script *and* told the checker to stop requiring one, so a PDN
# diagnosis could change both the implementation and the definition of an
# acceptable implementation. The runner also read `pdn.strap_layers`, which is
# not a schema field at all, so the required strap-layer tuple was always
# empty and a rails-only grid satisfied the gate.
#
# The postcondition now lives here, outside model-writable IR, and describes
# what the renderer is genuinely expected to construct for this methodology.


@dataclass(frozen=True)
class PDNContract:
    """What a PDN must contain, regardless of what the model proposed.

    Nothing in :mod:`rtl2gdsagi.ir` can relax any field of this object. A knob
    the model *may* still write (`pdn.core_ring`, strap width/pitch/offset) is
    one whose every legal value still yields a DEF satisfying this contract.
    """

    power_net: str = "VPWR"
    ground_net: str = "VGND"
    #: Standard-cell rails. Without these the grid reaches no cell.
    rail_layer: str = "met1"
    #: Upper distribution, required for **both** supplies. The renderer always
    #: emits met4 and met5 stripes; only the ring is conditional. So this is
    #: the fixed external-distribution requirement that survives `core_ring`
    #: being turned off, and a rails-only DEF now fails.
    distribution_layers: tuple[str, ...] = ("met4", "met5")
    #: Every adjacent transition from the rails up to the top distribution
    #: layer, required per supply net. Checking "some via exists somewhere"
    #: cannot tell a connected grid from one whose top layers float.
    via_ladder: tuple[tuple[str, str], ...] = (
        ("met1", "met2"), ("met2", "met3"), ("met3", "met4"), ("met4", "met5"),
    )
    #: The core ring is an implementation choice: `add_pdn_ring` is emitted
    #: only when `pdn.core_ring` is true, and the distribution requirement
    #: above holds either way. Requiring it here would make a legal model
    #: proposal unsatisfiable; requiring it *conditionally on the model's own
    #: value* is precisely the defect being fixed. So it is not required, and
    #: the strength of the gate does not depend on it.
    require_ring: bool = False

    def supplies(self) -> tuple[str, str]:
        return (self.power_net, self.ground_net)


#: The contract in force for the implemented SKY130 methodology.
SKY130_MINIMUM_PDN = PDNContract()

#: OpenROAD names PDN vias `via<lower>_<upper>_...` using *routing-layer
#: indices*, where li1 is 1. So met1 is index 2 and met1->met2 is `via2_3`.
#: Pinned to this environment deliberately: a hardcoded, explicit and tested
#: table beats inferring a naming convention we cannot verify.
_ROUTING_LAYER_INDEX = {
    "li1": 1, "met1": 2, "met2": 3, "met3": 4, "met4": 5, "met5": 6,
}


def via_prefix(lower: str, upper: str) -> str:
    """`("met1", "met2") -> "via2_3_"` -- the prefix OpenROAD emits."""
    try:
        lo = _ROUTING_LAYER_INDEX[lower]
        hi = _ROUTING_LAYER_INDEX[upper]
    except KeyError as exc:
        raise KeyError(f"no routing-layer index for {exc.args[0]!r}") from None
    return f"via{lo}_{hi}_"


@dataclass(frozen=True)
class PDNResult:
    def_path: Path
    power_nets: list[str] = field(default_factory=list)
    ground_nets: list[str] = field(default_factory=list)
    #: net -> shape kind -> [(layer, count)]
    shapes: dict[str, dict[str, dict[str, int]]] = field(default_factory=dict)
    via_count: int = 0
    via_layers: list[str] = field(default_factory=list)
    #: net -> the distinct via cell names placed on that net.
    vias_by_net: dict[str, list[str]] = field(default_factory=dict)
    problems: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return not self.problems

    def rails(self, net: str) -> dict[str, int]:
        return self.shapes.get(net, {}).get("FOLLOWPIN", {})

    def summary(self) -> str:
        if self.problems:
            return "PDN structurally invalid: " + "; ".join(self.problems)
        nets = ", ".join(sorted(self.power_nets + self.ground_nets))
        rails = sum(
            sum(self.rails(n).values())
            for n in self.power_nets + self.ground_nets
        )
        return (
            f"PDN structurally sound: nets {nets}, {rails} follow-pin rail "
            f"segment(s), {self.via_count} via(s). IR drop, EM and current "
            "density are NOT verified."
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "def_path": str(self.def_path),
            "power_nets": self.power_nets,
            "ground_nets": self.ground_nets,
            "shapes": self.shapes,
            "via_count": self.via_count,
            "via_layers": self.via_layers,
            "vias_by_net": self.vias_by_net,
            "ok": self.ok,
            "problems": list(self.problems),
            "unverified": ["ir_drop", "electromigration", "current_density"],
        }


def check_pdn_def(
    path: str | Path,
    *,
    contract: PDNContract = SKY130_MINIMUM_PDN,
) -> PDNResult:
    """Structural checks on a post-pdngen DEF against an immutable contract.

    The contract is **not** taken from the IR. See :class:`PDNContract`.
    """
    power_net = contract.power_net
    ground_net = contract.ground_net
    rail_layer = contract.rail_layer
    p = Path(path)
    if not p.is_file():
        return PDNResult(p, problems=(f"PDN DEF was not written: {p}",))
    if p.stat().st_size == 0:
        return PDNResult(p, problems=(f"PDN DEF is empty: {p}",))

    text = p.read_text(encoding="utf-8", errors="replace")
    problems: list[str] = []

    block = _SPECIALNETS.search(text)
    if not block:
        return PDNResult(
            p, problems=(
                "the DEF has no SPECIALNETS section, so it contains no power "
                "distribution at all -- pdngen produced a file but no grid",
            ),
        )

    power: list[str] = []
    ground: list[str] = []
    shapes: dict[str, dict[str, dict[str, int]]] = {}
    vias: list[str] = []
    vias_by_net: dict[str, list[str]] = {}
    solid: dict[str, dict[str, dict[str, int]]] = {}

    for name, body in _NET_HEAD.findall(block.group(2)):
        use = (_USE.search(body).group(1).upper() if _USE.search(body) else "")
        if use == "POWER":
            power.append(name)
        elif use == "GROUND":
            ground.append(name)
        per_net: dict[str, dict[str, int]] = {}
        per_net_solid: dict[str, dict[str, int]] = {}
        for layer, width, shape in _SEGMENT.findall(body):
            kind = shape.upper()
            per_net.setdefault(kind, {}).setdefault(layer, 0)
            per_net[kind][layer] += 1
            # A DEF entry with width 0 is a *via placement*, not a conductor:
            #   NEW met4 0 + SHAPE STRIPE ( 12120 12880 ) via5_6_...
            # Counting those as strap geometry means a grid with no met4 strap
            # at all still looks like it has one, purely because a via landed
            # on that layer. Only non-zero width carries current.
            if int(width) > 0:
                per_net_solid.setdefault(kind, {}).setdefault(layer, 0)
                per_net_solid[kind][layer] += 1
        shapes[name] = per_net
        solid[name] = per_net_solid
        # DEF keywords follow a coordinate pair too; a via is a cell name.
        found = [
            v for v in _VIA.findall(body)
            if v.upper() not in {"NEW", "ROUTED", "SHAPE", "USE", "STRIPE",
                                 "FOLLOWPIN", "RING", "POWER", "GROUND"}
        ]
        vias += found
        vias_by_net[name] = sorted(set(found))

    if power_net not in power:
        problems.append(
            f"no SPECIALNET named {power_net} with USE POWER; the design has "
            "no power supply to connect cells to"
        )
    if ground_net not in ground:
        problems.append(
            f"no SPECIALNET named {ground_net} with USE GROUND; the design has "
            "no ground return"
        )

    # Follow-pin rails are what actually reaches the standard cells. A grid
    # with straps but no rails is a grid floating above the design -- which is
    # exactly the defect this project shipped once already.
    for net in (power_net, ground_net):
        rails = solid.get(net, {}).get("FOLLOWPIN", {})
        if not rails:
            problems.append(
                f"{net} has no FOLLOWPIN geometry: nothing ties the grid down "
                "to the standard-cell rails, so no cell is connected to it"
            )
        elif rail_layer not in rails:
            problems.append(
                f"{net} follow-pin rails are on {sorted(rails)} rather than the "
                f"expected {rail_layer}"
            )

    # Upper distribution, required for BOTH supplies and independent of any
    # model-writable field. A grid of rails alone reaches the cells but has no
    # external distribution to deliver current through; a grid that
    # distributes only one supply is not a power network.
    for net in (power_net, ground_net):
        stripes = solid.get(net, {}).get("STRIPE", {})
        for layer in contract.distribution_layers:
            if layer not in stripes:
                problems.append(
                    f"{net} has no STRIPE geometry on {layer}, which the "
                    "minimum PDN contract requires for every supply; this "
                    "grid has no upper distribution for that net"
                )
        if contract.require_ring and not solid.get(net, {}).get("RING"):
            problems.append(
                f"{net} has no RING geometry although the PDN contract "
                "requires a core ring"
            )

    # Vertical connectivity, per supply and per transition. "Some via exists
    # somewhere in the grid" cannot distinguish a connected stack from one
    # whose upper layers float, nor from one where only VPWR is tied down.
    if not vias:
        problems.append(
            "the power grid contains no vias: its layers are not connected to "
            "each other, so the straps do not reach the rails"
        )
    else:
        for net in (power_net, ground_net):
            names = vias_by_net.get(net, [])
            for lower, upper in contract.via_ladder:
                pref = via_prefix(lower, upper)
                if not any(v.startswith(pref) for v in names):
                    problems.append(
                        f"{net} has no {lower}-to-{upper} via ({pref}*): the "
                        "supply is not continuously connected from the "
                        "standard-cell rails up to the distribution layers"
                    )

    for net, per_net in shapes.items():
        if not per_net:
            problems.append(f"special net {net} is declared with no geometry")

    return PDNResult(
        def_path=p, power_nets=power, ground_nets=ground, shapes=shapes,
        via_count=len(vias), via_layers=sorted(set(vias)),
        vias_by_net=vias_by_net,
        problems=tuple(problems),
    )
