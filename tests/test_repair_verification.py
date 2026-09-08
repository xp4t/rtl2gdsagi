from __future__ import annotations

from pathlib import Path

import pytest

from rtl2gdsagi.repair import (
    CertificationLevel, evaluate_certification, evaluate_repair,
    memory_is_compatible,
)
from rtl2gdsagi.repair.verification import EVIDENCE_REQUIRED, PHYSICAL_GATES
from rtl2gdsagi.runner import Orchestrator
from rtl2gdsagi.stages import StageId


def pdn_record():
    return {
        "known_error_id": "PDN-0185",
        "result": "resolved",
        "actions": [
            {"action_type": "SET_IR_VALUE", "target": "floorplan.core_utilization", "value": 0.30},
            {"action_type": "SET_IR_VALUE", "target": "pdn.strap_offset_um", "value": 0.84},
        ],
    }


def passing_results():
    return {stage: "pass" for stage in StageId}


def evidence():
    return set(EVIDENCE_REQUIRED)


def test_pdn_repair_does_not_require_simulation_for_physical_verification():
    stages = passing_results(); stages[StageId.SIM] = "skipped"
    result = evaluate_repair(
        pdn_record(), stage_results=stages, evidence_gates=evidence(),
        authoritative_simulation=False,
    )
    assert result.repair_verified
    assert result.requirement.scope.value == "physical_signoff"
    assert StageId.SIM not in result.requirement.required_gates
    assert result.physical_signoff_verified
    assert not result.functional_spec_verified


def test_floorplan_pdn_repair_requires_every_affected_physical_gate():
    result = evaluate_repair(
        pdn_record(), stage_results=passing_results(), evidence_gates=evidence(),
    )
    assert set(PHYSICAL_GATES) <= set(result.requirement.required_gates)
    assert StageId.LEC_SYNTH in result.requirement.required_gates


@pytest.mark.parametrize("gate", [StageId.DRC, StageId.LVS, StageId.STA_SIGNOFF])
def test_missing_signoff_gate_blocks_physical_repair_promotion(gate):
    stages = passing_results(); stages[gate] = "failed"
    result = evaluate_repair(
        pdn_record(), stage_results=stages, evidence_gates=evidence(),
    )
    assert not result.repair_verified
    assert gate in result.failed_gates


def test_missing_gate_evidence_blocks_physical_repair_promotion():
    records = evidence() - {StageId.DRC}
    result = evaluate_repair(
        pdn_record(), stage_results=passing_results(), evidence_gates=records,
    )
    assert not result.repair_verified
    assert StageId.DRC in result.failed_gates


def test_physical_repair_requires_unchanged_rtl_identity():
    record = {**pdn_record(), "rtl_identity_preserved": False}
    result = evaluate_repair(
        record, stage_results=passing_results(), evidence_gates=evidence(),
    )
    assert not result.repair_verified
    assert "working RTL identity changed" in result.promotion_reason[-1]


def test_rtl_repair_requires_authoritative_functional_evidence():
    record = {
        "result": "resolved",
        "actions": [{
            "action_type": "PATCH_WORKING_RTL", "target": "top.v",
            "value": {"old": "assign y = a", "new": "assign y = a;"},
        }],
    }
    no_tb = evaluate_repair(
        record, stage_results=passing_results(), evidence_gates=evidence(),
        authoritative_simulation=False,
    )
    assert not no_tb.repair_verified
    assert no_tb.requirement.scope.value == "full"
    with_tb = evaluate_repair(
        record, stage_results=passing_results(), evidence_gates=evidence(),
        authoritative_simulation=True,
    )
    assert with_tb.repair_verified


def test_certification_separates_physical_from_functional():
    stages = passing_results(); stages[StageId.SIM] = "skipped"
    summary = evaluate_certification(
        stage_results=stages, authoritative_simulation=False,
    )
    assert summary.level is CertificationLevel.PHYSICAL_SIGNOFF_VERIFIED
    assert summary.physical_signoff_verified
    assert summary.logical_identity_verified
    assert not summary.functional_spec_verified
    assert not summary.full_certification


def test_generated_testbench_is_not_authoritative():
    tb = Path(__file__).parent / "fixtures/validation/shift_register/shift_register_tb.v"
    assert Orchestrator._testbench_authority(tb) == "implementation_derived"


def test_physical_memory_cannot_support_rtl_repair():
    memory = {
        **pdn_record(), "repair_verified": True,
        "verification_scope": "physical_signoff",
        "modified_surfaces": ["floorplan", "pdn"],
    }
    compatible, reason = memory_is_compatible(
        memory, failure_code="PDN-0185", proposed_actions=[{
            "action_type": "PATCH_WORKING_RTL", "target": "top.v",
            "value": {"old": "a", "new": "b"},
        }],
    )
    assert not compatible
    assert "physical repair memory" in reason


def test_memory_match_is_strategy_only_and_current_run_must_revalidate():
    memory = {
        **pdn_record(), "repair_verified": True,
        "verification_scope": "physical_signoff",
        "modified_surfaces": ["floorplan", "pdn"],
    }
    compatible, reason = memory_is_compatible(
        memory, failure_code="PDN-0185",
        proposed_actions=pdn_record()["actions"],
    )
    assert compatible and "validation remains mandatory" in reason
    stages = passing_results(); stages[StageId.LVS] = "failed"
    assert not evaluate_repair(
        pdn_record(), stage_results=stages, evidence_gates=evidence(),
    ).repair_verified


def test_memory_failure_code_must_match():
    memory = {
        **pdn_record(), "repair_verified": True,
        "verification_scope": "physical_signoff",
        "modified_surfaces": ["floorplan", "pdn"],
    }
    compatible, _ = memory_is_compatible(
        memory, failure_code="RTL-0001", proposed_actions=pdn_record()["actions"],
    )
    assert not compatible
