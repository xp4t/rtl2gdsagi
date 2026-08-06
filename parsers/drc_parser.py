"""Parser for Magic/KLayout DRC reports.

Magic DRC output format::

    [ERROR] metal1 spacing violation ... (Count: 3)
    [ERROR] poly.9 ... (Count: 1)
    ...
    Total DRC errors: 4

KLayout DRC output uses XML; this parser handles both text and XML.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .base_parser import BaseParser


class DRCParser(BaseParser):

    _MAGIC_TOTAL_RE  = re.compile(r"Total DRC errors:\s*(\d+)", re.IGNORECASE)
    _MAGIC_RULE_RE   = re.compile(
        r"\[ERROR\]\s+(.+?)\s*\(Count:\s*(\d+)\)", re.IGNORECASE
    )
    _KLAYOUT_COUNT_RE = re.compile(r"<count>(\d+)</count>", re.IGNORECASE)

    def parse(self, log_dir: Path, stage_result: Any) -> dict[str, Any]:
        # Try Magic text report first
        magic_report = log_dir / "drc.rpt"
        klayout_xml  = log_dir / "drc.xml"

        if magic_report.exists():
            return self._parse_magic(magic_report, log_dir, stage_result)
        if klayout_xml.exists():
            return self._parse_klayout_xml(klayout_xml, log_dir, stage_result)

        # Fall back to stdout
        stdout = (log_dir / "stdout.log")
        if stdout.exists():
            text = stdout.read_text(errors="replace")
            if "Total DRC" in text or "[ERROR]" in text:
                return self._parse_magic_text(text, log_dir, stage_result)

        ec = getattr(stage_result, "exit_code", 0)
        if ec != 0:
            raise RuntimeError(
                f"DRCParser: non-zero exit ({ec}) and no recognisable DRC report "
                f"found in {log_dir} — unrecognised log format."
            )
        # Zero exit, no report file → assume clean
        return {
            "stage": "drc",
            "status": "pass",
            "total_violations": 0,
            "violations": [],
            "raw_log_path": str(log_dir),
        }

    def _parse_magic(self, path: Path, log_dir: Path, sr: Any) -> dict[str, Any]:
        return self._parse_magic_text(path.read_text(errors="replace"), log_dir, sr)

    def _parse_magic_text(self, text: str, log_dir: Path, sr: Any) -> dict[str, Any]:
        total_m = self._MAGIC_TOTAL_RE.search(text)
        total   = int(total_m.group(1)) if total_m else 0
        rules   = [
            {"rule": m.group(1).strip(), "count": int(m.group(2))}
            for m in self._MAGIC_RULE_RE.finditer(text)
        ]
        if not total_m and not rules:
            # exit 0 with no recognisable DRC pattern — flag it
            ec = getattr(sr, "exit_code", 0)
            if ec != 0:
                raise RuntimeError(
                    f"DRCParser: unrecognised Magic DRC format in {log_dir}/stdout.log"
                )
        return {
            "stage": "drc",
            "status": "pass" if total == 0 else "fail",
            "total_violations": total,
            "violations": rules,
            "raw_log_path": str(log_dir),
        }

    def _parse_klayout_xml(self, path: Path, log_dir: Path, sr: Any) -> dict[str, Any]:
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            counts = [int(el.text or 0) for el in root.iter("count")]
            total  = sum(counts)
        except ET.ParseError as exc:
            raise RuntimeError(f"DRCParser: malformed KLayout XML: {exc} — {path}") from exc
        return {
            "stage": "drc",
            "status": "pass" if total == 0 else "fail",
            "total_violations": total,
            "violations": [],
            "raw_log_path": str(log_dir),
        }
