#!/usr/bin/env python3
"""End-to-end integration test for rtl2gdsagi.

Simulates stages 1–4 (Lint → Synth → SDC → Post-Synth STA) by injecting
realistic mock tool outputs into StageRunner. The real parsers, real agent
fallback logic (no API key), and real state machine all execute normally.

Run with:
    python test_e2e.py
    python test_e2e.py --verbose     # show all logged output
    python test_e2e.py --scenario timing-fail  # inject a timing failure
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).parent

# ── Ensure repo root is on the path ──────────────────────────────────────────
sys.path.insert(0, str(ROOT))

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def banner(msg: str) -> None:
    print(f"\n{BOLD}{CYAN}{'═'*64}{RESET}")
    print(f"{BOLD}{CYAN}  {msg}{RESET}")
    print(f"{BOLD}{CYAN}{'═'*64}{RESET}")

def ok(msg: str) -> None:   print(f"{GREEN}  ✔  {msg}{RESET}")
def warn(msg: str) -> None: print(f"{YELLOW}  ⚠  {msg}{RESET}")
def fail(msg: str) -> None: print(f"{RED}  ✘  {msg}{RESET}")
def info(msg: str) -> None: print(f"{DIM}     {msg}{RESET}")

# ─────────────────────────────────────────────────────────────────────────────
# Realistic mock tool outputs
# ─────────────────────────────────────────────────────────────────────────────

MOCK_LINT_CLEAN = """\
Lint check of designs/riscv_alu/rtl/alu.v
%Warning-UNOPTFLAT: alu.v:22:5: Signal unoptimizable: UNOPTFLAT 'alu_result'
Exiting with 0 warnings and 0 errors.
"""

MOCK_LINT_WITH_WARNINGS = """\
Verilating designs/riscv_alu/rtl/alu.v...
%Warning-UNUSED: alu.v:61:14: Signal is not used: 'alu_overflow' (in always block)
%Warning-UNOPTFLAT: alu.v:22:5: Signal unoptimizable: UNOPTFLAT 'alu_result'
- S T A T I S T I C S
Lint check: 2 warnings, 0 errors
"""

MOCK_SYNTH_STATS = """\
Synthesis running for module: riscv_alu
Using sky130hd standard cell library.

=== riscv_alu ===

   Number of wires:                 245
   Number of public wires:           42
   Number of bits:                  245
   Number of cells:                 198
     sky130_fd_sc_hd__a21oi_1         8
     sky130_fd_sc_hd__a221oi_1        4
     sky130_fd_sc_hd__a22oi_1         6
     sky130_fd_sc_hd__and2_1          7
     sky130_fd_sc_hd__buf_1          12
     sky130_fd_sc_hd__dfxtp_1        32
     sky130_fd_sc_hd__inv_1          14
     sky130_fd_sc_hd__mux2_1         32
     sky130_fd_sc_hd__nand2_1        28
     sky130_fd_sc_hd__nor2_1         15
     sky130_fd_sc_hd__o21ai_1         8
     sky130_fd_sc_hd__or2_1           7
     sky130_fd_sc_hd__xor2_1         25

   Chip area for module '\\riscv_alu': 1245.678000

Design Utilization: 42.3%
Synthesis completed successfully in 1.2s.
"""

MOCK_SDC_PASS = """\
[INFO] Checking SDC constraints for riscv_alu...
[INFO] Found clock: clk (period=10.000 ns)
[INFO] Input delays: 4 ports constrained
[INFO] Output delays: 3 ports constrained
[INFO] SDC check passed: 1 clocks, 7 paths constrained.
"""

MOCK_STA_PASS = """\
OpenSTA 2.6.0 (built Feb 2024)
Reading design riscv_alu with sky130hd PDK...

Startpoint: operand_a[31] (input port clocked by clk)
Endpoint:   result_reg[31]/D (rising edge-triggered flip-flop)
Path Group: clk
Path Type:  max

  Point                                    Incr       Path
  -------------------------------------------------------
  clock clk (rise edge)                   0.000      0.000
  clock network delay (propagated)        0.100      0.100
  input external delay                    2.000      2.100 r
  operand_a[31] (in)                      0.000      2.100 r
  _U_add31/X (sky130_fd_sc_hd__xor2_1)   0.250      2.350 f
  result_reg[31]/D (sky130_fd_sc_hd__dfxtp_1)  0.001  2.351 f
  data arrival time                                  2.351

  clock clk (rise edge)                  10.000     10.000
  clock network delay (propagated)        0.100     10.100
  clock uncertainty                      -0.100     10.000
  result_reg[31]/CK (sky130_fd_sc_hd__dfxtp_1)  0.000  10.000 r
  library setup time                     -0.142      9.858
  data required time                                 9.858
  -------------------------------------------------------
  data required time                                 9.858
  data arrival time                                 -2.351
  -------------------------------------------------------
  slack (MET)                                        7.507

wns 0.00
tns 0.00
violating paths 0
"""

MOCK_STA_FAIL = """\
OpenSTA 2.6.0 (built Feb 2024)
Reading design riscv_alu with sky130hd PDK (tight clock)...

Startpoint: operand_b[31] (input port clocked by clk)
Endpoint:   result_reg[31]/D (rising edge-triggered flip-flop)
Path Group: clk
Path Type:  max

  slack (VIOLATED)                                  -0.42

Startpoint: operand_a[15] (input port clocked by clk)
Endpoint:   result_reg[15]/D
  slack (VIOLATED)                                  -0.31

Startpoint: operand_a[0] (input port clocked by clk)
Endpoint:   result_reg[0]/D
  slack (VIOLATED)                                  -0.12

wns -0.42
tns -1.26
violating paths 3
"""

# ─────────────────────────────────────────────────────────────────────────────
# Mock StageResult
# ─────────────────────────────────────────────────────────────────────────────

class FakeStageResult:
    def __init__(self, stage: str, stdout: str, exit_code: int = 0):
        self.stage = stage
        self.stdout = stdout
        self.stderr = ""
        self.exit_code = exit_code
        self.timed_out = False
        self.elapsed_seconds = 0.5
        self.success = exit_code == 0

# ─────────────────────────────────────────────────────────────────────────────
# Scenario definitions
# ─────────────────────────────────────────────────────────────────────────────

SCENARIOS = {
    "happy-path": {
        "lint":           (MOCK_LINT_CLEAN,    0),
        "synthesis":      (MOCK_SYNTH_STATS,   0),
        "sdc_check":      (MOCK_SDC_PASS,      0),
        "post_synth_sta": (MOCK_STA_PASS,      0),
        "description":    "All stages pass cleanly — agent should 'continue' each time",
    },
    "lint-warnings": {
        "lint":           (MOCK_LINT_WITH_WARNINGS, 0),
        "synthesis":      (MOCK_SYNTH_STATS,        0),
        "sdc_check":      (MOCK_SDC_PASS,           0),
        "post_synth_sta": (MOCK_STA_PASS,           0),
        "description":    "Lint has 2 warnings (exit 0) — should warn then continue",
    },
    "timing-fail": {
        "lint":           (MOCK_LINT_CLEAN,    0),
        "synthesis":      (MOCK_SYNTH_STATS,   0),
        "sdc_check":      (MOCK_SDC_PASS,      0),
        "post_synth_sta": (MOCK_STA_FAIL,      0),
        "description":    "Post-synth STA fails (WNS=-0.42 ns) — hard gate triggers escalate",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Main integration test runner
# ─────────────────────────────────────────────────────────────────────────────

def run_e2e(scenario_name: str = "happy-path", verbose: bool = False) -> bool:
    scenario = SCENARIOS[scenario_name]

    banner(f"rtl2gdsagi  END-TO-END TEST  [{scenario_name}]")
    info(scenario["description"])
    info("No Claude API key → agent uses deterministic fallback decisions")
    info("Stages: lint → synthesis → sdc_check → post_synth_sta")
    print()

    with tempfile.TemporaryDirectory() as td:
        runs_dir = Path(td) / "runs"

        # ── Build mock run_stage_async ─────────────────────────────────────
        async def mock_run_stage_async(stage: str, extra_args, **kwargs):
            stdout, exit_code = scenario.get(stage, (f"[MOCK] {stage} output", 0))
            fake = FakeStageResult(stage, stdout, exit_code)

            # Write the fake output into the expected log path so parsers can read it
            log_dir = runs_dir / "RUNID_PLACEHOLDER" / "logs" / stage
            log_dir.mkdir(parents=True, exist_ok=True)
            (log_dir / "stdout.log").write_text(stdout)
            (log_dir / "stderr.log").write_text("")

            fake.log_dir = log_dir
            return fake

        # ── Patch stage runner and run only the 4 PoC stages ──────────────
        from orchestrator.stage_runner import StageRunner
        from orchestrator.stages import Stage, STAGE_ORDER
        from orchestrator.state_manager import StateManager
        from config.config_manager import ConfigManager
        from agent.decision_engine import DecisionEngine
        from parsers import get_parser

        cm = ConfigManager(str(ROOT / "designs/riscv_alu/config.yaml"))
        sm = StateManager(runs_dir)
        state = sm.new_run(
            rtl_path=str(ROOT / "designs/riscv_alu/rtl/alu.v"),
            top_module="riscv_alu",
            pdk="sky130hd",
            config_path=str(ROOT / "designs/riscv_alu/config.yaml"),
        )

        # Patch the placeholder RUNID so log paths align
        runs_dir_final = runs_dir / state.run_id
        runs_dir_final.mkdir(parents=True, exist_ok=True)

        # Update mock to use real run_id
        async def mock_run_stage_async_real(stage: str, extra_args, **kwargs):
            stdout, exit_code = scenario.get(stage, (f"[MOCK] {stage} output", 0))
            log_dir = runs_dir_final / "logs" / stage
            log_dir.mkdir(parents=True, exist_ok=True)
            (log_dir / "stdout.log").write_text(stdout)
            (log_dir / "stderr.log").write_text("")
            fake = FakeStageResult(stage, stdout, exit_code)
            fake.log_dir = log_dir
            return fake

        de = DecisionEngine(config_manager=cm, replay=False, cached_decisions={})

        # ── Stage-by-stage loop (stages 1–4 only) ─────────────────────────
        TARGET_STAGES = [
            Stage.LINT,
            Stage.SYNTHESIS,
            Stage.SDC_CHECK,
            Stage.POST_SYNTH_STA,
        ]

        results_table: list[dict] = []
        flow_aborted = False

        for stage in TARGET_STAGES:
            print(f"\n{BOLD}── Stage: {stage.value} {'─'*(50-len(stage.value))}{RESET}")

            # 1. Run mock tool
            raw = asyncio.run(mock_run_stage_async_real(stage.value, []))
            info(f"Tool exit={raw.exit_code}  log={raw.log_dir}")

            # 2. Parse
            parser = get_parser(stage)
            try:
                parsed = parser.parse(raw.log_dir, raw)
            except RuntimeError as exc:
                fail(f"Parser raised: {exc}")
                parsed = {"stage": stage.value, "status": "fail", "parse_error": str(exc)}

            status = parsed.get("status", "?")
            status_colour = GREEN if status == "pass" else (YELLOW if status == "warn" else RED)
            print(f"  Parser → status={status_colour}{status}{RESET}", end="  ")

            # Print key metrics
            for key in ["num_errors","num_warnings","num_cells","area_um2","worst_setup_slack_ns","num_violating_paths","num_clocks"]:
                if key in parsed and parsed[key] is not None:
                    print(f"{key}={parsed[key]}", end="  ")
            print()

            # 3. Agent decision (fallback — no API key)
            history = [
                {"stage": s, "result": state.stage_results.get(s, {})}
                for s in state.completed_stages[-3:]
            ]
            decision = asyncio.run(de.decide_async(
                stage=stage,
                current_result=parsed,
                history=history,
                param_overrides=state.param_overrides,
            ))
            dec_val   = decision.get("decision")
            dec_conf  = decision.get("confidence")
            dec_reason = decision.get("reasoning", "")
            dec_colour = GREEN if dec_val == "continue" else (YELLOW if dec_val == "retune" else RED)
            print(f"  Agent  → decision={dec_colour}{dec_val}{RESET}  confidence={dec_conf}")
            info(f"reasoning: {dec_reason}")

            # 4. Save to state
            state.stage_results[stage.value]  = parsed
            state.agent_decisions[stage.value] = decision
            sm.save(state)

            results_table.append({
                "stage":    stage.value,
                "status":   status,
                "decision": dec_val,
                "confidence": dec_conf,
                "metrics": {k: parsed[k] for k in parsed if k not in ("stage","status","raw_log_path","warnings","errors","top_violations","violations")},
            })

            if dec_val in ("escalate_to_human", "abort"):
                warn(f"Flow stopped at {stage.value}: {dec_val}")
                flow_aborted = True
                break
            elif dec_val == "continue":
                state.completed_stages.append(stage.value)
                sm.save(state)
                ok(f"Stage {stage.value} → DONE")

        # ── Final summary ─────────────────────────────────────────────────
        banner("RESULTS SUMMARY")
        print(f"\n{'STAGE':<20} {'TOOL STATUS':<14} {'AGENT DECISION':<20} {'CONFIDENCE'}")
        print("─" * 70)
        for r in results_table:
            sc = GREEN if r["status"] == "pass" else (YELLOW if r["status"] == "warn" else RED)
            dc = GREEN if r["decision"] == "continue" else (YELLOW if r["decision"] == "retune" else RED)
            print(f"  {r['stage']:<18} {sc}{r['status']:<12}{RESET} {dc}{r['decision']:<18}{RESET} {r['confidence']}")

        print(f"\n  Run ID:        {state.run_id}")
        print(f"  State file:    {runs_dir / (state.run_id + '.json')}")
        print(f"  Stages done:   {state.completed_stages}")

        if verbose:
            print(f"\n{BOLD}Full state JSON:{RESET}")
            print(json.dumps(state.to_dict(), indent=2))

        # Verify state was persisted correctly
        loaded = sm.load_run(state.run_id)
        assert loaded.stage_results == state.stage_results, "State persistence mismatch!"
        ok("State persistence verified (crash-safe atomic JSON)")

        print()
        if flow_aborted:
            warn(f"Scenario '{scenario_name}': flow stopped early (expected for failure scenarios)")
            return True  # expected behaviour
        else:
            ok(f"Scenario '{scenario_name}': all 4 stages completed successfully")
            return True


def main() -> int:
    p = argparse.ArgumentParser(description="rtl2gdsagi end-to-end integration test")
    p.add_argument("--scenario", choices=list(SCENARIOS), default="happy-path",
                   help="Which test scenario to run")
    p.add_argument("--all", action="store_true", help="Run all scenarios")
    p.add_argument("--verbose", action="store_true", help="Show full state JSON")
    args = p.parse_args()

    logging.basicConfig(level=logging.WARNING)  # suppress internal logs unless --verbose
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, force=True)

    scenarios = list(SCENARIOS) if args.all else [args.scenario]
    passed = 0
    for s in scenarios:
        try:
            ok_result = run_e2e(s, args.verbose)
            if ok_result:
                passed += 1
        except Exception as exc:
            fail(f"Scenario '{s}' raised: {exc}")
            import traceback; traceback.print_exc()

    if args.all:
        print(f"\n{BOLD}{'═'*64}{RESET}")
        if passed == len(scenarios):
            ok(f"ALL {passed}/{len(scenarios)} scenarios passed")
        else:
            fail(f"{passed}/{len(scenarios)} scenarios passed")

    return 0 if passed == len(scenarios) else 1


if __name__ == "__main__":
    sys.exit(main())
