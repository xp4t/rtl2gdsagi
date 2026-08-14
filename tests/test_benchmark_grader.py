"""The strict grader must reject an incomplete causal chain.

A grader that only ever passes grades nothing. These mutate the real
`case_05_droute_iters` run one link at a time and require each to fail.
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

#: Neutral directory name -- see the run-directory policy.
RUN = BENCH / "runs" / "scripted_trial_04"
CASE = BENCH / "case_05_droute_iters.yaml"

pytestmark = pytest.mark.skipif(
    not (RUN / "result.json").is_file(),
    reason="the calibrated benchmark run is not present in this checkout",
)


@pytest.fixture
def case():
    return yaml.safe_load(CASE.read_text())


@pytest.fixture
def result():
    return json.loads((RUN / "result.json").read_text())


def test_the_real_run_passes(case, result):
    g = grader.grade(case, result, RUN)
    assert g.passed, g.report()


@pytest.mark.parametrize("mutate,expect", [
    (lambda r: r.update(injected={}), "injection"),
    (lambda r: r["stages_run"]["routing"].update(attempts=1), "rerun"),
    (lambda r: r.update(history=[]), "failure class"),
    (lambda r: r.update(accepted_delta={"sdc": {"default_clock_period_ns": 20}}),
     "authorized action space"),
    # P1-LIVE-02: a different *authorized* value is no longer wrong for being
    # different -- it is wrong when it is not what the rerun actually used.
    (lambda r: r.update(accepted_delta={"routing": {"droute_iters": 64}}),
     "what the rerun actually used"),
    (lambda r: r.update(exit_code=3), "closed"),
    (lambda r: r.update(autonomy_evidence=True), "autonomy"),
])
def test_breaking_one_link_fails_the_grade(case, result, mutate, expect):
    broken = copy.deepcopy(result)
    mutate(broken)
    g = grader.grade(case, broken, RUN)
    assert not g.passed, f"grader accepted a run with no {expect}"
    assert any(expect in name and not ok
               for name, ok, _, _ in g.checks), g.report()


def test_a_worse_after_metric_fails(case, result):
    broken = copy.deepcopy(result)
    for h in broken["history"]:
        if h.get("stage") == "routing" and (h.get("metrics") or {}).get(
                "route_violations") == 0:
            h["metrics"]["route_violations"] = 5
    g = grader.grade(case, broken, RUN)
    assert not g.passed, "a run that did not fix the violations must fail"


def test_pass_lines_never_carry_a_failure_message(case, result):
    """The report must not read as if it contradicts itself."""
    g = grader.grade(case, result, RUN)
    for name, ok, detail, _ in g.checks:
        if ok and detail:
            for bad in ("not recorded", "!=", "missing=", "rejected"):
                assert bad not in detail, f"PASS '{name}' shows {detail!r}"
