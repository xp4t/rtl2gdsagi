"""P0-LIVE-01 / P1-LIVE-02: the live grading path, end to end, with no network.

**P0-LIVE-01.** `grade()` asserted `autonomy_evidence is True` for live runs.
`autonomy_evidence` required `ground_truth_pass`. `ground_truth_pass` came from
`grade()`. A genuine live run could therefore never reach
`autonomy_evidence: true` — the exact defect the previous 830 tests missed,
because every one of them either graded a scripted run or checked
`attribution_complete` in isolation.

The fix is ordering, not loosening: the live attribution checks moved to
`grade_live_attribution`, invoked after attribution is computed, extending the
same `Grade` object so there is one verdict.

**P1-LIVE-02.** The grader demanded `accepted_delta == {"routing":
{"droute_iters": 32}}`. Case 05's own calibration shows 3 also closes the
violations, so a correct bounded remediation would have been failed for
choosing a different legal value. Success is now graded from observed
remediation plus causal linkage to the rerun.

Nothing here contacts Anthropic.
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
import run_case  # noqa: E402

CASE = BENCH / "case_05_droute_iters.yaml"


@pytest.fixture
def case():
    return yaml.safe_load(CASE.read_text())


def _run_tree(tmp_path, *, attempt2_value=32, before=2, after=0):
    """A run directory shaped like a real one, with a valid freeze."""
    import hashlib

    sd = tmp_path / "stages" / "12_routing"
    sd.mkdir(parents=True)

    def snap(attempt, value, script):
        text = (f"detailed_route -output_drc x.rpt -bottom_routing_layer met1"
                f" -top_routing_layer met5 -droute_end_iter {value}"
                f" -verbose 1\n")
        (sd / script).write_text(text)
        (sd / f"attempt_{attempt:02d}_config.json").write_text(json.dumps({
            "stage": "routing", "attempt": attempt,
            "attempt_id": f"routing#{attempt}", "ir_section": "routing",
            "effective_ir": {"droute_iters": value, "min_layer": 1,
                             "max_layer": 5},
            "script": script,
            "script_sha256": hashlib.sha256(text.encode()).hexdigest(),
        }))

    snap(1, 1, "routing.attempt_01.tcl")
    snap(2, attempt2_value, "routing.attempt_02.tcl")
    (sd / "attempt_01.log").write_text(
        f"[INFO DRT-0199] Number of violations = {before}.\n")

    case_copy = tmp_path / "case.yaml"
    case_copy.write_text(CASE.read_text())
    (tmp_path / "benchmark_freeze.json").write_text(
        json.dumps(run_case.freeze_instrument(case_copy)))

    # Realistic gate records: the grader now validates them with the same
    # production contracts signoff uses, so placeholder records are correctly
    # rejected. Built from GATE_CONTRACTS rather than hand-written.
    from rtl2gdsagi.evidence import (
        APPROVED_TOOL_IDENTITIES,
        CERTIFYING_GATES,
        GATE_CONTRACTS,
        GateEvidence,
        certification_id,
    )

    def _tool_for(contract):
        want = contract.tool_identities[0]
        return next((a for a in APPROVED_TOOL_IDENTITIES
                     if a.startswith(want) or want.startswith(a)), want)

    # Real files on disk, so the grader can re-hash the reports it is told
    # about rather than taking the recorded value on trust.
    art_dir = tmp_path / "artifacts"
    art_dir.mkdir()
    keys = ("rtl_dir", "design_facts", "testbench_dir", "netlist",
            "floorplan_def", "pdn_def", "cts_def", "sdc", "routed_def",
            "routed_netlist", "spef", "final_gds", "sim_result", "drc_report",
            "lvs_report", "antenna_report", "extracted_netlist",
            "gds_summary", "lvs_reference")
    shared, paths = {}, {}
    for k in keys:
        f = art_dir / f"{k}.bin"
        f.write_text(f"contents of {k}\n")
        shared[k] = hashlib.sha256(f.read_bytes()).hexdigest()
        paths[k] = str(f)
    records, gates = {}, {}
    for sid in CERTIFYING_GATES:
        c = GATE_CONTRACTS[sid]
        rec = GateEvidence(
            gate=sid.value, verdict="pass", attempt_id=f"{sid.value}#1",
            report_key=c.report_key,
            report_sha256=shared.get(c.report_key) if c.report_key else None,
            consumed={k: shared[k] for k in c.consumed},
            produced={k: shared[k] for k in c.produced},
            tool_identity=_tool_for(c), parser_contract=c.parser_contract,
        )
        records[sid] = rec
        gates[sid.value] = rec.to_dict()
    candidate = "d" * 64
    (tmp_path / "gate_evidence.json").write_text(json.dumps({
        "certification_id": certification_id(candidate, records),
        "candidate_id": candidate, "gates": gates}))
    (tmp_path / "release_candidate.json").write_text(json.dumps({
        "candidate_id": candidate,
        "artifacts": {k: {"path": paths[k], "sha256": shared[k]} for k in keys},
    }))
    (tmp_path / "signoff.json").write_text(json.dumps({"clean": True}))
    return tmp_path, case_copy


def _live_result(delta="__default__", *, before=2, after=0):
    """What the harness builds for a successful live-shaped run."""
    return {
        "diagnosis_source": "live_model",
        "agent_class": "ClaudeAgent",
        "provider": "anthropic",
        "model": "claude-opus-5",
        "non_scripted_model_calls": 1,
        "synthetic_transport": True,
        "network_call": False,
        "prompt_sha256": "a" * 64,
        "evidence_sha256": "b" * 64,
        "response_sha256": "c" * 64,
        "failure_class": "routing",
        "safety_result": "accepted",
        "accepted_delta": ({"routing": {"droute_iters": 32}}
                           if delta == "__default__" else delta),
        "rollback_target": "routing",
        "rerun_stages": ["routing"],
        "before_metrics": {"route_violations": before},
        "after_metrics": {"route_violations": after},
        "candidate_valid": True,
        "injected": {"routing": {"droute_iters": 1}},
        "exit_code": 0,
        "stages_run": {"routing": {"attempts": 2}},
        "history": [
            {"stage": "routing", "failure_class": "routing",
             "metrics": {"route_violations": before}},
            {"stage": "routing", "metrics": {"route_violations": after}},
        ],
    }


def _evaluate(case, result, run_dir, case_path):
    """The production post-run sequence, in the production order."""
    g = grader.grade(case, result, run_dir, case_path=case_path)
    result["ground_truth_pass"] = g.passed
    ok, missing = run_case.attribution_complete(result)
    result["autonomy_evidence"] = ok
    result["attribution_missing"] = missing
    if result.get("diagnosis_source") == "live_model":
        grader.grade_live_attribution(result, g)
    return g, result


# ---- P0-LIVE-01: the cycle is gone ----------------------------------------

def test_a_live_shaped_success_reaches_autonomy_evidence_and_passes(
        tmp_path, case):
    run, case_path = _run_tree(tmp_path)
    g, result = _evaluate(case, _live_result(), run, case_path)

    assert result["ground_truth_pass"] is True, g.report()
    assert result["autonomy_evidence"] is True, result["attribution_missing"]
    assert g.passed, g.report()
    # ... and it is labelled synthetic throughout.
    assert result["network_call"] is False
    assert result["synthetic_transport"] is True


def test_grade_no_longer_reads_autonomy_evidence(tmp_path, case):
    """The structural proof: the causal half cannot depend on the later half."""
    run, case_path = _run_tree(tmp_path)
    result = _live_result()
    result.pop("autonomy_evidence", None)
    g = grader.grade(case, result, run, case_path=case_path)
    assert g.passed, "the causal grade must stand alone"


@pytest.mark.parametrize("field", [
    "non_scripted_model_calls", "prompt_sha256", "evidence_sha256",
    "response_sha256", "failure_class", "safety_result", "accepted_delta",
    "rollback_target", "before_metrics", "after_metrics", "candidate_valid",
])
def test_removing_any_attribution_link_fails_the_live_grade(
        tmp_path, case, field):
    run, case_path = _run_tree(tmp_path)
    result = _live_result()
    result[field] = None
    g, result = _evaluate(case, result, run, case_path)
    assert result["autonomy_evidence"] is False
    assert not g.passed, f"a live run missing {field} must not pass"


def test_a_failed_causal_grade_withholds_autonomy(tmp_path, case):
    """ground_truth_pass is an input to attribution, so it must propagate."""
    run, case_path = _run_tree(tmp_path, attempt2_value=1)   # injection survived
    g, result = _evaluate(case, _live_result(), run, case_path)
    assert result["ground_truth_pass"] is False
    assert result["autonomy_evidence"] is False
    assert not g.passed


def test_a_live_run_with_no_model_call_fails(tmp_path, case):
    run, case_path = _run_tree(tmp_path)
    result = _live_result()
    result["non_scripted_model_calls"] = 0
    g, result = _evaluate(case, result, run, case_path)
    assert not g.passed
    assert any("non-scripted model call" in n and not ok
               for n, ok, _, _ in g.checks)


# ---- P1-LIVE-02: outcome, not the author's number -------------------------

@pytest.mark.parametrize("value", [32, 3, 8, 64])
def test_any_authorized_value_that_closes_the_violations_passes(
        tmp_path, case, value):
    """3 closes them too; the benchmark is not "guess 32"."""
    run, case_path = _run_tree(tmp_path, attempt2_value=value)
    result = _live_result({"routing": {"droute_iters": value}})
    g, result = _evaluate(case, result, run, case_path)
    assert g.passed, g.report()


def test_a_value_that_does_not_close_the_violations_fails(tmp_path, case):
    run, case_path = _run_tree(tmp_path, attempt2_value=2, after=9)
    result = _live_result({"routing": {"droute_iters": 2}}, after=9)
    g, _ = _evaluate(case, result, run, case_path)
    assert not g.passed
    assert any("improved" in n and not ok for n, ok, _, _ in g.checks)


def test_an_unauthorized_field_fails_even_with_a_forged_zero(tmp_path, case):
    run, case_path = _run_tree(tmp_path)
    result = _live_result({"sdc": {"default_clock_period_ns": 20.0}})
    g, _ = _evaluate(case, result, run, case_path)
    assert not g.passed


def test_a_frozen_no_op_field_is_not_an_acceptable_remedy(tmp_path, case):
    """`global_effort` is authorized-looking but not model-writable."""
    run, case_path = _run_tree(tmp_path)
    result = _live_result({"routing": {"global_effort": "high"}})
    g, _ = _evaluate(case, result, run, case_path)
    assert not g.passed
    assert any("writable and implemented" in n and not ok
               for n, ok, _, _ in g.checks)


def test_an_empty_delta_fails(tmp_path, case):
    run, case_path = _run_tree(tmp_path)
    result = _live_result({})
    g, _ = _evaluate(case, result, run, case_path)
    assert not g.passed


def test_a_delta_the_rerun_did_not_use_fails(tmp_path, case):
    """Causal linkage: the claim must match what actually ran."""
    run, case_path = _run_tree(tmp_path, attempt2_value=32)
    result = _live_result({"routing": {"droute_iters": 16}})
    g, _ = _evaluate(case, result, run, case_path)
    assert not g.passed
    assert any("what the rerun actually used" in n and not ok
               for n, ok, _, _ in g.checks)


def test_the_injection_surviving_into_the_rerun_fails(tmp_path, case):
    run, case_path = _run_tree(tmp_path, attempt2_value=1)
    result = _live_result({"routing": {"droute_iters": 1}})
    g, _ = _evaluate(case, result, run, case_path)
    assert not g.passed


def test_a_dirty_certification_fails(tmp_path, case):
    run, case_path = _run_tree(tmp_path)
    (run / "signoff.json").write_text(json.dumps({"clean": False}))
    g, _ = _evaluate(case, _live_result(), run, case_path)
    assert not g.passed


def test_the_exact_32_requirement_is_gone():
    src = (BENCH / "grade.py").read_text()
    assert "accepted delta matches the calibrated remedy" not in src
    assert "calibrated reference remedy" in src, (
        "the calibration should still be reported as reference data"
    )


def test_alternative_answers_are_not_in_the_prompt(fake_pdk):
    """Blindness: the model must not be told which values are acceptable."""
    from rtl2gdsagi.agent.client import DiagnosisRequest
    from rtl2gdsagi.agent.prompts import build_diagnosis_prompt
    from rtl2gdsagi.ir import IR
    from rtl2gdsagi.safety import (
        authorized_action_space,
        authorized_current_values,
    )
    from rtl2gdsagi.stages import StageId
    from rtl2gdsagi.taxonomy import FailureClass

    ir = IR({"routing": {"droute_iters": 1}})
    prompt = build_diagnosis_prompt(DiagnosisRequest(
        stage=StageId.ROUTING, failure_class_hint=FailureClass.ROUTING,
        summary="detailed routing finished with 2 violation(s)",
        evidence="[INFO DRT-0199] Number of violations = 2.\n",
        metrics={"route_violations": 2}, ir_section="routing",
        current_config=authorized_current_values(ir, FailureClass.ROUTING),
        pdk_context=fake_pdk.prompt_context(), attempt=1, retry_limit=3,
        action_space=authorized_action_space(FailureClass.ROUTING),
    ))
    for leak in ("known_remedy", "calibrated", "acceptable value",
                 "droute_iters=3", "droute_iters=32"):
        assert leak not in prompt
