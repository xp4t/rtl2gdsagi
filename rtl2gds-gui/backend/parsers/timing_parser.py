from __future__ import annotations

import re

from .base_parser import NUMBER_PATTERN, BaseParser, NormalizedEvent


class TimingParser(BaseParser):
    source = "sta"

    _wns_patterns = (
        re.compile(
            rf"\b(?:wns|worst\s+negative\s+slack)\b\s*(?:\([^)]*\))?\s*[:=]?\s*"
            rf"(?P<value>{NUMBER_PATTERN})\s*(?P<unit>ns|ps)?\b",
            re.IGNORECASE,
        ),
    )
    _tns_patterns = (
        re.compile(
            rf"\b(?:tns|total\s+negative\s+slack)\b\s*(?:\([^)]*\))?\s*[:=]?\s*"
            rf"(?P<value>{NUMBER_PATTERN})\s*(?P<unit>ns|ps)?\b",
            re.IGNORECASE,
        ),
    )

    def parse_line(self, line: str, stage: str, stream: str) -> list[NormalizedEvent]:
        events: list[NormalizedEvent] = []
        for name, patterns in (("wns", self._wns_patterns), ("tns", self._tns_patterns)):
            result = self.first_number(patterns, line)
            if not result:
                continue
            value, unit = result
            if unit.lower() == "ps":
                value /= 1000
            events.append(self.metric(name, value, "ns", stage))
        return events
