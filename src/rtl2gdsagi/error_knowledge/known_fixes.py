from __future__ import annotations

from typing import Any

from ..stages import StageId
from .models import FailureKnowledge, Repairability, ToolMessage


def _pdn_0185(message: ToolMessage, context: dict[str, Any]) -> FailureKnowledge:
    available = float(context.get("available_width_um") or 0.0)
    total = float(context.get("total_strap_width_um") or (2 * float(context["strap_width_um"])))
    offset = float(context.get("configured_offset_um") or context["strap_offset_um"])
    util = float(context["core_utilization"])
    delta: dict[str, dict[str, Any]] = {}

    # Preserve at least 0.5um edge clearance.  If the first pair can fit by
    # moving it inward, derive the new offset from the measured free width.
    fit_offset = max(0.0, available - total - 0.5)
    if available and fit_offset < offset:
        delta.setdefault("pdn", {})["strap_offset_um"] = round(max(0.5, fit_offset), 3)

    required = total + max(0.5, min(offset, fit_offset if available else offset)) + 0.5
    if available and available < required:
        # Core linear dimension grows approximately with 1/sqrt(utilization).
        # Add 10% margin so rounding/site snapping does not land on the edge.
        derived = util * (available / (required * 1.10)) ** 2
        delta.setdefault("floorplan", {})["core_utilization"] = round(max(0.05, min(util - 0.01, derived)), 2)
    elif util > 0.30 and available and available < max(20.0, 3 * total):
        delta.setdefault("floorplan", {})["core_utilization"] = round(max(0.05, util * 0.85), 2)

    if available and float(context["strap_pitch_um"]) > available:
        # Pitch is the distance between repeated strap sets, not the width of
        # the first set.  Making it nearly the full core width can leave only
        # one polarity on a layer.  Ten microns is the repository's captured
        # small-block seed; retain it as a lower bound while deriving a value
        # from half the measured span.
        delta.setdefault("pdn", {})["strap_pitch_um"] = round(
            min(float(context["strap_pitch_um"]), max(10.0, available / 2.0)), 3)
    if context.get("core_ring") and available and available < 4 * total:
        delta.setdefault("pdn", {})["core_ring"] = False

    cells = context.get("synthesized_cells")
    area = context.get("standard_cell_area_um2")
    dims = context.get("core_dimensions_um")
    detail = f"Your {context.get('top', 'design')} is a {context.get('rtl_kind', 'small block')}"
    if cells is not None:
        detail += f" with {cells} mapped cells"
    if area is not None:
        detail += f" occupying {area:g} um^2 of standard-cell area"
    if dims:
        detail += f". Its floorplan is {dims[0]:.2f} x {dims[1]:.2f} um"
    detail += (
        f". OpenROAD measured only {available:g} um for the {context.get('strap_layer', 'power')} "
        f"strap geometry, while the pair consumes {total:g} um before the {offset:g} um offset. "
        "The RTL is not functionally implicated; the generated physical geometry does not fit."
    )
    rollback = StageId.FLOORPLAN if "floorplan" in delta else StageId.PDN
    return FailureKnowledge(
        key="PDN-0185", tool="OpenROAD", title="PDN strap geometry does not fit",
        explanation="OpenROAD cannot place the configured power-strap pair inside the available grid width.",
        likely_causes=("very small synthesized block", "floorplan utilization leaves a narrow core",
                       "strap offset/width/pitch or core ring consumes the available span"),
        design_context_explanation=detail, repair_class="pdn_geometry",
        repairability=Repairability.DETERMINISTIC,
        allowed_actions=("SET_IR_VALUE",), earliest_rollback_stage=rollback,
        references=(message.source_file + (f":{message.source_line}" if message.source_line else ""),),
        proposed_delta=delta, evidence=context,
    )


def lookup_known_fix(message: ToolMessage, context: dict[str, Any]) -> FailureKnowledge | None:
    if message.canonical_id == "PDN-0185":
        return _pdn_0185(message, context)
    return None


def has_curated_fix(canonical_id: str) -> bool:
    return canonical_id.upper() == "PDN-0185"
