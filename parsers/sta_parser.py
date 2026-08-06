"""Parser for OpenSTA timing reports.

Expected input format (OpenSTA report_checks output)::

    Startpoint: ...
    Endpoint:   clk_reg
    Path Group: clk
    Path Type:  max

    Point                        Incr       Path
    -------------------------------------------------
    ...                          0.10       0.10
    data arrival time                       0.10

    clock CLK (rise edge)        5.00       5.00
    ...                          0.00       5.00
    data required time                      5.00
    -------------------------------------------------
    data required time                      5.00
    data arrival time                      -0.10
    -------------------------------------------------
    slack (MET)                             4.90

Also parses the summary line::
    wns -0.42
    tns -1.26
    violating paths 3
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .base_parser import BaseParser


class STAParser(BaseParser):

    _WNS_RE      = re.compile(r"wns\s+([\-\d.]+)", re.IGNORECASE)
    _TNS_RE      = re.compile(r"tns\s+([\-\d.]+)", re.IGNORECASE)
    _VIOL_RE     = re.compile(r"violating paths\s+(\d+)", re.IGNORECASE)
    _SLACK_RE    = re.compile(
        r"slack\s+\((MET|VIOLATED)\)\s+([\-\d.]+)", re.IGNORECASE
    )
    _ENDPOINT_RE = re.compile(r"Endpoint:\s*(.+)", re.IGNORECASE)
    # OpenLane2 STA summary sometimes uses these column headers
    _SETUP_WNS_RE = re.compile(r"Setup\s+WNS:\s+([\-\d.]+)", re.IGNORECASE)
    _HOLD_WNS_RE  = re.compile(r"Hold\s+WNS:\s+([\-\d.]+)", re.IGNORECASE)

    def __init__(self, stage_name: str = "sta") -> None:
        self._stage_name = stage_name

    def parse(self, log_dir: Path, stage_result: Any) -> dict[str, Any]:
        text = self._read_log(log_dir, "stdout.log")
        if not text.strip():
            # Try stderr
            text = self._read_log(log_dir, "stderr.log")

        ec = getattr(stage_result, "exit_code", 0)

        wns = self._extract_float(self._WNS_RE, text)
        # Fall back to setup WNS column header
        if wns is None:
            wns = self._extract_float(self._SETUP_WNS_RE, text)
        tns      = self._extract_float(self._TNS_RE, text)
        n_viol   = self._extract_int(self._VIOL_RE, text)
        hold_wns = self._extract_float(self._HOLD_WNS_RE, text)

        # Collect individual slack paths
        top_violations = []
        endpoints = self._ENDPOINT_RE.findall(text)
        slacks    = self._SLACK_RE.findall(text)  # list of ("MET"|"VIOLATED", slack_str)
        for ep, (met, slack_str) in zip(endpoints, slacks):
            slack_val = float(slack_str)
            if met.upper() == "VIOLATED" or slack_val < 0:
                top_violations.append(
                    {"endpoint": ep.strip(), "slack_ns": slack_val, "path": ep.strip()}
                )
        # Sort by worst first
        top_violations.sort(key=lambda x: x["slack_ns"])

        # Status logic
        if ec != 0:
            status = "fail"
        elif wns is not None and wns < 0:
            status = "fail"
        elif n_viol is not None and n_viol > 0:
            status = "fail"
        else:
            status = "pass"

        # Hard failure: non-zero exit but no parseable timing → format changed
        if ec != 0 and wns is None and len(text) > 100:
            raise RuntimeError(
                f"STAParser [{self._stage_name}]: non-zero exit and no parseable "
                f"timing data — unrecognised log format. Check {log_dir}/stdout.log"
            )

        return {
            "stage": self._stage_name,
            "status": status,
            "worst_setup_slack_ns": wns,
            "worst_hold_slack_ns":  hold_wns,
            "total_negative_slack_ns": tns,
            "num_violating_paths": n_viol or 0,
            "top_violations": top_violations[:5],
            "raw_log_path": str(log_dir),
        }

    @staticmethod
    def _extract_float(pattern: re.Pattern, text: str) -> float | None:
        m = pattern.search(text)
        return float(m.group(1)) if m else None

    @staticmethod
    def _extract_int(pattern: re.Pattern, text: str) -> int | None:
        m = pattern.search(text)
        return int(m.group(1)) if m else None
