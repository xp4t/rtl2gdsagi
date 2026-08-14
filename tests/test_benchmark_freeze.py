"""F7: a run whose evaluator changed after the answer is void.

The preserved pre-fix run had a `result.json` embedding `passed: false` and a
`grade.json` saying `passed: true` — written by different grader revisions,
with no re-run in between. A result and a grade that disagree describe no
single experiment.

The instrument is now hashed before anything executes, and the hashes are
written next to the result so a reviewer can detect exactly this.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parent.parent / "benchmarks" / "autonomy"
sys.path.insert(0, str(BENCH))

import run_case  # noqa: E402

CASE = BENCH / "case_05_droute_iters.yaml"

REQUIRED = ("case_yaml_sha256", "grader_sha256", "harness_sha256",
            "prompt_code_sha256", "authorization_code_sha256",
            "action_space_schema_sha256", "frozen_at")


def test_the_freeze_covers_the_whole_instrument():
    f = run_case.freeze_instrument(CASE)
    for key in REQUIRED:
        assert key in f, key
    for key in REQUIRED[:-1]:
        assert len(f[key]) == 64, key


def test_the_freeze_is_deterministic():
    a = run_case.freeze_instrument(CASE)
    b = run_case.freeze_instrument(CASE)
    assert {k: v for k, v in a.items() if k != "frozen_at"} == \
           {k: v for k, v in b.items() if k != "frozen_at"}


def test_changing_the_case_changes_the_freeze(tmp_path):
    copy = tmp_path / "case.yaml"
    copy.write_text(CASE.read_text() + "\n# retuned after the answer\n")
    assert (run_case.freeze_instrument(copy)["case_yaml_sha256"]
            != run_case.freeze_instrument(CASE)["case_yaml_sha256"])


def test_the_grader_and_harness_are_covered():
    """These are the files whose change would silently re-grade a response."""
    f = run_case.freeze_instrument(CASE)
    import hashlib
    for key, rel in (("grader_sha256", "grade.py"),
                     ("harness_sha256", "run_case.py")):
        actual = hashlib.sha256((BENCH / rel).read_bytes()).hexdigest()
        assert f[key] == actual, key


def test_the_voided_run_is_quarantined_and_explained():
    voided = BENCH / "runs" / "_voided"
    if not voided.is_dir():
        pytest.skip("no voided runs in this checkout")
    assert (voided / "README.md").is_file(), (
        "a voided run must carry a written reason"
    )
    text = (voided / "README.md").read_text()
    assert "grader revision" in text.replace("grader\n", "grader ")


def test_a_completed_run_records_its_freeze():
    runs = [d for d in (BENCH / "runs").glob("*")
            if (d / "result.json").is_file()]
    if not runs:
        pytest.skip("no completed run in this checkout")
    for d in runs:
        r = json.loads((d / "result.json").read_text())
        if "benchmark_freeze" not in r:
            continue                      # pre-freeze run, covered elsewhere
        assert (d / "benchmark_freeze.json").is_file()
        assert r["benchmark_freeze"]["grader_sha256"]
