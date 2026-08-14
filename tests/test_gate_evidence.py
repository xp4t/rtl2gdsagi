"""P0-03: signoff certifies on gate evidence, not on stage status.

The Codex reproduction was: set every `StageState` to OK, register two files
containing `not a gds` and `not sdc`, leave history empty, and the aggregator
returned `clean: true, problems: []`. It could not independently validate its
own state, because "the stage finished" was standing in for "the design was
verified".

These tests exercise the production signoff aggregator, not the serialisation.
"""

from __future__ import annotations

import json

import pytest

from rtl2gdsagi.agent.client import ScriptedAgent
from rtl2gdsagi.artifacts import ArtifactLedger, tree_sha256
from rtl2gdsagi.evidence import (
    CERTIFYING_GATES,
    GateEvidence,
    missing_evidence,
)
from rtl2gdsagi.manifest import ReleaseCandidateManifest
from rtl2gdsagi.runner import Orchestrator
from rtl2gdsagi.stages import StageId
from rtl2gdsagi.state import StageStatus


def build(cfg, toolchain):
    orch = Orchestrator(cfg, agent=ScriptedAgent())
    orch.invoker = toolchain(orch)
    return orch


def _signoff_bundle(orch):
    return json.loads((orch.run_dir / "signoff.json").read_text())


def _resignoff(orch):
    """Re-run the production aggregator after mutating state.

    `run()` closes the run log when it finishes, so a second aggregation needs
    a fresh handle. Nothing else about the orchestrator is reset -- the point
    is to drive the real `_signoff` against modified evidence.
    """
    from rtl2gdsagi.runlog import RunLog

    orch.log = RunLog(orch.run_dir)
    try:
        orch._signoff()
    except Exception:
        pass                       # the refusal itself is what is asserted


# ---- the reproduction ------------------------------------------------------

def test_all_stages_ok_with_no_evidence_still_fails(cfg, toolchain):
    """The Codex scenario, through the production aggregator.

    Every gate is marked complete and the run has produced nothing that
    certifies anything. A stage being finished is an orchestration fact.
    """
    orch = build(cfg, toolchain)
    orch.prepare()
    # Codex's construction: plausible-looking state, files that are not what
    # they claim, and no evidence at all.
    gds = orch.run_dir / "fake.gds"
    gds.write_text("not a gds")
    sdc = orch.run_dir / "fake.sdc"
    sdc.write_text("not sdc")
    orch.ledger.register("final_gds", gds, stage="gdsout")
    orch.ledger.register("sdc", sdc, stage="sdc")
    for sid in CERTIFYING_GATES:
        orch.state.stage(sid).status = StageStatus.OK
        orch.state.stage(sid).last_verdict = "pass"
    try:
        orch._signoff()
    except Exception:
        pass

    bundle = _signoff_bundle(orch)
    assert bundle["clean"] is False
    assert any("no verification evidence" in p for p in bundle["problems"])


def test_a_clean_run_produces_evidence_for_every_certifying_gate(cfg, toolchain):
    orch = build(cfg, toolchain)
    assert orch.run() == 0

    assert not missing_evidence(orch._evidence)
    bundle = json.loads((orch.run_dir / "gate_evidence.json").read_text())
    # P0-R2: the file now commits to a certification identity -- the candidate
    # plus exactly these proofs -- with the per-gate records under "gates".
    assert bundle["certification_id"]
    assert bundle["candidate_id"]
    written = bundle["gates"]
    for gate in CERTIFYING_GATES:
        assert gate.value in written, gate
        rec = written[gate.value]
        assert rec["verdict"] == "pass"
        assert rec["parser_contract"], f"{gate} records no parser contract"
        assert rec["consumed"], f"{gate} records no consumed artifacts"

    assert _signoff_bundle(orch)["clean"] is True


# ---- candidate mixing ------------------------------------------------------

def _candidate(orch):
    return ReleaseCandidateManifest.build(
        top=orch.cfg.top, ledger=orch.ledger, pdk=orch.cfg.pdk.to_dict(),
        config=orch.cfg.to_dict(), ir_fingerprint=orch.ir.fingerprint(), tools={},
    )


def test_evidence_from_another_candidate_is_refused(cfg, toolchain):
    """Candidate A's DRC evidence against candidate B's GDS."""
    orch = build(cfg, toolchain)
    assert orch.run() == 0
    manifest = _candidate(orch)

    stale = GateEvidence(
        gate="drc", verdict="pass", attempt_id="drc#1",
        report_key="drc_report",
        report_sha256=orch.ledger.get("drc_report").sha256,
        consumed={"final_gds": "f" * 64},        # a different layout
        parser_contract="x",
    )
    problems = stale.problems_against(
        manifest_artifacts=manifest.artifacts, ledger=orch.ledger)
    assert problems
    assert any("different design" in p for p in problems), problems


def test_evidence_whose_report_changed_afterwards_is_refused(cfg, toolchain):
    """A verdict is about a file; rewrite the file and the verdict is stale."""
    orch = build(cfg, toolchain)
    assert orch.run() == 0
    manifest = _candidate(orch)
    ev = orch._evidence[StageId.DRC]

    report = orch.ledger.get("drc_report").path
    report.write_text(report.read_text() + "\n<!-- edited after the verdict -->")

    problems = ev.problems_against(
        manifest_artifacts=manifest.artifacts, ledger=orch.ledger)
    assert any("changed after the verdict" in p for p in problems)


def test_evidence_recording_a_non_pass_verdict_is_refused(cfg, toolchain):
    orch = build(cfg, toolchain)
    assert orch.run() == 0
    manifest = _candidate(orch)

    ev = GateEvidence(gate="lvs", verdict="qor_below_target", attempt_id="lvs#1",
                      report_key=None, report_sha256=None)
    problems = ev.problems_against(
        manifest_artifacts=manifest.artifacts, ledger=orch.ledger)
    assert any("not a pass" in p for p in problems)


def test_evidence_naming_a_report_without_a_hash_is_refused(cfg, toolchain):
    orch = build(cfg, toolchain)
    assert orch.run() == 0
    manifest = _candidate(orch)

    ev = GateEvidence(gate="drc", verdict="pass", attempt_id="drc#1",
                      report_key="drc_report", report_sha256=None)
    problems = ev.problems_against(
        manifest_artifacts=manifest.artifacts, ledger=orch.ledger)
    assert any("recorded no hash" in p for p in problems)


def test_signoff_fails_when_a_certifying_gate_loses_its_evidence(cfg, toolchain):
    """Directly exercises the aggregator, not the helper."""
    orch = build(cfg, toolchain)
    assert orch.run() == 0
    assert _signoff_bundle(orch)["clean"] is True

    del orch._evidence[StageId.LVS]
    _resignoff(orch)

    bundle = _signoff_bundle(orch)
    assert bundle["clean"] is False
    assert any("lvs" in p and "no verification evidence" in p
               for p in bundle["problems"])


def test_signoff_fails_when_a_required_artifact_is_unbound(cfg, toolchain):
    orch = build(cfg, toolchain)
    assert orch.run() == 0

    del orch.ledger._items["spef"]
    _resignoff(orch)

    bundle = _signoff_bundle(orch)
    assert bundle["clean"] is False
    assert any("spef" in p for p in bundle["problems"])


# ---- source identity -------------------------------------------------------

def test_the_rtl_tree_is_bound_by_content_not_by_path(cfg, toolchain, design):
    """A design is identified by what it contains.

    `rtl_dir` used to be registered with sha256="", so two different designs
    at the same path were indistinguishable to a signoff.
    """
    orch = build(cfg, toolchain)
    assert orch.run() == 0

    rtl = orch.ledger.get("rtl_dir")
    assert len(rtl.sha256) == 64, "the RTL tree must have a content hash"

    before = tree_sha256(rtl.path)[0]
    (rtl.path / "widget.v").write_text("// a different design entirely\n")
    assert tree_sha256(rtl.path)[0] != before


def test_the_tree_hash_ignores_location_and_timestamps(tmp_path):
    """Identical sources hash identically wherever they live."""
    import os
    import shutil

    a = tmp_path / "a"
    a.mkdir()
    (a / "top.v").write_text("module top; endmodule\n")
    (a / "sub" ).mkdir()
    (a / "sub" / "x.v").write_text("module x; endmodule\n")

    b = tmp_path / "b"
    shutil.copytree(a, b)
    os.utime(b / "top.v", (0, 0))

    assert tree_sha256(a)[0] == tree_sha256(b)[0]


def test_reports_are_bound_to_the_candidate(cfg, toolchain):
    """Not just the layout: the verification outputs themselves."""
    orch = build(cfg, toolchain)
    assert orch.run() == 0
    rc = json.loads((orch.run_dir / "release_candidate.json").read_text())

    for key in ("drc_report", "lvs_report", "antenna_report", "rtl_dir"):
        assert rc["artifacts"][key]["sha256"], f"{key} is not bound"
