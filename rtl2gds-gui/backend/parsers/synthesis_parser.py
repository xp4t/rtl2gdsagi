from __future__ import annotations

import re

from .base_parser import NUMBER_PATTERN, BaseParser, NormalizedEvent


class SynthesisParser(BaseParser):
    source = "yosys"
    stage_keywords = ("synth", "elaborat")

    _area_patterns = (
        re.compile(
            rf"\bchip\s+area\s+for\s+module\b.*?[:=]\s*(?P<value>{NUMBER_PATTERN})",
            re.IGNORECASE,
        ),
        re.compile(
            rf"\b(?:design|total\s+cell)\s+area\b\s*[:=]\s*(?P<value>{NUMBER_PATTERN})"
            rf"\s*(?P<unit>um\^?2|µm²)?",
            re.IGNORECASE,
        ),
    )

    def parse_line(self, line: str, stage: str, stream: str) -> list[NormalizedEvent]:
        result = self.first_number(self._area_patterns, line)
        if not result:
            return []
        value, _ = result
        return [self.metric("area", value, "um2", stage)]
