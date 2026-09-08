"""Command line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .agent.client import ClaudeAgent, ScriptedAgent, api_key_present, resolve_model
from .config import RunConfig
from .errors import ConfigError, PDKError
from .ir import SCHEMA, describe_section
from .runner import Orchestrator
from .stages import STAGE_ORDER, STAGES
from .state import RunState
from .taxonomy import TAXONOMY

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_ESCALATED = 3
EXIT_BUDGET = 4
EXIT_SAFETY = 5


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rtl2gdsagi",
        description="Agentic RTL-to-GDSII orchestrator with schema-bounded "
                    "self-healing and deterministic verdicts.",
    )
    p.add_argument("--version", action="version", version=f"rtl2gdsagi {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run the flow")
    run.add_argument("--rtl", help="RTL source directory (read-only)")
    run.add_argument("--top", help="top module name")
    run.add_argument("--pdk", default=None, help="PDK name, default sky130A")
    run.add_argument("--pdk-root", default=None, help="PDK root path")
    run.add_argument("--retry-limit", type=int, default=None,
                     help="per-stage attempt limit (default 3)")
    run.add_argument("--budget", type=int, default=None,
                     help="global attempt budget across all stages")
    run.add_argument("--config", dest="config_path", default=None,
                     help="YAML/JSON config file")
    run.add_argument("--resume-from", default=None, metavar="STAGE",
                     help="start at this stage instead of the beginning. This "
                          "does NOT restore an earlier run: every run gets a "
                          "fresh artifact ledger, so the stage stops with "
                          "'required input is unavailable' unless its inputs "
                          "already exist in this run directory")
    run.add_argument("--model", default=None,
                     help=f"Claude model (default {resolve_model()})")
    run.add_argument("--run-dir", default=None, help="explicit run directory")
    run.add_argument("--skip", action="append", default=None, metavar="STAGE",
                     help="skip a stage (repeatable). Recorded in the signoff "
                          "bundle; a skipped signoff gate always fails signoff, "
                          "so this measures the rest of the flow rather than "
                          "producing a clean result")
    run.add_argument("--mock-tools", action="store_true",
                     help="use the mock invoker; runs the full state machine "
                          "without invoking any EDA tool")
    run.add_argument("--no-api", action="store_true",
                     help="do not call Claude; diagnosis becomes a no-op and any "
                          "hard failure escalates immediately")
    run.add_argument("--dry-run", action="store_true",
                     help="render every config and exit without running tools")
    run.add_argument("--repair-policy", choices=("ask", "auto", "manual"), default=None,
                     help="known-failure policy; ask uses manual in a non-TTY")
    run.add_argument("--klayout-backend", choices=("native", "native_isolated", "container"),
                     default=None, help="initial KLayout execution backend")

    sub.add_parser("stages", help="list the stage graph")
    sub.add_parser("taxonomy", help="show the failure class -> stage table")

    errors = sub.add_parser("errors", help="query the offline OpenROAD failure catalog")
    errors.add_argument("error_id", nargs="?")
    errors.add_argument("--tool")
    errors.add_argument("--search")
    errors.add_argument("--known-fixes", action="store_true")

    schema = sub.add_parser("schema", help="show the agent-writable IR schema")
    schema.add_argument("section", nargs="?", help="limit to one section")

    st = sub.add_parser("status", help="summarise a run directory")
    st.add_argument("run_dir")

    doctor = sub.add_parser("doctor", help="check tools and PDK are usable")
    doctor.add_argument("--pdk", default="sky130A")
    doctor.add_argument("--pdk-root", default=None)
    return p


def cmd_stages() -> int:
    print(f"{'#':>2}  {'stage':<14} {'tool':<10} {'gate':<9} {'ir section':<11} produces")
    print("-" * 88)
    for i, s in enumerate(STAGES):
        print(
            f"{i:>2}  {s.name:<14} {str(s.tool):<10} {str(s.gate):<9} "
            f"{(s.ir_section or '-'):<11} {', '.join(s.produces) or '-'}"
        )
    print()
    print("gate: hard = blocks and can trigger rollback; advisory = logged only, "
          "never blocks; none = produces data for the planner.")
    return EXIT_OK


def cmd_taxonomy() -> int:
    print(f"{'failure class':<18} {'-> stage':<14} {'resolution':<17} forbids")
    print("-" * 96)
    for e in TAXONOMY:
        stage = e.responsible_stage.value if e.responsible_stage else "-"
        if e.escalate_to:
            stage += f" >{e.escalate_to.value}"
        print(
            f"{e.failure.value:<18} {stage:<14} {e.resolution.value:<17} "
            f"{', '.join(e.forbids) or '-'}"
        )
    print()
    print("'>' marks the deeper target used when shallow retries are exhausted.")
    return EXIT_OK


def cmd_schema(section: str | None) -> int:
    if section:
        if section not in SCHEMA:
            print(f"unknown section {section!r}; known: {', '.join(sorted(SCHEMA))}",
                  file=sys.stderr)
            return EXIT_USAGE
        print(json.dumps({section: describe_section(section)}, indent=2))
        return EXIT_OK
    print(json.dumps({s: describe_section(s) for s in sorted(SCHEMA)}, indent=2))
    return EXIT_OK


def cmd_errors(error_id: str | None, *, tool: str | None = None,
               search: str | None = None, known_fixes: bool = False) -> int:
    from .error_knowledge.known_fixes import has_curated_fix
    from .error_knowledge.openroad_catalog import OpenRoadCatalog

    catalog = OpenRoadCatalog()
    if error_id:
        item = catalog.get(error_id)
        if item is None:
            print(f"unknown OpenROAD message ID {error_id}", file=sys.stderr)
            return EXIT_ERROR
        print(f"{item.canonical_id}  {item.severity}  OpenROAD/{item.subsystem}")
        print(f"source: {item.source_file}:{item.source_line or '?'}")
        print(f"message: {item.canonical_message or '-'}")
        if item.documentation:
            print(f"documentation: {item.documentation}")
        curated = has_curated_fix(item.canonical_id)
        print(f"curated executable repair: {'yes' if curated else 'no'}")
        if curated:
            print("allowed actions: typed IR updates")
            print("rollback: derived from each changed IR section (PDN or floorplan)")
        return EXIT_OK
    rows = catalog.query(tool=tool, search=search, failures_only=True)
    if known_fixes:
        rows = [m for m in rows if has_curated_fix(m.canonical_id)]
    for item in rows:
        mark = " repair" if has_curated_fix(item.canonical_id) else ""
        print(f"{item.canonical_id:<10} {item.severity:<8} {item.canonical_message[:100]}{mark}")
    print(f"{len(rows)} message(s); catalog revision {catalog.metadata.revision}")
    return EXIT_OK


def cmd_status(run_dir: str) -> int:
    try:
        state = RunState.load(run_dir)
    except (OSError, ValueError, KeyError) as exc:
        print(f"cannot read run state: {exc}", file=sys.stderr)
        return EXIT_ERROR
    print(f"run  : {state.run_id}")
    print(f"top  : {state.config.get('top')}")
    print(f"state: {state.status}")
    print()
    print(f"{'stage':<14} {'status':<9} {'tries':>5}  last error")
    print("-" * 76)
    for sid in STAGE_ORDER:
        s = state.stage(sid)
        if s.attempts == 0 and s.status.value == "pending":
            continue
        print(f"{sid.value:<14} {s.status.value:<9} {s.attempts:>5}  {(s.last_error or '')[:40]}")
    rep = Path(state.run_dir) / "failure_report.md"
    if rep.is_file():
        print(f"\nfailure report: {rep}")
    return EXIT_OK if state.status.value == "ok" else EXIT_ERROR


def cmd_doctor(pdk_name: str, pdk_root: str | None) -> int:
    from .tools.invoker import RealInvoker
    from .stages import Tool

    inv = RealInvoker()
    print("tools:")
    missing = []
    _GATE = {
        Tool.IVERILOG: "sim gate (skipped without it)",
        Tool.EQY: "LEC gates (signoff refuses to certify without them)",
    }
    for t in (Tool.VERILATOR, Tool.IVERILOG, Tool.YOSYS, Tool.EQY,
              Tool.OPENSTA, Tool.OPENROAD, Tool.KLAYOUT):
        ok = inv.available(t)
        note = "" if ok else f"  <- {_GATE.get(t, 'required')}"
        print(f"  {str(t):<11} {'ok' if ok else 'MISSING'}{note}")
        if not ok:
            missing.append(str(t))

    print(f"\npdk {pdk_name}:")
    try:
        from .pdk import PDKConfig
        pdk = PDKConfig.discover(pdk_name, pdk_root)
    except PDKError as exc:
        print(f"  {exc}")
        return EXIT_ERROR
    print(f"  root      {pdk.root}")
    for label, path in (
        ("liberty", pdk.liberty_path), ("tech lef", pdk.tech_lef_path),
        ("cell lef", pdk.cell_lef_path), ("drc deck", pdk.drc_deck_path),
        ("lvs deck", pdk.lvs_deck_path),
    ):
        print(f"  {label:<9} {'ok  ' if path.exists() else 'MISS'} {path}")
    print(f"  corners   {len(pdk.timing_libs())}")

    print("\napi:")
    print(f"  ANTHROPIC_API_KEY {'set' if api_key_present() else 'NOT SET'}")
    print(f"  model             {resolve_model()}")
    return EXIT_OK if not missing else EXIT_ERROR


def cmd_run(args: argparse.Namespace) -> int:
    try:
        cfg = RunConfig.build(
            rtl_dir=args.rtl,
            top=args.top,
            pdk_name=args.pdk,
            pdk_root=args.pdk_root,
            retry_limit=args.retry_limit,
            model=args.model,
            resume_from=args.resume_from,
            config_path=args.config_path,
            mock_tools=args.mock_tools or None,
            skip_stages=args.skip,
            repair_policy=args.repair_policy,
            klayout_backend=args.klayout_backend,
        )
    except (ConfigError, PDKError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    if args.no_api:
        agent = ScriptedAgent()
    elif not api_key_present():
        print(
            "error: ANTHROPIC_API_KEY is not set. Export it, or pass --no-api to "
            "run without diagnosis (failures will escalate immediately).",
            file=sys.stderr,
        )
        return EXIT_USAGE
    else:
        agent = ClaudeAgent(cfg.model)

    orch = Orchestrator(
        cfg, agent=agent,
        run_dir=Path(args.run_dir) if args.run_dir else None,
        global_budget=args.budget,
    )
    print(f"run directory: {orch.run_dir}")

    if args.dry_run:
        return _dry_run(orch)

    code = orch.run()
    if code == EXIT_OK:
        print(f"\nsignoff clean. bundle: {orch.run_dir / 'signoff.json'}")
    else:
        rep = orch.run_dir / "failure_report.md"
        if rep.is_file():
            print(f"\n{rep.read_text(encoding='utf-8')[:2000]}", file=sys.stderr)
    return code


def _dry_run(orch: Orchestrator) -> int:
    """Render every stage's config without invoking anything."""
    from .render import render
    from .stages import get_stage as _gs

    orch.prepare()
    ok = 0
    for sid in STAGE_ORDER:
        spec = _gs(sid)
        if sid not in orch._renderable() and sid.value != "sdc":
            continue
        ctx = orch._context(spec)
        try:
            text = render(sid, orch.ir, ctx)
        except (KeyError, ValueError) as exc:
            print(f"  {sid.value:<14} SKIP  ({exc})")
            continue
        out = orch.stage_dir(sid) / f"{sid.value}.rendered"
        out.write_text(text, encoding="utf-8")
        print(f"  {sid.value:<14} rendered {len(text):>6} bytes -> {out}")
        ok += 1
    print(f"\n{ok} config(s) rendered. No tools were invoked.")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        return cmd_run(args)
    if args.command == "stages":
        return cmd_stages()
    if args.command == "taxonomy":
        return cmd_taxonomy()
    if args.command == "errors":
        return cmd_errors(args.error_id, tool=args.tool, search=args.search,
                          known_fixes=args.known_fixes)
    if args.command == "schema":
        return cmd_schema(args.section)
    if args.command == "status":
        return cmd_status(args.run_dir)
    if args.command == "doctor":
        return cmd_doctor(args.pdk, args.pdk_root)
    return EXIT_USAGE


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
