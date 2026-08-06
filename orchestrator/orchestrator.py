"""Main orchestrator — drives the state machine across all RTL-to-GDS stages.

Design decisions
----------------
* Reads/writes :class:`RunState` via :class:`StateManager` after **every**
  stage so a crash cannot lose more than one stage of work.
* Never stores inter-stage data in RAM only.
* All LLM calls go through :mod:`agent.decision_engine`; the orchestrator
  never directly calls the Claude API.
* Hard-gate stages (DRC, LVS, post-route STA) always escalate or retry on
  failure — they can never silently continue.
"""
from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from .stages import Stage, STAGE_ORDER, HARD_GATE_STAGES, STAGE_LABELS
from .state_manager import StateManager, RunState
from .stage_runner import StageRunner

log = logging.getLogger(__name__)


class Orchestrator:
    """Drives the RTL-to-GDS flow from lint through GDS output."""

    def __init__(
        self,
        rtl_path: str,
        top_module: str,
        pdk: str,
        config_path: str,
        runs_dir: Path,
        max_iterations: int = 3,
        resume_run_id: str | None = None,
        replay_decisions: bool = False,
    ) -> None:
        self.runs_dir = runs_dir
        self.state_mgr = StateManager(runs_dir)
        self.max_iterations = max_iterations
        self.replay_decisions = replay_decisions

        if resume_run_id:
            log.info("Resuming run %s", resume_run_id)
            self.state = self.state_mgr.load_run(resume_run_id)
        else:
            self.state = self.state_mgr.new_run(
                rtl_path=rtl_path,
                top_module=top_module,
                pdk=pdk,
                config_path=config_path,
            )
            log.info("New run %s", self.state.run_id)

        self.run_dir = runs_dir / self.state.run_id
        self.runner = StageRunner(self.run_dir)

        # Import here to avoid circular deps at module level
        from config.config_manager import ConfigManager
        from agent.decision_engine import DecisionEngine
        from parsers import get_parser

        self.config_mgr = ConfigManager(config_path)
        self.decision_engine = DecisionEngine(
            config_manager=self.config_mgr,
            replay=replay_decisions,
            cached_decisions=self.state.agent_decisions,
        )
        self._get_parser = get_parser

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> bool:
        """Execute the flow; returns True on full success."""
        return asyncio.run(self._run_async())

    async def _run_async(self) -> bool:
        for stage in STAGE_ORDER:
            if stage.value in self.state.completed_stages:
                log.info("Skipping already-completed stage: %s", stage.value)
                continue

            success = await self._run_stage_with_retries(stage)
            if not success:
                self.state.status = "failed"
                self.state_mgr.save(self.state)
                log.error("Flow failed at stage %s — run_id=%s", stage.value, self.state.run_id)
                return False

        self.state.status = "completed"
        self.state_mgr.save(self.state)
        log.info("Flow COMPLETED successfully — run_id=%s", self.state.run_id)
        return True

    # ------------------------------------------------------------------
    # Stage retry loop
    # ------------------------------------------------------------------

    async def _run_stage_with_retries(self, stage: Stage) -> bool:
        for attempt in range(1, self.max_iterations + 1):
            self.state.stage_attempts[stage.value] = attempt
            self.state.current_stage = stage
            self.state_mgr.save(self.state)

            log.info(
                "=== Stage: %s (attempt %d/%d) ===",
                STAGE_LABELS[stage], attempt, self.max_iterations,
            )

            # 1. Build OpenLane2 args for this stage
            stage_args = self._build_stage_args(stage)

            # 2. Run the tool
            raw = await self.runner.run_stage_async(
                stage=stage.value,
                extra_args=stage_args,
            )

            # 3. Parse the result
            try:
                parser = self._get_parser(stage)
                parsed = parser.parse(raw.log_dir, raw)
            except Exception as exc:
                log.error("[%s] Parser failed: %s", stage.value, exc)
                parsed = {
                    "stage": stage.value,
                    "status": "fail",
                    "parse_error": str(exc),
                    "raw_log_path": str(raw.log_dir),
                }

            # Save parsed result
            self.state.stage_results[stage.value] = parsed
            self.state_mgr.save(self.state)

            # 4. Hard-gate check
            if stage in HARD_GATE_STAGES and parsed.get("status") == "fail":
                if attempt < self.max_iterations:
                    log.warning(
                        "[%s] Hard-gate FAIL on attempt %d — will retry after agent re-tune",
                        stage.value, attempt,
                    )
                else:
                    log.error(
                        "[%s] Hard-gate FAIL: exhausted %d attempts — escalating",
                        stage.value, self.max_iterations,
                    )
                    self._record_escalation(stage, parsed)
                    return False

            # 5. Agent decision
            decision = await self._get_decision(stage, parsed)
            self.state.agent_decisions[stage.value] = decision
            self.state_mgr.save(self.state)

            log.info(
                "[%s] Agent decision: %s (confidence=%s)",
                stage.value, decision.get("decision"), decision.get("confidence"),
            )

            action = decision.get("decision", "continue")

            if action == "continue":
                self.state.completed_stages.append(stage.value)
                self.state_mgr.save(self.state)
                return True

            elif action == "retune":
                # Apply validated param updates from agent
                updates = decision.get("param_updates", {})
                validated = self.config_mgr.validate_and_apply(updates)
                self.state.param_overrides.update(validated)
                self.state_mgr.save(self.state)
                log.info("[%s] Retuning with params: %s", stage.value, validated)
                # Loop back for next attempt

            elif action == "escalate_to_human":
                log.warning(
                    "[%s] Agent escalated to human — run_id=%s",
                    stage.value, self.state.run_id,
                )
                self.state.status = "escalated"
                self._record_escalation(stage, parsed)
                self.state_mgr.save(self.state)
                return False

            elif action == "abort":
                log.error("[%s] Agent aborted the run", stage.value)
                self.state.status = "failed"
                self.state_mgr.save(self.state)
                return False

            else:
                log.warning("[%s] Unknown agent action '%s' — defaulting to continue", stage.value, action)
                self.state.completed_stages.append(stage.value)
                self.state_mgr.save(self.state)
                return True

        # Exhausted all attempts without explicit continue
        log.error("[%s] Exhausted all %d attempts without success", stage.value, self.max_iterations)
        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_stage_args(self, stage: Stage) -> list[str]:
        """Build OpenLane2 CLI args for the given stage.

        OpenLane2 format::

            openlane --run-tag <run_id> --from <stage> --to <stage> \
                <config_file.json>
        """
        cfg_file = self.config_mgr.generate_run_config(
            self.state.param_overrides,
            self.run_dir / "config_applied.json",
        )
        args = [
            "--run-tag", self.state.run_id,
            "--from", self._openlane_stage_name(stage),
            "--to",   self._openlane_stage_name(stage),
            str(cfg_file),
        ]
        return args

    @staticmethod
    def _openlane_stage_name(stage: Stage) -> str:
        """Map our internal stage enum to OpenLane2 step class names."""
        _map = {
            Stage.SYNTHESIS:      "Yosys.Synthesis",
            Stage.FLOORPLAN:      "OpenROAD.Floorplan",
            Stage.PLACEMENT:      "OpenROAD.GlobalPlacement",
            Stage.CTS:            "OpenROAD.CTS",
            Stage.ROUTING:        "OpenROAD.GlobalRouting",
            Stage.DRC:            "Magic.DRC",
            Stage.LVS:            "Netgen.LVS",
            Stage.GDS:            "KLayout.StreamOut",
            # STA and SDC stages use custom external runners
            Stage.POST_SYNTH_STA: "OpenROAD.STAPostSynth",
            Stage.POST_PLACE_STA: "OpenROAD.STAPostPlace",
            Stage.POST_CTS_STA:   "OpenROAD.STAPostCTS",
            Stage.POST_ROUTE_STA: "OpenROAD.STAPostRoute",
            Stage.SDC_CHECK:      "Checker.SDC",
            Stage.LINT:           "Verilator.Lint",
        }
        return _map.get(stage, stage.value)

    async def _get_decision(
        self,
        stage: Stage,
        parsed: dict[str, Any],
    ) -> dict[str, Any]:
        """Get agent decision, with timeout + fallback."""
        try:
            decision = await asyncio.wait_for(
                self.decision_engine.decide_async(
                    stage=stage,
                    current_result=parsed,
                    history=self._recent_history(stage),
                    param_overrides=self.state.param_overrides,
                ),
                timeout=120,  # 2 min max per LLM call
            )
            return decision
        except asyncio.TimeoutError:
            log.error("[%s] Agent decision TIMED OUT — defaulting to escalate", stage.value)
            return {
                "decision": "escalate_to_human",
                "reasoning": "LLM API timeout — human review required",
                "param_updates": {},
                "confidence": "low",
            }
        except Exception as exc:
            log.error("[%s] Agent decision error: %s — defaulting to continue", stage.value, exc)
            return {
                "decision": "continue",
                "reasoning": f"API error ({exc}) — continuing with prior config",
                "param_updates": {},
                "confidence": "low",
            }

    def _recent_history(
        self,
        current_stage: Stage,
        n: int = 3,
    ) -> list[dict[str, Any]]:
        """Return the last N completed stage results for context."""
        completed = self.state.completed_stages[-n:]
        return [
            {
                "stage": s,
                "result": self.state.stage_results.get(s, {}),
                "decision": self.state.agent_decisions.get(s, {}),
            }
            for s in completed
        ]

    def _record_escalation(self, stage: Stage, parsed: dict[str, Any]) -> None:
        escalation = {
            "stage": stage.value,
            "stage_label": STAGE_LABELS[stage],
            "result": parsed,
            "run_id": self.state.run_id,
            "param_overrides": self.state.param_overrides,
        }
        esc_path = self.run_dir / "escalation.json"
        import json
        esc_path.write_text(json.dumps(escalation, indent=2))
        log.warning("Escalation report written to %s", esc_path)
