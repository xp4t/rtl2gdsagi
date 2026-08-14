"""Independent geometric proof that the substrate is tied to the ground net.

Why this module exists
======================

LVS cannot check this, and the gap is structural rather than incidental.

The SKY130 KLayout deck models the substrate as ``sub = polygon_layer`` -- an
empty layer with no geometry -- promoted to a global net by
``connect_global(sub, substrate_name)``. Since the node carries no geometry,
nothing in a layout can be *physically* connected to it. LVS compares the
substrate as a logical node (which, after the P0-07 fix, it does properly: the
reference declares its own substrate pin and every transistor bulk is compared
against it), but no LVS run can confirm that the well taps actually tie the
p-substrate to the ground metal, because the deck has no geometric substrate to
tie anything to.

This module answers that separate question directly, with KLayout's own
connectivity engine (``LayoutToNetlist``) over the same GDS that was signed
off, using the deck's ground chain::

    ptap_conn = tap & psdm - nwell
    ptap_conn -> licon -> li -> mcon -> met1 -> via1 -> ... -> met5

and asserts that every substrate tap contact lands in a single net together
with the ground metal.

The proof is **conservative by construction**. It declares strictly fewer
``connect()`` relations than the full deck, and the two layers the deck derives
(``li_con = li - li_res - vpp``, ``met1_con = met1 - met1_res - vpp``) differ
from the raw layers only by geometry this flow's designs do not contain.
Removing connect relations can only fragment nets further -- never merge two
the full deck would keep apart. So finding a single component here implies one
under the full deck: the proof is one-sided in the safe direction.

Status and permitted use
------------------------

This is **diagnostic evidence only**. It is not wired into the LVS verdict.

It must never be used substitutively -- an LVS ``must-connect`` failure is not
cleared by this proof passing, because the two speak about different objects:
this measures tap-contact-to-metal connectivity, while KLayout's must-connect
obligation concerns the deck's geometry-less substrate node. If it is ever
wired into production it may only be **conjunctive** (LVS pass *and* this
proof pass), never a bypass.

Everything fails closed. No proof, an unreadable proof, a proof for a different
layout, or a proof that did not establish a single component all leave
``proved`` false.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: The message class this proof is allowed to speak about, and nothing else.
#:
#: KLayout emits several must-connect variants. Only the one naming a net that
#: the flow globalised as the substrate is in scope; any other must-connect
#: message is outside what the geometry below proves and keeps blocking.
SUBSTRATE_MESSAGE_RE = re.compile(
    r"must-connect subnets of (?P<net>\S+) of circuit (?P<cell>\S+) must be "
    r"connected further up in the hierarchy",
    re.IGNORECASE,
)

#: Identity of the proof procedure, recorded in evidence alongside the result.
PROOF_CONTRACT = "substrate_tie/v1-conservative-l2n"

#: KLayout script emitting the proof as a single JSON line.
#:
#: Kept as a literal so its exact text is covered by the deck/tool identity
#: recorded with the result: the proof is only as trustworthy as the procedure
#: that produced it, and that procedure has to be pinned like any other.
PROOF_SCRIPT = r"""
ly = RBA::Layout::new
ly.read($gds)
top = ly.top_cell
l2n = RBA::LayoutToNetlist::new(RBA::RecursiveShapeIterator::new(ly, top, []))
def mk(l2n, ly, lay, dt, name)
  l2n.make_polygon_layer(ly.layer(lay, dt), name)
end
nwell = mk(l2n, ly, 64, 20, "nwell")
tap   = mk(l2n, ly, 65, 44, "tap")
psdm  = mk(l2n, ly, 94, 20, "psdm")
licon = mk(l2n, ly, 66, 44, "licon")
li    = mk(l2n, ly, 67, 20, "li")
mcon  = mk(l2n, ly, 67, 44, "mcon")
met1  = mk(l2n, ly, 68, 20, "met1")
via1  = mk(l2n, ly, 68, 44, "via1")
met2  = mk(l2n, ly, 69, 20, "met2")
via2  = mk(l2n, ly, 69, 44, "via2")
met3  = mk(l2n, ly, 70, 20, "met3")
via3  = mk(l2n, ly, 70, 44, "via3")
met4  = mk(l2n, ly, 71, 20, "met4")
via4  = mk(l2n, ly, 71, 44, "via4")
met5  = mk(l2n, ly, 72, 20, "met5")

# The deck's own p-substrate tap derivation (sky130.lvs: ptap_conn).
ptap = tap.and(psdm).not(nwell)
l2n.register(ptap, "ptap_conn")

[ptap, licon, li, mcon, met1, via1, met2, via2,
 met3, via3, met4, via4, met5].each { |x| l2n.connect(x) }
[[ptap, licon], [licon, li], [li, mcon], [mcon, met1], [met1, via1],
 [via1, met2], [met2, via2], [via2, met3], [met3, via3], [via3, met4],
 [met4, via4], [via4, met5]].each { |a, b| l2n.connect(a, b) }

l2n.extract_netlist
circuit = l2n.netlist.circuit_by_name(top.name)

carriers = []
circuit.each_net do |n|
  shapes = l2n.shapes_of_net(n, ptap, true)
  next if shapes.nil? || shapes.size == 0
  m = l2n.shapes_of_net(n, met1, true)
  carriers << [n, shapes.size, m.nil? ? 0 : m.size]
end

result = {
  "top_cell" => top.name,
  "nets_carrying_taps" => carriers.size,
  "tap_shapes" => carriers.map { |c| c[1] }.inject(0) { |a, b| a + b },
}

if carriers.size == 1
  net, ntaps, nmet1 = carriers[0]
  result["ground_net"] = net.expanded_name
  result["ground_net_taps"] = ntaps
  result["ground_net_met1"] = nmet1
  ground = RBA::Region::new
  l2n.shapes_of_net(net, met1, true).each { |sh| ground.insert(sh) }
  ground.merge
  probes = []
  ($probes.to_s.empty? ? [] : $probes.split(";")).each do |spec|
    parts = spec.split(",")
    box = RBA::Box::new((parts[0].to_f / ly.dbu).to_i,
                        (parts[1].to_f / ly.dbu).to_i,
                        (parts[2].to_f / ly.dbu).to_i,
                        (parts[3].to_f / ly.dbu).to_i)
    region = RBA::Region::new
    region.insert(box)
    probes << { "box" => spec, "in_ground_net" => !ground.interacting(region).is_empty? }
  end
  result["probes"] = probes
else
  result["ground_net"] = nil
  result["probes"] = []
end

puts "RTL2GDSAGI_SUBSTRATE_TIE " + result.to_s.gsub("=>", ":").gsub("nil", "null")
"""

#: Marker the runner greps for; keeps the payload separable from KLayout noise.
PROOF_MARKER = "RTL2GDSAGI_SUBSTRATE_TIE"


@dataclass(frozen=True)
class SubstrateTieProof:
    """Result of the conservative connectivity proof.

    ``proved`` is the only thing callers should key on, and it is true only
    when every part of the claim held.
    """

    #: sha256 of the GDS the proof was computed over. Bound, not assumed.
    gds_sha256: str
    top_cell: str = ""
    #: How many distinct nets carry substrate-tap geometry. Must be exactly 1.
    nets_carrying_taps: int = 0
    tap_shapes: int = 0
    ground_net: str | None = None
    ground_net_met1: int = 0
    #: One entry per flagged instance: its message polygon and whether the
    #: single ground net's metal reaches into it.
    probes: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    tool_identity: str = ""
    contract: str = PROOF_CONTRACT
    problems: tuple[str, ...] = field(default_factory=tuple)

    @property
    def proved(self) -> bool:
        if self.problems:
            return False
        if self.tap_shapes <= 0:
            return False
        if self.nets_carrying_taps != 1:
            return False
        if not self.ground_net:
            return False
        if self.ground_net_met1 <= 0:
            return False
        if not self.probes:
            return False
        return all(bool(p.get("in_ground_net")) for p in self.probes)

    def why_not(self) -> str:
        """One line explaining a failed proof, for the LVS problem text."""
        if self.problems:
            return "; ".join(self.problems)
        if self.tap_shapes <= 0:
            return "the layout contains no p-substrate tap geometry at all"
        if self.nets_carrying_taps != 1:
            return (
                f"substrate taps are split across {self.nets_carrying_taps} "
                "separate nets, so the ground network is genuinely fragmented"
            )
        if self.ground_net_met1 <= 0:
            return "the net carrying the substrate taps holds no met1 geometry"
        if not self.probes:
            return "no flagged instance was probed, so nothing was established"
        missing = [p.get("box") for p in self.probes if not p.get("in_ground_net")]
        return (
            "the ground network does not reach these flagged instances: "
            + ", ".join(str(m) for m in missing)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": self.contract,
            "gds_sha256": self.gds_sha256,
            "top_cell": self.top_cell,
            "nets_carrying_taps": self.nets_carrying_taps,
            "tap_shapes": self.tap_shapes,
            "ground_net": self.ground_net,
            "ground_net_met1": self.ground_net_met1,
            "probes": [dict(p) for p in self.probes],
            "tool_identity": self.tool_identity,
            "proved": self.proved,
            "problems": list(self.problems),
        }


def parse_proof(
    output: str,
    *,
    gds_sha256: str,
    tool_identity: str = "",
) -> SubstrateTieProof:
    """Read the proof payload out of a KLayout run's combined output."""
    line = ""
    for candidate in output.splitlines():
        if candidate.strip().startswith(PROOF_MARKER):
            line = candidate.strip()[len(PROOF_MARKER):].strip()
    if not line:
        return SubstrateTieProof(
            gds_sha256=gds_sha256, tool_identity=tool_identity,
            problems=("the substrate-tie proof produced no result; treating the "
                      "must-connect condition as unproven",),
        )
    try:
        data = json.loads(line)
    except json.JSONDecodeError as exc:
        return SubstrateTieProof(
            gds_sha256=gds_sha256, tool_identity=tool_identity,
            problems=(f"the substrate-tie proof output was unreadable: {exc}",),
        )
    if not isinstance(data, dict):
        return SubstrateTieProof(
            gds_sha256=gds_sha256, tool_identity=tool_identity,
            problems=("the substrate-tie proof output was not an object",),
        )
    probes = data.get("probes") or []
    if not isinstance(probes, list):
        probes = []
    return SubstrateTieProof(
        gds_sha256=gds_sha256,
        top_cell=str(data.get("top_cell") or ""),
        nets_carrying_taps=int(data.get("nets_carrying_taps") or 0),
        tap_shapes=int(data.get("tap_shapes") or 0),
        ground_net=data.get("ground_net") or None,
        ground_net_met1=int(data.get("ground_net_met1") or 0),
        probes=tuple(p for p in probes if isinstance(p, dict)),
        tool_identity=tool_identity,
    )


def probe_boxes(polygons: list[str]) -> str:
    """Turn ``Q('x1,y1;x2,y2;...')`` message polygons into probe boxes.

    KLayout localises each must-connect message with the flagged instance's
    bounding box grown slightly. The probe asks whether the proven ground
    network's metal reaches into that box.
    """
    specs: list[str] = []
    for poly in polygons:
        pts: list[tuple[float, float]] = []
        for pair in poly.split(";"):
            bits = pair.strip().strip("()").split(",")
            if len(bits) != 2:
                continue
            try:
                pts.append((float(bits[0]), float(bits[1])))
            except ValueError:
                continue
        if not pts:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        specs.append(f"{min(xs)},{min(ys)},{max(xs)},{max(ys)}")
    return ";".join(specs)


def write_script(directory: str | Path) -> Path:
    """Materialise the proof script next to the stage's other inputs."""
    path = Path(directory) / "substrate_tie.rb"
    path.write_text(PROOF_SCRIPT, encoding="utf-8")
    return path
