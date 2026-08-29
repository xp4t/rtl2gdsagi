from __future__ import annotations

from collections import defaultdict

from .artifact_parser import ArtifactParser
from .base_parser import BaseParser, NormalizedEvent
from .placement_parser import PlacementParser
from .routing_parser import RoutingParser
from .signoff_parser import SignoffParser
from .synthesis_parser import SynthesisParser
from .timing_parser import TimingParser


class ParserPipeline:
    """Incrementally frames process chunks and routes complete lines to parsers."""

    def __init__(self, parsers: list[BaseParser] | None = None) -> None:
        self._parsers = parsers or [
            TimingParser(),
            SynthesisParser(),
            PlacementParser(),
            RoutingParser(),
            SignoffParser(),
            ArtifactParser(),
        ]
        self._buffers: dict[tuple[str, str], str] = defaultdict(str)

    def feed(self, chunk: str, *, stage: str, stream: str = "stdout") -> list[NormalizedEvent]:
        if not isinstance(chunk, str) or not chunk:
            return []
        key = (stage, stream)
        self._buffers[key] += chunk
        events: list[NormalizedEvent] = []
        while "\n" in self._buffers[key]:
            line, self._buffers[key] = self._buffers[key].split("\n", 1)
            events.extend(self.parse_line(line.rstrip("\r"), stage=stage, stream=stream))
        return events

    def flush(self, *, stage: str | None = None, stream: str | None = None) -> list[NormalizedEvent]:
        events: list[NormalizedEvent] = []
        keys = [
            key
            for key in self._buffers
            if (stage is None or key[0] == stage) and (stream is None or key[1] == stream)
        ]
        for key in keys:
            line = self._buffers.pop(key)
            if line:
                events.extend(self.parse_line(line.rstrip("\r"), stage=key[0], stream=key[1]))
        return events

    def reset(self) -> None:
        self._buffers.clear()

    def parse_line(self, line: str, *, stage: str, stream: str = "stdout") -> list[NormalizedEvent]:
        events: list[NormalizedEvent] = []
        seen: set[tuple] = set()
        matching = [parser for parser in self._parsers if parser.supports_stage(stage)]
        # Unknown/custom stage labels still benefit from all tool formats.
        if len(matching) <= 2:
            matching = self._parsers
        for parser in matching:
            try:
                parsed = parser.parse(line, stage, stream)
            except Exception:
                parsed = []
            for event in parsed:
                identity = (
                    type(event).__name__,
                    getattr(event, "name", getattr(event, "path", "")),
                    getattr(event, "value", ""),
                    getattr(event, "source", ""),
                )
                if identity not in seen:
                    seen.add(identity)
                    events.append(event)
        return events
