"""Structured logging.

Two sinks per run, both under the timestamped run directory:

* ``run.jsonl`` -- one JSON object per event, machine-readable. Every stage
  attempt, every config regeneration and every Claude API call appears here.
* ``run.log`` -- the same events rendered for humans.

API keys are never passed to the logger; prompts and completions are recorded
to per-attempt files under the stage directory rather than inlined into events,
so the JSONL stays greppable.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

JSONL_FILENAME = "run.jsonl"
TEXT_FILENAME = "run.log"


RUN_START = "run_start"
RUN_END = "run_end"
STAGE_START = "stage_start"
STAGE_END = "stage_end"
CONFIG_CHECK = "config_check"
CONFIG_GENERATED = "config_generated"
TOOL_RUN = "tool_run"
RESULT_CHECK = "result_check"
FIX_ATTEMPT = "fix_attempt"
API_CALL = "api_call"
ARTIFACT = "artifact"
RTL_PATCH = "rtl_patch"
NOTE = "note"


class RunLog:
    """Append-only structured log bound to one run directory."""

    def __init__(self, run_dir: str | os.PathLike[str], *, echo: bool = True) -> None:
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.jsonl_path = self.run_dir / JSONL_FILENAME
        self.text_path = self.run_dir / TEXT_FILENAME
        self._jsonl = open(self.jsonl_path, "a", encoding="utf-8")

        self._log = logging.getLogger(f"rtl2gdsagi.run.{self.run_dir.name}")
        self._log.setLevel(logging.DEBUG)
        self._log.propagate = False
        if not self._log.handlers:
            fh = logging.FileHandler(self.text_path, encoding="utf-8")
            fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(message)s"))
            self._log.addHandler(fh)
            if echo:
                sh = logging.StreamHandler()
                sh.setFormatter(logging.Formatter("%(message)s"))
                sh.setLevel(logging.INFO)
                self._log.addHandler(sh)

    # ---- core ------------------------------------------------------------

    def event(
        self,
        kind: str,
        /,  # positional-only: callers pass metrics named "kind" through **fields
        *,
        stage: str | None = None,
        attempt: int | None = None,
        message: str = "",
        level: int = logging.INFO,
        **fields: Any,
    ) -> dict[str, Any]:
        rec: dict[str, Any] = {"ts": time.time(), "event": kind}
        if stage is not None:
            rec["stage"] = str(stage)
        if attempt is not None:
            rec["attempt"] = attempt
        if message:
            rec["message"] = message
        for k, v in fields.items():
            # never let a metric shadow the record's own structural keys
            rec[k if k not in ("ts", "event", "stage", "attempt", "message") else f"m_{k}"] = v
        self._jsonl.write(json.dumps(rec, default=str) + "\n")
        self._jsonl.flush()

        prefix = f"[{stage}]" if stage else "[run]"
        if attempt is not None:
            prefix += f"[try {attempt}]"
        human = message or kind
        extra = " ".join(
            f"{k}={_short(v)}" for k, v in fields.items() if k not in {"traceback"}
        )
        self._log.log(level, f"{prefix} {human}" + (f"  ({extra})" if extra else ""))
        return rec

    # ---- convenience wrappers -------------------------------------------

    def run_start(self, **fields: Any) -> None:
        self.event(RUN_START, message="pipeline starting", **fields)

    def run_end(self, status: str, **fields: Any) -> None:
        self.event(
            RUN_END,
            message=f"pipeline finished: {status}",
            status=status,
            level=logging.INFO if status == "ok" else logging.ERROR,
            **fields,
        )

    def stage_start(self, stage: str, **fields: Any) -> None:
        self.event(STAGE_START, stage=stage, message="stage starting", **fields)

    def stage_end(self, stage: str, status: str, attempts: int, **fields: Any) -> None:
        self.event(
            STAGE_END,
            stage=stage,
            message=f"stage {status} after {attempts} attempt(s)",
            status=status,
            attempts=attempts,
            level=logging.INFO if status == "ok" else logging.ERROR,
            **fields,
        )

    def config_check(self, stage: str, ok: bool, missing: list[str], **fields: Any) -> None:
        self.event(
            CONFIG_CHECK,
            stage=stage,
            message="config valid" if ok else "config invalid",
            ok=ok,
            missing=missing,
            level=logging.INFO if ok else logging.WARNING,
            **fields,
        )

    def config_generated(self, stage: str, attempt: int, files: list[str], **fields: Any) -> None:
        self.event(
            CONFIG_GENERATED,
            stage=stage,
            attempt=attempt,
            message=f"generated {len(files)} config file(s)",
            files=files,
            **fields,
        )

    def tool_run(self, stage: str, attempt: int, argv: list[str], **fields: Any) -> None:
        self.event(
            TOOL_RUN, stage=stage, attempt=attempt, message="invoking tool", argv=argv, **fields
        )

    def result_check(self, stage: str, attempt: int, ok: bool, summary: str, **fields: Any) -> None:
        self.event(
            RESULT_CHECK,
            stage=stage,
            attempt=attempt,
            message=summary,
            ok=ok,
            level=logging.INFO if ok else logging.WARNING,
            **fields,
        )

    def fix_attempt(self, stage: str, attempt: int, reason: str, **fields: Any) -> None:
        self.event(
            FIX_ATTEMPT,
            stage=stage,
            attempt=attempt,
            message=f"asking Claude to fix: {reason}",
            level=logging.WARNING,
            **fields,
        )

    def api_call(
        self,
        stage: str,
        attempt: int,
        purpose: str,
        model: str,
        **fields: Any,
    ) -> None:
        self.event(
            API_CALL,
            stage=stage,
            attempt=attempt,
            message=f"claude {purpose}",
            purpose=purpose,
            model=model,
            **fields,
        )

    def artifact(self, stage: str, key: str, path: str, sha256: str, **fields: Any) -> None:
        self.event(
            ARTIFACT,
            stage=stage,
            message=f"registered {key}",
            key=key,
            path=path,
            sha256=sha256,
            **fields,
        )

    def rtl_patch(self, stage: str, attempt: int, files: list[str], patch: str) -> None:
        self.event(
            RTL_PATCH,
            stage=stage,
            attempt=attempt,
            message=f"patched {len(files)} RTL file(s) in the run copy",
            files=files,
            patch_file=patch,
        )

    def note(self, message: str, *, stage: str | None = None, **fields: Any) -> None:
        self.event(NOTE, stage=stage, message=message, **fields)

    def warn(self, message: str, *, stage: str | None = None, **fields: Any) -> None:
        self.event(NOTE, stage=stage, message=message, level=logging.WARNING, **fields)

    def error(self, message: str, *, stage: str | None = None, **fields: Any) -> None:
        self.event(NOTE, stage=stage, message=message, level=logging.ERROR, **fields)

    # ---- lifecycle -------------------------------------------------------

    def close(self) -> None:
        try:
            self._jsonl.close()
        except Exception:  # pragma: no cover
            pass
        for h in list(self._log.handlers):
            h.close()
            self._log.removeHandler(h)

    def __enter__(self) -> "RunLog":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---- reading back ----------------------------------------------------

    def read_events(self) -> list[dict[str, Any]]:
        """Parse our own JSONL back. Used by tests and the failure report."""
        if not self.jsonl_path.is_file():
            return []
        out = []
        for line in self.jsonl_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out


def _short(value: Any, limit: int = 120) -> str:
    s = str(value)
    if len(s) <= limit:
        return s
    return s[: limit - 3] + "..."
