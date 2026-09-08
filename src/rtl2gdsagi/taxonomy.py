"""Failure taxonomy and table-driven rollback.

This module is the review's central fix (9.0, 20.5). A flowchart cannot show
"any stage's failure may need to roll back to any earlier stage" -- that is N^2
arrows, which is exactly why the original diagram managed to draw only two
return paths for eight failure gates. So rollback targets are represented as
**data** here and resolved at runtime, which makes every stage reachable by
construction rather than by whichever line someone remembered to draw.

Each entry also carries ``forbids``: what the agent must never touch in response
to this failure class. That list is enforced by the orchestrator
(:mod:`rtl2gdsagi.safety`), not merely stated in a prompt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .stages import StageId


class FailureClass(str, Enum):
    RTL_SYNTAX = "rtl_syntax"
    RTL_FUNCTIONAL = "rtl_functional"
    ELABORATION = "elaboration"
    LIBRARY = "library"
    SDC = "sdc"
    SYNTH_ERROR = "synth_error"
    SYNTH_QOR = "synth_qor"
    LEC_MISMATCH = "lec_mismatch"
    TIMING_PRELAYOUT = "timing_prelayout"
    FLOORPLAN = "floorplan"
    PDN = "pdn"
    PLACEMENT = "placement"
    CONGESTION = "congestion"
    CTS = "cts"
    HOLD = "hold"
    SETUP = "setup"
    ROUTING = "routing"
    EXTRACTION = "extraction"
    DRC = "drc"
    LVS_PHYSICAL = "lvs_physical"
    LVS_LIBRARY = "lvs_library"
    LVS_STRUCTURAL = "lvs_structural"
    ANTENNA = "antenna"
    GDS = "gds"
    TCL_CONFIG = "tcl_config"
    TOOL_RUNTIME = "tool_runtime"
    ENVIRONMENT = "environment"

    def __str__(self) -> str:
        return self.value


class Resolution(str, Enum):
    #: Record it and move on. Advisory gates only: the observation informs the
    #: optimizer's strategy but must never trigger remediation by itself
    #: (review 4.9 -- a pre-placement estimate is not grounds for a rollback).
    RECORD_ONLY = "record_only"
    #: Re-run the responsible stage with a bounded config change.
    RETRY_STAGE = "retry_stage"
    #: Restore the checkpoint before the responsible stage and re-run forward.
    ROLLBACK = "rollback"
    #: Not a design problem. Fix the environment and re-run the same config.
    ENVIRONMENT_FIX = "environment_fix"
    #: The agent has no business fixing this. Stop and tell a human.
    ESCALATE = "escalate"

    def __str__(self) -> str:
        return self.value


#: Things the agent is never allowed to modify, referenced by taxonomy rows.
RTL_LOGIC = "rtl_functional_logic"
SDC_TARGETS = "sdc_constraint_targets"
PDK_FILES = "pdk_and_library_files"
CHECK_DECKS = "drc_lvs_antenna_decks"
EXTRACTED_NETLIST = "extracted_netlist"
TEMPLATES = "renderer_templates"
BUDGET = "iteration_budget"


@dataclass(frozen=True)
class TaxonomyEntry:
    failure: FailureClass
    root_causes: str
    evidence: str
    #: Stage whose config should change. None for non-design problems.
    responsible_stage: StageId | None
    resolution: Resolution
    forbids: tuple[str, ...] = ()
    #: Prefer the shallowest rollback consistent with evidence (review 9.1).
    escalate_to: StageId | None = None
    #: The target is whichever stage failed, not a fixed one. Used for classes
    #: like a bad rendered script, where "the responsible stage" is by
    #: definition the stage whose script was rejected.
    targets_failing_stage: bool = False
    notes: str = ""


TAXONOMY: tuple[TaxonomyEntry, ...] = (
    TaxonomyEntry(
        FailureClass.RTL_SYNTAX,
        "Malformed Verilog, missing files, unresolved includes",
        "Verilator error output",
        StageId.LINT,
        Resolution.RETRY_STAGE,
        forbids=(RTL_LOGIC,),
        notes="Mechanical syntax repair only, applied to the run's RTL copy.",
    ),
    TaxonomyEntry(
        FailureClass.RTL_FUNCTIONAL,
        "Design does the wrong thing; testbench assertion or $error fired",
        "Simulation log",
        None,
        Resolution.ESCALATE,
        forbids=(RTL_LOGIC,),
        notes="A functional bug is a human's call. Never auto-patch logic.",
    ),
    TaxonomyEntry(
        FailureClass.ELABORATION,
        "Unresolved module refs, parameter or width mismatch",
        "Yosys elaboration log",
        StageId.SYNTHESIS,
        Resolution.RETRY_STAGE,
        forbids=(PDK_FILES,),
    ),
    TaxonomyEntry(
        FailureClass.LIBRARY,
        "Missing or malformed Liberty/LEF, corrupt PDK install",
        "Tool load errors, missing-cell errors",
        None,
        Resolution.ESCALATE,
        forbids=(PDK_FILES,),
        notes="Never 'repair' a foundry file. Flag it and stop.",
    ),
    TaxonomyEntry(
        FailureClass.SDC,
        "Missing create_clock, unconstrained endpoints, unit mismatch",
        "SDC parser output, OpenSTA check_setup",
        StageId.SDC,
        Resolution.ROLLBACK,
        forbids=(RTL_LOGIC, SDC_TARGETS),
        notes="Correcting a genuinely missing constraint is allowed; relaxing a "
              "real target to make a check pass is not.",
    ),
    TaxonomyEntry(
        FailureClass.SYNTH_ERROR,
        "Yosys crash or unsupported construct",
        "Yosys exit code and log",
        StageId.SYNTHESIS,
        Resolution.RETRY_STAGE,
        forbids=(PDK_FILES,),
        notes="A crash is not a strategy problem; do not retune effort for it.",
    ),
    TaxonomyEntry(
        FailureClass.SYNTH_QOR,
        "Area or timing far off target despite a clean run",
        "Synthesis report metrics versus threshold",
        StageId.SYNTHESIS,
        Resolution.RETRY_STAGE,
        forbids=(RTL_LOGIC,),
        notes="Soft verdict. Adjust strategy/effort, never the RTL.",
    ),
    TaxonomyEntry(
        FailureClass.LEC_MISMATCH,
        "Netlist no longer functionally equivalent to RTL",
        "Yosys equiv_status unproven points",
        None,
        Resolution.ESCALATE,
        forbids=(RTL_LOGIC,),
        notes="Something changed function. Always a human decision.",
    ),
    TaxonomyEntry(
        FailureClass.TIMING_PRELAYOUT,
        "Estimate-only slack shortfall before placement exists",
        "Pre-layout STA report",
        None,
        Resolution.RECORD_ONLY,
        notes="Advisory only. Logged and fed to the optimizer; must never "
              "trigger an autonomous rollback by itself (review 4.9).",
    ),
    TaxonomyEntry(
        FailureClass.FLOORPLAN,
        "Illegal geometry, macro overlap, bad aspect ratio",
        "OpenROAD floorplan log",
        StageId.FLOORPLAN,
        Resolution.RETRY_STAGE,
    ),
    TaxonomyEntry(
        FailureClass.PDN,
        "IR-drop violation, insufficient strap coverage",
        "PDN analysis report",
        StageId.PDN,
        Resolution.RETRY_STAGE,
        forbids=(PDK_FILES,),
    ),
    TaxonomyEntry(
        FailureClass.PLACEMENT,
        "Illegal placement or placer crash",
        "OpenROAD placement log",
        StageId.PLACEMENT,
        Resolution.RETRY_STAGE,
        escalate_to=StageId.FLOORPLAN,
    ),
    TaxonomyEntry(
        FailureClass.CONGESTION,
        "Global-route overflow after placement",
        "GRT congestion/overflow report versus placement density map",
        StageId.PLACEMENT,
        Resolution.ROLLBACK,
        escalate_to=StageId.FLOORPLAN,
        notes="Localised overflow -> placement only. Uniformly high density "
              "across the core -> floorplan utilisation. Prefer the shallowest "
              "rollback and escalate only if it fails (review 9.1).",
    ),
    TaxonomyEntry(
        FailureClass.CTS,
        "Clock tree build failure or excessive buffering",
        "CTS log and clock tree report",
        StageId.CTS,
        Resolution.RETRY_STAGE,
        forbids=(RTL_LOGIC,),
    ),
    TaxonomyEntry(
        FailureClass.HOLD,
        "Short reg-to-reg paths, clock skew, insufficient useful skew",
        "Post-CTS or signoff STA hold report",
        StageId.CTS,
        Resolution.ROLLBACK,
        forbids=(RTL_LOGIC, SDC_TARGETS),
        notes="Hard rule: hold is never an RTL problem. Short-path signature -> "
              "CTS. Broad uniform signature -> clock uncertainty in SDC "
              "(review 9.3).",
    ),
    TaxonomyEntry(
        FailureClass.SETUP,
        "Long logic paths, weak drive, real interconnect delay",
        "Signoff STA setup report, delta versus pre-layout snapshot",
        StageId.PLACEMENT,
        Resolution.ROLLBACK,
        escalate_to=StageId.SYNTHESIS,
        forbids=(RTL_LOGIC, SDC_TARGETS),
        notes="Delta analysis decides: already near-critical pre-layout -> "
              "synthesis strategy. Only critical after real routing -> "
              "placement (review 9.2).",
    ),
    TaxonomyEntry(
        FailureClass.ROUTING,
        "In-route DRC violations, unroutable congestion",
        "OpenROAD routing log and DRC markers",
        StageId.ROUTING,
        Resolution.RETRY_STAGE,
        escalate_to=StageId.PLACEMENT,
        forbids=(PDK_FILES,),
    ),
    TaxonomyEntry(
        FailureClass.EXTRACTION,
        "Extraction tool failure or missing SPEF",
        "Extraction log",
        StageId.EXTRACTION,
        Resolution.ENVIRONMENT_FIX,
        notes="Tooling problem, not a design problem.",
    ),
    TaxonomyEntry(
        FailureClass.DRC,
        "Spacing/width/enclosure rule violations",
        "KLayout DRC report, per-category counts",
        StageId.ROUTING,
        Resolution.ROLLBACK,
        forbids=(CHECK_DECKS,),
        notes="Fix the geometry, never the deck.",
    ),
    TaxonomyEntry(
        FailureClass.LVS_PHYSICAL,
        "Short or open tied to a specific (x,y) location",
        "LVS mismatch coordinates cross-checked against the DEF",
        StageId.ROUTING,
        Resolution.ROLLBACK,
        forbids=(CHECK_DECKS, EXTRACTED_NETLIST),
    ),
    TaxonomyEntry(
        FailureClass.LVS_LIBRARY,
        "Same mismatch repeats on every instance of one cell: LEF/GDS disagree",
        "LVS report grouped by cell type",
        None,
        Resolution.ESCALATE,
        forbids=(PDK_FILES, EXTRACTED_NETLIST),
        notes="Library integrity problem. Not a design bug and not auto-fixable "
              "(review 9.4).",
    ),
    TaxonomyEntry(
        FailureClass.LVS_STRUCTURAL,
        "Devices missing/extra globally with no location: netlist export desync",
        "LVS report with no spatial clustering",
        StageId.ROUTING,
        Resolution.RETRY_STAGE,
        forbids=(EXTRACTED_NETLIST,),
        notes="Usually an ECO that updated the database but not the exported "
              "netlist. Re-run the export; escalate if it recurs.",
    ),
    TaxonomyEntry(
        FailureClass.ANTENNA,
        "Long metal runs without diode protection",
        "Antenna check report",
        StageId.ROUTING,
        Resolution.RETRY_STAGE,
        forbids=(CHECK_DECKS,),
    ),
    TaxonomyEntry(
        FailureClass.GDS,
        "Stream-out failure, unresolved cell reference, empty top cell",
        "KLayout streamout log and the written GDS",
        StageId.GDSOUT,
        Resolution.RETRY_STAGE,
    ),
    TaxonomyEntry(
        FailureClass.TCL_CONFIG,
        "Rendered script rejected by the tool's parser, or bad schema value",
        "Tool parse error at invocation",
        None,  # resolved at runtime to whichever stage's script was rejected
        Resolution.RETRY_STAGE,
        targets_failing_stage=True,
        forbids=(TEMPLATES,),
        notes="Fix the IR value that produced it. A broken template is a system "
              "bug to escalate, not a design iteration.",
    ),
    TaxonomyEntry(
        FailureClass.TOOL_RUNTIME,
        "OOM, timeout, segfault",
        "Exit code and system logs",
        None,
        Resolution.ENVIRONMENT_FIX,
        notes="Re-run the same config with more resources. A crash is not a "
              "design problem.",
    ),
    TaxonomyEntry(
        FailureClass.ENVIRONMENT,
        "Wrong PDK path, missing tool, version mismatch",
        "Startup and setup errors",
        None,
        Resolution.ESCALATE,
        forbids=(PDK_FILES,),
    ),
)

_BY_CLASS: dict[FailureClass, TaxonomyEntry] = {e.failure: e for e in TAXONOMY}


def lookup(failure: FailureClass | str) -> TaxonomyEntry:
    key = failure if isinstance(failure, FailureClass) else FailureClass(failure)
    return _BY_CLASS[key]


def responsible_stage(
    failure: FailureClass | str,
    *,
    escalated: bool = False,
    failing_stage: StageId | None = None,
) -> StageId | None:
    """Resolve which stage should change. This replaces the drawn arrows.

    ``escalated`` asks for the deeper target, used only after the shallow fix
    has already been tried and failed (review 9.1 step 4). ``failing_stage``
    supplies the dynamic target for classes whose responsible stage is by
    definition the one that just failed.
    """
    entry = lookup(failure)
    if escalated and entry.escalate_to is not None:
        return entry.escalate_to
    if entry.targets_failing_stage:
        return failing_stage
    return entry.responsible_stage


def forbidden_targets(failure: FailureClass | str) -> tuple[str, ...]:
    return lookup(failure).forbids


def is_autonomous(failure: FailureClass | str) -> bool:
    """False when this class must go to a human instead of being retried."""
    return lookup(failure).resolution is not Resolution.ESCALATE


@dataclass
class Diagnosis:
    """What the agent proposes. It never sets a verdict (review 14.1)."""

    failure: FailureClass
    evidence: str
    implicated_stage: StageId | None
    confidence: float
    reasoning: str = ""
    #: Bounded IR delta the agent wants applied to the implicated stage.
    config_delta: dict[str, object] = field(default_factory=dict)
    #: Typed executable actions. Models may set bounded IR or patch the private
    #: RTL copy for deterministic syntax failures; trusted code validates both.
    recommended_actions: list[dict[str, object]] = field(default_factory=list)
    escalated: bool = False

    @property
    def resolution(self) -> Resolution:
        return lookup(self.failure).resolution

    def to_dict(self) -> dict[str, object]:
        return {
            "failure_class": self.failure.value,
            "evidence": self.evidence,
            "implicated_stage": self.implicated_stage.value if self.implicated_stage else None,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "config_delta": self.config_delta,
            "recommended_actions": self.recommended_actions,
            "resolution": self.resolution.value,
            "escalated": self.escalated,
        }
