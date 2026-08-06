"""Strategy sweep controller — runs K config variants for a stage and
asks the agent to rank them by PPA + timing.

All variant configs + results are logged so any run is reproducible
from its sweep_id.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.stage_runner import StageRunner
from orchestrator.stages import Stage
from parsers import get_parser

log = logging.getLogger(__name__)


class SweepController:
    """Run multiple config variants for *stage* and rank them via the agent."""

    def __init__(
        self,
        run_dir: Path,
        config_manager: Any,
        decision_engine: Any,
        max_parallel: int = 2,
    ) -> None:
        self.run_dir = run_dir
        self.config_mgr = config_manager
        self.decision_engine = decision_engine
        self.max_parallel = max_parallel

    async def run_sweep(
        self,
        stage: Stage,
        base_overrides: dict[str, Any],
        history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Run all sweep variants for *stage*; return the best variant.

        Returns::

            {
                "best_variant": {"params": {...}, "result": {...}},
                "all_variants": [...],
                "sweep_id": "...",
                "ranking_decision": {...},
            }
        """
        sweep_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + f"_{stage.value}"
        sweep_dir = self.run_dir / "sweeps" / sweep_id
        sweep_dir.mkdir(parents=True, exist_ok=True)

        variants = self.config_mgr.get_sweep_variants(stage.value)
        if not variants:
            log.info("[sweep:%s] No sweep variants defined — skipping sweep", stage.value)
            return {}

        log.info("[sweep:%s] Running %d variants (max_parallel=%d)",
                 stage.value, len(variants), self.max_parallel)

        # Chunk into parallel batches
        results = []
        for batch_start in range(0, len(variants), self.max_parallel):
            batch = variants[batch_start:batch_start + self.max_parallel]
            batch_tasks = [
                self._run_variant(stage, sweep_dir, idx + batch_start, v, base_overrides)
                for idx, v in enumerate(batch)
            ]
            batch_results = await asyncio.gather(*batch_tasks)
            results.extend(batch_results)

        # Persist the sweep table
        sweep_table = {"sweep_id": sweep_id, "stage": stage.value, "variants": results}
        (sweep_dir / "sweep_table.json").write_text(json.dumps(sweep_table, indent=2))

        # Ask agent to rank
        best_idx = await self._rank_variants(stage, results, history, sweep_dir)
        best = results[best_idx] if results else {}

        summary = {
            "best_variant": best,
            "all_variants": results,
            "sweep_id": sweep_id,
        }
        (sweep_dir / "sweep_summary.json").write_text(json.dumps(summary, indent=2))
        log.info("[sweep:%s] Best variant: idx=%d params=%s", stage.value, best_idx,
                 best.get("params", {}))
        return summary

    async def _run_variant(
        self,
        stage: Stage,
        sweep_dir: Path,
        idx: int,
        variant_params: dict[str, Any],
        base_overrides: dict[str, Any],
    ) -> dict[str, Any]:
        """Run a single variant and return its result dict."""
        variant_dir = sweep_dir / f"variant_{idx:02d}"
        variant_dir.mkdir(parents=True, exist_ok=True)

        merged_params = {**base_overrides, **variant_params}
        # Validate variant params
        validated = self.config_mgr.validate_and_apply(variant_params)
        merged_params.update(validated)

        # Write variant config
        cfg_path = self.config_mgr.generate_run_config(
            merged_params,
            variant_dir / "config.json",
        )

        # Persist variant params for reproducibility
        (variant_dir / "variant_params.json").write_text(
            json.dumps({"idx": idx, "params": merged_params}, indent=2)
        )

        runner = StageRunner(variant_dir)
        t0 = time.monotonic()
        raw = await runner.run_stage_async(
            stage=stage.value,
            extra_args=[
                "--run-tag", f"sweep_{idx:02d}",
                "--from", stage.value,
                "--to", stage.value,
                str(cfg_path),
            ],
        )
        elapsed = time.monotonic() - t0

        try:
            parser = get_parser(stage)
            parsed = parser.parse(raw.log_dir, raw)
        except Exception as exc:
            parsed = {"stage": stage.value, "status": "fail", "parse_error": str(exc)}

        result = {
            "idx": idx,
            "params": merged_params,
            "result": parsed,
            "exit_code": raw.exit_code,
            "elapsed_seconds": round(elapsed, 2),
        }
        (variant_dir / "result.json").write_text(json.dumps(result, indent=2))
        log.info("[sweep:variant_%02d] status=%s elapsed=%.1fs",
                 idx, parsed.get("status"), elapsed)
        return result

    async def _rank_variants(
        self,
        stage: Stage,
        variants: list[dict[str, Any]],
        history: list[dict[str, Any]],
        sweep_dir: Path,
    ) -> int:
        """Ask the agent to pick the best variant index."""
        if not variants:
            return 0

        # Build a compact summary table for the agent
        table = [
            {
                "idx": v["idx"],
                "params": v["params"],
                "status": v["result"].get("status"),
                "metrics": {
                    k: v["result"].get(k)
                    for k in [
                        "num_cells", "area_um2", "utilization_pct",
                        "worst_setup_slack_ns", "num_violating_paths",
                    ]
                    if k in v["result"]
                },
            }
            for v in variants
        ]

        # Reuse the decision engine but ask about sweep ranking
        # We encode the ranking ask as the current_result
        ranking_ask = {
            "stage": stage.value,
            "status": "pass",  # don't trigger hard gates
            "sweep_ranking_request": True,
            "variants": table,
            "message": (
                "You are ranking sweep variants. Call make_flow_decision with "
                "decision='continue' and set param_updates to the params of the "
                "best-performing variant (lowest area and best timing)."
            ),
        }

        decision = await self.decision_engine.decide_async(
            stage=stage,
            current_result=ranking_ask,
            history=history,
            param_overrides={},
        )
        (sweep_dir / "ranking_decision.json").write_text(json.dumps(decision, indent=2))

        # Identify which variant index the agent's params match best
        agent_params = decision.get("param_updates", {})
        if agent_params:
            for v in variants:
                if all(v["params"].get(k) == val for k, val in agent_params.items()):
                    return v["idx"]

        # Fallback: pick the variant with best timing or lowest area
        passed = [v for v in variants if v["result"].get("status") == "pass"]
        if not passed:
            passed = variants
        best = min(passed, key=lambda v: v["result"].get("area_um2") or float("inf"))
        return best["idx"]
