"""N2: the grader refuses to grade a run whose instrument has changed.

The freeze was recorded and never verified, so an edited grader could re-grade
an old response -- exactly the retuning the void policy forbids.

Every mutation below is applied to a *copy* of the repo file, and the recorded
freeze is left untouched: the run's own `benchmark_freeze.json` is evidence.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
BENCH = REPO / "benchmarks" / "autonomy"
sys.path.insert(0, str(BENCH))

import grade as grader  # noqa: E402

CASE = BENCH / "case_05_droute_iters.yaml"

COMPONENTS = {
    "case_yaml_sha256": None,                       # the case file itself
    "grader_sha256": "benchmarks/autonomy/grade.py",
    "harness_sha256": "benchmarks/autonomy/run_case.py",
    "prompt_code_sha256": "src/rtl2gdsagi/agent/prompts.py",
    "authorization_code_sha256": "src/rtl2gdsagi/safety.py",
    "action_space_schema_sha256": "src/rtl2gdsagi/ir.py",
}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _current_freeze(case_path: Path) -> dict:
    out = {"case_yaml_sha256": _sha(case_path)}
    for key, rel in COMPONENTS.items():
        if rel:
            out[key] = _sha(REPO / rel)
    out["frozen_at"] = "2026-01-01T00:00:00Z"
    return out


@pytest.fixture
def frozen_run(tmp_path):
    """A run directory whose freeze matches the current instrument."""
    case = tmp_path / "case.yaml"
    shutil.copy(CASE, case)
    run = tmp_path / "run"
    run.mkdir()
    (run / "benchmark_freeze.json").write_text(
        json.dumps(_current_freeze(case), indent=2))
    return case, run


def _freeze_checks(g):
    return {n: ok for n, ok, _, _ in g.checks
            if "freeze" in n or "instrument" in n}


def test_an_unchanged_instrument_passes(frozen_run):
    case, run = frozen_run
    g = grader.Grade()
    grader.check_freeze(case, run, g)
    assert all(_freeze_checks(g).values()), g.report()


def test_a_changed_case_yaml_voids_the_run(frozen_run):
    case, run = frozen_run
    case.write_text(case.read_text() + "\n# retuned after the answer\n")
    g = grader.Grade()
    grader.check_freeze(case, run, g)
    assert not g.passed
    assert any("case_yaml_sha256" in d for _, ok, d, _ in g.checks if not ok)


@pytest.mark.parametrize("key,rel", [
    (k, v) for k, v in COMPONENTS.items() if v
])
def test_a_changed_instrument_component_voids_the_run(frozen_run, key, rel):
    """Mutate the *recorded* hash, which is equivalent to the file changing."""
    case, run = frozen_run
    freeze = json.loads((run / "benchmark_freeze.json").read_text())
    freeze[key] = "0" * 64
    (run / "benchmark_freeze.json").write_text(json.dumps(freeze))

    g = grader.Grade()
    grader.check_freeze(case, run, g)
    assert not g.passed, f"{key} drift was not detected"
    detail = " ".join(d for _, ok, d, _ in g.checks if not ok)
    assert key in detail and "VOID" in detail


def test_the_graders_own_hash_is_enforced(frozen_run):
    """grade.py is frozen too, deliberately and without exception."""
    case, run = frozen_run
    freeze = json.loads((run / "benchmark_freeze.json").read_text())
    freeze["grader_sha256"] = "f" * 64
    (run / "benchmark_freeze.json").write_text(json.dumps(freeze))

    g = grader.Grade()
    grader.check_freeze(case, run, g)
    assert not g.passed
    src = (BENCH / "grade.py").read_text()
    assert "grader_sha256" in src and "special-cas" in src.lower()


def test_a_missing_freeze_fails(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    g = grader.Grade()
    grader.check_freeze(CASE, run, g)
    assert not g.passed


def test_a_malformed_freeze_fails(frozen_run):
    case, run = frozen_run
    (run / "benchmark_freeze.json").write_text("{not json")
    g = grader.Grade()
    grader.check_freeze(case, run, g)
    assert not g.passed


def test_a_freeze_that_is_not_an_object_fails(frozen_run):
    case, run = frozen_run
    (run / "benchmark_freeze.json").write_text('["a", "b"]')
    g = grader.Grade()
    grader.check_freeze(case, run, g)
    assert not g.passed


@pytest.mark.parametrize("missing", list(COMPONENTS))
def test_a_missing_hash_entry_fails_closed(frozen_run, missing):
    case, run = frozen_run
    freeze = json.loads((run / "benchmark_freeze.json").read_text())
    freeze.pop(missing, None)
    (run / "benchmark_freeze.json").write_text(json.dumps(freeze))

    g = grader.Grade()
    grader.check_freeze(case, run, g)
    assert not g.passed, f"a freeze missing {missing} must not grade"


def test_grading_never_rewrites_the_recorded_freeze(frozen_run):
    """The historical freeze is evidence, not a cache."""
    case, run = frozen_run
    before = (run / "benchmark_freeze.json").read_bytes()
    g = grader.Grade()
    grader.check_freeze(case, run, g)
    assert (run / "benchmark_freeze.json").read_bytes() == before


def test_drift_is_reported_with_the_components_named(frozen_run):
    case, run = frozen_run
    freeze = json.loads((run / "benchmark_freeze.json").read_text())
    freeze["harness_sha256"] = "1" * 64
    freeze["prompt_code_sha256"] = "2" * 64
    (run / "benchmark_freeze.json").write_text(json.dumps(freeze))

    g = grader.Grade()
    grader.check_freeze(case, run, g)
    detail = " ".join(d for _, ok, d, _ in g.checks if not ok)
    assert "harness_sha256" in detail and "prompt_code_sha256" in detail
    assert "re-run from scratch" in detail
