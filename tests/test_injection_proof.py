"""F1: the grader must prove the *failing attempt* ran with the injection.

The clean-room audit broke the old check two ways, both fatal:

* **Prefix collision.** It grepped `run.jsonl` for the substring
  `'"droute_iters": 1'`, which is a prefix of `'"droute_iters": 16'`. A run
  rewritten to use 16 throughout — never 1 — graded as a success.
* **No anchoring.** Deleting *every* routing event still passed, because the
  surviving match was the config-load note emitted before any stage ran. The
  check proved "the config file declared it", never "the tool was configured
  that way on the attempt that failed".

The replacement reads the immutable per-attempt record the runner freezes
before invoking the tool, and compares typed values.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest
import yaml

BENCH = Path(__file__).resolve().parent.parent / "benchmarks" / "autonomy"
sys.path.insert(0, str(BENCH))

import grade as grader  # noqa: E402

CASE = BENCH / "case_05_droute_iters.yaml"


@pytest.fixture
def case():
    return yaml.safe_load(CASE.read_text())


def _snapshot(value=1, attempt=1, stage="routing", script="routing.attempt_01.tcl"):
    return {
        "stage": stage,
        "attempt": attempt,
        "attempt_id": f"{stage}#{attempt}",
        "ir_section": stage,
        "effective_ir": {"droute_iters": value, "min_layer": 1, "max_layer": 5},
        "script": script,
        "script_sha256": "",
    }


def _build_run(tmp_path, *, snap1=None, snap2_value=32, script1_iters=1,
               write_snap1=True, write_script=True):
    """A minimal run tree the grader can read."""
    sd = tmp_path / "stages" / "12_routing"
    sd.mkdir(parents=True)
    import hashlib

    if write_snap1:
        s1 = snap1 if snap1 is not None else _snapshot()
        text = (f"detailed_route -output_drc x.rpt -bottom_routing_layer met1"
                f" -top_routing_layer met5 -droute_end_iter {script1_iters}"
                f" -verbose 1\n")
        if write_script:
            (sd / s1["script"]).write_text(text)
            s1 = dict(s1)
            s1["script_sha256"] = hashlib.sha256(text.encode()).hexdigest()
        (sd / "attempt_01_config.json").write_text(json.dumps(s1))
    (sd / "attempt_02_config.json").write_text(
        json.dumps(_snapshot(snap2_value, attempt=2,
                             script="routing.attempt_02.tcl")))
    (sd / "attempt_01.log").write_text("[INFO DRT-0199] Number of violations = 2.\n")
    return tmp_path


def _result():
    return {
        "diagnosis_source": "scripted",
        "injected": {"routing": {"droute_iters": 1}},
        "accepted_delta": {"routing": {"droute_iters": 32}},
        "exit_code": 0,
        "autonomy_evidence": False,
        "stages_run": {"routing": {"attempts": 2}},
        "history": [
            {"stage": "routing", "failure_class": "routing",
             "metrics": {"route_violations": 2}},
            {"stage": "routing", "metrics": {"route_violations": 0}},
        ],
    }


def _injection_checks(g):
    return [(n, ok) for n, ok, _, _ in g.checks
            if "effective" in n or "snapshot" in n or "renders" in n]


def test_the_honest_case_passes_the_injection_proof(tmp_path, case):
    run = _build_run(tmp_path)
    g = grader.grade(case, _result(), run)
    assert all(ok for _, ok in _injection_checks(g)), g.report()


# ---- the two exploits, now closed -----------------------------------------

@pytest.mark.parametrize("bogus", [16, 10, 11, 100])
def test_a_prefix_colliding_value_is_rejected(tmp_path, case, bogus):
    """`16` used to satisfy a substring search for `1`."""
    run = _build_run(tmp_path, snap1=_snapshot(bogus), script1_iters=bogus)
    g = grader.grade(case, _result(), run)
    assert not g.passed
    assert any(not ok and "effective" in n for n, ok in _injection_checks(g))


def test_a_value_only_in_a_config_note_is_rejected(tmp_path, case):
    """Anchoring: the pre-run config note is not the failing attempt."""
    run = _build_run(tmp_path, snap1=_snapshot(32), script1_iters=32)
    (run / "run.jsonl").write_text(
        '{"message": "applied ir overrides", "droute_iters": 1}\n')
    g = grader.grade(case, _result(), run)
    assert not g.passed, "a config note must not stand in for the attempt"


def test_the_value_only_on_attempt_2_is_rejected(tmp_path, case):
    run = _build_run(tmp_path, snap1=_snapshot(32), script1_iters=32,
                     snap2_value=1)
    g = grader.grade(case, _result(), run)
    assert not g.passed


def test_a_missing_attempt_1_snapshot_is_rejected(tmp_path, case):
    run = _build_run(tmp_path, write_snap1=False)
    g = grader.grade(case, _result(), run)
    assert not g.passed
    assert any(not ok and "snapshot exists" in n for n, ok in _injection_checks(g))


def test_a_snapshot_for_another_stage_is_rejected(tmp_path, case):
    run = _build_run(tmp_path, snap1=_snapshot(stage="placement"))
    g = grader.grade(case, _result(), run)
    assert not g.passed
    assert any(not ok and "anchored to the failing stage" in n
               for n, ok, _, _ in g.checks)


def test_a_snapshot_for_another_attempt_is_rejected(tmp_path, case):
    run = _build_run(tmp_path, snap1=_snapshot(attempt=3))
    g = grader.grade(case, _result(), run)
    assert not g.passed
    assert any(not ok and "anchored to attempt 1" in n
               for n, ok, _, _ in g.checks)


def test_a_script_disagreeing_with_the_snapshot_is_rejected(tmp_path, case):
    """Effective IR says 1 but the frozen script rendered 32."""
    run = _build_run(tmp_path, snap1=_snapshot(1), script1_iters=32)
    g = grader.grade(case, _result(), run)
    assert not g.passed
    assert any(not ok and "renders" in n for n, ok, _, _ in g.checks)


def test_a_tampered_script_fails_its_recorded_hash(tmp_path, case):
    run = _build_run(tmp_path)
    script = run / "stages" / "12_routing" / "routing.attempt_01.tcl"
    script.write_text(script.read_text() + "\n# edited after the fact\n")
    g = grader.grade(case, _result(), run)
    assert not g.passed
    assert any(not ok and "matches its recorded hash" in n
               for n, ok, _, _ in g.checks)


def test_a_missing_script_snapshot_is_rejected(tmp_path, case):
    run = _build_run(tmp_path, write_script=False)
    g = grader.grade(case, _result(), run)
    assert not g.passed


def test_a_string_valued_injection_does_not_match_an_int(tmp_path, case):
    """Type is compared, not just equality."""
    snap = _snapshot()
    snap["effective_ir"]["droute_iters"] = "1"
    run = _build_run(tmp_path, snap1=snap)
    g = grader.grade(case, _result(), run)
    assert not g.passed


def test_the_grader_no_longer_substring_matches():
    src = (BENCH / "grade.py").read_text()
    assert "token in trail" not in src
    assert 'f\'"{field_name}": {json.dumps(value)}\'' not in src
