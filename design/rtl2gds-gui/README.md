# RTL2GDS-GUI design package

This package captures the selected product direction and the generated screen set for
the `rtl2gdsagi` operator console.

## Product model

The GUI is an engineering console for the repository's 14-stage flow:

`Lint -> Synthesis -> SDC Check -> Post-Synth STA -> Floorplan -> Placement -> Post-Place STA -> CTS -> Post-CTS STA -> Routing -> Post-Route STA -> DRC -> LVS -> GDS`

Primary operator tasks:

- start a bounded, reproducible run from RTL, top module, PDK, and YAML config;
- monitor stage execution, normalized metrics, logs, attempts, and artifacts;
- inspect the agent's structured decision, confidence, reasoning, and parameter diff;
- require human review when a hard gate or retry limit is reached;
- resume or replay prior runs from crash-safe checkpoints;
- compare strategy-sweep candidates by timing, area, power, congestion, and runtime.

## Visual system

- Direction: dark industrial lab instrument, compact and evidence-led.
- Typeface: Fira Sans for interface copy; Fira Code for metrics, paths, logs, and parameters.
- Base: near-black blue-gray surfaces with crisp 1 px borders and minimal elevation.
- Cyan: live data and links.
- Green: pass, running, or approved actions only.
- Amber: review, bounded risk, or pending human judgment.
- Red: failed hard gates and destructive controls only.
- Avoid gradients, glass effects, decorative AI motifs, chat bubbles, and oversized KPI cards.

## Files

- `selected-direction.png`: approved visual direction.
- `screens/a.png`: placement retune review state.
- `screens/b.png`: runs history with current run details.
- `screens/c.png`: failed-run evidence and resume/replay actions.
- `screens/d.png`: new-run setup and validation.
- `screens/e.png`: mandatory human-review escalation.
- `screens/f.png`: strategy-sweep comparison.
- `pages/`: responsive HTML conversions available from the completed 12ui export.
- `branch-plan.json`: screen purposes and generation lineage.

The example project/run values in the generated visuals are representative content.
Production UI should bind them to `RunState`, parser outputs, configuration ranges, and
the structured `AgentDecision` schema in this repository.
