"""Schema-bounded intermediate representation.

Replaces "Claude writes TCL from scratch" (review 4.2, 7, 20.2). The agent's
entire write surface is the set of fields declared here: typed, range-checked
enums and numbers. A deterministic renderer (:mod:`rtl2gdsagi.render`) turns a
validated IR into tool syntax, so identical IR yields byte-identical scripts and
controlled A/B comparison becomes possible.

The safety property this buys is **structural, not behavioural**: there is no
field for "skip this rule", "waive this violation" or "relax this constraint",
so the model cannot express those things -- not because it was told not to, but
because the schema has no way to say it. Note in particular that the ``drc``,
``lvs`` and ``antenna`` sections expose only performance knobs. Nothing an agent
writes can weaken a signoff check.
"""

from __future__ import annotations

import copy
import json
import hashlib
import math
import re
from dataclasses import dataclass
from typing import Any, Iterable

from .errors import ConfigError


class SchemaViolation(ConfigError):
    """A proposed IR value is outside the schema. Rejected before rendering."""


@dataclass(frozen=True)
class Field:
    name: str
    kind: str  # "int" | "float" | "bool" | "enum" | "str" | "list[str]"
    default: Any
    doc: str
    lo: float | None = None
    hi: float | None = None
    choices: tuple[Any, ...] | None = None
    #: False for fields only the orchestrator may set (paths, top name, ...).
    agent_writable: bool = True
    #: Regex every string value must match in full. Set it on any field whose
    #: value is interpolated into a tool script: a bare ``str`` field is an
    #: injection surface, because Tcl treats ``;`` as a command separator and
    #: the renderer cannot tell a cell name from a payload.
    pattern: str | None = None

    def coerce(self, value: Any) -> Any:
        """Validate and normalise ``value``, or raise SchemaViolation."""
        k = self.kind
        try:
            if k == "int":
                v: Any = int(value)
            elif k == "float":
                v = float(value)
            elif k == "bool":
                if isinstance(value, str):
                    v = value.strip().lower() in {"1", "true", "yes", "on"}
                else:
                    v = bool(value)
            elif k == "enum":
                v = value
            elif k == "str":
                v = str(value)
            elif k == "list[str]":
                if isinstance(value, str):
                    v = [value]
                else:
                    v = [str(x) for x in value]
            else:  # pragma: no cover - schema authoring error
                raise SchemaViolation(f"field {self.name!r} has unknown kind {k!r}")
        except (TypeError, ValueError) as exc:
            raise SchemaViolation(
                f"{self.name}: {value!r} is not a valid {k} ({exc})"
            ) from None

        if k in ("int", "float"):
            # NaN and the infinities pass every range comparison, because all
            # comparisons against NaN are False. Left in, a NaN timing
            # guardband silently defeated the slack check it was meant to
            # tighten. A bound that cannot be compared is not a bound.
            if not math.isfinite(v):
                raise SchemaViolation(
                    f"{self.name}={v} is not a finite number"
                )
            if self.lo is not None and v < self.lo:
                raise SchemaViolation(
                    f"{self.name}={v} is below the allowed minimum {self.lo}"
                )
            if self.hi is not None and v > self.hi:
                raise SchemaViolation(
                    f"{self.name}={v} is above the allowed maximum {self.hi}"
                )
        if k == "enum" and self.choices is not None and v not in self.choices:
            raise SchemaViolation(
                f"{self.name}={v!r} is not one of {list(self.choices)}"
            )
        if k == "list[str]" and self.choices is not None:
            bad = [x for x in v if x not in self.choices]
            if bad:
                raise SchemaViolation(
                    f"{self.name} contains invalid entries {bad}; allowed: {list(self.choices)}"
                )
        if self.pattern is not None:
            rx = re.compile(self.pattern)
            for s in (v if k == "list[str]" else [v]):
                if s != "" and not rx.fullmatch(str(s)):
                    raise SchemaViolation(
                        f"{self.name}={s!r} does not match {self.pattern}. This "
                        "field is written into a tool script, so it is "
                        "restricted to plain identifiers."
                    )
        return v

    def describe(self) -> dict[str, Any]:
        """Machine-readable field description handed to the agent."""
        d: dict[str, Any] = {"type": self.kind, "default": self.default, "doc": self.doc}
        if self.lo is not None or self.hi is not None:
            d["range"] = [self.lo, self.hi]
        if self.choices is not None:
            d["choices"] = list(self.choices)
        return d


#: A standard-cell identifier. Anything written into a tool script must match
#: this: no whitespace, no ';', no braces, no quotes, no substitution
#: characters -- none of the things that turn a name into a payload.
CELL_NAME = r"[A-Za-z_][A-Za-z0-9_$]*"

#: A Verilator warning code (WIDTH, UNOPTFLAT, ...). Constrained for the same
#: reason as CELL_NAME: the value is concatenated into a tool argument, so it
#: must not be able to carry anything but an identifier.
WARNING_CODE = r"[A-Za-z][A-Za-z0-9_]*"


def _f(name: str, kind: str, default: Any, doc: str, **kw: Any) -> Field:
    return Field(name=name, kind=kind, default=default, doc=doc, **kw)


SYNTH_STRATEGIES = ("AREA0", "AREA1", "AREA2", "DELAY0", "DELAY1", "DELAY2", "DELAY3")
EFFORTS = ("low", "medium", "high")

#: section -> fields. Sections line up with StageSpec.ir_section.
SCHEMA: dict[str, tuple[Field, ...]] = {
    "lint": (
        _f("fail_on_warning", "bool", False, "Promote Verilator warnings to errors.", agent_writable=False),
        _f("waived_rules", "list[str]", [],
           "Verilator warning codes to suppress, e.g. WIDTH. Each becomes a "
           "-Wno-<CODE> argument, so it is restricted to a warning identifier: "
           "unvalidated it would be a way to put text of the model's choosing "
           "onto a tool's command line. Structural errors are unaffected -- "
           "check_lint fails on %Error regardless of what is listed here, and "
           "-Wno- only governs warnings.",
           pattern=WARNING_CODE, agent_writable=False),
        _f("timescale", "str", "1ns/1ps", "Default timescale when the RTL omits one."),
    ),
    "sim": (
        _f("timeout_s", "int", 600, "Per-testbench wall-clock limit.", lo=1, hi=7200, agent_writable=False),
        _f("testbench_glob", "str", "*_tb.v", "Pattern locating testbenches.", agent_writable=False),
        _f("testbench_dir", "str", "",
           "Explicit directory holding testbenches. Empty means search the RTL "
           "tree and then a sibling tb/ directory. Set this when the "
           "testbenches live in a different repository from the RTL.", agent_writable=False),
        _f("plusargs", "list[str]", [], "Plusargs passed to each simulation.", agent_writable=False),
    ),
    "sdc": (
        _f("default_clock_period_ns", "float", 10.0,
           "Period used for a clock the design declares but the user did not "
           "constrain.", lo=0.1, hi=1000.0, agent_writable=False),
        _f("clock_uncertainty_ns", "float", 0.25,
           "Setup/hold uncertainty budget.", lo=0.0, hi=10.0, agent_writable=False),
        _f("input_delay_frac", "float", 0.2,
           "Input delay as a fraction of the clock period.", lo=0.0, hi=0.9, agent_writable=False),
        _f("output_delay_frac", "float", 0.2,
           "Output delay as a fraction of the clock period.", lo=0.0, hi=0.9, agent_writable=False),
        _f("output_load_pf", "float", 0.05, "Capacitive load on outputs.", lo=0.0, hi=10.0, agent_writable=False),
    ),
    "synthesis": (
        _f("strategy", "enum", "AREA0", "ABC mapping strategy.", choices=SYNTH_STRATEGIES),
        _f("flatten", "bool", True, "Flatten the hierarchy before mapping."),
        _f("max_fanout", "int", 10, "Fanout limit driving buffering.", lo=1, hi=64),
        _f("adder_type", "enum", "yosys", "Adder mapping.",
           choices=("yosys", "fa", "rca", "csa")),
        _f("share_resources", "bool", True, "Enable resource sharing."),
        _f("dff_map", "bool", True, "Map flip-flops to the standard cell library."),
    ),
    "lec": (
        _f("induction_steps", "int", 8,
           "Temporal induction depth for equiv_induct.", lo=1, hi=64),
        _f("timeout_s", "int", 900, "Wall-clock limit for the proof.", lo=1, hi=7200),
        _f("smt_solver", "enum", "z3",
           "SMT solver for the fallback proof strategy. The plain SAT strategy "
           "returns 'equivalence unknown' on deep sequential logic; this is "
           "what settles those. Empty disables the fallback (needs sby).",
           choices=("", "z3", "yices", "boolector", "bitwuzla", "cvc5")),
    ),
    "sta": (
        _f("corners", "list[str]", ["tt_025C_1v80"],
           "Liberty corners to analyse. Signoff should use more than one.",
           agent_writable=False),
        _f("derate_setup", "float", 0.0, "Setup derate factor.", lo=0.0, hi=0.5,
           agent_writable=False),
        _f("derate_hold", "float", 0.0, "Hold derate factor.", lo=0.0, hi=0.5,
           agent_writable=False),
        _f("slack_guardband_ns", "float", 0.0,
           "Extra margin required beyond zero slack.", lo=0.0, hi=5.0,
           agent_writable=False),
        _f("max_paths", "int", 20, "Paths per report.", lo=1, hi=1000),
    ),
    "floorplan": (
        _f("core_utilization", "float", 0.45,
           "Core area utilisation. Lower means more routing room.", lo=0.05, hi=0.90),
        _f("aspect_ratio", "float", 1.0, "Core height/width.", lo=0.2, hi=5.0),
        _f("core_margin_um", "float", 10.0,
           "Gap between core and die boundary.", lo=0.0, hi=500.0),
        _f("io_mode", "enum", "random_equidistant", "IO pin placement mode.",
           choices=("random_equidistant", "matching", "hungarian"), agent_writable=False),
        _f("tapcell_distance_um", "float", 13.0,
           "Spacing between well-tap cell rows. Too large leaves nwell "
           "untied and fails nwell.* DRC at signoff.", lo=1.0, hi=100.0),
    ),
    "pdn": (
        _f("strap_width_um", "float", 1.6, "Power strap width.", lo=0.1, hi=50.0),
        _f("strap_pitch_um", "float", 30.0, "Strap spacing.", lo=1.0, hi=500.0),
        _f("strap_offset_um", "float", 2.0,
           "Distance from the core edge to the first power strap. Must leave "
           "room for the straps themselves: a small die with a large offset "
           "fails with PDN-0185 'insufficient width to add straps'.",
           lo=0.0, hi=200.0),
        _f("core_ring", "bool", True, "Generate a core power ring."),
        _f("ir_drop_budget_mv", "float", 50.0,
           "Maximum acceptable IR drop.", lo=1.0, hi=500.0),
    ),
    "placement": (
        _f("target_density", "float", 0.55, "Global placement density.", lo=0.15, hi=0.99),
        _f("effort", "enum", "medium", "Placement effort.", choices=EFFORTS, agent_writable=False),
        _f("max_displacement_um", "float", 50.0,
           "Detailed placement displacement limit.", lo=1.0, hi=1000.0, agent_writable=False),
        _f("routability_driven", "bool", True, "Enable routability-driven placement."),
        _f("padding_sites", "int", 0,
           "Blank sites left either side of each cell. Packing cells edge to "
           "edge leaves the router no room to land its via pads, which shows "
           "up as li1 spacing violations at signoff rather than as a routing "
           "failure.", lo=0, hi=8),
        _f("congestion_overflow_limit", "float", 0.15,
           "Soft threshold on the overflow global placement converges to. "
           "OpenROAD's placer targets 0.1 by default and stops once it gets "
           "there, so a converged design normally lands just under 0.1 -- the "
           "previous 0.02 default would have flagged every design that worked "
           "perfectly. What this catches is a placement that settled "
           "materially worse than the placer's own target.",
           lo=0.0, hi=1.0, agent_writable=False),
    ),
    "cts": (
        _f("target_skew_ns", "float", 0.2, "Clock tree skew target.", lo=0.0, hi=10.0),
        _f("max_fanout", "int", 16, "Clock buffer fanout limit.", lo=1, hi=128),
        _f("root_buffer", "str", "",
           "Root clock buffer cell; empty means auto. Restricted to a plain "
           "cell identifier: this value is written straight into the CTS Tcl, "
           "where a ';' would start a second command.",
           pattern=CELL_NAME),
        _f("balance_levels", "bool", True, "Balance clock tree levels."),
        _f("hold_margin_ns", "float", 0.05,
           "Extra hold slack to aim for when inserting delay cells. Hold is "
           "fixed by adding delay on short paths, never by touching RTL.",
           lo=0.0, hi=2.0),
        _f("fix_hold", "bool", True,
           "Insert delay cells to repair hold violations after the clock tree "
           "exists. Turning this off does not make hold violations acceptable; "
           "the signoff timing gate still fails on them."),
    ),
    "routing": (
        _f("min_layer", "int", 1, "Lowest routing metal layer.", lo=1, hi=12),
        _f("max_layer", "int", 5, "Highest routing metal layer.", lo=1, hi=12),
        _f("global_effort", "enum", "medium", "Global routing effort.", choices=EFFORTS, agent_writable=False),
        _f("droute_iters", "int", 32, "Detailed routing iterations.", lo=1, hi=64),
        _f("insert_filler", "bool", True,
           "Fill row gaps after routing. Needed for nwell continuity (without "
           "it the nwell is a row of islands and fails nwell.* DRC), so "
           "disabling this trades one DRC failure class for another."),
        _f("insert_diodes", "bool", True,
           "Insert antenna diodes during routing. This fixes antenna violations; "
           "it does not suppress the antenna check."),
    ),
    "extraction": (
        _f("corner", "enum", "nom", "RC extraction corner.",
           choices=("min", "nom", "max"), agent_writable=False),
        _f("min_net_coverage", "float", 0.5,
           "Smallest fraction of the routed design's nets the SPEF must "
           "describe. Extraction legitimately omits some nets, but a SPEF "
           "covering almost none of them means signoff timing is running on "
           "interconnect that was never extracted.",
           lo=0.0, hi=1.0, agent_writable=False),
    ),
    "gdsout": (
        _f("merge_mode", "enum", "full", "Cell merge behaviour on streamout.",
           choices=("full", "flatten_top")),
    ),
    # Signoff sections expose performance knobs only. There is deliberately no
    # field here that can waive, filter or skip a check.
    "drc": (
        _f("threads", "int", 4, "KLayout worker threads.", lo=1, hi=64),
        _f("deep_mode", "bool", True, "Hierarchical DRC."),
    ),
    "lvs": (
        _f("threads", "int", 4, "KLayout worker threads.", lo=1, hi=64),
        _f("deep_mode", "bool", True, "Hierarchical extraction."),
    ),
    "antenna": (
        _f("threads", "int", 4, "Worker threads.", lo=1, hi=64),
    ),
}


class IR:
    """A validated configuration for the whole flow."""

    def __init__(self, sections: dict[str, dict[str, Any]] | None = None) -> None:
        self._data: dict[str, dict[str, Any]] = {}
        for name, fields in SCHEMA.items():
            self._data[name] = {f.name: copy.deepcopy(f.default) for f in fields}
        if sections:
            for sec, vals in sections.items():
                self.update(sec, vals, agent=False)

    # ---- access ----------------------------------------------------------

    def section(self, name: str) -> dict[str, Any]:
        if name not in self._data:
            raise SchemaViolation(
                f"unknown IR section {name!r}; known: {', '.join(sorted(self._data))}"
            )
        return dict(self._data[name])

    def get(self, section: str, field: str) -> Any:
        return self.section(section)[field]

    def as_dict(self) -> dict[str, dict[str, Any]]:
        return copy.deepcopy(self._data)

    # ---- mutation --------------------------------------------------------

    def update(self, section: str, values: dict[str, Any], *, agent: bool = True) -> dict[str, Any]:
        """Apply a delta to one section. Raises SchemaViolation on any bad key.

        ``agent=True`` additionally refuses fields the agent may not write.
        The update is all-or-nothing: nothing is applied if any key fails.
        """
        if section not in SCHEMA:
            raise SchemaViolation(
                f"unknown IR section {section!r}; the agent may only configure: "
                + ", ".join(sorted(SCHEMA))
            )
        by_name = {f.name: f for f in SCHEMA[section]}
        staged: dict[str, Any] = {}
        for key, raw in values.items():
            fld = by_name.get(key)
            if fld is None:
                raise SchemaViolation(
                    f"{section}.{key} is not a field in the schema; allowed: "
                    + ", ".join(sorted(by_name))
                )
            if agent and not fld.agent_writable:
                raise SchemaViolation(f"{section}.{key} is not agent-writable")
            staged[key] = fld.coerce(raw)
        self._data[section].update(staged)
        return dict(self._data[section])

    def apply_delta(self, delta: dict[str, dict[str, Any]], *, agent: bool = True) -> None:
        """Apply a multi-section delta atomically."""
        snapshot = self.as_dict()
        try:
            for sec, vals in delta.items():
                self.update(sec, vals, agent=agent)
        except SchemaViolation:
            self._data = snapshot
            raise

    # ---- identity --------------------------------------------------------

    def fingerprint(self, sections: Iterable[str] | None = None) -> str:
        """Stable hash of the IR, used to refuse duplicate failed configs."""
        data = self.as_dict()
        if sections is not None:
            data = {k: v for k, v in data.items() if k in set(sections)}
        blob = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def __eq__(self, other: object) -> bool:
        return isinstance(other, IR) and other._data == self._data

    def __repr__(self) -> str:
        return f"IR(fingerprint={self.fingerprint()[:12]})"


def describe_section(name: str) -> dict[str, Any]:
    """Schema description for one section, injected into agent prompts."""
    if name not in SCHEMA:
        raise SchemaViolation(f"unknown IR section {name!r}")
    return {f.name: f.describe() for f in SCHEMA[name]}


def writable_fields(name: str) -> dict[str, Any]:
    """Only the fields of `name` the agent may actually write.

    `describe_section` returns the whole schema including locked fields. Handing
    that to the model advertises fields validation always rejects, which is how
    the prompt came to misstate the action space (P1-AUTH-01).
    """
    if name not in SCHEMA:
        raise SchemaViolation(f"unknown IR section {name!r}")
    return {f.name: f.describe() for f in SCHEMA[name] if f.agent_writable}


def agent_writable_sections() -> tuple[str, ...]:
    return tuple(sorted(SCHEMA))
