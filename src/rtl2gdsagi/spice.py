"""Gate-level Verilog netlist -> SPICE, for the LVS reference side.

The KLayout LVS runset reads its reference netlist with ``NetlistSpiceReader``:
SPICE only. Handing it Verilog fails with ``'M' element must have four nodes``,
because it tries to parse ``module`` as a MOSFET card.

Converting is not just a syntax change. SPICE subcircuit calls are
**positional**, and the PDK's pin order is its own:

    .SUBCKT sky130_fd_sc_hd__inv_1 A VGND VNB VPB VPWR Y

while the Verilog view of the same cell is ``(Y, A)`` and the power-pin view is
``(Y, A, VPWR, VGND, VPB, VNB)``. None of the three agree, so anything that
emits ports in Verilog order -- ``yosys write_spice`` included -- miswires every
instance while looking perfectly plausible.

So the pin order is read from the PDK's own CDL and the netlist's *named*
connections are placed into it. Power pins, which the Verilog does not mention,
are tied to the global supplies; physical-only cells (fill, decap, well taps)
have nothing but power pins and would otherwise vanish from the reference side
while being plainly present in the layout.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .errors import Rtl2GdsError

#: Pins every standard cell has that the gate-level Verilog never mentions.
POWER_PINS: dict[str, str] = {
    "VPWR": "VPWR",   # cell power
    "VPB":  "VPWR",   # p-well/nwell bulk tie, same supply
    "VGND": "VGND",   # cell ground
    "VNB":  "VGND",   # n-bulk tie, same ground
    "KAPWR": "VPWR",  # low-power variants
    "LOWLVPWR": "VPWR",
    "VPWRIN": "VPWR",
}

_SUBCKT = re.compile(r"^\s*\.SUBCKT\s+(\S+)\s*(.*)$", re.IGNORECASE | re.MULTILINE)
_MODULE = re.compile(r"\bmodule\s+([A-Za-z_]\w*)\s*\((.*?)\)\s*;", re.DOTALL)
_PORT_DECL = re.compile(
    r"\b(input|output|inout)\b\s*(?:wire|reg)?\s*(?:\[([^\]]*)\])?\s*([^;]+);")
#: `celltype instname ( .PIN(net), ... );`  -- also matches an empty list.
_INSTANCE = re.compile(
    r"\b([A-Za-z_]\w*)\s+([A-Za-z_]\w*)\s*\(\s*(.*?)\s*\)\s*;", re.DOTALL)
_CONNECTION = re.compile(r"\.\s*(\w+)\s*\(\s*([^)]*?)\s*\)")
_LINE_COMMENT = re.compile(r"//[^\n]*")
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


class SpiceConversionError(Rtl2GdsError):
    """The netlist could not be converted into a usable SPICE reference."""


@dataclass
class Instance:
    cell: str
    name: str
    connections: dict[str, str] = field(default_factory=dict)


@dataclass
class GateNetlist:
    top: str
    ports: list[str]
    instances: list[Instance]


def _cdl_blocks(text: str) -> dict[str, str]:
    """Split a CDL into ``name -> full .SUBCKT ... .ENDS text``."""
    blocks: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        head = line.strip()
        if head.upper().startswith(".SUBCKT"):
            parts = head.split()
            current = parts[1] if len(parts) > 1 else None
            buf = [line]
        elif current is not None:
            buf.append(line)
            if head.upper().startswith(".ENDS"):
                blocks[current] = "\n".join(buf)
                current = None
    return blocks


def _called_subckts(block: str) -> set[str]:
    """Subcircuits a block instantiates.

    CDL writes calls two ways -- ``X<n> <nets> <subckt>`` and
    ``X<n> <nets> / <subckt>`` -- so the name is taken from the end either way.
    """
    out: set[str] = set()
    for line in block.splitlines():
        t = line.strip()
        if not t.startswith(("X", "x")):
            continue
        toks = t.replace("/", " ").split()
        if len(toks) >= 2:
            out.add(toks[-1])
    return out


def extract_subckts(cdl: str | Path, needed: set[str]) -> str:
    """Pull just the cells this design uses, and whatever they call.

    The full SKY130 CDL cannot be included wholesale: one of its own cells
    (``macro_sparecell``) uses a call syntax KLayout's SPICE reader mis-counts,
    and it aborts the whole run with a pin-count mismatch on a cell the design
    never instantiates. Including only what is reachable sidesteps that, and
    shrinks the reference netlist by a couple of orders of magnitude.
    """
    text = Path(cdl).read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"\n\+\s*", " ", text)
    blocks = _cdl_blocks(text)

    keep: set[str] = set()
    queue = list(needed)
    while queue:
        name = queue.pop()
        if name in keep or name not in blocks:
            continue
        keep.add(name)
        queue.extend(_called_subckts(blocks[name]) - keep)

    missing = sorted(n for n in needed if n not in blocks)
    if missing:
        raise SpiceConversionError(
            f"no .SUBCKT in the CDL for: {', '.join(missing[:8])}"
        )
    return "\n".join(blocks[n] for n in sorted(keep))


def globalize_substrate(spice: str, bulk_pin: str, sub_net: str) -> str:
    """Drop the substrate bulk pin from cell definitions and tie it to ``sub_net``.

    The KLayout SKY130 deck ends with ``connect_global(sub, substrate_name)``:
    the p-substrate is one global net, not a per-cell terminal. So an extracted
    cell comes back as ``VPB VGND A2 VPWR A1 Y B1`` -- ``VPB`` survives because
    an nwell really is per-cell, but there is no ``VNB``.

    A reference netlist that keeps the CDL's ``VNB`` pin therefore mismatches
    every single cell, with paired complaints in both directions ("No
    equivalent pin VNB from reference netlist found in netlist" and the
    reverse). Rewriting the definitions to match how the layout is actually
    extracted removes no check: with the substrate declared global up front,
    there is no per-cell bulk net left for LVS to compare either way.
    """
    tok = re.compile(rf"(?<![\w.$\[]){re.escape(bulk_pin)}(?![\w.$\]])")
    out: list[str] = []
    for line in spice.splitlines():
        head = line.strip().upper()
        if head.startswith(".SUBCKT"):
            parts = line.split()
            out.append(" ".join(p for p in parts if p != bulk_pin))
        elif head.startswith("*.PININFO"):
            parts = line.split()
            out.append(" ".join(
                p for p in parts if p.split(":", 1)[0] != bulk_pin
            ))
        elif head.startswith("*"):
            out.append(line)
        else:
            out.append(tok.sub(sub_net, line))
    return "\n".join(out)


#: Name of the substrate node, used identically on both sides of the comparison.
#:
#: It must not collide with a net the standard cells label (``VGND``, ``VPWR``):
#: the deck's ``connect_implicit("*")`` joins same-named parts by name alone,
#: and joining the geometry-less substrate node to a labelled metal net that way
#: creates a must-connect obligation nothing can discharge. That collision was
#: P0-07. One name, one node, both sides.
SUBSTRATE_NET = "VSUBS"


def model_substrate(spice: str, bulk_pin: str, sub_net: str) -> str:
    """Rename the substrate bulk pin, **keeping it as a pin**.

    This is the correct counterpart to :func:`globalize_substrate`, which
    deletes the pin instead. Deleting it was the root cause of P0-07.

    The KLayout SKY130 deck models the substrate as ``sub = polygon_layer`` --
    an empty layer with no geometry -- promoted to a global net by
    ``connect_global(sub, substrate_name)``. Extraction therefore hands every
    cell a substrate terminal carrying that global name, and promotes it to a
    pin on the top cell.

    The old workaround deleted the reference's ``VNB`` pin and rewrote its
    occurrences to ``VGND``, then told extraction to *also* call the substrate
    ``VGND`` (``-rd lvs_sub=VGND``). The two sides then agreed, but only by
    sharing a name: the deck's ``connect_implicit("*")`` joins same-named parts
    "without need for a physical connection", and KLayout records that nominal
    join as a must-connect obligation to be discharged higher up. It never can
    be, because the substrate node has no geometry to connect with -- which is
    exactly the three unresolvable messages P0-07 tracked.

    Renaming instead of deleting keeps the substrate a first-class node on both
    sides, so the bulk terminal of every transistor is actually compared rather
    than merged into ground by name.
    """
    tok = re.compile(rf"(?<![\w.$\[]){re.escape(bulk_pin)}(?![\w.$\]])")
    out: list[str] = []
    for line in spice.splitlines():
        head = line.strip().upper()
        if head.startswith("*.PININFO"):
            # `VNB:B` -> `VSUBS:B`; the suffix records the pin's direction.
            out.append(" ".join(
                (f"{sub_net}:{p.split(':', 1)[1]}"
                 if p.split(":", 1)[0] == bulk_pin else p)
                for p in line.split()
            ))
        elif head.startswith("*"):
            out.append(line)
        else:
            out.append(tok.sub(sub_net, line))
    return "\n".join(out)


def deviceless_cells(cdl: str | Path) -> set[str]:
    """Cells whose CDL body contains no device at all.

    Fill and well-tap cells are contacts and metal: no transistor, no
    capacitor, nothing a netlist comparison can look at. KLayout purges such
    circuits from the extracted layout netlist, so a reference that still
    declares them leaves circuits with no counterpart, and the top cell is
    reported as uncomparable rather than as matching.
    """
    text = re.sub(r"\n\+\s*", " ",
                  Path(cdl).read_text(encoding="utf-8", errors="replace"))
    out: set[str] = set()
    for name, block in _cdl_blocks(text).items():
        for line in block.splitlines():
            t = line.strip()
            if not t or t.startswith("*"):
                continue
            if t[0] in "MmDdQqRrCcLlXx":
                break
        else:
            out.add(name)
    return out


def qualify_device_models(spice: str, prefix: str) -> str:
    """Namespace the model name on each device card, e.g. ``nfet_01v8`` ->
    ``sky130_fd_pr__nfet_01v8``.

    The LVS deck extracts into device classes named for the primitive library.
    The CDL uses bare model names. Unqualified, not one device matches, and
    because LVS matches nets *through* devices the report blames the nets: every
    net and pin fails in both directions at once, on cells whose pins and
    topology are in fact perfectly correct.

    A card is ``M<name> <d> <g> <s> <b> <model> [params]``, so the model is the
    sixth token. Names that already carry a ``__`` namespace are left alone.
    """
    if not prefix:
        return spice
    out: list[str] = []
    for line in spice.splitlines():
        t = line.lstrip()
        toks = line.split()
        if not t or t.startswith("*") or t[0] not in "Mm" or len(toks) < 6:
            out.append(line)
            continue
        if "__" not in toks[5]:
            toks[5] = prefix + toks[5]
        out.append(" ".join(toks))
    return "\n".join(out)


#: Device parameters written as bare micron values in the SKY130 CDL.
_DIMENSION_PARAMS = ("w", "l")


def unit_device_dimensions(spice: str, suffix: str = "u") -> str:
    """Give bare ``w=``/``l=`` values an explicit unit.

    The CDL writes ``w=0.65 l=0.15``, meaning microns -- that transistor really
    is 0.65um wide, and extraction reports it as ``W 0.65``. But SPICE numbers
    are unitless *metres* by convention, and KLayout's reader honours that: it
    reads 0.65 as 0.65m and stores 650000um. The reference is then wrong by a
    factor of a million.

    W and L are primary parameters for a MOS device class, so they are compared
    and nothing matches. Since LVS matches nets *through* devices, the report
    never mentions a parameter: it says every net and pin failed, on cells
    whose nets, pins and device counts are all demonstrably identical.
    """
    if not suffix:
        return spice
    out: list[str] = []
    for line in spice.splitlines():
        t = line.lstrip()
        if not t or t.startswith("*") or t[0] not in "Mm":
            out.append(line)
            continue
        toks = line.split()
        for i, tok in enumerate(toks):
            key, sep, val = tok.partition("=")
            if not sep or key.lower() not in _DIMENSION_PARAMS:
                continue
            if val and (val[-1].isdigit() or val[-1] == "."):
                toks[i] = f"{key}={val}{suffix}"
        out.append(" ".join(toks))
    return "\n".join(out)


def strip_klayout_unsupported_metadata(spice: str) -> str:
    """Remove the non-electrical ``topography=normal`` CDL annotation.

    KLayout 0.28 rejects the bare word ``normal`` where its SPICE reader
    expects a real-valued MOS parameter.  The pinned SKY130 CDL uses this exact
    annotation, while connectivity, model, W/L, multiplicity and all numeric
    parameters carry the LVS meaning.  Keep the rewrite deliberately narrow:
    unknown string parameters remain visible and make the tool fail closed.
    """
    out: list[str] = []
    for line in spice.splitlines():
        stripped = line.lstrip()
        if stripped and not stripped.startswith("*") and stripped[0] in "Mm":
            line = " ".join(
                token for token in line.split() if token != "topography=normal"
            )
        out.append(line)
    return "\n".join(out)


def parse_cdl_pins(cdl: str | Path) -> dict[str, list[str]]:
    """Map cell name -> its pin order, straight from the PDK's CDL.

    This is the authority on ordering. Nothing else in the flow gets to guess.
    """
    path = Path(cdl)
    if not path.is_file():
        raise SpiceConversionError(f"cell CDL not found: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    # Join SPICE continuation lines ("+" at the start) before parsing.
    text = re.sub(r"\n\+\s*", " ", text)
    out: dict[str, list[str]] = {}
    for name, rest in _SUBCKT.findall(text):
        out[name] = rest.split()
    if not out:
        raise SpiceConversionError(f"no .SUBCKT definitions found in {path}")
    return out


def strip_comments(text: str) -> str:
    return _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", text))


def parse_gate_netlist(netlist: str | Path, top: str) -> GateNetlist:
    """Read a structural Verilog netlist: its top ports and cell instances."""
    path = Path(netlist)
    if not path.is_file():
        raise SpiceConversionError(f"netlist not found: {path}")
    text = strip_comments(path.read_text(encoding="utf-8", errors="replace"))

    m = next((m for m in _MODULE.finditer(text) if m.group(1) == top), None)
    if m is None:
        found = ", ".join(sorted({x.group(1) for x in _MODULE.finditer(text)})[:10])
        raise SpiceConversionError(
            f"module {top!r} not found in {path.name}; saw: {found or '<none>'}"
        )

    body = text[m.end():]
    end = body.find("endmodule")
    if end >= 0:
        body = body[:end]

    ports: list[str] = []
    for _direction, width, names in _PORT_DECL.findall(body):
        for n in (x.strip() for x in names.split(",")):
            if not n or not re.match(r"^[A-Za-z_]\w*$", n):
                continue
            if width and width.strip():
                hi, _, lo = width.partition(":")
                try:
                    a, b = int(hi), int(lo)
                except ValueError:
                    ports.append(n)
                    continue
                step = -1 if a >= b else 1
                ports.extend(f"{n}[{i}]" for i in range(a, b + step, step))
            else:
                ports.append(n)

    instances: list[Instance] = []
    for cell, name, conns in _INSTANCE.findall(body):
        if cell in ("module", "input", "output", "inout", "wire", "reg", "assign"):
            continue
        mapping = {p: net.strip() for p, net in _CONNECTION.findall(conns)}
        instances.append(Instance(cell=cell, name=name, connections=mapping))

    return GateNetlist(top=top, ports=ports, instances=instances)


def to_spice(
    netlist: str | Path,
    top: str,
    cdl: str | Path,
    *,
    power_net: str = "VPWR",
    ground_net: str = "VGND",
    include_cdl: bool = True,
    flatten: bool = False,
    substrate_pin: str = "VNB",
    substrate_net: str | None = None,
    model_prefix: str = "",
    dimension_unit: str = "u",
    omit_deviceless: bool = True,
) -> str:
    """Render the SPICE reference netlist for LVS.

    ``substrate_net`` selects how the substrate is represented:

    ``None``
        Legacy behaviour: delete the bulk pin and tie its occurrences to
        ``ground_net``. Requires extraction to alias the substrate to the same
        name (``-rd lvs_sub=VGND``), which is what created P0-07. Retained so
        the old failure remains reproducible in tests; not used in production.

    a net name (e.g. ``"VSUBS"``)
        Correct behaviour: keep the bulk pin, rename it to that net, and expose
        it as a top-level port. Extraction must be told the same name so both
        sides model one substrate node and the bulk terminals are compared.
    """
    pins = parse_cdl_pins(cdl)
    design = parse_gate_netlist(netlist, top)
    # Without an explicit substrate node the extracted cells have no bulk
    # terminal at all, so the reference has to drop it too or every cell
    # mismatches. Only in hierarchical mode: flattening emits the transistors
    # themselves, where the bulk node is a real terminal needing a supply.
    if substrate_pin and not flatten and not substrate_net:
        pins = {c: [p for p in ps if p != substrate_pin] for c, ps in pins.items()}

    bulk_net = substrate_net or ground_net
    supplies = {"VPWR": power_net, "VPB": power_net, "VGND": ground_net,
                "VNB": bulk_net, "KAPWR": power_net, "LOWLVPWR": power_net,
                "VPWRIN": power_net}
    if substrate_pin:
        supplies[substrate_pin] = bulk_net

    unknown = sorted({i.cell for i in design.instances if i.cell not in pins})
    if unknown:
        raise SpiceConversionError(
            f"{len(unknown)} cell type(s) in the netlist have no .SUBCKT in the "
            f"CDL, so their pin order is unknown: {', '.join(unknown[:8])}. "
            "LVS cannot be trusted without it."
        )

    # Cells with no devices are purged from the *layout* netlist by extraction,
    # so keeping them on the reference side leaves circuits with no counterpart
    # and the top cell is reported as uncomparable. Fill and well-tap cells are
    # the whole of this set: contacts and metal, not a single transistor.
    # Nothing is lost by dropping them -- a device-less cell has nothing for LVS
    # to compare in the first place, and its real job (nwell continuity) is
    # checked by DRC, loudly, in nwell.* and hvtp.*.
    dropped: set[str] = set()
    if omit_deviceless and not flatten:
        dropped = deviceless_cells(cdl) & {i.cell for i in design.instances}

    instances = [i for i in design.instances if i.cell not in dropped]
    used = {i.cell for i in instances}
    lines = [
        "* SPICE reference netlist for LVS, generated by rtl2gdsagi.",
        "* Pin order taken from the PDK CDL, not from the Verilog: SPICE",
        "* subcircuit calls are positional and the two orders differ.",
        "",
    ]
    if dropped:
        lines.insert(3, "* omitted (no devices, so extraction purges them too): "
                        + ", ".join(sorted(dropped)))
    if include_cdl and not flatten:
        defs = extract_subckts(cdl, used)
        if substrate_pin and substrate_net:
            defs = model_substrate(defs, substrate_pin, substrate_net)
        elif substrate_pin:
            defs = globalize_substrate(defs, substrate_pin, ground_net)
        defs = qualify_device_models(defs, model_prefix)
        defs = unit_device_dimensions(defs, dimension_unit)
        defs = strip_klayout_unsupported_metadata(defs)
        lines += [
            f"* cell definitions for the {len(used)} cell type(s) this design uses",
            defs,
            "",
        ]

    # Ground, but not power, is a top-level pin.
    #
    # Extraction promotes the global substrate net to a pin on the top cell, so
    # the extracted top reads "... i_clk VGND o_data[7]" -- VGND present, VPWR
    # absent. VPWR has no such mechanism behind it: unless the design places
    # real power pins, the supply is just an internal net that every cell and
    # tap connects to, and it comes back from extraction unnamed. Listing it as
    # a port here would be claiming a pin the layout does not have.
    top_ports = list(design.ports)
    if ground_net not in top_ports:
        top_ports.append(ground_net)
    # Extraction promotes the global substrate net to a pin on the top cell too,
    # so the reference has to declare it or the tops differ by one port.
    if substrate_net and substrate_net not in top_ports:
        top_ports.append(substrate_net)
    lines.append(f".SUBCKT {design.top} " + " ".join(top_ports))

    if flatten:
        blocks = _cdl_blocks(re.sub(r"\n\+\s*", " ",
                                    Path(cdl).read_text(encoding="utf-8",
                                                        errors="replace")))
        lines.extend(flatten_instances(design, pins, blocks, supplies))
        lines.append(f".ENDS {design.top}")
        lines.append("")
        return "\n".join(lines)

    dangling = 0
    for inst in instances:
        nets: list[str] = []
        for pin in pins[inst.cell]:
            if pin in inst.connections and inst.connections[pin]:
                nets.append(_spice_net(inst.connections[pin]))
            elif pin in supplies:
                nets.append(supplies[pin])
            else:
                # An unconnected signal pin still exists in the layout; give it
                # its own net rather than silently shorting it to something.
                dangling += 1
                nets.append(f"{_spice_net(inst.name)}_{pin}_open")
        lines.append(f"X{inst.name} " + " ".join(nets) + f" {inst.cell}")
    lines.append(f".ENDS {design.top}")
    lines.append("")

    if dangling:
        lines.insert(3, f"* note: {dangling} unconnected cell pin(s) given their "
                        "own nets")
    return "\n".join(lines)


#: A SPICE device card: `M<name> <nodes...> <model> [params]`.
_DEVICE = re.compile(r"^\s*([MmDdQqRrCcLl])(\S+)\s+(.*)$")


def _subckt_devices(block: str) -> list[tuple[str, str, list[str], str]]:
    """Device cards inside a .SUBCKT: (letter, name, nodes, trailing text)."""
    out: list[tuple[str, str, list[str], str]] = []
    for line in block.splitlines():
        t = line.strip()
        if not t or t.startswith("*") or t.upper().startswith((".SUBCKT", ".ENDS")):
            continue
        m = _DEVICE.match(t)
        if not m:
            continue
        letter, name, rest = m.groups()
        toks = rest.split()
        # MOS devices take four nodes; the rest take two. Everything after the
        # nodes is the model name and its parameters, carried through verbatim.
        count = 4 if letter.upper() == "M" else 2
        out.append((letter, name, toks[:count], " ".join(toks[count:])))
    return out


def flatten_instances(
    design: "GateNetlist",
    pins: dict[str, list[str]],
    blocks: dict[str, str],
    supplies: dict[str, str],
) -> list[str]:
    """Expand every cell instance into its transistors.

    A hierarchical reference cannot be compared cleanly here. Extraction merges
    a cell's bulk pin into the supply when the layout ties them inside the cell
    (an inverter comes back as ``VPB A Y VPWR VGND`` -- no VNB), while the CDL
    always declares both. Whether that merge happens depends on each cell's
    internal connectivity, so the pin lists cannot be predicted per cell.

    Flat transistors have no pin lists to disagree about. Kept as a fallback
    rather than the default: a hierarchical reference matches the layout's own
    cell structure and gives per-cell diagnostics, which is worth more when
    something genuinely differs.
    """
    lines: list[str] = []
    for inst in design.instances:
        formal = pins[inst.cell]
        actual: dict[str, str] = {}
        for pin in formal:
            if pin in inst.connections and inst.connections[pin]:
                actual[pin] = _spice_net(inst.connections[pin])
            elif pin in supplies:
                actual[pin] = supplies[pin]
            else:
                actual[pin] = f"{_spice_net(inst.name)}_{pin}_open"

        def net(n: str) -> str:
            # Formal pins map to the caller's nets; anything else is internal
            # to the cell and is namespaced so two instances cannot collide.
            return actual.get(n, f"{_spice_net(inst.name)}/{n}")

        for letter, dname, nodes, tail in _subckt_devices(blocks[inst.cell]):
            mapped = " ".join(net(n) for n in nodes)
            lines.append(f"{letter}{_spice_net(inst.name)}/{dname} {mapped} {tail}".rstrip())
    return lines


def _spice_net(name: str) -> str:
    """Make a Verilog net name safe for SPICE while keeping it recognisable.

    Bus indices are kept as-is: the layout's net names come from the DEF, which
    uses the same `foo[3]` spelling, and top-level pins are matched by name.
    """
    return name.strip().replace(" ", "")


def write_spice(
    netlist: str | Path,
    top: str,
    cdl: str | Path,
    out: str | Path,
    **kw: object,
) -> Path:
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_spice(netlist, top, cdl, **kw), encoding="utf-8")  # type: ignore[arg-type]
    return path
