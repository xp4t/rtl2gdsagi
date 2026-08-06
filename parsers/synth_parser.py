"""Parser for Yosys synthesis statistics (OpenLane2 synth log)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .base_parser import BaseParser


class SynthParser(BaseParser):
    """Parse Yosys synthesis statistics and OpenLane2 utilisation reports.

    Yosys prints a ``Printing statistics.`` section::

        === riscv_alu ===
           Number of wires:              245
           Number of cells:              198
             sky130_fd_sc_hd__buf_1        12
             ...
           Chip area for module '\\riscv_alu': 1245.678000
    """

    _CELLS_RE   = re.compile(r"Number of cells:\s+(\d+)", re.IGNORECASE)
    _WIRES_RE   = re.compile(r"Number of wires:\s+(\d+)", re.IGNORECASE)
    _AREA_RE    = re.compile(r"Chip area.*?:\s+([\d.]+)", re.IGNORECASE)
    _UTIL_RE    = re.compile(r"Design Utilization:\s+([\d.]+)%?", re.IGNORECASE)
    # OpenLane2 JSON stat file (preferred over text parsing)
    _STAT_FILE  = "synthesis/synthesis.stat.json"

    def parse(self, log_dir: Path, stage_result: Any) -> dict[str, Any]:
        text = ""
        # Try reading the Yosys stat section from stdout
        stdout_path = log_dir / "stdout.log"
        if stdout_path.exists():
            text = stdout_path.read_text(errors="replace")

        cells   = self._extract_int(self._CELLS_RE, text)
        wires   = self._extract_int(self._WIRES_RE, text)
        area    = self._extract_float(self._AREA_RE, text)
        util    = self._extract_float(self._UTIL_RE, text)

        ec = getattr(stage_result, "exit_code", 0)
        status = "pass" if ec == 0 else "fail"

        # If synthesis "succeeded" but we couldn't parse basic cell count
        # and there's meaningful stdout, something is wrong.
        if ec == 0 and cells is None and len(text) > 200:
            raise RuntimeError(
                f"SynthParser: exit 0 but could not parse cell count — "
                f"unrecognised log format. Check {log_dir}/stdout.log"
            )

        return {
            "stage": "synthesis",
            "status": status,
            "num_cells": cells,
            "num_wires": wires,
            "area_um2": area,
            "utilization_pct": util,
            "raw_log_path": str(log_dir),
        }

    @staticmethod
    def _extract_int(pattern: re.Pattern, text: str) -> int | None:
        m = pattern.search(text)
        return int(m.group(1)) if m else None

    @staticmethod
    def _extract_float(pattern: re.Pattern, text: str) -> float | None:
        m = pattern.search(text)
        return float(m.group(1)) if m else None
