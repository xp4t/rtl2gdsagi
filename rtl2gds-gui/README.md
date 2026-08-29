# RTL2GDSAGI standalone GUI

Native PySide6/Qt Quick operator console for the RTL-to-GDS flow. Active Run
process state and logs are supplied by an asynchronous `QProcess` execution
layer, while incremental tool-output parsers populate normalized runtime
metrics and artifact metadata. No EDA command is built into QML or enabled by
default.

```bash
python3 -m pip install -r rtl2gds-gui/requirements.txt
python3 rtl2gds-gui/main.py
```

To load an execution plan, set `RTL2GDS_FLOW_CONFIG` to a JSON file. Commands
run sequentially and may define per-stage working directories and environment
overrides:

```json
{
  "total_stages": 14,
  "commands": [
    {
      "stage": "Synthesis Logic",
      "stage_number": 3,
      "description": "Running the configured synthesis stage.",
      "program": "/path/to/tool",
      "arguments": ["--config", "flow.json"],
      "working_directory": "./runs/run_042",
      "environment": {"PDK_ROOT": "/path/to/pdks"}
    }
  ]
}
```

Relative working directories are resolved from the configuration file. An
empty or unset plan leaves the runner in `Idle`; the GUI never starts a mock
process automatically.

## Runtime metric events

Streaming process chunks are parsed outside `FlowRunner` by the modules under
`backend/parsers/`. Tool-specific formats are normalized into three immutable
event types:

- `MetricUpdate(name, value, unit, stage, source, timestamp)`
- `StageUpdate(stage, status, runtime_seconds, source, timestamp)`
- `ArtifactUpdate(artifact_type, path, stage, source, timestamp)`

The initial normalized metric names are `wns`, `tns`, `area`, `power`,
`utilization`, `total_congestion`, `peak_congestion`, `drc_violations`,
`lvs_status`, and `stage_runtime`. Unknown and malformed lines are ignored.
Every accepted update is retained in `MetricsModel` history with its stage,
source, timestamp, and improvement/degradation classification.

Artifact references found in output are indexed as metadata only. The index
records type, path, stage, timestamp, existence, and size without opening or
interpreting the generated file.

## Read-only failure diagnosis

Phase 4 adds a diagnosis pipeline under `backend/diagnosis/`:

```text
detached runtime snapshots
  → deterministic evidence and failure classification
  → immutable DiagnosisContext
  → provider-independent diagnosis request
  → validated DiagnosisResult
  → read-only DiagnosisModel
```

`FlowRunner`, metrics, artifacts, and deterministic gates are not exposed to a
diagnosis provider as mutable Qt objects. Prompts contain bounded structured
facts only, never unrestricted logs. Provider results are rejected if they
invent evidence or stages, claim changes/reruns, introduce unavailable metrics
as facts, or conflict with deterministic root-stage/signoff evidence.

No provider is configured by default. In that state deterministic
classification remains operational and the GUI reports `AI diagnosis
unavailable`. `MockDiagnosisProvider` supports network-free tests. The Phase 4
runtime path has no methods for editing files, changing configuration, invoking
tools, restarting a run, or modifying signoff verdicts.

See `DIAGNOSIS_BENCHMARK.md` for the fixed 25-case injected-failure benchmark.

The required Active Run diagnosis states can be rendered headlessly at the
authoritative viewport with:

```bash
python3 rtl2gds-gui/scripts/render_diagnosis_states.py /tmp/rtl2gds-phase4-states
```

The harness uses real healthy/failing `QProcess` commands, renders all seven
required validation scenarios plus the explicit provider-error state at
1536×1024, and exits nonzero if Qt emits a warning.

The interface requests Fira Sans and Fira Code, matching the approved design.
Qt will use the platform fallback fonts if they are not installed.

For headless rendering during development:

```bash
QT_QPA_PLATFORM=offscreen \
QT_QUICK_BACKEND=software \
RTL2GDS_PAGE=activeRun \
RTL2GDS_SIZE=1600x900 \
RTL2GDS_SCREENSHOT=/tmp/rtl2gds.png \
python3 rtl2gds-gui/main.py
```
