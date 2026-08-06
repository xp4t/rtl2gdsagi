"""Log/report parsers — one per EDA stage output.

All parsers return a normalised JSON-compatible dict and RAISE on
unrecognised log formats (never silently return a false-clean result).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orchestrator.stages import Stage

from .lint_parser import LintParser
from .synth_parser import SynthParser
from .sta_parser import STAParser
from .drc_parser import DRCParser
from .lvs_parser import LVSParser
from .sdc_parser import SDCParser


def get_parser(stage: "Stage"):
    """Return the appropriate parser for *stage*."""
    from orchestrator.stages import Stage
    _map = {
        Stage.LINT:           LintParser(),
        Stage.SYNTHESIS:      SynthParser(),
        Stage.SDC_CHECK:      SDCParser(),
        Stage.POST_SYNTH_STA: STAParser(stage_name="post_synth_sta"),
        Stage.POST_PLACE_STA: STAParser(stage_name="post_place_sta"),
        Stage.POST_CTS_STA:   STAParser(stage_name="post_cts_sta"),
        Stage.POST_ROUTE_STA: STAParser(stage_name="post_route_sta"),
        Stage.DRC:            DRCParser(),
        Stage.LVS:            LVSParser(),
        # Physical stages without specialised parsers yet — use generic
        Stage.FLOORPLAN:      SynthParser(),   # reads utilisation
        Stage.PLACEMENT:      SynthParser(),
        Stage.CTS:            SynthParser(),
        Stage.ROUTING:        SynthParser(),
        Stage.GDS:            SynthParser(),
    }
    parser = _map.get(stage)
    if parser is None:
        raise KeyError(f"No parser registered for stage {stage!r}")
    return parser
