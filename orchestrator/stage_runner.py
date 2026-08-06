"""Stage runner — wraps OpenLane2 CLI subprocess calls with timeout,
exit-code handling, and async-compatible background execution."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


_DEFAULT_TIMEOUT = int(os.environ.get("STAGE_TIMEOUT_SECONDS", str(60 * 60 * 4)))  # 4 h default


class StageResult:
    """Holds the raw output of one stage subprocess invocation."""

    def __init__(
        self,
        stage: str,
        exit_code: int,
        stdout: str,
        stderr: str,
        log_dir: Path,
        elapsed_seconds: float,
        timed_out: bool = False,
    ) -> None:
        self.stage = stage
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.log_dir = log_dir
        self.elapsed_seconds = elapsed_seconds
        self.timed_out = timed_out

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "exit_code": self.exit_code,
            "success": self.success,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "timed_out": self.timed_out,
            "log_dir": str(self.log_dir),
            "stdout_tail": self.stdout[-4000:] if self.stdout else "",
            "stderr_tail": self.stderr[-4000:] if self.stderr else "",
        }


class StageRunner:
    """Executes EDA tool subprocesses via OpenLane2 and external tools.

    Every invocation is logged to `run_dir/logs/<stage>/`.
    The runner is *async* internally so long PnR stages never block the
    event loop — use `await run_stage_async(...)` from async callers or
    `run_stage(...)` for synchronous contexts.
    """

    def __init__(self, run_dir: Path, openlane_cmd: list[str] | None = None) -> None:
        self.run_dir = run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        # Allow override via env for CI / different install methods
        self.openlane_cmd = openlane_cmd or self._detect_openlane_cmd()

    # ------------------------------------------------------------------
    # Public synchronous wrapper
    # ------------------------------------------------------------------

    def run_stage(
        self,
        stage: str,
        extra_args: list[str],
        env_override: dict[str, str] | None = None,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> StageResult:
        """Blocking wrapper — runs asyncio event loop internally."""
        return asyncio.run(
            self.run_stage_async(stage, extra_args, env_override, timeout)
        )

    # ------------------------------------------------------------------
    # Async core
    # ------------------------------------------------------------------

    async def run_stage_async(
        self,
        stage: str,
        extra_args: list[str],
        env_override: dict[str, str] | None = None,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> StageResult:
        log_dir = self.run_dir / "logs" / stage
        log_dir.mkdir(parents=True, exist_ok=True)

        cmd = self.openlane_cmd + extra_args
        env = {**os.environ, **(env_override or {})}

        log.info("[%s] Starting: %s", stage, " ".join(cmd))
        t0 = time.monotonic()

        stdout_buf: list[str] = []
        stderr_buf: list[str] = []
        timed_out = False
        exit_code = -1

        stdout_path = log_dir / "stdout.log"
        stderr_path = log_dir / "stderr.log"

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=str(self.run_dir),
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
                exit_code = proc.returncode or 0
                stdout_buf = stdout_bytes.decode(errors="replace")
                stderr_buf = stderr_bytes.decode(errors="replace")
            except asyncio.TimeoutError:
                proc.kill()
                timed_out = True
                log.error("[%s] TIMED OUT after %d s", stage, timeout)
                stdout_buf = ""
                stderr_buf = ""
        except FileNotFoundError as exc:
            log.error("[%s] Command not found: %s — %s", stage, cmd[0], exc)
            stdout_buf = ""
            stderr_buf = str(exc)
            exit_code = 127

        elapsed = time.monotonic() - t0
        log.info("[%s] Finished in %.1f s  exit=%d", stage, elapsed, exit_code)

        # Persist raw logs
        stdout_path.write_text(stdout_buf if isinstance(stdout_buf, str) else "")
        stderr_path.write_text(stderr_buf if isinstance(stderr_buf, str) else "")

        return StageResult(
            stage=stage,
            exit_code=exit_code,
            stdout=stdout_buf if isinstance(stdout_buf, str) else "",
            stderr=stderr_buf if isinstance(stderr_buf, str) else "",
            log_dir=log_dir,
            elapsed_seconds=elapsed,
            timed_out=timed_out,
        )

    # ------------------------------------------------------------------
    # Convenience: run an arbitrary external command (non-OpenLane stages)
    # ------------------------------------------------------------------

    async def run_external_async(
        self,
        stage: str,
        cmd: list[str],
        env_override: dict[str, str] | None = None,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> StageResult:
        log_dir = self.run_dir / "logs" / stage
        log_dir.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, **(env_override or {})}
        log.info("[%s] External: %s", stage, " ".join(cmd))
        t0 = time.monotonic()
        timed_out = False
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            try:
                out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                exit_code = proc.returncode or 0
                stdout = out.decode(errors="replace")
                stderr = err.decode(errors="replace")
            except asyncio.TimeoutError:
                proc.kill()
                timed_out = True
                stdout = stderr = ""
                exit_code = -1
        except FileNotFoundError as exc:
            stdout = ""
            stderr = str(exc)
            exit_code = 127
        elapsed = time.monotonic() - t0
        (log_dir / "stdout.log").write_text(stdout)
        (log_dir / "stderr.log").write_text(stderr)
        return StageResult(stage, exit_code, stdout, stderr, log_dir, elapsed, timed_out)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_openlane_cmd() -> list[str]:
        """Detect the available OpenLane2 invocation method.

        Priority order:
        1. OPENLANE_CMD env var (space-separated)
        2. `openlane` on PATH
        3. `python -m openlane`
        """
        if env_cmd := os.environ.get("OPENLANE_CMD"):
            return env_cmd.split()
        if shutil.which("openlane"):
            return ["openlane"]
        return [sys.executable, "-m", "openlane"]
