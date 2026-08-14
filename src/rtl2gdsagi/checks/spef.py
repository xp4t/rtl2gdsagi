"""SPEF validation.

Extraction used to pass on "the file is not empty". A header-only SPEF naming
a different design and containing zero ``*D_NET`` records returned
``pass: extraction completed`` -- and, worse, signoff STA then read it, emitted
only a parse *warning*, and reported the same timing numbers as the analysis
with no parasitics at all. Both gates said the design met timing with real
interconnect when no interconnect had been read.

So the file has to be shown to be:

* a SPEF at all (header, version, units);
* about **this** design;
* actually populated -- a nonzero number of structurally complete nets;
* finite throughout;
* terminated rather than truncated;
* consistent with the nets the routed design actually has.

None of that is parasitic *accuracy*, which this project cannot check. It is
the much weaker claim that the file describes this design and contains data.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_HEADER = re.compile(r'^\s*\*SPEF\s+"([^"]*)"', re.MULTILINE)
_DESIGN = re.compile(r'^\s*\*DESIGN\s+"([^"]*)"', re.MULTILINE)
_UNIT = re.compile(r"^\s*\*([TCRL])_UNIT\s+([\d.eE+-]+)\s+(\w+)", re.MULTILINE)
_D_NET = re.compile(r"^\s*\*D_NET\s+(\S+)\s+([\d.eE+-]+)", re.MULTILINE)
_END_NET = re.compile(r"^\s*\*END\s*$", re.MULTILINE)
#: Any bare numeric token, for the finiteness sweep.
_NUMERIC = re.compile(r"(?<![\w.*:])[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?(?![\w.])")

#: `*NAME_MAP` block: `*21 _00_`, one mapping per line, until the next `*`
#: keyword section.
_NAME_MAP_BLOCK = re.compile(
    r"^\s*\*NAME_MAP\s*$(.*?)(?=^\s*\*[A-Z_]+\b)", re.S | re.M)
_NAME_MAP_ENTRY = re.compile(r"^\s*\*(\d+)\s+(\S+)\s*$", re.M)
#: One whole `*D_NET ... *END` section.
_D_NET_SECTION = re.compile(
    r"^\s*\*D_NET\s+(\S+)\s+(\S+)\s*$(.*?)^\s*\*END\s*$", re.S | re.M)
_CONN_ENTRY = re.compile(r"^\s*\*[PI]\s+\S+", re.M)


def parse_name_map(text: str) -> dict[str, str]:
    """`*NAME_MAP` index -> logical net name.

    SPEF refers to nets by index (`*D_NET *21 ...`). Comparing those raw
    tokens against DEF net names is comparing `*21` to `_00_`, which never
    matches and never can -- so a count ratio was the only thing left to
    check, and a count is exactly what P0-R1 forged.
    """
    m = _NAME_MAP_BLOCK.search(text)
    if not m:
        return {}
    return {idx: name for idx, name in _NAME_MAP_ENTRY.findall(m.group(1))}


def resolve_net_name(token: str, name_map: dict[str, str]) -> str | None:
    """`*21` -> `_00_`; a bare name resolves to itself; unknown -> None."""
    if token.startswith("*"):
        return name_map.get(token[1:])
    return token


@dataclass(frozen=True)
class SPEFResult:
    path: Path
    design: str
    version: str
    net_count: int
    total_capacitance: float
    units: dict[str, str] = field(default_factory=dict)
    routed_net_count: int | None = None
    coverage: float | None = None
    #: Every *D_NET resolved through *NAME_MAP, in file order.
    resolved_net_names: tuple[str, ...] = field(default_factory=tuple)
    #: D_NET tokens with no *NAME_MAP entry.
    unresolved: tuple[str, ...] = field(default_factory=tuple)
    #: Resolved names appearing on more than one *D_NET.
    duplicates: tuple[str, ...] = field(default_factory=tuple)
    #: Routed nets with no *D_NET, and *D_NET names absent from the DEF.
    missing: tuple[str, ...] = field(default_factory=tuple)
    extra: tuple[str, ...] = field(default_factory=tuple)
    problems: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return not self.problems

    def summary(self) -> str:
        if self.problems:
            return "SPEF unusable: " + "; ".join(self.problems)
        cov = "" if self.coverage is None else f", {self.coverage:.1%} of routed nets"
        return (
            f"SPEF valid: design {self.design!r}, {self.net_count} net(s){cov}, "
            f"total C {self.total_capacitance:.4g}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "spef_design": self.design,
            "spef_version": self.version,
            "spef_net_count": self.net_count,
            "routed_net_count": self.routed_net_count,
            "coverage": self.coverage,
            "resolved_net_names": list(self.resolved_net_names),
            "unresolved": list(self.unresolved),
            "duplicates": list(self.duplicates),
            "missing": list(self.missing),
            "extra": list(self.extra),
            "total_capacitance": self.total_capacitance,
            "units": self.units,
            "ok": self.ok,
            "parse_errors": list(self.problems),
        }


def routed_net_names(def_path: str | Path) -> set[str]:
    """Signal net names from a routed DEF's NETS section.

    Used only to size the expected inventory. Power/ground live in
    SPECIALNETS and are deliberately not counted: they are not extracted as
    ordinary parasitic nets.
    """
    text = Path(def_path).read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^NETS\s+\d+\s*;(.*?)^END NETS", text, re.S | re.M)
    if not m:
        return set()
    return {
        name for name in re.findall(r"^\s*-\s+(\S+)", m.group(1), re.M)
    }


def validate_spef(
    path: str | Path,
    *,
    expected_design: str,
    routed_def: str | Path | None = None,
    min_coverage: float = 0.5,
) -> SPEFResult:
    """Structural validation of a SPEF against the design it claims to describe."""
    p = Path(path)
    problems: list[str] = []

    if not p.is_file():
        return SPEFResult(p, "", "", 0, 0.0,
                          problems=(f"SPEF was not written: {p}",))
    if p.stat().st_size == 0:
        return SPEFResult(p, "", "", 0, 0.0, problems=(f"SPEF is empty: {p}",))

    text = p.read_text(encoding="utf-8", errors="replace")

    hm = _HEADER.search(text)
    version = hm.group(1) if hm else ""
    if not hm:
        problems.append(
            "no *SPEF header: this is not a SPEF file, whatever its extension"
        )

    dm = _DESIGN.search(text)
    design = dm.group(1) if dm else ""
    if not dm:
        problems.append("no *DESIGN record, so the file does not say what it describes")
    elif design != expected_design:
        problems.append(
            f"SPEF describes design {design!r}, not {expected_design!r}; "
            "parasitics from another design are not evidence about this one"
        )

    units = {k: f"{v} {u}" for k, v, u in _UNIT.findall(text)}
    for required in ("C", "R"):
        if required not in units:
            problems.append(f"no *{required}_UNIT declaration, so values have no scale")

    name_map = parse_name_map(text)

    # Whole sections, not just headers. A *D_NET line on its own says nothing
    # about whether the net carries any parasitics.
    sections = _D_NET_SECTION.findall(text)
    nets = _D_NET.findall(text)
    net_count = len(nets)
    if sections and len(sections) < net_count:
        problems.append(
            f"{net_count} *D_NET header(s) but only {len(sections)} complete "
            "*D_NET ... *END section(s): at least one net is truncated"
        )

    total_c = 0.0
    resolved: list[str] = []
    unresolved: list[str] = []
    for token, cap, body in sections:
        who = resolve_net_name(token, name_map)
        if who is None:
            unresolved.append(token)
        else:
            resolved.append(who)
        label = who or token
        try:
            value = float(cap)
        except ValueError:
            problems.append(f"net {label} has an unparseable capacitance {cap!r}")
            continue
        if not math.isfinite(value):
            problems.append(f"net {label} has a non-finite capacitance {cap!r}")
            continue
        total_c += value
        # A net with no connections is not annotated interconnect. OpenRCX
        # always emits *CONN with at least the driver or a pin.
        if not _CONN_ENTRY.search(body):
            problems.append(
                f"net {label} has no *CONN entries, so it connects to nothing "
                "and annotates no pin"
            )

    if unresolved:
        problems.append(
            f"{len(unresolved)} *D_NET identifier(s) have no *NAME_MAP entry "
            f"({', '.join(sorted(unresolved)[:5])}): their net identity is "
            "unknown, so nothing can be said about what was annotated"
        )

    seen: dict[str, int] = {}
    for who in resolved:
        seen[who] = seen.get(who, 0) + 1
    duplicates = sorted(n for n, c in seen.items() if c > 1)
    if duplicates:
        problems.append(
            f"{len(duplicates)} net name(s) appear on more than one *D_NET "
            f"({', '.join(duplicates[:5])}): a SPEF that describes the same "
            "net repeatedly is not evidence about the nets it omits"
        )

    if net_count == 0:
        problems.append(
            "the SPEF contains no *D_NET records: it declares a design and no "
            "parasitics, so timing read from it is timing with no interconnect"
        )

    # Truncation: every *D_NET is closed by *END, and the file ends with one.
    ends = len(_END_NET.findall(text))
    if net_count and ends < net_count:
        problems.append(
            f"{net_count} *D_NET record(s) but only {ends} *END: the file is "
            "truncated mid-net"
        )
    if not text.rstrip().endswith("*END"):
        problems.append("the SPEF does not end with *END; it is truncated")

    # A cheap sweep for NaN/Inf that slipped in as text.
    if re.search(r"\b(nan|inf|-inf)\b", text, re.IGNORECASE):
        problems.append("the SPEF contains non-finite numeric tokens (nan/inf)")

    routed_count: int | None = None
    coverage: float | None = None
    missing: list[str] = []
    extra: list[str] = []
    if routed_def is not None:
        try:
            routed = routed_net_names(routed_def)
        except OSError as exc:
            problems.append(f"could not read the routed DEF for comparison: {exc}")
            routed = set()
        if routed:
            routed_count = len(routed)
            # Identity, not arithmetic.
            #
            # Coverage used to be `len(D_NET) / len(routed nets)`. A SPEF with
            # 35 *D_NET records all describing the *same* routed net scored
            # 100% and was accepted -- the reproduction behind P0-R1. The set
            # of resolved names must equal the set of routed nets.
            unique = set(resolved)
            missing = sorted(routed - unique)
            extra = sorted(unique - routed)
            coverage = len(unique & routed) / routed_count if routed_count else 0.0
            if missing:
                problems.append(
                    f"{len(missing)} routed net(s) have no *D_NET "
                    f"({', '.join(missing[:5])}): their interconnect is "
                    "unannotated, so timing on them is timing with no parasitics"
                )
            if extra:
                problems.append(
                    f"{len(extra)} *D_NET name(s) are not routed nets in this "
                    f"design ({', '.join(extra[:5])}): the SPEF describes "
                    "interconnect that does not exist here"
                )
            if coverage < min_coverage:
                problems.append(
                    f"the SPEF annotates {len(unique & routed)} of "
                    f"{routed_count} routed nets ({coverage:.1%}), below the "
                    f"{min_coverage:.0%} minimum"
                )

    return SPEFResult(
        path=p, design=design, version=version, net_count=net_count,
        total_capacitance=total_c, units=units, routed_net_count=routed_count,
        coverage=coverage,
        resolved_net_names=tuple(resolved), unresolved=tuple(sorted(unresolved)),
        duplicates=tuple(duplicates), missing=tuple(missing), extra=tuple(extra),
        problems=tuple(problems),
    )
