from __future__ import annotations

import re
from pathlib import Path

from .base_parser import ArtifactUpdate, BaseParser, NormalizedEvent


class ArtifactParser(BaseParser):
    source = "process"

    _path_pattern = re.compile(
        r"(?P<path>(?:[A-Za-z]:)?[^\s\"'=<>()\[\],;]+?\."
        r"(?:log|rpt|report|v|vg|def|spef|sdc|gds|gdsii)(?:\.gz)?)\b",
        re.IGNORECASE,
    )

    def parse_line(self, line: str, stage: str, stream: str) -> list[NormalizedEvent]:
        events: list[NormalizedEvent] = []
        seen: set[str] = set()
        for match in self._path_pattern.finditer(line):
            path = match.group("path").rstrip(".:")
            if path in seen:
                continue
            seen.add(path)
            events.append(ArtifactUpdate(
                artifact_type=self._artifact_type(path),
                path=path,
                stage=stage,
                source=self.source,
            ))
        return events

    @staticmethod
    def _artifact_type(path: str) -> str:
        lowered = path.lower()
        name = Path(lowered).name
        if "timing" in name or "sta" in name:
            return "timing_report"
        if "congestion" in name:
            return "congestion_report"
        if "drc" in name:
            return "drc_report"
        if "lvs" in name:
            return "lvs_report"
        suffixes = {
            ".log": "log",
            ".rpt": "report",
            ".report": "report",
            ".v": "netlist",
            ".vg": "netlist",
            ".def": "def",
            ".spef": "spef",
            ".sdc": "sdc",
            ".gds": "gds",
            ".gdsii": "gds",
        }
        stem = lowered.removesuffix(".gz")
        return next((kind for suffix, kind in suffixes.items() if stem.endswith(suffix)), "artifact")
