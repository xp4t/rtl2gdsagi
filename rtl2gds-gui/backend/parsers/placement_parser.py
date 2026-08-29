from __future__ import annotations

import re

from .base_parser import NUMBER_PATTERN, BaseParser, NormalizedEvent, parse_duration


class PlacementParser(BaseParser):
    source = "openroad"
    stage_keywords = ("place", "placement", "floorplan", "power_plan", "cts")

    _utilization_patterns = (
        re.compile(
            rf"\b(?:utilization|density)\b\s*[:=]\s*(?P<value>{NUMBER_PATTERN})\s*(?P<unit>%|percent)?",
            re.IGNORECASE,
        ),
    )
    _peak_congestion_patterns = (
        re.compile(
            rf"\bpeak\s+(?:routing\s+)?congestion\b\s*[:=]\s*(?P<value>{NUMBER_PATTERN})\s*(?P<unit>%|percent)?",
            re.IGNORECASE,
        ),
    )
    _total_congestion_patterns = (
        re.compile(
            rf"(?<!peak\s)(?<!routing\s)\b(?:total\s+)?congestion\b\s*[:=]\s*"
            rf"(?P<value>{NUMBER_PATTERN})\s*(?P<unit>%|percent)?",
            re.IGNORECASE,
        ),
    )
    _area_patterns = (
        re.compile(
            rf"\b(?:design|core|total\s+cell)\s+area\b\s*[:=]\s*(?P<value>{NUMBER_PATTERN})"
            rf"\s*(?P<unit>um\^?2|µm²)?",
            re.IGNORECASE,
        ),
    )
    _power_patterns = (
        re.compile(
            rf"\b(?:total\s+)?power\b\s*[:=]\s*(?P<value>{NUMBER_PATTERN})\s*"
            rf"(?P<unit>mw|uw|w)?\b",
            re.IGNORECASE,
        ),
    )
    _runtime_patterns = (
        re.compile(
            rf"\b(?:stage\s+)?(?:runtime|elapsed)\b\s*[:=]\s*"
            rf"(?P<value>\d{{1,3}}:\d{{2}}(?::\d{{2}}(?:\.\d+)?)?|{NUMBER_PATTERN})\s*"
            rf"(?P<unit>ms|s|sec(?:onds?)?|min(?:utes?)?)?",
            re.IGNORECASE,
        ),
    )

    def parse_line(self, line: str, stage: str, stream: str) -> list[NormalizedEvent]:
        events: list[NormalizedEvent] = []
        peak = self.first_number(self._peak_congestion_patterns, line)
        if peak:
            events.append(self.metric("peak_congestion", self._ratio(peak), "ratio", stage))

        total = self.first_number(self._total_congestion_patterns, line)
        if total:
            events.append(self.metric("total_congestion", self._ratio(total), "ratio", stage))

        utilization = self.first_number(self._utilization_patterns, line)
        if utilization:
            value, unit = utilization
            if unit or abs(value) > 1:
                normalized = value
            else:
                normalized = value * 100
            events.append(self.metric("utilization", normalized, "%", stage))

        area = self.first_number(self._area_patterns, line)
        if area:
            events.append(self.metric("area", area[0], "um2", stage))

        power = self.first_number(self._power_patterns, line)
        if power:
            value, unit = power
            normalized_unit = unit.lower()
            if normalized_unit == "w":
                value *= 1000
            elif normalized_unit == "uw":
                value /= 1000
            events.append(self.metric("power", value, "mW", stage))

        for pattern in self._runtime_patterns:
            match = pattern.search(line)
            if not match:
                continue
            seconds = parse_duration(match.group("value"), match.group("unit") or "")
            if seconds is not None:
                events.append(self.metric("stage_runtime", seconds, "s", stage))
            break
        return events

    @staticmethod
    def _ratio(result: tuple[float, str]) -> float:
        value, unit = result
        return value / 100 if unit or abs(value) > 1 else value
