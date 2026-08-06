"""Persistent run-state manager — writes JSON after every stage so the flow
can resume after a crash without relying on in-memory state."""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .stages import Stage


class RunState:
    """Encapsulates the full persisted state for one orchestrator run."""

    def __init__(
        self,
        run_id: str,
        rtl_path: str,
        top_module: str,
        pdk: str,
        config_path: str,
        runs_dir: Path,
    ) -> None:
        self.run_id = run_id
        self.rtl_path = rtl_path
        self.top_module = top_module
        self.pdk = pdk
        self.config_path = config_path
        self.runs_dir = runs_dir
        self.current_stage: Stage | None = None
        self.completed_stages: list[str] = []
        self.stage_results: dict[str, Any] = {}      # stage -> parsed JSON report
        self.agent_decisions: dict[str, Any] = {}    # stage -> agent decision
        self.param_overrides: dict[str, Any] = {}    # accumulated param overrides
        self.stage_attempts: dict[str, int] = {}     # stage -> attempt count
        self.created_at: str = datetime.now(timezone.utc).isoformat()
        self.updated_at: str = self.created_at
        self.status: str = "running"                 # running | completed | failed | escalated
        self.error: str | None = None

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "rtl_path": self.rtl_path,
            "top_module": self.top_module,
            "pdk": self.pdk,
            "config_path": self.config_path,
            "current_stage": self.current_stage.value if self.current_stage else None,
            "completed_stages": self.completed_stages,
            "stage_results": self.stage_results,
            "agent_decisions": self.agent_decisions,
            "param_overrides": self.param_overrides,
            "stage_attempts": self.stage_attempts,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any], runs_dir: Path) -> "RunState":
        rs = cls(
            run_id=d["run_id"],
            rtl_path=d["rtl_path"],
            top_module=d["top_module"],
            pdk=d["pdk"],
            config_path=d["config_path"],
            runs_dir=runs_dir,
        )
        rs.current_stage = Stage(d["current_stage"]) if d.get("current_stage") else None
        rs.completed_stages = d.get("completed_stages", [])
        rs.stage_results = d.get("stage_results", {})
        rs.agent_decisions = d.get("agent_decisions", {})
        rs.param_overrides = d.get("param_overrides", {})
        rs.stage_attempts = d.get("stage_attempts", {})
        rs.created_at = d.get("created_at", "")
        rs.updated_at = d.get("updated_at", "")
        rs.status = d.get("status", "running")
        rs.error = d.get("error")
        return rs


class StateManager:
    """Reads and writes :class:`RunState` to disk atomically."""

    def __init__(self, runs_dir: Path) -> None:
        self.runs_dir = runs_dir
        runs_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def new_run(
        self,
        rtl_path: str,
        top_module: str,
        pdk: str,
        config_path: str,
    ) -> RunState:
        """Create a new :class:`RunState` with a fresh run_id and persist it."""
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "_" + uuid.uuid4().hex[:6]
        rs = RunState(
            run_id=run_id,
            rtl_path=rtl_path,
            top_module=top_module,
            pdk=pdk,
            config_path=config_path,
            runs_dir=self.runs_dir,
        )
        self._save(rs)
        return rs

    def load_run(self, run_id: str) -> RunState:
        """Load an existing run from disk; raises FileNotFoundError if absent."""
        path = self._path(run_id)
        if not path.exists():
            raise FileNotFoundError(f"Run state not found: {path}")
        with path.open() as f:
            data = json.load(f)
        return RunState.from_dict(data, self.runs_dir)

    def save(self, rs: RunState) -> None:
        """Persist run state (atomic write via temp file)."""
        rs.updated_at = datetime.now(timezone.utc).isoformat()
        self._save(rs)

    def list_runs(self) -> list[str]:
        """Return all known run_ids sorted newest-first."""
        return sorted(
            [p.stem for p in self.runs_dir.glob("*.json")],
            reverse=True,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _path(self, run_id: str) -> Path:
        return self.runs_dir / f"{run_id}.json"

    def _save(self, rs: RunState) -> None:
        path = self._path(rs.run_id)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(rs.to_dict(), indent=2))
        tmp.replace(path)  # atomic rename on Linux
