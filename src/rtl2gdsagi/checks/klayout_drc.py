"""KLayout DRC report (.lyrdb) parsing.

The whole point of this module is that a DRC "pass" must be a parsed fact, not
an exit code and not the absence of a report.

Three failure modes this deliberately treats as NOT clean:

1. **Report missing or unparseable.** A deck that crashed writes no report, or a
   truncated one. Both look like "no violations found" to anything that just
   greps. Both are failures here.
2. **Report with zero declared categories.** If the runset failed to load its
   rules, KLayout still emits a well-formed but ruleless report: zero
   categories, zero items. That is a deck that checked nothing, not a clean
   layout.
3. **Report describing the wrong layout.** ``<top-cell>`` must match the design
   top. Combined with the artifact ledger's GDS binding, this is what stops the
   pre-merge-macro false-clean.

Counting note: in a real report the string ``<category>`` appears both in the
declaration block and once inside every item, so a naive ``grep -c`` massively
overcounts. Items are counted from ``items/item`` only.
"""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator

from ..artifacts import Artifact

#: (rule prefix, plain-English note). Longest-matching prefix wins, so order
#: these most-specific first. Every note here was written after tracking the
#: rule down to its actual cause on a real run; none of them are paraphrases
#: of the rule text.
_RULE_NOTES: tuple[tuple[str, str], ...] = (
    (
        "m2.x",
        "floating met2 -- metal with no via to anything. Usually a top-level "
        "port that nothing in the RTL drives or reads: synthesis removes the "
        "logic but the port survives, so its pin is streamed out as an "
        "isolated piece of metal. Check the named net in the routed DEF; if "
        "it reads '- <name> ( PIN <name> ) + USE SIGNAL ;' with no instance "
        "pins, delete the unused port from the RTL or connect it.",
    ),
    (
        "li.3",
        "li1 spacing. Seen when the detailed router is left unbounded and "
        "routes on li1 even though global route was restricted to met1 and "
        "above: its li1 wires land closer to the cells' li1 power rails than "
        "the rule allows. detailed_route needs -bottom_routing_layer and "
        "-top_routing_layer, not just set_routing_layers.",
    ),
    (
        "nwell",
        "nwell width/spacing. The classic cause is missing filler: without "
        "fill cells the nwell is a row of islands instead of one continuous "
        "strip, even though placement and routing are perfectly legal.",
    ),
    (
        "hvtp",
        "high-Vt implant layer width/spacing, and it travels with the nwell "
        "violations -- same root cause, usually missing filler cells.",
    ),
)


@dataclass(frozen=True)
class DRCResult:
    report_path: Path
    top_cell: str
    generator: str
    #: Violations per category name, only categories that actually have items.
    by_category: dict[str, int]
    total_violations: int
    #: How many rule categories the deck declared. Zero means the deck no-opped.
    declared_categories: int
    #: True when the declared rule names matched the approved deck's inventory,
    #: False when they did not, None when no deck identity was supplied.
    inventory_verified: bool | None = None
    #: The GDS this report was checked against, as bound by the orchestrator.
    checked_gds: Artifact | None = None
    problems: tuple[str, ...] = field(default_factory=tuple)

    @property
    def clean(self) -> bool:
        return not self.problems and self.total_violations == 0

    @property
    def violated_categories(self) -> int:
        return len(self.by_category)

    def top_categories(self, n: int = 10) -> list[tuple[str, int]]:
        return sorted(self.by_category.items(), key=lambda kv: -kv[1])[:n]

    def summary(self) -> str:
        if self.problems:
            return "DRC report unusable: " + "; ".join(self.problems)
        if self.total_violations == 0:
            return (
                f"DRC clean: 0 violations across {self.declared_categories} rule "
                f"categories on top cell {self.top_cell!r}"
            )
        worst = ", ".join(f"{name} ({n})" for name, n in self.top_categories(3))
        return (
            f"DRC FAILED: {self.total_violations} violations in "
            f"{self.violated_categories} of {self.declared_categories} categories "
            f"on top cell {self.top_cell!r}; worst: {worst}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_path": str(self.report_path),
            "top_cell": self.top_cell,
            "generator": self.generator,
            "total_violations": self.total_violations,
            "violated_categories": self.violated_categories,
            "declared_categories": self.declared_categories,
            "by_category": dict(sorted(self.by_category.items(), key=lambda kv: -kv[1])),
            "checked_gds": self.checked_gds.to_dict() if self.checked_gds else None,
            "clean": self.clean,
            "problems": list(self.problems),
        }

    def explanations(self) -> list[tuple[str, str]]:
        """Plain-English cause for each violated rule we have diagnosed.

        A KLayout rule name like ``m2.x`` is accurate and completely opaque if
        you have not seen it before. Every entry here comes from a real
        failure on this flow, so the note says what actually produced it
        rather than restating the rule.
        """
        out: list[tuple[str, str]] = []
        for name in sorted(self.by_category):
            for prefix, note in _RULE_NOTES:
                if name.startswith(prefix):
                    out.append((name, note))
                    break
        return out

    def violation_digest(self, limit: int = 25) -> str:
        """Compact, token-cheap rendering handed to Claude for diagnosis."""
        lines = [
            f"top cell: {self.top_cell}",
            f"total violations: {self.total_violations}",
            f"categories with violations: {self.violated_categories} "
            f"(of {self.declared_categories} declared)",
            "",
            "violations by rule (descending):",
        ]
        for name, n in self.top_categories(limit):
            lines.append(f"  {n:>7}  {name}")
        remaining = self.violated_categories - min(limit, self.violated_categories)
        if remaining > 0:
            lines.append(f"  ... and {remaining} further categories")
        notes = self.explanations()
        if notes:
            lines += ["", "what these usually mean here:"]
            lines += [f"  {name}: {note}" for name, note in notes]
        return "\n".join(lines)


def _clean_category(raw: str | None) -> str:
    """Item category refs are single-quoted; declarations are not."""
    s = (raw or "").strip()
    # Nested categories serialise as 'parent'.'child'; normalise to parent/child.
    parts = [p.strip().strip("'") for p in s.split(".'")] if ".'" in s else [s.strip("'")]
    return "/".join(p for p in parts if p)


def _iter_declared(cats: ET.Element | None, prefix: str = "") -> Iterator[str]:
    if cats is None:
        return
    for cat in cats.findall("category"):
        name = _clean_category(cat.findtext("name"))
        full = f"{prefix}{name}"
        yield full
        yield from _iter_declared(cat.find("categories"), prefix=f"{full}/")


#: deck sha256 -> (category count, sha256 of the sorted category names, label).
#:
#: "At least one rule ran" is not evidence that *the* deck ran. A valid report
#: declaring a single dummy category and zero items previously came back clean.
#: Counting categories is not enough either: a fabricated 211-entry report would
#: satisfy a count check while naming rules the foundry never wrote.
#:
#: So the contract is the exact name set, bound to the exact deck that produced
#: it. Both preserved real reports -- the clean register one and the OV7670 one
#: with a real m2.x violation -- declare the identical 211 names, which is what
#: makes this a stable contract rather than a snapshot of one run.
APPROVED_INVENTORIES: dict[str, tuple[int, str, str]] = {
    "ff4c0281ff485ae1c85f44d6d2695d43dd71422363edea8bc6c1b3dde6ef9470": (
        211,
        "cfa36171d93a4eccc91eee907f301e05b217f635a0c322b3feed96beedfe4e13",
        "sky130A_mr.drc (volare bdc9412b)",
    ),
}


def inventory_digest(names: Iterable[str]) -> str:
    return hashlib.sha256("\n".join(sorted(names)).encode("utf-8")).hexdigest()


def parse_drc_report(
    path: str | Path,
    *,
    expected_top: str | None = None,
    checked_gds: Artifact | None = None,
    deck_sha256: str | None = None,
) -> DRCResult:
    """Parse a ``.lyrdb`` into a verdict.

    Never raises on a bad report: an unusable report becomes a DRCResult whose
    ``problems`` is non-empty and whose ``clean`` is therefore False. Callers
    turn that into a ResultInvalid.
    """
    p = Path(path)
    problems: list[str] = []

    if not p.is_file():
        return DRCResult(
            report_path=p, top_cell="", generator="", by_category={},
            total_violations=0, declared_categories=0, checked_gds=checked_gds,
            problems=(f"DRC report was not written: {p}",),
        )
    if p.stat().st_size == 0:
        return DRCResult(
            report_path=p, top_cell="", generator="", by_category={},
            total_violations=0, declared_categories=0, checked_gds=checked_gds,
            problems=(f"DRC report is empty: {p}",),
        )

    try:
        root = ET.parse(p).getroot()
    except ET.ParseError as exc:
        return DRCResult(
            report_path=p, top_cell="", generator="", by_category={},
            total_violations=0, declared_categories=0, checked_gds=checked_gds,
            problems=(f"DRC report is not valid XML (truncated or crashed run): {exc}",),
        )

    if root.tag != "report-database":
        problems.append(f"unexpected root element {root.tag!r}, expected 'report-database'")

    top_cell = (root.findtext("top-cell") or "").strip()
    generator = (root.findtext("generator") or "").strip()

    declared = list(_iter_declared(root.find("categories")))

    # Prove the intended deck's whole rule set actually executed.
    inventory_ok = None
    if deck_sha256 is not None:
        contract = APPROVED_INVENTORIES.get(deck_sha256)
        if contract is None:
            inventory_ok = False
            problems.append(
                f"no approved rule inventory is known for DRC deck "
                f"{deck_sha256[:12]}, so this report cannot be shown to be a "
                "complete run of the intended deck"
            )
        else:
            want_count, want_digest, label = contract
            got_digest = inventory_digest(declared)
            if got_digest != want_digest:
                inventory_ok = False
                got, want = set(declared), None
                problems.append(
                    f"the report declares {len(declared)} rule categories but "
                    f"{label} defines {want_count}; the executed rule set is not "
                    f"the approved one (inventory {got_digest[:12]} vs "
                    f"{want_digest[:12]})"
                )
            else:
                inventory_ok = True

    counts: dict[str, int] = {}
    total = 0
    for item in root.findall("items/item"):
        name = _clean_category(item.findtext("category")) or "<uncategorised>"
        counts[name] = counts.get(name, 0) + 1
        total += 1

    if not declared:
        problems.append(
            "the DRC deck declared zero rule categories, so it checked nothing; "
            "this is a deck/runset failure, not a clean layout"
        )
    if not top_cell:
        problems.append("report does not name a top cell")
    elif expected_top and top_cell != expected_top:
        problems.append(
            f"report is for top cell {top_cell!r} but the design top is "
            f"{expected_top!r}; this report describes a different layout"
        )

    return DRCResult(
        report_path=p,
        top_cell=top_cell,
        generator=generator,
        by_category=counts,
        total_violations=total,
        declared_categories=len(declared),
        inventory_verified=inventory_ok,
        checked_gds=checked_gds,
        problems=tuple(problems),
    )
