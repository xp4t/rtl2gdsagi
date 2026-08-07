# rtl2gdsagi 🔧➡️💎

> **Agentic RTL-to-GDS orchestrator** — OpenLane2 (sky130hd) driven by Claude AI at every stage checkpoint

[![CI](https://github.com/xp4t/rtl2gdsagi/actions/workflows/ci.yml/badge.svg)](https://github.com/xp4t/rtl2gdsagi/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-green.svg)](LICENSE)
[![OpenLane2](https://img.shields.io/badge/backend-OpenLane2-purple)](https://github.com/efabless/openlane2)

---

## What is this?

`rtl2gdsagi` wraps the full **OpenLane2** open-source ASIC flow (Yosys → OpenROAD → Magic → Netgen → KLayout) and places a **Claude AI agent** at every stage checkpoint. The agent inspects structured results from each stage and decides: **continue**, **retune parameters**, **escalate to a human**, or **abort**.

**The LLM never generates raw EDA commands.** It only adjusts config knobs (e.g. `PL_TARGET_DENSITY`, `CLOCK_PERIOD`) within validated ranges — a deterministic wrapper runs the actual tools.

```
RTL  ──►  Lint  ──►  Synth  ──►  SDC  ──►  STA  ──►  FP  ──►  PnR  ──►  Signoff  ──►  GDS
               ▲       ▲           ▲          ▲       ▲     ▲         ▲
               └───────┴───────────┴──────────┴───────┴─────┴─────────┘
                                  Claude agent at each checkpoint
                          (tool-use / function-calling, never free text)
```

---

## Features

| Feature | Details |
|---|---|
| **14-stage state machine** | Lint → Synth → SDC → STA (×3) → FP → Placement → CTS → Routing → DRC → LVS → GDS |
| **Crash-safe persistence** | Atomic JSON state after every stage — resume from any point with `--resume <run_id>` |
| **Structured agent decisions** | Claude uses tool-use (`make_flow_decision`) — strict JSON schema, never free text |
| **Hard gates in code** | DRC/LVS/signoff STA failures always escalate — LLM cannot override this |
| **Param validation** | All LLM `param_updates` clamped/rejected against YAML-defined allowed ranges |
| **Strategy sweeps** | Run K config variants in parallel, agent ranks them by PPA + timing |
| **Full audit trail** | Every LLM call logged with timestamp, prompt, and decision |
| **Deterministic replay** | Re-run any prior run without calling the API using `--replay-decisions` |
| **API fallback** | Network timeout or missing key → conservative fallback, never crashes the flow |
| **Zero-config start** | `python setup_env.py` installs OpenLane2 + sky130hd PDK + all deps |

---

## Quick start

### 1. Clone and setup (≈ 5–15 min first time, downloads PDK)

```bash
git clone https://github.com/your-org/rtl2gdsagi.git
cd rtl2gdsagi
python setup_env.py          # installs everything — Rust, OpenLane2, sky130hd PDK
```

### 2. Set your Claude API key

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

> No key? The flow still runs with conservative fallback decisions — great for testing.

### 3. Run the demo (RISC-V ALU, stages 1–4)

```bash
python run_flow.py \
    --rtl  designs/riscv_alu/rtl/alu.v \
    --top  riscv_alu \
    --config designs/riscv_alu/config.yaml
```

### 4. Watch it work

```
2024-01-15T10:30:00  INFO  === Stage: Lint (Verilator) (attempt 1/3) ===
2024-01-15T10:30:01  INFO  [lint] Finished in 0.8s  exit=0
2024-01-15T10:30:01  INFO  [lint] Agent decision: continue (confidence=high)
2024-01-15T10:30:01  INFO  === Stage: Synthesis (Yosys/OpenLane2) (attempt 1/3) ===
...
```

---

## Test it (no PDK or API key needed)

```bash
pip install -r requirements.txt
pytest                      # 35 unit tests — parsers, config, agent schema, state
python test_e2e.py --all    # 3 end-to-end scenarios with realistic mock tool output
```

```
✔  Scenario 'happy-path':    all 4 stages completed successfully
✔  Scenario 'lint-warnings': all 4 stages completed successfully
⚠  Scenario 'timing-fail':   flow stopped at post_synth_sta → escalate_to_human (expected)
✔  ALL 3/3 scenarios passed
```

---

## CLI reference

```bash
# New full run
python run_flow.py --rtl <path> --top <module> --config <yaml>

# Resume after crash
python run_flow.py --resume 20240115T103000_abc123

# Replay without LLM (cached decisions)
python run_flow.py --resume 20240115T103000_abc123 --replay-decisions

# Cap retries per stage
python run_flow.py --rtl ... --max-iterations 2

# Parallel strategy sweep for synthesis
python run_flow.py --rtl ... --sweep synthesis --sweep-parallelism 3

# List all runs
python run_flow.py --list-runs
```

---

## Repository layout

```
rtl2gdsagi/
│
├── run_flow.py               ← CLI entrypoint
├── setup_env.py              ← One-shot environment setup
├── test_e2e.py               ← End-to-end integration test
├── requirements.txt
├── pyproject.toml
│
├── orchestrator/
│   ├── orchestrator.py       ← State machine (stage retry loop, hard gates)
│   ├── stages.py             ← Stage enum, ordering, hard-gate sets
│   ├── stage_runner.py       ← Async subprocess wrapper + timeout
│   └── state_manager.py     ← Atomic JSON crash-safe persistence
│
├── parsers/
│   ├── lint_parser.py        ← Verilator → errors/warnings JSON
│   ├── synth_parser.py       ← Yosys → cells/area/utilisation JSON
│   ├── sta_parser.py         ← OpenSTA → WNS/TNS/violations JSON
│   ├── drc_parser.py         ← Magic + KLayout XML → violation count JSON
│   ├── lvs_parser.py         ← Netgen → match/mismatch JSON
│   └── sdc_parser.py         ← SDC → constraint completeness JSON
│
├── agent/
│   ├── decision_engine.py    ← Claude tool-use, audit logging, replay, fallback
│   ├── schema.py             ← make_flow_decision tool schema + AgentDecision
│   └── system_prompts.py     ← Per-stage system prompts (tunable params listed)
│
├── config/
│   ├── config_manager.py     ← YAML loader + LLM param validation/clamping
│   └── defaults.yaml         ← Global defaults + allowed param ranges
│
├── sweep/
│   └── sweep_controller.py   ← K-variant parallel sweep + agent ranking
│
├── designs/
│   └── riscv_alu/
│       ├── rtl/alu.v         ← RV32I ALU demo design (all 12 operations)
│       ├── config.yaml       ← Design-specific config + param ranges
│       └── constraints.sdc   ← Timing constraints (100 MHz, sky130hd)
│
└── tests/                    ← 35 unit tests (no EDA tools needed)
```

---

## How the agent layer works

Every stage produces a **normalised JSON report** (from the parser), which is fed to Claude along with the last 3 stages of history and a per-stage system prompt listing exactly which parameters can be tuned at this stage.

Claude **must** respond by calling the `make_flow_decision` tool — never plain text:

```json
{
  "decision":    "continue | retune | escalate_to_human | abort",
  "reasoning":   "WNS = -0.42 ns — tightening clock period for retry",
  "param_updates": { "CLOCK_PERIOD": 12.0 },
  "confidence":  "high | medium | low"
}
```

Before applying `param_updates`, the orchestrator **validates every value against the YAML-defined allowed range** — out-of-range LLM suggestions are clamped or rejected silently.

### Hard gates (override any agent decision)

| Stage | Trigger | Enforced action |
|---|---|---|
| `drc` | `total_violations > 0` | `escalate_to_human` |
| `lvs` | `circuits_matched == false` | `escalate_to_human` |
| `post_route_sta` | `worst_setup_slack_ns < 0` | `escalate_to_human` / bounded retry |
| `post_synth_sta` | `status == fail` | agent may retune but cannot `continue` |

---

## Parser output schemas

### STA (post_synth / post_place / post_cts / post_route)
```json
{
  "stage": "post_place_sta",
  "status": "fail",
  "worst_setup_slack_ns": -0.42,
  "worst_hold_slack_ns": 0.05,
  "total_negative_slack_ns": -1.26,
  "num_violating_paths": 3,
  "top_violations": [
    { "endpoint": "result_reg[31]/D", "slack_ns": -0.42 }
  ],
  "raw_log_path": "runs/<run_id>/logs/post_place_sta/"
}
```

### Synthesis
```json
{
  "stage": "synthesis",
  "status": "pass",
  "num_cells": 198,
  "num_wires": 245,
  "area_um2": 1245.68,
  "utilization_pct": 42.3,
  "raw_log_path": "..."
}
```

### DRC / LVS
```json
{
  "stage": "drc",
  "status": "fail",
  "total_violations": 4,
  "violations": [{ "rule": "metal1 spacing", "count": 3 }],
  "raw_log_path": "..."
}
```

---

## Config reference

All parameters below can be set in your design's `config.yaml`. Any value the agent suggests outside the defined range is automatically clamped.

| Parameter | Default | Range | Description |
|---|---|---|---|
| `CLOCK_PERIOD` | 10.0 ns | 2–100 | Target clock period |
| `FP_CORE_UTIL` | 45% | 20–75 | Core utilisation |
| `FP_ASPECT_RATIO` | 1.0 | 0.5–2.0 | Die aspect ratio |
| `PL_TARGET_DENSITY` | 0.55 | 0.30–0.85 | Placement density |
| `SYNTH_STRATEGY` | 2 | 0–4 | 0=area 1=delay 2=balanced |
| `SYNTH_MAX_FANOUT` | 10 | 4–32 | Max cell fanout |
| `CTS_TARGET_SKEW` | 200 ps | 100–500 | CTS skew target |
| `ROUTING_CORES` | 4 | 1–16 | Parallel routing threads |

---

## Extending to stages 5–10

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full step-by-step pattern. In short:

1. The `_openlane_stage_name()` map in [`orchestrator.py`](orchestrator/orchestrator.py) already has all 14 stages — just confirm the step class name for your OpenLane2 version
2. Write a dedicated parser (subclass `BaseParser`, raise on bad format)
3. Verify the system prompt in [`agent/system_prompts.py`](agent/system_prompts.py) lists the right tunable params
4. Add unit tests

---

## Environment notes

| Item | Default | Override |
|---|---|---|
| OpenLane2 | `pip install openlane` (Python package) | `export OPENLANE_CMD='openlane'` |
| PDK | `sky130hd` at `~/OpenLane/pdks/` | `export PDK_ROOT=/your/path` |
| Claude model | `claude-sonnet-4-5` | `export CLAUDE_MODEL=...` |
| Stage timeout | 4 hours | `export STAGE_TIMEOUT_SECONDS=7200` |
| Audit logs | `runs/audit/` | `export AUDIT_DIR=/your/path` |

> **`libparse` on Python 3.13:** The `libparse` PyPI package (an OpenLane2 dependency for Liberty file parsing) requires SWIG + a Yosys git submodule and does not build cleanly from the PyPI tarball on Python 3.13. `setup_env.py` installs a minimal stub that satisfies the import — Liberty parsing is only needed in the signoff Liberty-corner STA path, not stages 1–10 of the basic flow. To fully resolve, use OpenLane2 via Docker (includes pre-built binaries) or build `libparse` from its GitHub source directly.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

## Acknowledgements

Built on top of:
- [OpenLane2](https://github.com/efabless/openlane2) — open-source RTL-to-GDS flow
- [OpenROAD](https://github.com/The-OpenROAD-Project/OpenROAD) — physical design engine
- [Yosys](https://github.com/YosysHQ/yosys) — open-source synthesis
- [Anthropic Claude](https://www.anthropic.com/) — AI decision layer
- [Google Skywater sky130 PDK](https://github.com/google/skywater-pdk)
