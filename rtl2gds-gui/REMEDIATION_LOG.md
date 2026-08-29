# RTL2GDS GUI remediation log

## Pass 1 — P0 and global shell

- Fixed: Retune Review decision values and explanatory copy; full-width header; logo placement; eleven-item sidebar; route-specific active navigation; vector header/sidebar icons; persistent EST. REMAIN and STARTED metadata at 1536×1024; content origin; centralized spacing/type tokens; bundled Fira Sans and Fira Code loading.
- Files: `backend/app_controller.py`, `main.py`, `qml/Theme.qml`, `qml/Main.qml`, `qml/components/ActionButton.qml`, `qml/components/AppSidebar.qml`, `qml/components/ConsoleIcon.qml`, `qml/components/SectionHeader.qml`, `qml/components/TopBar.qml`, `assets/fonts/*`.
- Reference: approved `selected-direction.png` and screens `a.png`–`f.png`; HTML used only for legible labels and icon intent.
- Validation: all seven routes rendered at 1536×1024; zero runtime QML warnings; 35 tests passed; Python compileall passed.

## Pass 2 — Retune Review

- Fixed: stage pipeline, alert placement, approved `high → medium`, `0.70 → 0.66`, and `0.20 → 0.30` changes, direction helpers, timestamps, before/after heatmaps, critical paths, impacted-region table, recommendation hierarchy, and full vertical composition.
- Files: `backend/app_controller.py`, `qml/components/EvidenceHeatmap.qml`, `qml/components/PipelineBand.qml`, `qml/pages/RetuneReviewPage.qml`.
- Reference: approved `screens/a.png`; `pages/p0-active-run-placement-a.html` used for legible secondary labels.
- Validation: Retune Review rendered at 1536×1024; zero runtime QML warnings; 35 tests passed; Python compileall passed.

## Pass 3 — Human Review

- Fixed: failed-stage pipeline, summary origin, View details, four timing paths, two distinct analytical maps, five hotspot bars, corrected numeric deltas, iteration note, 0/400 counter, Last Human Review state, prior-context table, and decision/action hierarchy.
- Files: `qml/components/PipelineBand.qml`, `qml/pages/HumanReviewPage.qml`.
- Reference: approved `screens/e.png`; `pages/p3-human-review.html` used for readable evidence labels.
- Validation: Human Review rendered at 1536×1024; zero runtime QML warnings; 35 tests passed; Python compileall passed.

## Later passes — remaining P1 screens

- Active Run: corrected ACTIVE stage state, metric geometry, rail sizing, type roles, retune copy, and placement evidence rendering.
- Run History: restored row subtitles, PPA Outcome grouping, WNS/TNS sparklines, issue status, timestamps/actions, expanded run detail, and Run Notes / Agents / Next Actions footer.
- Checkpoint Recovery: restored dedicated action rail, six retained checkpoints, downloads, Run Notes, metric trends/previous values, hotspot map and legend, and full violations report.
- New Run: replaced static field blocks with native Qt Quick controls, restored multiline description, stepper rule, column proportions, control heights, validation position, and summary rail geometry.
- Strategy Sweep: restored focus bars, constraint violations, completion timestamps, row actions, annotated radar, 24 trend plots, selection/actions, and full-height summary.
- Files: `backend/checkpoint_model.py`, `backend/strategy_model.py`, `qml/components/FormField.qml`, `qml/components/LogConsole.qml`, `qml/components/MetricCard.qml`, `qml/components/MiniSparkline.qml`, `qml/components/QualityGate.qml`, and all five affected page files.
- References: approved `selected-direction.png` and `screens/b.png`, `c.png`, `d.png`, and `f.png`; corresponding HTML references used only for legible details.
- Validation: each affected route rendered at 1536×1024 with zero runtime QML warnings; 35 tests passed after each route; Python compileall passed.

## Final pixel-polish pass

- Fixed: final shared alignment review, bounded Strategy Sweep row heights, two-line recovery status in the header, warning emphasis for `run_041`, and Active Run rail minimum width at 1366×768.
- Files: `qml/components/TopBar.qml`, `qml/pages/ActiveRunPage.qml`, `qml/pages/RunHistoryPage.qml`, `qml/pages/StrategySweepPage.qml`.
- Reference: the approved PNG set remained the pixel-level authority; critique baseline `2026-08-28T05-43-44Z__rtl2gds-gui-against-approved-references.md` was rechecked against the completed routes.
- Validation: all seven routes rendered at 1536×1024 with zero runtime QML warnings; Active Run, New Run, and Strategy Sweep also smoke-rendered at 1366×768 and 2560×1440; 35 tests passed; Python compileall and `git diff --check` passed.

## Phase 2 — execution infrastructure

- Fixed: replaced mock Active Run process status, stage, progress, timing, and logs with a non-blocking `QProcess` state layer; added validated JSON command plans, incremental stdout/stderr capture, cancellation, and application-exit teardown.
- Files: `backend/flow_config.py`, `backend/flow_runner.py`, `backend/flow_controller.py`, `backend/app_controller.py`, `backend/log_model.py`, `backend/pipeline_model.py`, `backend/run_model.py`, `main.py`, `qml/pages/ActiveRunPage.qml`, `qml/components/LogConsole.qml`, `qml/components/TopBar.qml`, `README.md`, `tests/test_gui_flow_runner.py`.
- Reference: the approved QML component and layout APIs were retained; Phase 2 changes are limited to execution-state bindings and semantic status colors.
- Validation: all seven routes rendered at 1536×1024 with zero runtime QML warnings; 42 tests passed, including all 35 pre-existing tests; Python compileall and `git diff --check` passed.

## Phase 3 — runtime metrics and evidence

- Fixed: added fault-tolerant incremental parsers for timing, synthesis, placement, routing, signoff, and artifact references; normalized process output into metric, stage, and artifact events; replaced Active Run metric/artifact mocks with explicit unavailable/live state and accumulated history.
- Files: `backend/parsers/*`, `backend/metrics_model.py`, `backend/artifact_model.py`, `backend/app_controller.py`, `README.md`, `tests/test_gui_parsers.py`, `tests/test_gui_flow_runner.py`, `tests/fixtures/gui_logs/*`.
- Integration: existing Active Run card, gate, pipeline, and artifact QML contracts were retained unchanged; model rows now update from normalized events.
- Validation: all seven routes rendered at 1536×1024 with zero runtime QML warnings; idle and synthetic-metric Active Run renders passed; 57 tests passed, including all pre-existing tests; Python compileall and `git diff --check` passed.

## Phase 4 — read-only failure diagnosis

- Added: immutable diagnosis snapshots/evidence/failures/results; deterministic failure taxonomy and earliest-stage selection; bounded prompt construction; provider-independent asynchronous diagnosis; strict result validation; snapshot fingerprint caching; current-run diagnosis history; explicit no-provider behavior.
- GUI: added one full-width `AI DIAGNOSIS` operator panel to Active Run using existing theme/components, with `NO_DIAGNOSIS`, `ANALYZING`, `AVAILABLE`, `UNAVAILABLE`, and `ERROR` states and no mutation actions.
- Files: `backend/diagnosis/*`, `backend/app_controller.py`, `backend/metrics_model.py`, `backend/run_model.py`, `qml/components/DiagnosisPanel.qml`, `qml/pages/ActiveRunPage.qml`, `tests/test_gui_diagnosis.py`, `tests/test_gui_diagnosis_integration.py`, `tests/fixtures/gui_failures/benchmark.json`, `DIAGNOSIS_BENCHMARK.md`, `README.md`.
- Safety: diagnosis receives detached plain data only; no diagnosis component can edit RTL/TCL/constraints/configuration/artifacts, invoke a tool, restart a flow, or mutate deterministic gates.
- Validation: all seven routes rendered at 1536×1024 with zero runtime QML warnings; all seven required Active Run scenarios plus the explicit provider-error state rendered with zero warnings using real healthy/failing `QProcess` fixtures; 91 tests passed; Python compileall and `git diff --check` passed.
- Benchmark: 25 fixed injected failures, 25 expected-label root stages matched (100% automated score), zero cases removed. Independent human grading remains the formal acceptance checkpoint documented in `DIAGNOSIS_BENCHMARK.md`.
