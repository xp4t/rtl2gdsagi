"""Release-candidate identity, attempt fingerprints, and rollback invalidation.

These three answer questions the run has to be able to answer about itself:

* *what exactly was certified?*  -- the release candidate manifest;
* *have we already run this experiment?* -- the attempt fingerprint;
* *does anything downstream of a rollback still look current?* -- invalidation.

Signoff previously answered the first with "these stages each passed", which is
not the same claim.
"""

from __future__ import annotations

import json

from rtl2gdsagi.agent.client import ScriptedAgent
from rtl2gdsagi.artifacts import ArtifactLedger
from rtl2gdsagi.checkpoints import fingerprint_attempt
from rtl2gdsagi.checks.tools import ToolRun
from rtl2gdsagi.ir import IR
from rtl2gdsagi.manifest import ReleaseCandidateManifest
from rtl2gdsagi.runner import Orchestrator
from rtl2gdsagi.stages import StageId
from rtl2gdsagi.state import StageStatus
from rtl2gdsagi.taxonomy import Diagnosis, FailureClass


def build(cfg, toolchain, *, fail=None, agent=None):
    orch = Orchestrator(cfg, agent=agent or ScriptedAgent())
    orch.invoker = toolchain(orch, fail=fail)
    return orch


# ---- B1: release candidate manifest ---------------------------------------

def test_a_clean_run_produces_a_verifiable_release_candidate(cfg, toolchain):
    orch = build(cfg, toolchain)
    assert orch.run() == 0

    rc = json.loads((orch.run_dir / "release_candidate.json").read_text())
    assert len(rc["candidate_id"]) == 64
    for key in ("final_gds", "sdc", "routed_netlist"):
        assert rc["artifacts"][key]["sha256"], f"{key} not bound"
    assert rc["pdk"]["name"]
    assert rc["tools"], "tool versions must be recorded"
    assert rc["config_sha256"] and rc["ir_sha256"]

    bundle = json.loads((orch.run_dir / "signoff.json").read_text())
    assert bundle["candidate_id"] == rc["candidate_id"]
    assert bundle["clean"] is True


def test_the_candidate_id_changes_when_a_bound_artifact_changes(cfg, toolchain):
    orch = build(cfg, toolchain)
    assert orch.run() == 0
    before = json.loads((orch.run_dir / "release_candidate.json").read_text())

    gds = orch.ledger.get("final_gds")
    gds.path.write_bytes(gds.path.read_bytes() + b"\x00extra")

    after = ReleaseCandidateManifest.build(
        top=orch.cfg.top, ledger=ArtifactLedger.from_dict(orch.ledger.to_dict()),
        pdk=orch.cfg.pdk.to_dict(), config=orch.cfg.to_dict(),
        ir_fingerprint=orch.ir.fingerprint(),
        tools=before["tools"],
    )
    # The ledger still holds the old hash, so the id is unchanged...
    assert after.candidate_id == before["candidate_id"]
    # ...but verification re-hashes from disk and catches it.
    problems = after.verify(orch.ledger)
    assert problems and "changed after it was bound" in problems[0]


def test_signoff_refuses_when_a_bound_artifact_changed_underneath_it(cfg, toolchain):
    """The manifest is re-verified, not merely written."""
    orch = build(cfg, toolchain)
    orch.run()
    gds = orch.ledger.get("final_gds")

    manifest = ReleaseCandidateManifest.build(
        top=orch.cfg.top, ledger=orch.ledger, pdk=orch.cfg.pdk.to_dict(),
        config=orch.cfg.to_dict(), ir_fingerprint=orch.ir.fingerprint(), tools={},
    )
    gds.path.write_bytes(b"a different layout entirely")
    problems = manifest.verify(orch.ledger)
    assert any("final_gds" in p for p in problems)


def test_a_candidate_without_a_gds_cannot_be_certified():
    empty = ArtifactLedger()
    m = ReleaseCandidateManifest.build(
        top="widget", ledger=empty, pdk={"name": "sky130A"}, config={},
        ir_fingerprint="x", tools={},
    )
    problems = m.required_present(("final_gds", "sdc"))
    assert len(problems) == 2
    assert not m.binds("final_gds")


def test_a_gate_that_checked_another_gds_is_reported():
    m = ReleaseCandidateManifest(
        top="widget", candidate_id="c", artifacts={"final_gds": {"sha256": "a" * 64}},
        pdk={}, tools={}, config_sha256="", ir_sha256="",
    )
    problems = m.gate_binding_problems(
        [{"stage": "drc", "metrics": {"checked_gds_sha256": "b" * 64}}]
    )
    assert problems and "drc" in problems[0]


# ---- B2: attempt fingerprints ---------------------------------------------

def test_the_fingerprint_follows_the_rendered_script():
    """Two attempts whose section config matches can still differ materially.

    Renderers read other sections -- routing reads cts.fix_hold -- so hashing
    the rendered script is what makes the duplicate guard ask the right
    question: is this the same effective experiment?
    """
    ir = IR()
    a = fingerprint_attempt(ir, "routing", {}, script="detailed_route -x")
    b = fingerprint_attempt(ir, "routing", {}, script="detailed_route -y")
    assert a != b


def test_the_fingerprint_follows_the_environment():
    ir = IR()
    a = fingerprint_attempt(ir, "routing", {}, causal_env={"pdk": "sky130A"})
    b = fingerprint_attempt(ir, "routing", {}, causal_env={"pdk": "gf180"})
    assert a != b, "the same knobs against a different PDK is a different run"


def test_the_fingerprint_ignores_things_that_are_not_causal():
    """Identical experiments must collide, or the duplicate guard never fires."""
    ir = IR()
    args = ("routing", {"cts_def": "abc"})
    assert fingerprint_attempt(ir, *args, script="x", causal_env={"pdk": "s"}) == \
           fingerprint_attempt(ir, *args, script="x", causal_env={"pdk": "s"})


def test_the_fingerprint_follows_upstream_content():
    ir = IR()
    a = fingerprint_attempt(ir, "routing", {"cts_def": "aaa"})
    b = fingerprint_attempt(ir, "routing", {"cts_def": "bbb"})
    assert a != b


# ---- B3: rollback invalidation --------------------------------------------

def _rollback_run(cfg, toolchain):
    """A routing failure the agent blames on placement."""
    agent = ScriptedAgent(diagnoses=[
        Diagnosis(
            failure=FailureClass.CONGESTION,
            evidence="overflow concentrated core-wide",
            implicated_stage=StageId.PLACEMENT,
            confidence=0.85,
            config_delta={"placement": {"target_density": 0.40}},
        )
    ])
    fail = {StageId.ROUTING: [
        ToolRun(argv=[], returncode=0,
                stdout=("[INFO DRT-0199]   Number of violations = 87.\n"
                        "[INFO DRT-0198] Complete detail routing.\n"),
                stderr="")
    ]}
    orch = build(cfg, toolchain, fail=fail, agent=agent)
    orch.run()
    return orch


def test_rollback_reruns_every_stage_downstream_of_the_target(cfg, toolchain):
    orch = _rollback_run(cfg, toolchain)
    # Placement and everything after it ran twice.
    for sid in (StageId.PLACEMENT, StageId.CTS, StageId.ROUTING):
        assert orch.invoker.stage_calls[sid] == 2, sid


def test_rollback_retires_stale_output_files(cfg, toolchain):
    """A re-run must not be able to inherit the previous attempt's outputs.

    Without this, a tool that exits 0 without writing leaves last attempt's
    file sitting exactly where the new one was expected -- and it would be
    registered and verified as if it were current.
    """
    orch = _rollback_run(cfg, toolchain)
    routing_dir = orch.run_dir / "stages" / "12_routing"
    attic = routing_dir / "superseded"
    assert attic.is_dir(), "superseded outputs should be kept for audit"
    assert any(attic.iterdir()), "the stale attempt should have been moved aside"

    # Whatever the ledger now points at is from the successful re-run, and it
    # is not inside the attic.
    routed = orch.ledger.get("routed_def")
    assert "superseded" not in str(routed.path)
    routed.assert_unchanged()


def test_rollback_drops_evidence_from_superseded_attempts(cfg, toolchain):
    """Signoff cross-checks history; stale entries are not evidence."""
    orch = _rollback_run(cfg, toolchain)
    routing_entries = [h for h in orch._history if h["stage"] == "routing"]
    assert routing_entries, "the successful re-run should be recorded"
    assert all(h["kind"] == "pass" for h in routing_entries), (
        "the failed pre-rollback attempt must not remain in the record: "
        f"{[h['kind'] for h in routing_entries]}")
    assert all(h["failure_class"] is None for h in routing_entries)


def test_rollback_resets_stages_that_never_checkpointed(cfg, toolchain):
    """invalidate_from only knew about stages that left a checkpoint."""
    orch = build(cfg, toolchain)
    orch.prepare()
    # Pretend a downstream stage was skipped in an earlier pass.
    orch.state.stage(StageId.DRC).status = StageStatus.SKIPPED
    orch.state.stage(StageId.DRC).last_error = "stale skip"

    orch._rollback(StageId.PLACEMENT, "test")

    assert orch.state.stage(StageId.DRC).status is StageStatus.PENDING
    assert orch.state.stage(StageId.DRC).last_error == ""
