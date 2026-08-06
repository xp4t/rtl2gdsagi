"""Parser for Netgen LVS reports.

Netgen output::

    Circuit 1 cell sky130_fd_sc_hd__buf_1 is correctly matched
    ...
    Result: Circuits match uniquely.
    -or-
    Result: Netlists do not match.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .base_parser import BaseParser


class LVSParser(BaseParser):

    _MATCH_RE  = re.compile(r"Circuits match uniquely", re.IGNORECASE)
    _FAIL_RE   = re.compile(r"Netlists do not match", re.IGNORECASE)
    _ERRORS_RE = re.compile(r"(\d+)\s+errors", re.IGNORECASE)
    _WARN_RE   = re.compile(r"(\d+)\s+warnings", re.IGNORECASE)

    def parse(self, log_dir: Path, stage_result: Any) -> dict[str, Any]:
        # Netgen writes to comp.out
        for filename in ["comp.out", "lvs.log", "stdout.log"]:
            cand = log_dir / filename
            if cand.exists():
                text = cand.read_text(errors="replace")
                if text.strip():
                    break
        else:
            ec = getattr(stage_result, "exit_code", 0)
            if ec != 0:
                raise RuntimeError(
                    f"LVSParser: no LVS report found in {log_dir} and exit={ec}"
                )
            text = ""

        matched  = bool(self._MATCH_RE.search(text))
        failed   = bool(self._FAIL_RE.search(text))
        em       = self._ERRORS_RE.search(text)
        wm       = self._WARN_RE.search(text)
        n_errors = int(em.group(1)) if em else 0
        n_warns  = int(wm.group(1)) if wm else 0

        if not matched and not failed and text.strip():
            # Non-empty output but neither verdict found — flag format issue
            ec = getattr(stage_result, "exit_code", 0)
            if ec != 0:
                raise RuntimeError(
                    f"LVSParser: unrecognised Netgen output format — "
                    f"no verdict line found. Check {log_dir}"
                )

        status = "pass" if matched and not failed and n_errors == 0 else "fail"
        return {
            "stage": "lvs",
            "status": status,
            "circuits_matched": matched,
            "num_errors": n_errors,
            "num_warnings": n_warns,
            "raw_log_path": str(log_dir),
        }
