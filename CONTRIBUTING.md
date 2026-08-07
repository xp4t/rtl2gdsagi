# Contributing to rtl2gdsagi

Thank you for your interest in contributing! This document explains the project structure,
development workflow, and conventions so your contribution fits in cleanly.

---

## Development setup

```bash
git clone https://github.com/your-org/rtl2gdsagi.git
cd rtl2gdsagi

# Create a venv
python -m venv .venv && source .venv/bin/activate

# Install all deps including dev extras
pip install -e ".[dev]"

# Verify everything works
pytest            # 35 unit tests, no EDA tools needed
python test_e2e.py --all   # 3 E2E scenarios
```

---

## Project structure

```
orchestrator/     State machine + subprocess runner
parsers/          One parser per EDA stage output
agent/            Claude API decision layer
config/           YAML config + LLM param validation
sweep/            Parallel strategy sweep controller
designs/          Sample RTL designs
tests/            Unit tests (no EDA tools required)
test_e2e.py       End-to-end integration test
```

---

## Adding a new stage parser

1. Create `parsers/<stage>_parser.py` subclassing `BaseParser`
2. Implement `parse(log_dir, stage_result) -> dict` — **must raise** on unrecognised format
3. Register it in `parsers/__init__.py` `get_parser()` dispatch
4. Add unit tests in `tests/test_parsers.py` using a fake log directory
5. Add an E2E scenario mock output in `test_e2e.py` if desired

### Parser contract

- Return dict **always** containing `stage`, `status` (`"pass"|"fail"|"warn"`), `raw_log_path`
- **Raise `RuntimeError`** on unrecognised log format — never silently return a clean result
- Do not swallow exceptions; a failed parse that looks like a pass is a signoff risk

---

## Adding a new flow stage

1. Add the stage to `orchestrator/stages.py` `Stage` enum in the correct position
2. Add the OpenLane2 step name to `_openlane_stage_name()` in `orchestrator/orchestrator.py`
3. Add the stage to `agent/system_prompts.py` `_STAGE_CONTEXT`
4. Add the parser (see above)
5. If the stage is a hard gate (DRC/LVS/signoff STA), add it to `HARD_GATE_STAGES`
6. Add sweep variants to `config/defaults.yaml` under `sweeps:` if tunable

---

## Code style

- **Python 3.11+**, type annotations on all public functions
- Line length 100 (ruff configured)
- All async tool calls use `asyncio.wait_for` with explicit timeout
- No bare `except:` — always catch specific exceptions
- Log with `logging.getLogger(__name__)`, never `print()` in library code

---

## Testing rules

- Unit tests must not require EDA tools, a PDK, or an API key
- Use `tmp_path` fixture for all file I/O in tests
- Parser tests: write fake log content → assert parsed dict fields
- E2E tests: mock `StageRunner.run_stage_async`, exercise real parsers + agent fallback

---

## Pull request checklist

- [ ] `pytest` passes (35+ tests)
- [ ] `python test_e2e.py --all` passes
- [ ] New parsers have at least 3 unit tests (pass, fail, format-error raise)
- [ ] No secrets or API keys committed
- [ ] `runs/` directory is empty (only `runs/.gitkeep` committed)
- [ ] README updated if user-visible behaviour changed
