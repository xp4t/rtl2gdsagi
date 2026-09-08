from __future__ import annotations

import re

from .models import ToolMessage
from .openroad_catalog import OpenRoadCatalog

MESSAGE = re.compile(r"\[(?P<severity>ERROR|WARNING|WARN|INFO|CRITICAL)\s+(?P<id>[A-Z]{3}-\d{4})\]\s*(?P<text>[^\n\r]*)")


def match_openroad_messages(log: str, catalog: OpenRoadCatalog | None = None) -> list[ToolMessage]:
    catalog = catalog or OpenRoadCatalog()
    out: list[ToolMessage] = []
    for match in MESSAGE.finditer(log):
        known = catalog.get(match.group("id"))
        if known is None:
            continue  # fail closed: an unknown ID is never represented as catalogued
        out.append(ToolMessage(
            tool=known.tool, subsystem=known.subsystem, code=known.code,
            severity=known.severity, raw_message=match.group("text").strip(),
            canonical_id=known.canonical_id, source_file=known.source_file,
            source_line=known.source_line, canonical_message=known.canonical_message,
            documentation=known.documentation,
        ))
    return out
