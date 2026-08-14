"""L1/L2/L3 and the first-live retry envelope.

**L1.** The documented `grade.py <case> <run_dir>` called `grade()` alone,
omitting the live-only checks. For a live run it could overwrite `grade.json`
with PASS and exit 0 while `result.json` said FAIL -- two files disagreeing
about one experiment.

**L2.** `"-droute_end_iter 1" in text` is satisfied by `-droute_end_iter 16`.
The rendered argument is now tokenised and compared against the snapshot's
typed value.

**L3.** The old regressions transcribed `run_case.main()`'s post-run sequence
by hand, which is how P0-LIVE-01 survived: the copy did not have the cycle the
original had. Production and tests now call one helper.

Nothing here contacts Anthropic.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
BENCH = REPO / "benchmarks" / "autonomy"
sys.path.insert(0, str(BENCH))

import grade as grader  # noqa: E402
import run_case  # noqa: E402

CASE = BENCH / "case_05_droute_iters.yaml"


@pytest.fixture
def case():
    return yaml.safe_load(CASE.read_text())


# --------------------------------------------------------------------------
# a realistic run tree, built once and reused
# --------------------------------------------------------------------------

def _run_tree(tmp_path, *, a1_snap=1, a1_script=None, a2_snap=32,
              a2_script=None, before=2, after=0, third_attempt=False):
    from rtl2gdsagi.evidence import (
        APPROVED_TOOL_IDENTITIES,
        CERTIFYING_GATES,
        GATE_CONTRACTS,
        GateEvidence,
        certification_id,
    )

    sd = tmp_path / "stages" / "12_routing"
    sd.mkdir(parents=True)

    def snap(attempt, snap_value, script_text):
        script = f"routing.attempt_{attempt:02d}.tcl"
        (sd / script).write_text(script_text)
        (sd / f"attempt_{attempt:02d}_config.json").write_text(json.dumps({
            "stage": "routing", "attempt": attempt,
            "attempt_id": f"routing#{attempt}", "ir_section": "routing",
            "effective_ir": {"droute_iters": snap_value, "min_layer": 1,
                             "max_layer": 5},
            "script": script,
            "script_sha256": hashlib.sha256(script_text.encode()).hexdigest(),
        }))

    def tcl(value):
        return (f"detailed_route -output_drc x.rpt -bottom_routing_layer met1"
                f" -top_routing_layer met5 -droute_end_iter {value}"
                f" -verbose 1\n")

    snap(1, a1_snap, a1_script if a1_script is not None else tcl(a1_snap))
    snap(2, a2_snap, a2_script if a2_script is not None else tcl(a2_snap))
    if third_attempt:
        snap(3, 48, tcl(48))
    (sd / "attempt_01.log").write_text(
        f"[INFO DRT-0199] Number of violations = {before}.\n")

    case_copy = tmp_path / "case.yaml"
    case_copy.write_text(CASE.read_text())
    (tmp_path / "benchmark_freeze.json").write_text(
        json.dumps(run_case.freeze_instrument(case_copy)))

    art = tmp_path / "artifacts"
    art.mkdir()
    keys = ("rtl_dir", "design_facts", "testbench_dir", "netlist",
            "floorplan_def", "pdn_def", "cts_def", "sdc", "routed_def",
            "routed_netlist", "spef", "final_gds", "sim_result", "drc_report",
            "lvs_report", "antenna_report", "extracted_netlist",
            "gds_summary", "lvs_reference")
    shared, paths = {}, {}
    for k in keys:
        f = art / f"{k}.bin"
        f.write_text(f"contents of {k}\n")
        shared[k] = hashlib.sha256(f.read_bytes()).hexdigest()
        paths[k] = str(f)

    def tool_for(c):
        want = c.tool_identities[0]
        return next((a for a in APPROVED_TOOL_IDENTITIES
                     if a.startswith(want) or want.startswith(a)), want)

    records, gates = {}, {}
    for sid in CERTIFYING_GATES:
        c = GATE_CONTRACTS[sid]
        rec = GateEvidence(
            gate=sid.value, verdict="pass", attempt_id=f"{sid.value}#1",
            report_key=c.report_key,
            report_sha256=shared.get(c.report_key) if c.report_key else None,
            consumed={k: shared[k] for k in c.consumed},
            produced={k: shared[k] for k in c.produced},
            tool_identity=tool_for(c), parser_contract=c.parser_contract)
        records[sid] = rec
        gates[sid.value] = rec.to_dict()
    candidate = "d" * 64
    (tmp_path / "gate_evidence.json").write_text(json.dumps({
        "certification_id": certification_id(candidate, records),
        "candidate_id": candidate, "gates": gates}))
    (tmp_path / "release_candidate.json").write_text(json.dumps({
        "candidate_id": candidate,
        "artifacts": {k: {"path": paths[k], "sha256": shared[k]} for k in keys}}))
    (tmp_path / "signoff.json").write_text(json.dumps({"clean": True}))
    return tmp_path, case_copy


PROMPT_H, EV_H, RESP_H = "a" * 64, "b" * 64, "c" * 64


def _live_result(*, calls=1, delta=None, before=2, after=0, attempts=2,
                 audits=None):
    if audits is None:
        audits = [{"provider": "anthropic", "model": "claude-opus-5",
                   "user_prompt_sha256": PROMPT_H,
                   "evidence_payload_sha256": EV_H,
                   "response_sha256": RESP_H,
                   "synthetic_transport": True}] * calls
    return {
        "diagnosis_source": "live_model", "agent_class": "ClaudeAgent",
        "provider": "anthropic", "model": "claude-opus-5",
        "non_scripted_model_calls": calls, "call_audits": audits,
        "synthetic_transport": True, "network_call": False,
        "prompt_sha256": PROMPT_H, "evidence_sha256": EV_H,
        "response_sha256": RESP_H,
        "failure_class": "routing", "safety_result": "accepted",
        "accepted_delta": delta or {"routing": {"droute_iters": 32}},
        "rollback_target": "routing", "rerun_stages": ["routing"],
        "before_metrics": {"route_violations": before},
        "after_metrics": {"route_violations": after},
        "candidate_valid": True,
        "injected": {"routing": {"droute_iters": 1}}, "exit_code": 0,
        "stages_run": {"routing": {"attempts": attempts}},
        "history": [
            {"stage": "routing", "failure_class": "routing",
             "metrics": {"route_violations": before}},
            {"stage": "routing", "metrics": {"route_violations": after}}],
    }


# --------------------------------------------------------------------------
# L3 -- one production helper, used by production and by tests
# --------------------------------------------------------------------------

def test_the_helper_exists_and_main_uses_it():
    src = (BENCH / "run_case.py").read_text()
    assert "def finalize_run_result(" in src
    assert "g, result = finalize_run_result(" in src
    # main() must not carry its own copy of the sequence.
    after_main = src.split("def main() -> int:", 1)[1]
    assert "attribution_complete(result)" not in after_main


def test_production_helper_grades_a_live_success(tmp_path, case):
    run, case_path = _run_tree(tmp_path)
    g, result = run_case.finalize_run_result(
        case, _live_result(), run, case_path, write=False)
    assert result["ground_truth_pass"] is True, g.report()
    assert result["autonomy_evidence"] is True, result["attribution_missing"]
    assert g.passed, g.report()


@pytest.mark.parametrize("field", [
    "prompt_sha256", "evidence_sha256", "response_sha256", "failure_class",
    "safety_result", "accepted_delta", "rollback_target", "before_metrics",
    "after_metrics", "candidate_valid",
])
def test_helper_fails_when_an_attribution_link_is_missing(
        tmp_path, case, field):
    run, case_path = _run_tree(tmp_path)
    r = _live_result()
    r[field] = None
    g, result = run_case.finalize_run_result(case, r, run, case_path,
                                             write=False)
    assert result["autonomy_evidence"] is False
    assert not g.passed


def test_helper_fails_a_live_run_with_no_model_call(tmp_path, case):
    run, case_path = _run_tree(tmp_path)
    g, result = run_case.finalize_run_result(
        case, _live_result(calls=0, audits=[]), run, case_path, write=False)
    assert not g.passed
    assert result["autonomy_evidence"] is False


def test_a_failed_causal_result_withholds_autonomy(tmp_path, case):
    run, case_path = _run_tree(tmp_path, a2_snap=1)      # injection survived
    g, result = run_case.finalize_run_result(
        case, _live_result(delta={"routing": {"droute_iters": 1}}),
        run, case_path, write=False)
    assert result["ground_truth_pass"] is False
    assert result["autonomy_evidence"] is False
    assert not g.passed


# --------------------------------------------------------------------------
# L1 -- the standalone CLI reaches the same verdict
# --------------------------------------------------------------------------

def _cli(case_path, run_dir):
    return subprocess.run(
        [sys.executable, str(BENCH / "grade.py"), str(case_path), str(run_dir)],
        capture_output=True, text=True)


def test_standalone_cli_fails_a_live_run_with_zero_calls(tmp_path, case):
    run, case_path = _run_tree(tmp_path)
    r = _live_result(calls=0, audits=[])
    run_case.finalize_run_result(case, r, run, case_path)   # writes both files
    assert json.loads((run / "result.json").read_text())["grade_passed"] is False

    p = _cli(case_path, run)
    assert p.returncode != 0, p.stdout
    assert "non-scripted model call" in p.stdout
    assert json.loads((run / "grade.json").read_text())["passed"] is False


def test_standalone_cli_passes_a_complete_live_run(tmp_path, case):
    run, case_path = _run_tree(tmp_path)
    run_case.finalize_run_result(case, _live_result(), run, case_path)
    p = _cli(case_path, run)
    assert p.returncode == 0, p.stdout + p.stderr
    assert json.loads((run / "grade.json").read_text())["passed"] is True


def test_standalone_cli_cannot_contradict_the_recorded_result(tmp_path, case):
    """grade.json and result.json must not disagree about overall success."""
    run, case_path = _run_tree(tmp_path)
    run_case.finalize_run_result(case, _live_result(calls=0, audits=[]),
                                 run, case_path)
    _cli(case_path, run)
    assert (json.loads((run / "grade.json").read_text())["passed"]
            == json.loads((run / "result.json").read_text())["grade_passed"])


def test_standalone_grader_reuses_the_live_checks_not_a_copy():
    src = (BENCH / "grade.py").read_text()
    after_main = src.split("def main() -> int:", 1)[1]
    assert "grade_live_attribution(result, g)" in after_main
    assert "non_scripted_model_calls" not in after_main, (
        "the CLI must reuse grade_live_attribution, not reimplement it"
    )


# --------------------------------------------------------------------------
# L2 -- typed snapshot -> rendered argument binding
# --------------------------------------------------------------------------

def _binding_ok(g):
    return all(ok for n, ok, _, _ in g.checks if "renders" in n)


@pytest.mark.parametrize("script_value", [16, 10, 100, 11])
def test_a_prefix_or_other_value_in_the_script_fails(
        tmp_path, case, script_value):
    """`-droute_end_iter 16` used to satisfy a search for `1`."""
    run, case_path = _run_tree(
        tmp_path, a1_snap=1,
        a1_script=f"detailed_route -droute_end_iter {script_value} -verbose 1\n")
    g = grader.grade(case, _live_result(), run, case_path=case_path)
    assert not _binding_ok(g), f"script said {script_value}, snapshot said 1"
    assert not g.passed


def test_the_exact_value_passes_even_with_trailing_options(tmp_path, case):
    run, case_path = _run_tree(
        tmp_path, a1_snap=1,
        a1_script="detailed_route -droute_end_iter 1 -verbose 1\n")
    g = grader.grade(case, _live_result(), run, case_path=case_path)
    assert _binding_ok(g), g.report()


def test_a_non_numeric_suffix_fails(tmp_path, case):
    run, case_path = _run_tree(
        tmp_path, a1_snap=1,
        a1_script="detailed_route -droute_end_iter 1foo -verbose 1\n")
    g = grader.grade(case, _live_result(), run, case_path=case_path)
    assert not _binding_ok(g)


def test_a_missing_option_fails(tmp_path, case):
    run, case_path = _run_tree(
        tmp_path, a1_snap=1, a1_script="detailed_route -verbose 1\n")
    g = grader.grade(case, _live_result(), run, case_path=case_path)
    assert not _binding_ok(g)


def test_conflicting_duplicate_options_fail_closed(tmp_path, case):
    run, case_path = _run_tree(
        tmp_path, a1_snap=1,
        a1_script="detailed_route -droute_end_iter 1 -droute_end_iter 16\n")
    g = grader.grade(case, _live_result(), run, case_path=case_path)
    assert not g.passed
    assert any("one value" in n and not ok for n, ok, _, _ in g.checks)


def test_attempt_two_is_bound_to_its_own_typed_value(tmp_path, case):
    run, case_path = _run_tree(
        tmp_path, a2_snap=32,
        a2_script="detailed_route -droute_end_iter 64 -verbose 1\n")
    g = grader.grade(case, _live_result(), run, case_path=case_path)
    assert not g.passed


def test_substring_matching_is_gone():
    src = (BENCH / "grade.py").read_text()
    assert "m in text" not in src
    assert "rendered_option_values" in src


# --------------------------------------------------------------------------
# retry envelope
# --------------------------------------------------------------------------

def test_the_case_declares_a_one_diagnosis_envelope(case):
    env = case["envelope"]
    assert env["max_model_calls"] == 1
    assert env["max_retries"] == 1
    # limit=2 means: attempt 1, one diagnosis, attempt 2, then escalate.
    assert env["retry_limits"]["routing"] == 2


def test_retry_limit_semantics_are_what_the_envelope_assumes():
    """Read from the runner, not assumed.

    `st.attempts` increments before each execution and the limit is tested
    *before* diagnosing, so `limit == attempts_allowed` and the number of
    diagnoses is `limit - 1`.
    """
    src = (REPO / "src" / "rtl2gdsagi" / "runner.py").read_text()
    assert "st.attempts += 1" in src
    body = src.split("def _attempt_stage", 1)[1]
    assert "if st.attempts >= limit:" in body
    assert body.index("if st.attempts >= limit:") < body.index("self._diagnose(")


def test_the_harness_applies_the_envelope_as_stage_policy():
    src = (BENCH / "run_case.py").read_text()
    assert 'envelope.get("retry_limits")' in src
    assert "retry_limit=int(limit)" in src


def test_a_third_attempt_fails_the_grade(tmp_path, case):
    run, case_path = _run_tree(tmp_path, third_attempt=True)
    g = grader.grade(case, _live_result(attempts=3), run, case_path=case_path)
    assert not g.passed
    assert any("third attempt" in n and not ok for n, ok, _, _ in g.checks)


def test_two_model_calls_fail_the_envelope(tmp_path, case):
    run, case_path = _run_tree(tmp_path)
    g = grader.grade(case, _live_result(calls=2), run, case_path=case_path)
    assert not g.passed
    assert any("envelope" in n and not ok for n, ok, _, _ in g.checks)


def test_hashes_must_belong_to_the_single_recorded_call(tmp_path, case):
    run, case_path = _run_tree(tmp_path)
    r = _live_result()
    r["response_sha256"] = "f" * 64          # not the audited response
    g = grader.grade(case, r, run, case_path=case_path)
    assert not g.passed
    assert any("single model call" in n and not ok
               for n, ok, _, _ in g.checks)
