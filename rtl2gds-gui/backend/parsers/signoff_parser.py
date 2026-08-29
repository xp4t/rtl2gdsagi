from __future__ import annotations

import re

from .base_parser import NUMBER_PATTERN, BaseParser, NormalizedEvent


class SignoffParser(BaseParser):
    source = "signoff"
    stage_keywords = ("signoff", "drc", "lvs", "gds")

    _drc_patterns = (
        re.compile(
            rf"\b(?:total\s+)?drc\s+(?:violations?|errors?)\b\s*[:=]\s*(?P<value>{NUMBER_PATTERN})",
            re.IGNORECASE,
        ),
        re.compile(
            rf"\bdrc\b.*?\b(?:count|total)\b\s*[:=]\s*(?P<value>{NUMBER_PATTERN})",
            re.IGNORECASE,
        ),
    )
    _lvs_pass = re.compile(
        r"\b(?:lvs\s*(?:pass(?:ed)?|clean)|netlists?\s+match|circuits?\s+match\s+uniquely)\b",
        re.IGNORECASE,
    )
    _lvs_fail = re.compile(
        r"\b(?:lvs\s*(?:fail(?:ed)?|mismatch)|netlists?\s+(?:do\s+not|don't)\s+match|circuits?\s+do\s+not\s+match)\b",
        re.IGNORECASE,
    )
    _power_patterns = (
        re.compile(
            rf"\b(?:total\s+)?power\b\s*[:=]\s*(?P<value>{NUMBER_PATTERN})\s*"
            rf"(?P<unit>mw|uw|w)?\b",
            re.IGNORECASE,
        ),
    )

    def parse_line(self, line: str, stage: str, stream: str) -> list[NormalizedEvent]:
        events: list[NormalizedEvent] = []
        drc = self.first_number(self._drc_patterns, line)
        if drc:
            events.append(self.metric("drc_violations", int(drc[0]), "count", stage, source="drc"))
        if self._lvs_fail.search(line):
            events.append(self.metric("lvs_status", "fail", "status", stage, source="lvs"))
        elif self._lvs_pass.search(line):
            events.append(self.metric("lvs_status", "pass", "status", stage, source="lvs"))
        power = self.first_number(self._power_patterns, line)
        if power:
            value, unit = power
            if unit.lower() == "w":
                value *= 1000
            elif unit.lower() == "uw":
                value /= 1000
            events.append(self.metric("power", value, "mW", stage, source="power"))
        return events
