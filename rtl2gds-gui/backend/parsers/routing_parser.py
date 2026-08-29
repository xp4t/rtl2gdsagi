from __future__ import annotations

from .placement_parser import PlacementParser


class RoutingParser(PlacementParser):
    source = "openroad"
    stage_keywords = ("route", "routing")
