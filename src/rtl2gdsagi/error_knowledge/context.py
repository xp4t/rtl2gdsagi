from __future__ import annotations

import re
from pathlib import Path
from typing import Any

PDN_WIDTH = re.compile(
    r"Insufficient width\s*\(([\d.]+)\s*um\).*?layer\s+(\S+).*?"
    r"total strap width\s+([\d.]+)\s*um\s+and offset\s+([\d.]+)\s*um",
    re.IGNORECASE,
)
DIEAREA = re.compile(r"^DIEAREA\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)", re.MULTILINE)
UNITS = re.compile(r"UNITS\s+DISTANCE\s+MICRONS\s+(\d+)")


def floorplan_dimensions(path: Path | None) -> tuple[float, float] | None:
    if path is None or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    area, units = DIEAREA.search(text), UNITS.search(text)
    if not area:
        return None
    scale = float(units.group(1)) if units else 1000.0
    return ((int(area.group(3)) - int(area.group(1))) / scale,
            (int(area.group(4)) - int(area.group(2))) / scale)


def pdn_context(log: str, *, facts: dict[str, Any], history: list[dict[str, Any]],
                ir: Any, floorplan_def: Path | None = None) -> dict[str, Any]:
    match = PDN_WIDTH.search(log)
    parsed: dict[str, Any] = {}
    if match:
        parsed.update(available_width_um=float(match.group(1)), strap_layer=match.group(2),
                      total_strap_width_um=float(match.group(3)),
                      configured_offset_um=float(match.group(4)))
        parsed["required_width_um"] = parsed["total_strap_width_um"] + parsed["configured_offset_um"]
    synth = next((h for h in reversed(history) if h.get("stage") == "synthesis"), {})
    metrics = synth.get("metrics") or {}
    dims = floorplan_dimensions(floorplan_def)
    parsed.update({
        "top": facts.get("top", "design"),
        "rtl_kind": "tiny sequential block" if facts.get("always_blocks", 0) and int(metrics.get("cells") or 0) < 100 else "logic block",
        "synthesized_cells": metrics.get("cells"),
        "standard_cell_area_um2": metrics.get("area_um2"),
        "core_dimensions_um": dims,
        "core_utilization": ir.get("floorplan", "core_utilization"),
        "strap_width_um": ir.get("pdn", "strap_width_um"),
        "strap_pitch_um": ir.get("pdn", "strap_pitch_um"),
        "strap_offset_um": ir.get("pdn", "strap_offset_um"),
        "core_ring": ir.get("pdn", "core_ring"),
    })
    return parsed
