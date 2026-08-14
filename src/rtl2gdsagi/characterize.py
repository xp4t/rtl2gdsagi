"""Deterministic RTL characterization.

Review 5.1: this produces facts for the planner and the renderers -- module
hierarchy, clock ports, resets, memories, rough size. It is explicitly not a
pass/fail gate, and it involves no model call: these are lookups, not judgments.

The parsing is deliberately lightweight (regex over comment-stripped source)
rather than a full Verilog frontend. Everything it produces is either
corroborated by Verilator at the lint stage or by Yosys at elaboration, so a
mis-parse surfaces immediately downstream rather than silently corrupting a
constraint.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"//[^\n]*")
_MODULE = re.compile(r"\bmodule\s+([A-Za-z_]\w*)", re.MULTILINE)
_ENDMODULE = re.compile(r"\bendmodule\b")
_INSTANCE = re.compile(r"^\s*([A-Za-z_]\w*)\s+(?:#\s*\([^)]*\)\s*)?([A-Za-z_]\w*)\s*\(", re.M)
# Horizontal whitespace only ([ \t], never \s) in the comma continuation: with
# \s the name list runs past the end of one declaration, swallows the newline
# and captures the next line's `input`/`output` keyword as a port name while
# dropping the real ports after it.
_PORT = re.compile(
    r"\b(input|output|inout)\b[ \t]+"
    r"(?:(?:wire|reg|logic|bit|signed|unsigned)\b[ \t]*)*"
    r"(?:\[[^\]]*\][ \t]*)?"
    # The comma continuation must stop at the next direction keyword. Without
    # the lookahead, `input wire a, input wire b` captures "a, input" and loses
    # b entirely; with \s instead of [ \t] the same happens across newlines.
    r"([A-Za-z_]\w*(?:[ \t]*,[ \t]*(?!input\b|output\b|inout\b)[A-Za-z_]\w*)*)",
)
_VERILOG_KEYWORDS = frozenset({
    "input", "output", "inout", "wire", "reg", "logic", "bit", "signed",
    "unsigned", "parameter", "localparam", "module", "endmodule", "begin", "end",
})
_POSEDGE = re.compile(r"@\s*\(\s*(?:posedge|negedge)\s+([A-Za-z_]\w*)")
_MEM = re.compile(r"\breg\s*\[[^\]]+\]\s*([A-Za-z_]\w*)\s*\[[^\]]+\]")
_ALWAYS_FF = re.compile(r"\balways(?:_ff)?\s*@")

#: Ports whose names look like clocks even without an edge-sensitive reference.
#: Substring rather than whole-segment matching, deliberately: real designs use
#: pclk, xclk, sclk, clk25m and similar, and missing one of those silently
#: produces an SDC with an unconstrained clock domain -- the worst kind of
#: wrong, because STA then reports clean timing on a path it never checked.
_CLOCK_HINT = re.compile(r"(?:^|_)[a-z]{0,2}(clk|clock)\w*$", re.IGNORECASE)
#: Substring matching, and checked *before* the clock hint. Names like
#: `i_rstn_clk` (a reset synchronised into the clk domain) contain "clk" and
#: would otherwise be constrained with create_clock, which is nonsense: it
#: invents a clock domain that does not exist and leaves the real reset path
#: unconstrained.
_RESET_HINT = re.compile(
    r"(?:^|_)(a?rst_?n?|a?reset_?n?|nrst|nreset)(?:_|$|\d)", re.IGNORECASE
)

RTL_SUFFIXES = (".v", ".sv", ".vh", ".svh")


def strip_comments(text: str) -> str:
    return _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", text))


@dataclass
class DesignFacts:
    top: str
    sources: list[Path] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)
    #: Clock port names found on the top module, with an assumed period.
    clocks: list[dict[str, Any]] = field(default_factory=list)
    resets: list[str] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    instances: dict[str, list[str]] = field(default_factory=dict)
    memories: list[str] = field(default_factory=list)
    #: Rough proxy for size, used only to pick sane starting knobs.
    always_blocks: int = 0
    total_lines: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def clock_domains(self) -> int:
        return len(self.clocks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "top": self.top,
            "sources": [str(p) for p in self.sources],
            "modules": self.modules,
            "clocks": self.clocks,
            "clock_domains": self.clock_domains,
            "resets": self.resets,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "instances": self.instances,
            "memories": self.memories,
            "always_blocks": self.always_blocks,
            "total_lines": self.total_lines,
            "warnings": self.warnings,
        }


def _split_modules(text: str) -> dict[str, str]:
    """Map module name -> its body text."""
    out: dict[str, str] = {}
    for m in _MODULE.finditer(text):
        name = m.group(1)
        end = _ENDMODULE.search(text, m.end())
        out[name] = text[m.end() : end.start() if end else len(text)]
    return out


def _ports(body: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {"input": [], "output": [], "inout": []}
    for direction, names in _PORT.findall(body):
        for n in (x.strip() for x in names.split(",")):
            if n and n not in _VERILOG_KEYWORDS and n not in found[direction]:
                found[direction].append(n)
    return found


def characterize(
    rtl_dir: str | Path,
    top: str,
    *,
    default_period_ns: float = 10.0,
    extra_sources: list[Path] | None = None,
) -> DesignFacts:
    """Walk ``rtl_dir`` and extract deterministic facts about ``top``."""
    root = Path(rtl_dir)
    sources = sorted(
        p for p in root.rglob("*")
        if p.is_file() and p.suffix in RTL_SUFFIXES and "_tb" not in p.stem
    )
    if extra_sources:
        sources = sorted(set(sources) | set(extra_sources))

    facts = DesignFacts(top=top, sources=sources)
    if not sources:
        facts.warnings.append(f"no RTL sources found under {root}")
        return facts

    bodies: dict[str, str] = {}
    for p in sources:
        try:
            raw = p.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            facts.warnings.append(f"could not read {p}: {exc}")
            continue
        facts.total_lines += raw.count("\n") + 1
        text = strip_comments(raw)
        facts.always_blocks += len(_ALWAYS_FF.findall(text))
        facts.memories += [m for m in _MEM.findall(text) if m not in facts.memories]
        bodies.update(_split_modules(text))

    facts.modules = sorted(bodies)
    if top not in bodies:
        facts.warnings.append(
            f"top module {top!r} not found in {len(sources)} source file(s); "
            f"available: {', '.join(facts.modules[:12])}"
        )
        return facts

    body = bodies[top]
    ports = _ports(body)
    facts.inputs = ports["input"]
    facts.outputs = ports["output"]

    # A clock is an input that is edge-referenced anywhere in the design, or one
    # whose name is conventionally a clock. Edge references are the strong
    # signal; the name hint only catches clocks fed straight to a submodule.
    edged = {n for b in bodies.values() for n in _POSEDGE.findall(b)}
    for name in facts.inputs:
        if _RESET_HINT.search(name):
            continue  # exclusion wins: a reset is never a clock
        if name in edged or _CLOCK_HINT.search(name):
            facts.clocks.append({"name": name, "period_ns": default_period_ns})
    facts.resets = [n for n in facts.inputs if _RESET_HINT.search(n)]

    for mod, b in bodies.items():
        kids = sorted({
            inst_type for inst_type, _inst_name in _INSTANCE.findall(b)
            if inst_type in bodies and inst_type != mod
        })
        if kids:
            facts.instances[mod] = kids

    if not facts.clocks:
        facts.warnings.append(
            "no clock port identified on the top module; STA will be constrained "
            "against a virtual clock, which is almost certainly not what you want"
        )
    return facts


def suggest_starting_ir(facts: DesignFacts) -> dict[str, dict[str, Any]]:
    """Pick sane initial knobs from design size. Deterministic, not a model call.

    Review 5.1/19 Phase 9: characterization should inform the starting point so
    the flow does not begin from the same fixed defaults for every design.
    """
    delta: dict[str, dict[str, Any]] = {}
    size = facts.always_blocks + len(facts.modules)

    if size <= 8:
        delta["floorplan"] = {"core_utilization": 0.35}
        delta["placement"] = {"target_density": 0.45}
    elif size <= 40:
        delta["floorplan"] = {"core_utilization": 0.45}
        delta["placement"] = {"target_density": 0.55}
    else:
        delta["floorplan"] = {"core_utilization": 0.55}
        delta["placement"] = {"target_density": 0.60}

    if facts.clock_domains > 1:
        # Multiple asynchronous domains: give CTS more room and relax skew,
        # because a single tight skew target across independent domains is
        # not meaningful.
        delta["cts"] = {"target_skew_ns": 0.4}
    if facts.memories:
        delta.setdefault("floorplan", {})["core_utilization"] = min(
            0.40, delta.get("floorplan", {}).get("core_utilization", 0.40)
        )
    return delta
