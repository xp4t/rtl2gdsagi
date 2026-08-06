"""Parser for SDC constraint completeness check output.

OpenLane2 checker output::

    [WARNING] No clock constraint found for pin CLK
    [WARNING] Unconstrained path: ...
    [INFO] SDC check passed: 2 clocks, 4 paths constrained.
    -or-
    [ERROR] SDC check failed: missing constraints.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .base_parser import BaseParser


class SDCParser(BaseParser):

    _PASS_RE    = re.compile(r"SDC check passed", re.IGNORECASE)
    _FAIL_RE    = re.compile(r"SDC check failed", re.IGNORECASE)
    _WARN_RE    = re.compile(r"\[WARNING\]\s+(.+)", re.IGNORECASE)
    _ERROR_RE   = re.compile(r"\[ERROR\]\s+(.+)", re.IGNORECASE)
    _CLOCK_RE   = re.compile(r"(\d+)\s+clocks?", re.IGNORECASE)
    _PATH_RE    = re.compile(r"(\d+)\s+paths?", re.IGNORECASE)

    def parse(self, log_dir: Path, stage_result: Any) -> dict[str, Any]:
        text = self._read_log(log_dir, "stdout.log")
        ec   = getattr(stage_result, "exit_code", 0)

        warnings = self._WARN_RE.findall(text)
        errors   = self._ERROR_RE.findall(text)
        passed   = bool(self._PASS_RE.search(text))
        failed   = bool(self._FAIL_RE.search(text))

        cm = self._CLOCK_RE.search(text)
        pm = self._PATH_RE.search(text)

        if ec != 0 and not errors and len(text) > 100:
            raise RuntimeError(
                f"SDCParser: non-zero exit ({ec}) but no error lines found — "
                f"unrecognised format. Check {log_dir}/stdout.log"
            )

        status = "pass" if (passed and not failed and ec == 0) else (
                 "warn" if warnings and not failed else "fail")

        return {
            "stage": "sdc_check",
            "status": status,
            "num_clocks": int(cm.group(1)) if cm else None,
            "num_paths": int(pm.group(1)) if pm else None,
            "warnings": warnings,
            "errors": errors,
            "raw_log_path": str(log_dir),
        }
