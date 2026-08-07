"""Claude API decision engine with tool-use, timeout, audit logging,
and deterministic replay support.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic

from orchestrator.stages import Stage, HARD_GATE_STAGES
from .schema import AgentDecision, DECISION_TOOL_SCHEMA
from .system_prompts import get_system_prompt

log = logging.getLogger(__name__)

_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5")
_MAX_TOKENS = 1024
_AUDIT_DIR = Path(os.environ.get("AUDIT_DIR", "runs/audit"))


class DecisionEngine:
    """Wraps the Claude API with:

    * Tool-use / function-calling (never free-text parsing)
    * Full audit trail (every call logged to disk with timestamp)
    * Deterministic replay (use cached decisions from prior run)
    * Timeout + fallback: network timeout → escalate / continue
    * Hard-gate enforcement: failure on signoff stages always escalates
    """

    def __init__(
        self,
        config_manager: Any,
        replay: bool = False,
        cached_decisions: dict[str, Any] | None = None,
    ) -> None:
        self.config_mgr = config_manager
        self.replay = replay
        self.cached = cached_decisions or {}
        _AUDIT_DIR.mkdir(parents=True, exist_ok=True)

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            log.warning(
                "ANTHROPIC_API_KEY not set — all decisions will fall back to 'continue'"
            )
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def decide_async(
        self,
        stage: Stage,
        current_result: dict[str, Any],
        history: list[dict[str, Any]],
        param_overrides: dict[str, Any],
    ) -> dict[str, Any]:
        """Return an :class:`AgentDecision` dict for the given stage."""

        # Replay mode: return cached decision without calling API
        if self.replay and stage.value in self.cached:
            log.info("[%s] Replaying cached decision", stage.value)
            return self.cached[stage.value]

        # No API key → fallback
        if self.client is None:
            return self._fallback_decision(stage, current_result, reason="no API key")

        prompt_payload = self._build_prompt(stage, current_result, history, param_overrides)
        system_prompt  = get_system_prompt(stage)

        t0 = time.monotonic()
        try:
            raw_decision = await asyncio.to_thread(
                self._call_claude,
                system_prompt,
                prompt_payload,
            )
        except Exception as exc:
            log.error("[%s] Claude API error: %s", stage.value, exc)
            raw_decision = self._fallback_decision(stage, current_result, reason=str(exc))

        elapsed = time.monotonic() - t0
        log.info("[%s] Agent call completed in %.2f s", stage.value, elapsed)

        # Hard-gate override: DRC/LVS/signoff fail must escalate
        raw_decision = self._enforce_hard_gates(stage, current_result, raw_decision)

        self._write_audit(
            stage=stage,
            prompt=prompt_payload,
            system_prompt=system_prompt,
            decision=raw_decision,
            elapsed=elapsed,
        )
        return raw_decision

    # ------------------------------------------------------------------
    # Internal: Claude API call (blocking, run in thread)
    # ------------------------------------------------------------------

    def _call_claude(
        self,
        system_prompt: str,
        user_content: str,
    ) -> dict[str, Any]:
        response = self.client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=system_prompt,
            tools=[DECISION_TOOL_SCHEMA],
            tool_choice={"type": "any"},  # force tool use
            messages=[{"role": "user", "content": user_content}],
        )

        # Extract tool-use block
        for block in response.content:
            if block.type == "tool_use" and block.name == "make_flow_decision":
                raw = block.input
                try:
                    decision = AgentDecision(raw)
                    return decision.to_dict()
                except (ValueError, KeyError) as exc:
                    raise RuntimeError(
                        f"Claude returned invalid decision schema: {exc} — raw: {raw}"
                    ) from exc

        raise RuntimeError(
            "Claude did not call make_flow_decision tool — unexpected response format. "
            f"Response: {response.content}"
        )

    # ------------------------------------------------------------------
    # Prompt builder
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt(
        stage: Stage,
        current_result: dict[str, Any],
        history: list[dict[str, Any]],
        param_overrides: dict[str, Any],
    ) -> str:
        sections = [
            f"## Current Stage: {stage.value}",
            "## Current Result",
            json.dumps(current_result, indent=2),
            "## Recent History (last 3 stages)",
            json.dumps(history, indent=2),
            "## Current Config Overrides (diff from defaults)",
            json.dumps(param_overrides, indent=2),
            "## Action Required",
            "Call the make_flow_decision tool now.",
        ]
        return "\n\n".join(sections)

    # ------------------------------------------------------------------
    # Hard-gate enforcement
    # ------------------------------------------------------------------

    @staticmethod
    def _enforce_hard_gates(
        stage: Stage,
        current_result: dict[str, Any],
        decision: dict[str, Any],
    ) -> dict[str, Any]:
        """Override agent decision if hard-gate conditions are triggered."""
        if stage not in HARD_GATE_STAGES:
            return decision
        if current_result.get("status") != "fail":
            return decision

        allowed = {"escalate_to_human", "retune", "abort"}
        if decision.get("decision") not in allowed:
            log.warning(
                "[%s] Hard-gate: overriding agent decision '%s' → escalate_to_human",
                stage.value, decision.get("decision"),
            )
            return {
                "decision": "escalate_to_human",
                "reasoning": (
                    f"Hard gate: {stage.value} failed — "
                    f"overriding agent decision '{decision.get('decision')}'."
                ),
                "param_updates": {},
                "confidence": "high",
            }
        return decision

    # ------------------------------------------------------------------
    # Fallback decision
    # ------------------------------------------------------------------

    @staticmethod
    def _fallback_decision(
        stage: Stage,
        current_result: dict[str, Any],
        reason: str = "",
    ) -> dict[str, Any]:
        """Conservative fallback when the API is unavailable."""
        status = current_result.get("status", "pass")
        if status == "fail" and stage in HARD_GATE_STAGES:
            dec = "escalate_to_human"
        elif status == "fail":
            dec = "escalate_to_human"
        else:
            dec = "continue"
        return {
            "decision": dec,
            "reasoning": f"API fallback ({reason}): defaulting to {dec}",
            "param_updates": {},
            "confidence": "low",
        }

    # ------------------------------------------------------------------
    # Audit logging
    # ------------------------------------------------------------------

    def _write_audit(
        self,
        stage: Stage,
        prompt: str,
        system_prompt: str,
        decision: dict[str, Any],
        elapsed: float,
    ) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        record = {
            "timestamp": ts,
            "stage": stage.value,
            "model": _MODEL,
            "elapsed_seconds": round(elapsed, 3),
            "system_prompt": system_prompt,
            "user_prompt": prompt,
            "decision": decision,
        }
        audit_file = _AUDIT_DIR / f"{ts.replace(':', '-')}_{stage.value}.json"
        try:
            audit_file.write_text(json.dumps(record, indent=2))
        except OSError as exc:
            log.warning("Failed to write audit log: %s", exc)
