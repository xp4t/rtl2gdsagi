from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Iterable

from .models import ToolMessage


@dataclass(frozen=True)
class CatalogMetadata:
    revision: str
    retrieved_at: str
    upstream: str


class OpenRoadCatalog:
    def __init__(self, payload: dict | None = None) -> None:
        if payload is None:
            resource = files("rtl2gdsagi.resources").joinpath("openroad_messages.json")
            payload = json.loads(resource.read_text(encoding="utf-8"))
        raw = payload.get("messages")
        if payload.get("schema_version") != 1 or not isinstance(raw, list):
            raise ValueError("invalid OpenROAD message catalog")
        self.metadata = CatalogMetadata(str(payload.get("revision", "")),
                                        str(payload.get("retrieved_at", "")),
                                        str(payload.get("upstream", "")))
        self._messages: dict[str, ToolMessage] = {}
        for item in raw:
            key = str(item["id"]).upper()
            if key in self._messages:
                raise ValueError(f"duplicate OpenROAD message ID {key}")
            self._messages[key] = ToolMessage(
                tool="OpenROAD", subsystem=str(item["tool"]), code=int(item["code"]),
                severity=str(item["severity"]), raw_message="", canonical_id=key,
                source_file=str(item.get("source_file", "")),
                source_line=int(item["source_line"]) if item.get("source_line") else None,
                canonical_message=str(item.get("message", "")),
                documentation=str(item.get("documentation", "")),
            )

    def get(self, canonical_id: str) -> ToolMessage | None:
        return self._messages.get(canonical_id.upper())

    def require(self, canonical_id: str) -> ToolMessage:
        item = self.get(canonical_id)
        if item is None:
            raise KeyError(f"unknown OpenROAD message ID {canonical_id}")
        return item

    def query(self, *, tool: str | None = None, search: str | None = None,
              failures_only: bool = False) -> list[ToolMessage]:
        values: Iterable[ToolMessage] = self._messages.values()
        if tool:
            values = (m for m in values if m.subsystem.upper() == tool.upper())
        if failures_only:
            values = (m for m in values if m.severity in {"WARN", "ERROR", "CRITICAL"})
        if search:
            needle = search.casefold()
            values = (m for m in values if needle in (m.canonical_id + " " + m.canonical_message + " " + m.documentation).casefold())
        return list(values)

    def __len__(self) -> int:
        return len(self._messages)
