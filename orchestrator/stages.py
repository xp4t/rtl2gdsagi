"""Flow stage definitions and ordering."""
from enum import Enum, auto


class Stage(str, Enum):
    """RTL-to-GDS flow stages in execution order."""
    LINT            = "lint"
    SYNTHESIS       = "synthesis"
    SDC_CHECK       = "sdc_check"
    POST_SYNTH_STA  = "post_synth_sta"
    FLOORPLAN       = "floorplan"
    PLACEMENT       = "placement"
    POST_PLACE_STA  = "post_place_sta"
    CTS             = "cts"
    POST_CTS_STA    = "post_cts_sta"
    ROUTING         = "routing"
    POST_ROUTE_STA  = "post_route_sta"
    DRC             = "drc"
    LVS             = "lvs"
    GDS             = "gds"

    def next_stage(self) -> "Stage | None":
        """Return the next stage in the flow, or None if this is the last."""
        stages = list(Stage)
        idx = stages.index(self)
        return stages[idx + 1] if idx + 1 < len(stages) else None


STAGE_ORDER: list[Stage] = list(Stage)

# Stages that must pass hard gates — DRC/LVS/signoff STA failures always
# escalate or retry; they cannot silently continue.
HARD_GATE_STAGES: set[Stage] = {
    Stage.DRC,
    Stage.LVS,
    Stage.POST_ROUTE_STA,
    Stage.POST_SYNTH_STA,
}

# Stages that support parallel strategy sweeps
SWEEPABLE_STAGES: set[Stage] = {
    Stage.SYNTHESIS,
    Stage.FLOORPLAN,
    Stage.PLACEMENT,
    Stage.CTS,
    Stage.ROUTING,
}

# Human-readable labels
STAGE_LABELS: dict[Stage, str] = {
    Stage.LINT:           "Lint (Verilator)",
    Stage.SYNTHESIS:      "Synthesis (Yosys/OpenLane2)",
    Stage.SDC_CHECK:      "SDC Constraint Check",
    Stage.POST_SYNTH_STA: "Post-Synthesis STA (OpenSTA)",
    Stage.FLOORPLAN:      "Floorplan",
    Stage.PLACEMENT:      "Placement",
    Stage.POST_PLACE_STA: "Post-Placement STA (OpenSTA)",
    Stage.CTS:            "Clock Tree Synthesis",
    Stage.POST_CTS_STA:   "Post-CTS STA (OpenSTA)",
    Stage.ROUTING:        "Global + Detailed Routing",
    Stage.POST_ROUTE_STA: "Post-Route STA (with parasitics)",
    Stage.DRC:            "DRC (Magic/KLayout)",
    Stage.LVS:            "LVS (Netgen)",
    Stage.GDS:            "GDS Output",
}
