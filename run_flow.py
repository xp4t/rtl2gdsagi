#!/usr/bin/env python3
"""RTL-to-GDS Agentic Orchestrator — CLI entrypoint.

Usage::

    python run_flow.py --rtl designs/riscv_alu/rtl/alu.v \\
                       --top riscv_alu \\
                       --config config/defaults.yaml \\
                       --pdk sky130hd

    # Resume after a crash
    python run_flow.py --resume 20240101T120000_abc123

    # Replay a prior run without calling the LLM
    python run_flow.py --resume 20240101T120000_abc123 --replay-decisions

    # Cap retries per stage
    python run_flow.py --rtl ... --max-iterations 2
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging setup — must happen before any project import so all loggers pick
# up the root configuration.
# ---------------------------------------------------------------------------

def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%S"
    logging.basicConfig(level=level, format=fmt, datefmt=datefmt)
    # Suppress noisy third-party loggers
    for noisy in ("anthropic", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Agentic RTL-to-GDS orchestrator (OpenLane2 + Claude)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # -- Design inputs -------------------------------------------------------
    design_grp = p.add_argument_group("Design inputs")
    design_grp.add_argument(
        "--rtl",
        metavar="PATH",
        help="Path to the top-level RTL file (or directory containing *.v/*.sv)",
    )
    design_grp.add_argument(
        "--top", "--module",
        metavar="MODULE",
        dest="top",
        help="Top-level module name",
    )
    design_grp.add_argument(
        "--pdk",
        default="sky130hd",
        metavar="PDK",
        help="PDK variant (default: sky130hd)",
    )
    design_grp.add_argument(
        "--config",
        metavar="YAML",
        default="config/defaults.yaml",
        help="Path to design YAML config (default: config/defaults.yaml)",
    )

    # -- Run control ---------------------------------------------------------
    run_grp = p.add_argument_group("Run control")
    run_grp.add_argument(
        "--max-iterations",
        type=int,
        default=3,
        metavar="N",
        help="Max retune attempts per stage before escalating (default: 3)",
    )
    run_grp.add_argument(
        "--resume",
        metavar="RUN_ID",
        help="Resume an interrupted run by its run_id",
    )
    run_grp.add_argument(
        "--replay-decisions",
        action="store_true",
        help="Replay a prior run using cached LLM decisions (no API calls)",
    )
    run_grp.add_argument(
        "--runs-dir",
        metavar="DIR",
        default="runs",
        help="Directory for run state and logs (default: ./runs)",
    )
    run_grp.add_argument(
        "--from-stage",
        metavar="STAGE",
        dest="from_stage",
        help="Start flow from this stage (e.g. placement). Implies --resume behaviour.",
    )
    run_grp.add_argument(
        "--to-stage",
        metavar="STAGE",
        dest="to_stage",
        help="Stop flow after this stage.",
    )

    # -- Sweep ---------------------------------------------------------------
    sweep_grp = p.add_argument_group("Strategy sweep")
    sweep_grp.add_argument(
        "--sweep",
        metavar="STAGE",
        help="Run a strategy sweep for the given stage (e.g. synthesis)",
    )
    sweep_grp.add_argument(
        "--sweep-parallelism",
        type=int,
        default=2,
        metavar="K",
        help="Number of sweep variants to run concurrently (default: 2)",
    )

    # -- Misc ----------------------------------------------------------------
    p.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    p.add_argument("--list-runs", action="store_true", help="List known runs and exit")
    p.add_argument("--version", action="version", version="rtl2gdsagi 0.1.0")

    return p.parse_args(argv)


def _validate_args(args: argparse.Namespace) -> None:
    """Raise SystemExit with a helpful message on bad args."""
    if args.list_runs:
        return  # handled separately
    if args.resume or args.replay_decisions:
        if not args.resume:
            sys.exit("--replay-decisions requires --resume <run_id>")
        return  # resuming — no --rtl/--top required
    if not args.rtl:
        sys.exit("--rtl is required for a new run (or use --resume to continue)")
    if not args.top:
        sys.exit("--top <module_name> is required for a new run")
    rtl = Path(args.rtl)
    if not rtl.exists():
        sys.exit(f"RTL path not found: {rtl}")
    cfg = Path(args.config)
    if not cfg.exists():
        sys.exit(
            f"Config file not found: {cfg}\n"
            f"  Run: cp config/defaults.yaml {cfg}  and customise it."
        )


def _list_runs(runs_dir: Path) -> None:
    from orchestrator.state_manager import StateManager
    sm = StateManager(runs_dir)
    runs = sm.list_runs()
    if not runs:
        print("No runs found in", runs_dir)
        return
    print(f"{'RUN_ID':<35}  {'STATUS':<12}  {'STAGE':<20}  UPDATED")
    print("-" * 90)
    import json
    for run_id in runs:
        try:
            rs = sm.load_run(run_id)
            stage = rs.current_stage.value if rs.current_stage else "-"
            print(f"{run_id:<35}  {rs.status:<12}  {stage:<20}  {rs.updated_at}")
        except Exception as exc:
            print(f"{run_id:<35}  ERROR: {exc}")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    _setup_logging(args.verbose)

    runs_dir = Path(args.runs_dir)

    if args.list_runs:
        _list_runs(runs_dir)
        return 0

    _validate_args(args)

    # -- Check API key early -------------------------------------------------
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logging.getLogger(__name__).warning(
            "ANTHROPIC_API_KEY is not set. Agent decisions will fall back to "
            "conservative defaults (continue/escalate). Set the env var for "
            "real LLM-assisted decisions."
        )

    # -- Launch orchestrator -------------------------------------------------
    from orchestrator.orchestrator import Orchestrator

    orch = Orchestrator(
        rtl_path=args.rtl or "",
        top_module=args.top or "",
        pdk=args.pdk,
        config_path=args.config,
        runs_dir=runs_dir,
        max_iterations=args.max_iterations,
        resume_run_id=args.resume,
        replay_decisions=args.replay_decisions,
        from_stage=args.from_stage,
        to_stage=args.to_stage,
    )

    # Sweep mode
    if args.sweep:
        from orchestrator.stages import Stage
        from sweep.sweep_controller import SweepController
        import asyncio
        try:
            stage = Stage(args.sweep)
        except ValueError:
            valid = [s.value for s in Stage]
            sys.exit(f"Unknown stage {args.sweep!r}. Valid stages: {valid}")

        sweep = SweepController(
            run_dir=orch.run_dir,
            config_manager=orch.config_mgr,
            decision_engine=orch.decision_engine,
            max_parallel=args.sweep_parallelism,
        )
        result = asyncio.run(
            sweep.run_sweep(stage, orch.state.param_overrides, [])
        )
        import json
        print(json.dumps(result, indent=2))
        return 0

    # Full flow
    success = orch.run()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
