"""Abstract base for all log parsers."""
from __future__ import annotations

import abc
from pathlib import Path
from typing import Any


class BaseParser(abc.ABC):
    """All parsers must implement :meth:`parse`.

    Rules:
    * RAISE on unrecognised log format — never silently return a clean result.
    * Always include ``raw_log_path`` and ``stage`` in the output dict.
    """

    @abc.abstractmethod
    def parse(self, log_dir: Path, stage_result: Any) -> dict[str, Any]:
        """Parse logs in *log_dir* and return a normalised report dict."""

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_log(log_dir: Path, filename: str = "stdout.log") -> str:
        path = log_dir / filename
        if not path.exists():
            # Also check for files directly in log_dir matching pattern
            candidates = list(log_dir.glob(f"*{filename}*"))
            if candidates:
                return candidates[0].read_text(errors="replace")
            raise FileNotFoundError(
                f"Expected log file not found: {path}\n"
                f"  Files present: {list(log_dir.iterdir()) if log_dir.exists() else 'directory missing'}"
            )
        return path.read_text(errors="replace")

    @staticmethod
    def _status_from_exit(exit_code: int) -> str:
        return "pass" if exit_code == 0 else "fail"
