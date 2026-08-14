"""The stage graph, as data.

This is the corrected architecture from the review, not the original nine-box
sketch. Differences that matter:

* ``sta_pre`` is **advisory**: pre-placement slack is an estimate and must not
  hard-block or trigger a rollback on its own (review 4.9).
* ``sta_postcts`` (hold, first point where clock latency is real) and
  ``sta_signoff`` (post-route, with extracted parasitics) are hard gates. The
  original flow had neither, so a GDS could be declared final having never been
  timed with a real clock tree (review 4.3).
* ``lec_synth`` and ``lec_route`` bracket every netlist-transforming step, so an
  autonomously-applied patch cannot silently change function (review 4.4).
* ``drc``, ``lvs`` and ``antenna`` are three separate gates with three different
  root causes, not one "DRC/LVS Completed?" boolean (review 4.7).
* ``signoff`` re-verifies every hard constraint against one exact final GDS
  hash, rather than trusting a patchwork of checks that passed at different
  times against different artifacts (review 4.10).

No stage takes hand-written TCL. Every stage is configured by a schema-bounded
IR section which a deterministic renderer turns into tool syntax
(:mod:`rtl2gdsagi.ir`, :mod:`rtl2gdsagi.render`), so "build from scratch" is not
a code path that exists (review 4.2, 20.2).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StageId(str, Enum):
    CHARACTERIZE = "characterize"
    LINT = "lint"
    SIM = "sim"
    SDC = "sdc"
    SYNTHESIS = "synthesis"
    LEC_SYNTH = "lec_synth"
    STA_PRE = "sta_pre"
    FLOORPLAN = "floorplan"
    PDN = "pdn"
    PLACEMENT = "placement"
    CTS = "cts"
    STA_POSTCTS = "sta_postcts"
    ROUTING = "routing"
    EXTRACTION = "extraction"
    STA_SIGNOFF = "sta_signoff"
    GDSOUT = "gdsout"
    DRC = "drc"
    LVS = "lvs"
    ANTENNA = "antenna"
    LEC_ROUTE = "lec_route"
    SIGNOFF = "signoff"

    def __str__(self) -> str:
        return self.value


class Tool(str, Enum):
    NONE = "none"          # deterministic, in-process
    VERILATOR = "verilator"
    IVERILOG = "iverilog"
    YOSYS = "yosys"
    EQY = "eqy"        # equivalence prover; yosys equiv_* cannot do signoff LEC
    OPENSTA = "sta"
    OPENROAD = "openroad"  # via the OpenLane container
    KLAYOUT = "klayout"

    def __str__(self) -> str:
        return self.value


class Gate(str, Enum):
    #: Blocks the flow. Failure triggers diagnosis and rollback.
    HARD = "hard"
    #: Logged and fed to the optimizer; never blocks, never rolls back alone.
    ADVISORY = "advisory"
    #: Produces data for the planner; not a pass/fail gate at all.
    NONE = "none"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class StageSpec:
    id: StageId
    tool: Tool
    gate: Gate
    summary: str
    #: IR section name that configures this stage. None = no tunable config.
    ir_section: str | None = None
    needs_pdk: bool = False
    pdk_requirements: tuple[str, ...] = ()
    consumes: tuple[str, ...] = ()
    produces: tuple[str, ...] = ()
    #: Does this stage transform the netlist? If so it must be bracketed by LEC.
    transforms_netlist: bool = False
    #: Stage writes a durable checkpoint that rollback can restore.
    checkpoint: bool = True
    #: Stage may be skipped when its prerequisite tooling/inputs are absent.
    optional: bool = False
    success_criteria: str = ""

    @property
    def name(self) -> str:
        return self.id.value

    @property
    def is_hard(self) -> bool:
        return self.gate is Gate.HARD


_SC = ("liberty_path",)
_PHYS = ("liberty_path", "tech_lef_path", "cell_lef_path")


STAGES: tuple[StageSpec, ...] = (
    StageSpec(
        id=StageId.CHARACTERIZE,
        tool=Tool.NONE,
        gate=Gate.NONE,
        summary="Deterministic RTL facts: hierarchy, clock domains, macros, size.",
        consumes=("rtl_dir",),
        produces=("design_facts",),
        checkpoint=False,
        success_criteria="Always succeeds; feeds the planner rather than gating.",
    ),
    StageSpec(
        id=StageId.LINT,
        tool=Tool.VERILATOR,
        gate=Gate.HARD,
        summary="Verilator lint: structural RTL problems.",
        ir_section="lint",
        consumes=("rtl_dir",),
        produces=("linted_rtl",),
        success_criteria="Zero Verilator errors for the top module.",
    ),
    StageSpec(
        id=StageId.SIM,
        tool=Tool.IVERILOG,
        gate=Gate.HARD,
        summary="RTL simulation against the design's testbenches.",
        ir_section="sim",
        consumes=("linted_rtl",),
        produces=("sim_result",),
        optional=True,  # skipped when no testbench or no iverilog
        success_criteria=(
            "Every testbench compiles, runs, and reports no assertion failures "
            "or $error/$fatal. Lint is not functional verification (review 4.5)."
        ),
    ),
    StageSpec(
        id=StageId.SDC,
        tool=Tool.NONE,
        gate=Gate.HARD,
        summary="SDC generation and validation: syntax plus semantic completeness.",
        ir_section="sdc",
        consumes=("design_facts",),
        produces=("sdc",),
        success_criteria=(
            "Parses, and every clock port found by characterization has a "
            "create_clock, with no fully unconstrained IO (review 4.8)."
        ),
    ),
    StageSpec(
        id=StageId.SYNTHESIS,
        tool=Tool.YOSYS,
        gate=Gate.HARD,
        summary="Yosys elaboration, optimisation and technology mapping.",
        ir_section="synthesis",
        needs_pdk=True,
        pdk_requirements=_SC,
        consumes=("linted_rtl", "sdc"),
        produces=("netlist", "synth_report"),
        transforms_netlist=True,
        success_criteria=(
            "Tool exits clean, a netlist is written, cell count is non-zero, "
            "nothing remains unmapped, and no unintended latches were inferred. "
            "Area/timing shortfall is a separate soft verdict, not an error."
        ),
    ),
    StageSpec(
        id=StageId.LEC_SYNTH,
        tool=Tool.EQY,
        gate=Gate.HARD,
        summary="Formal equivalence: RTL versus post-synthesis netlist.",
        ir_section="lec",
        needs_pdk=True,
        pdk_requirements=_SC,
        consumes=("linted_rtl", "netlist"),
        produces=("lec_synth_report",),
        optional=True,
        success_criteria=(
            "equiv_induct/equiv_status prove every compared cell equivalent "
            "with zero unproven points."
        ),
    ),
    StageSpec(
        id=StageId.STA_PRE,
        tool=Tool.OPENSTA,
        gate=Gate.ADVISORY,  # review 4.9: estimate only, must not hard-block
        summary="Pre-layout STA. Advisory sanity check on synthesis output.",
        ir_section="sta",
        needs_pdk=True,
        pdk_requirements=_SC,
        consumes=("netlist", "sdc"),
        produces=("sta_pre_report",),
        success_criteria=(
            "Recorded for the optimizer and for later delta analysis. A negative "
            "estimate here never blocks the flow or triggers a rollback."
        ),
    ),
    StageSpec(
        id=StageId.FLOORPLAN,
        tool=Tool.OPENROAD,
        gate=Gate.HARD,
        summary="Die/core sizing, IO placement, macro placement, tracks and rows.",
        ir_section="floorplan",
        needs_pdk=True,
        pdk_requirements=_PHYS,
        consumes=("netlist", "sdc"),
        produces=("floorplan_def",),
        success_criteria="Legal die/core geometry, non-zero rows, no macro overlap.",
    ),
    StageSpec(
        id=StageId.PDN,
        tool=Tool.OPENROAD,
        gate=Gate.HARD,
        summary="Power distribution network generation and IR-drop check.",
        ir_section="pdn",
        needs_pdk=True,
        pdk_requirements=_PHYS,
        consumes=("floorplan_def",),
        produces=("pdn_def", "pdn_report"),
        success_criteria=(
            "Straps cover the core, every power pin connects, and worst IR drop "
            "is within the configured budget."
        ),
    ),
    StageSpec(
        id=StageId.PLACEMENT,
        tool=Tool.OPENROAD,
        gate=Gate.HARD,
        summary="Global and detailed placement, plus routability estimate.",
        ir_section="placement",
        needs_pdk=True,
        pdk_requirements=_PHYS,
        consumes=("pdn_def",),
        produces=("placement_def", "congestion_report"),
        transforms_netlist=True,  # repair_design may resize/buffer
        success_criteria=(
            "Detailed placement legal, zero overlaps, zero off-grid instances. "
            "Global-route overflow is a soft verdict feeding the optimizer, "
            "caught here because it is far cheaper than a failed routing run."
        ),
    ),
    StageSpec(
        id=StageId.CTS,
        tool=Tool.OPENROAD,
        gate=Gate.HARD,
        summary="Clock tree synthesis.",
        ir_section="cts",
        needs_pdk=True,
        pdk_requirements=_PHYS,
        consumes=("placement_def",),
        produces=("cts_def", "cts_report"),
        transforms_netlist=True,
        success_criteria="A clock tree exists for every clock; skew within target.",
    ),
    StageSpec(
        id=StageId.STA_POSTCTS,
        tool=Tool.OPENROAD,
        gate=Gate.HARD,
        summary="Post-CTS timing, hold-focused. First point hold is meaningful.",
        ir_section="sta",
        needs_pdk=True,
        pdk_requirements=_PHYS,
        consumes=("cts_def", "sdc"),
        produces=("sta_postcts_report",),
        success_criteria=(
            "Hold slack non-negative with real clock latency. Hold before CTS is "
            "close to meaningless, which is why this gate exists (review 4.3)."
        ),
    ),
    StageSpec(
        id=StageId.ROUTING,
        tool=Tool.OPENROAD,
        gate=Gate.HARD,
        summary="Global and detailed routing.",
        ir_section="routing",
        needs_pdk=True,
        pdk_requirements=_PHYS,
        consumes=("cts_def",),
        produces=("routed_def",),
        transforms_netlist=True,
        success_criteria="Routing completes with zero violations and zero opens.",
    ),
    StageSpec(
        id=StageId.EXTRACTION,
        tool=Tool.OPENROAD,
        gate=Gate.HARD,
        summary="Parasitic extraction to SPEF.",
        ir_section="extraction",
        needs_pdk=True,
        pdk_requirements=_PHYS,
        consumes=("routed_def",),
        produces=("spef",),
        success_criteria="A SPEF is written covering every net in the routed design.",
    ),
    StageSpec(
        id=StageId.STA_SIGNOFF,
        tool=Tool.OPENROAD,
        gate=Gate.HARD,
        summary="Signoff STA with real extracted parasitics, all corners.",
        ir_section="sta",
        needs_pdk=True,
        pdk_requirements=_PHYS,
        consumes=("routed_def", "spef", "sdc"),
        produces=("sta_signoff_report",),
        success_criteria=(
            "Setup and hold slack non-negative at every signoff corner, using "
            "extracted parasitics. This is the authoritative timing check."
        ),
    ),
    StageSpec(
        id=StageId.GDSOUT,
        tool=Tool.KLAYOUT,
        gate=Gate.HARD,
        summary="Stream out one final merged GDSII.",
        ir_section="gdsout",
        needs_pdk=True,
        pdk_requirements=("tech_lef_path",),
        consumes=("routed_def",),
        produces=("final_gds",),
        success_criteria=(
            "Exactly one merged GDS, containing the expected non-empty top cell, "
            "with no unresolved cell references after the merge."
        ),
    ),
    StageSpec(
        id=StageId.DRC,
        tool=Tool.KLAYOUT,
        gate=Gate.HARD,
        summary="Signoff DRC against the final GDS.",
        ir_section="drc",
        needs_pdk=True,
        pdk_requirements=("drc_deck_path",),
        consumes=("final_gds",),
        produces=("drc_report",),
        success_criteria=(
            "Report parses, the deck declared a non-zero rule set, the report's "
            "top cell matches the design, and total violation items are zero."
        ),
    ),
    StageSpec(
        id=StageId.LVS,
        tool=Tool.KLAYOUT,
        gate=Gate.HARD,
        summary="Signoff LVS: extracted layout netlist versus the design netlist.",
        ir_section="lvs",
        needs_pdk=True,
        pdk_requirements=("lvs_deck_path",),
        consumes=("final_gds", "netlist"),
        produces=("lvs_report",),
        success_criteria=(
            "Exit code, log verdict and the .lvsdb cross-reference all agree that "
            "the netlists match. Disagreement is a failure, never a pass."
        ),
    ),
    StageSpec(
        id=StageId.ANTENNA,
        tool=Tool.OPENROAD,
        gate=Gate.HARD,
        summary="Antenna ratio check.",
        ir_section="antenna",
        needs_pdk=True,
        pdk_requirements=_PHYS,
        consumes=("routed_def",),
        produces=("antenna_report",),
        success_criteria="Zero nets exceeding the PDK antenna ratio limit.",
    ),
    StageSpec(
        id=StageId.LEC_ROUTE,
        tool=Tool.EQY,
        gate=Gate.HARD,
        summary="Formal equivalence after all netlist-transforming physical steps.",
        ir_section="lec",
        needs_pdk=True,
        pdk_requirements=_SC,
        consumes=("linted_rtl", "routed_netlist"),
        produces=("lec_route_report",),
        optional=True,
        success_criteria=(
            "The post-route netlist, after CTS buffering and any repair_timing "
            "ECO, is still formally equivalent to the RTL."
        ),
    ),
    StageSpec(
        id=StageId.SIGNOFF,
        tool=Tool.NONE,
        gate=Gate.HARD,
        summary="Aggregate signoff: re-verify every hard constraint on one GDS hash.",
        ir_section=None,
        consumes=(
            "final_gds", "drc_report", "lvs_report", "antenna_report",
            "sta_signoff_report", "lec_route_report",
        ),
        produces=("signoff_bundle",),
        success_criteria=(
            "Every hard gate passed, and every signoff report is bound to the "
            "same final GDS sha256. A patchwork of checks that passed against "
            "different artifacts is not signoff (review 4.10)."
        ),
    ),
)

STAGE_ORDER: tuple[StageId, ...] = tuple(s.id for s in STAGES)
_BY_ID: dict[StageId, StageSpec] = {s.id: s for s in STAGES}

#: Stages whose output the signoff aggregator must bind to the final GDS.
SIGNOFF_GATES: tuple[StageId, ...] = (
    StageId.DRC, StageId.LVS, StageId.ANTENNA, StageId.STA_SIGNOFF, StageId.LEC_ROUTE,
)

#: Functional-verification stages that are not bound to the final GDS, and so
#: appear in no other signoff check, but without which nothing has been proved
#: about how the design actually behaves.
#:
#: They are declared ``optional=True`` so the runner can skip them when the
#: tool or the testbench is missing -- otherwise an absent dependency would
#: look like a design failure. Optional to *run* is not optional to *certify*:
#: signoff requires an explicit pass from each, whether it was skipped by
#: ``--skip`` or automatically by the runner. ``lec_route`` is already covered
#: by SIGNOFF_GATES.
REQUIRED_VERIFICATION: tuple[StageId, ...] = (StageId.SIM, StageId.LEC_SYNTH)


def get_stage(stage: StageId | str) -> StageSpec:
    key = stage if isinstance(stage, StageId) else StageId(stage)
    return _BY_ID[key]


def stage_index(stage: StageId | str) -> int:
    return STAGE_ORDER.index(stage if isinstance(stage, StageId) else StageId(stage))


def stages_from(start: StageId | str | None) -> tuple[StageSpec, ...]:
    """Stages to execute starting at ``start`` (for --resume-from)."""
    if start is None:
        return STAGES
    return STAGES[stage_index(start):]


def downstream_of(stage: StageId | str, *, inclusive: bool = True) -> tuple[StageId, ...]:
    """Every stage causally after ``stage``.

    Rollback invalidates all of these, not just the implicated stage: anything
    downstream of a changed stage is stale by construction (review 10).
    """
    i = stage_index(stage)
    return STAGE_ORDER[i:] if inclusive else STAGE_ORDER[i + 1:]


def parse_stage(value: str) -> StageId:
    try:
        return StageId(value)
    except ValueError:
        raise ValueError(
            f"unknown stage {value!r}; expected one of: "
            + ", ".join(s.value for s in STAGE_ORDER)
        ) from None
