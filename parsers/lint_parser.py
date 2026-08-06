"""Parser for Verilator lint output."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .base_parser import BaseParser


class LintParser(BaseParser):
    """Parse Verilator --lint-only output into a normalised report.

    Expected patterns (Verilator ≥4.x)::

        %Warning-UNUSED: file.v:42:10: Signal is not used
        %Error: file.v:10:1: Cannot find module
        %Error-UNDRIVEN: ...
    """

    _WARNING_RE = re.compile(
        r"^%Warning(?:-(?P<code>\w+))?:\s+(?P<loc>\S+):\s*(?P<msg>.*)$",
        re.MULTILINE,
    )
    _ERROR_RE = re.compile(
        r"^%Error(?:-(?P<code>\w+))?:\s+(?P<loc>\S+):\s*(?P<msg>.*)$",
        re.MULTILINE,
    )

    def parse(self, log_dir: Path, stage_result: Any) -> dict[str, Any]:
        stdout = self._read_log(log_dir, "stdout.log")
        stderr = self._read_log(log_dir, "stderr.log") if (log_dir / "stderr.log").exists() else ""
        combined = stdout + "\n" + stderr

        warnings = [
            {
                "code": m.group("code") or "GENERIC",
                "location": m.group("loc"),
                "message": m.group("msg").strip(),
            }
            for m in self._WARNING_RE.finditer(combined)
        ]
        errors = [
            {
                "code": m.group("code") or "GENERIC",
                "location": m.group("loc"),
                "message": m.group("msg").strip(),
            }
            for m in self._ERROR_RE.finditer(combined)
        ]

        # Determine status
        if errors:
            status = "fail"
        elif warnings:
            status = "warn"
        else:
            # If exit code non-zero but no parsed errors, still flag it
            ec = getattr(stage_result, "exit_code", 0)
            status = "pass" if ec == 0 else "fail"

        # A clean Verilator run with no warnings/errors but non-zero exit code
        # is suspicious — flag it rather than silently pass.
        ec = getattr(stage_result, "exit_code", 0)
        if not errors and not warnings and ec != 0:
            raise RuntimeError(
                f"Lint: non-zero exit ({ec}) but no parseable warnings/errors — "
                f"unrecognised log format. Check: {log_dir}/stdout.log"
            )

        return {
            "stage": "lint",
            "status": status,
            "num_errors": len(errors),
            "num_warnings": len(warnings),
            "errors": errors,
            "warnings": warnings,
            "raw_log_path": str(log_dir),
        }
