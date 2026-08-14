"""P0-R2: exact gate contracts, causal lineage, and certification identity.

Codex reproduced two things through the production `_signoff()` aggregator:

1. Ten PASS records with empty optional fields and empty consumed maps were
   accepted, because every check was conditional on the field being present.
2. More decisively, two *organically generated* clean candidates were combined
   without editing a single evidence record -- candidate A supplied the GDS
   with its DRC and LVS evidence, candidate B supplied the routed DEF, SPEF,
   STA, antenna and LEC evidence -- and the aggregator reported clean. Every
   file hash was internally correct. The manifest was an artifact *set*, not a
   causal graph.
"""

from __future__ import annotations

import json

import pytest

from rtl2gdsagi.agent.client import ScriptedAgent
from rtl2gdsagi.evidence import (
    APPROVED_TOOL_IDENTITIES,
    CERTIFYING_GATES,
    GATE_CONTRACTS,
    GateEvidence,
    certification_id,
    lineage_problems,
)
from rtl2gdsagi.manifest import ReleaseCandidateManifest
from rtl2gdsagi.runner import Orchestrator
from rtl2gdsagi.stages import StageId


def build(cfg, toolchain, generation: str = ""):
    orch = Orchestrator(cfg, agent=ScriptedAgent())
    orch.invoker = toolchain(orch, generation=generation)
    return orch


def _candidate(orch):
    return ReleaseCandidateManifest.build(
        top=orch.cfg.top, ledger=orch.ledger, pdk=orch.cfg.pdk.to_dict(),
        config=orch.cfg.to_dict(), ir_fingerprint=orch.ir.fingerprint(), tools={},
    )


def _resignoff(orch):
    from rtl2gdsagi.runlog import RunLog
    orch.log = RunLog(orch.run_dir)
    try:
        orch._signoff()
    except Exception:
        pass
    return json.loads((orch.run_dir / "signoff.json").read_text())


# ---- the contracts exist and are complete ---------------------------------

def test_gdsout_is_a_certifying_gate():
    """It used to be absent, so nothing bound routed_def -> final_gds."""
    assert StageId.GDSOUT in CERTIFYING_GATES
    c = GATE_CONTRACTS[StageId.GDSOUT]
    assert "routed_def" in c.consumed
    assert "final_gds" in c.produced
    assert c.report_key == "gds_summary"


@pytest.mark.parametrize("gate", CERTIFYING_GATES)
def test_every_contract_names_a_parser_and_a_tool(gate):
    c = GATE_CONTRACTS[gate]
    assert c.parser_contract, f"{gate} has no approved parser contract"
    assert c.tool_identities, f"{gate} has no approved tool identity"
    assert c.consumed, f"{gate} consumes nothing, so it proves nothing"


def test_corrected_input_contracts():
    """The specific mis-declarations Codex listed."""
    # STA signoff reads the routed DEF, not the routed netlist.
    assert "routed_def" in GATE_CONTRACTS[StageId.STA_SIGNOFF].consumed
    assert "spef" in GATE_CONTRACTS[StageId.STA_SIGNOFF].consumed
    assert "sdc" in GATE_CONTRACTS[StageId.STA_SIGNOFF].consumed
    # Simulation binds the testbench that earned the PASS.
    assert "testbench_dir" in GATE_CONTRACTS[StageId.SIM].consumed
    # Route LEC binds its RTL gold side.
    assert "rtl_dir" in GATE_CONTRACTS[StageId.LEC_ROUTE].consumed
    # PDN binds the floorplan it was generated from.
    assert "floorplan_def" in GATE_CONTRACTS[StageId.PDN].consumed
    # LVS binds the schematic it compared against.
    assert "routed_netlist" in GATE_CONTRACTS[StageId.LVS].consumed


# ---- reproduction 1: present but empty ------------------------------------

def _empty_record(gate: StageId) -> GateEvidence:
    return GateEvidence(gate=gate.value, verdict="pass", attempt_id="",
                        report_key=None, report_sha256=None)


def test_present_but_empty_evidence_is_refused(cfg, toolchain):
    """Ten PASS records with nothing in them used to certify."""
    orch = build(cfg, toolchain)
    assert orch.run() == 0

    for gate in CERTIFYING_GATES:
        orch._evidence[gate] = _empty_record(gate)
    bundle = _resignoff(orch)

    assert bundle["clean"] is False
    joined = " ".join(bundle["problems"])
    assert "records no attempt identity" in joined
    assert "did not record what it consumed" in joined
    assert "unapproved tool identity" in joined


@pytest.mark.parametrize("field,value,expect", [
    ("attempt_id", "", "records no attempt identity"),
    ("tool_identity", "", "unapproved tool identity"),
    ("tool_identity", "container:evil/image:v1", "unapproved tool identity"),
    ("parser_contract", "made-up/v9", "not the approved"),
    ("report_key", None, "must record its verdict against"),
])
def test_each_required_field_is_individually_required(
        cfg, toolchain, field, value, expect):
    orch = build(cfg, toolchain)
    assert orch.run() == 0
    manifest = _candidate(orch)

    from dataclasses import replace
    rec = replace(orch._evidence[StageId.DRC], **{field: value})
    problems = rec.problems_against(
        manifest_artifacts=manifest.artifacts, ledger=orch.ledger)
    assert any(expect in p for p in problems), problems


def test_missing_produced_edge_is_refused(cfg, toolchain):
    orch = build(cfg, toolchain)
    assert orch.run() == 0
    manifest = _candidate(orch)

    from dataclasses import replace
    rec = replace(orch._evidence[StageId.GDSOUT], produced={})
    problems = rec.problems_against(
        manifest_artifacts=manifest.artifacts, ledger=orch.ledger)
    assert any("did not record what it produced" in p for p in problems)


# ---- reproduction 2: the hybrid candidate ---------------------------------

def test_two_clean_candidates_cannot_be_combined(cfg, toolchain, tmp_path):
    """THE reproduction, with organically generated evidence from two runs.

    Nothing is edited: both runs are clean, and their records are simply
    interleaved the way Codex did it.
    """
    a = build(cfg, toolchain, generation="A")
    assert a.run() == 0
    b = build(cfg, toolchain, generation="B")
    assert b.run() == 0
    assert a.ledger.get("routed_def").sha256 != b.ledger.get("routed_def").sha256

    # A supplies GDS/DRC/LVS; B supplies the routed generation and its checks.
    from_a = (StageId.GDSOUT, StageId.DRC, StageId.LVS)
    hybrid = {}
    for gate in CERTIFYING_GATES:
        src = a if gate in from_a else b
        hybrid[gate] = src._evidence[gate]

    problems = lineage_problems(hybrid)
    assert problems, "the hybrid must not be accepted"
    assert any("different physical generations" in p for p in problems), problems
    assert any("routed_def" in p for p in problems), problems


def test_the_production_aggregator_rejects_the_hybrid(cfg, toolchain):
    """Not just the helper -- the real `_signoff()` path."""
    a = build(cfg, toolchain, generation="A")
    assert a.run() == 0
    b = build(cfg, toolchain, generation="B")
    assert b.run() == 0

    for gate in (StageId.EXTRACTION, StageId.STA_SIGNOFF, StageId.ANTENNA):
        a._evidence[gate] = b._evidence[gate]
    bundle = _resignoff(a)

    assert bundle["clean"] is False
    assert any("different physical generations" in p or "disagree about" in p
               for p in bundle["problems"]), bundle["problems"]


def test_a_coherent_proof_set_has_no_lineage_problems(cfg, toolchain):
    orch = build(cfg, toolchain)
    assert orch.run() == 0
    assert lineage_problems(orch._evidence) == []


# ---- certification identity -----------------------------------------------

def test_certification_identity_covers_the_proofs_not_just_the_files(
        cfg, toolchain):
    """Same artifacts, different proof set -> different certification."""
    orch = build(cfg, toolchain)
    assert orch.run() == 0
    manifest = _candidate(orch)

    before = certification_id(manifest.candidate_id, orch._evidence)

    from dataclasses import replace
    swapped = dict(orch._evidence)
    swapped[StageId.DRC] = replace(orch._evidence[StageId.DRC],
                                   attempt_id="drc#99")
    after = certification_id(manifest.candidate_id, swapped)

    assert before != after
    # ... and it is deterministic.
    assert before == certification_id(manifest.candidate_id, orch._evidence)


def test_the_run_records_a_certification_id(cfg, toolchain):
    orch = build(cfg, toolchain)
    assert orch.run() == 0
    bundle = json.loads((orch.run_dir / "gate_evidence.json").read_text())
    assert len(bundle["certification_id"]) == 64
    assert bundle["candidate_id"]
    assert set(bundle["gates"]) == {g.value for g in CERTIFYING_GATES}


# ---- testbench binding ----------------------------------------------------

def test_simulation_pass_does_not_survive_a_testbench_change(cfg, toolchain):
    """P0-R2/R2.4: the testbench hash is part of the candidate now."""
    orch = build(cfg, toolchain)
    assert orch.run() == 0

    tb = orch.ledger.get("testbench_dir")
    assert len(tb.sha256) == 64
    manifest = _candidate(orch)
    assert manifest.artifacts["testbench_dir"]["sha256"] == tb.sha256

    # Change a bench; the candidate no longer verifies.
    bench = next(iter(sorted(tb.path.glob("*.v"))), None)
    assert bench is not None, "the fixture design should have a testbench"
    bench.write_text(bench.read_text() + "\n// weakened check\n")
    problems = manifest.verify(orch.ledger)
    assert problems, "a changed testbench must invalidate the candidate"
    assert any("testbench_dir" in p for p in problems), problems


def test_approved_tool_identities_are_explicit():
    assert APPROVED_TOOL_IDENTITIES
    assert all(isinstance(x, str) and x for x in APPROVED_TOOL_IDENTITIES)
