"""Regressions for the Codex pre-autonomy review (2026-08-14).

Each test reproduces a finding Codex demonstrated against this repository and
fails against the behaviour that shipped before the remediation. They are
grouped by the review's own IDs.

The organising idea behind all of them is one Codex stated plainly:

    schema-bounded model output != safe semantic authority

A model constrained to typed fields can still change what is measured, and a
gate that inspects the right file can still be reading a file from a different
attempt. Both are certification failures even though every value involved is
individually valid.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rtl2gdsagi.agent.client import ScriptedAgent
from rtl2gdsagi.checks.tools import ToolRun
from rtl2gdsagi.ir import IR, SchemaViolation
from rtl2gdsagi.runner import Orchestrator
from rtl2gdsagi.safety import (
    SafetyViolation,
    authorized_sections,
    earliest_affected_stage,
    review_delta_scope,
)
from rtl2gdsagi.stages import StageId
from rtl2gdsagi.taxonomy import Diagnosis, FailureClass

ROUTED_OK = ("[INFO DRT-0199]   Number of violations = 0.\n"
             "[INFO DRT-0198] Complete detail routing.\n")
ROUTED_DIRTY = ("[INFO DRT-0199]   Number of violations = 7.\n"
                "[INFO DRT-0198] Complete detail routing.\n")


def build(cfg, toolchain, *, fail=None, agent=None):
    orch = Orchestrator(cfg, agent=agent or ScriptedAgent())
    orch.invoker = toolchain(orch, fail=fail)
    return orch


# ---- P0-01: verification intent is frozen ---------------------------------

@pytest.mark.parametrize("section,field,value", [
    ("sdc", "default_clock_period_ns", 100.0),   # lengthen the clock
    ("sdc", "clock_uncertainty_ns", 0.0),        # remove the margin
    ("sdc", "input_delay_frac", 0.0),            # remove IO constraints
    ("sim", "testbench_glob", "known_pass_tb.v"),  # pick a weaker testbench
    ("sim", "testbench_dir", "/tmp/elsewhere"),
    ("sta", "corners", ["ff_n40C_1v95"]),        # an optimistic corner
    ("sta", "derate_setup", 0.0),
    ("sta", "slack_guardband_ns", 0.0),
    ("extraction", "corner", "min"),             # optimistic RC
    ("extraction", "min_net_coverage", 0.0),     # accept an empty SPEF
    ("lint", "fail_on_warning", False),
])
def test_the_model_cannot_write_verification_intent(section, field, value):
    """What counts as "verified" belongs to the user, not to the diagnosis.

    Codex reproduced routing diagnoses that lengthened the clock and selected a
    different testbench, and a setup diagnosis that changed the STA corner.
    Every one of those is schema-valid; none of them fixes anything. They make
    the measurement agree with the design instead.
    """
    with pytest.raises(SchemaViolation):
        IR().apply_delta({section: {field: value}}, agent=True)


def test_the_user_can_still_set_verification_intent():
    """Frozen means frozen *to the model*, not immutable."""
    ir = IR()
    ir.apply_delta({"sdc": {"default_clock_period_ns": 20.0}}, agent=False)
    assert ir.get("sdc", "default_clock_period_ns") == 20.0


def test_implementation_knobs_remain_writable():
    ir = IR()
    ir.apply_delta({"routing": {"droute_iters": 48}}, agent=True)
    assert ir.get("routing", "droute_iters") == 48


# ---- P0-01: per-failure authorization --------------------------------------

def test_a_delta_outside_the_failure_authorization_is_refused():
    routing_plus_sdc = {"routing": {"droute_iters": 48}, "sdc": {}}
    with pytest.raises(SafetyViolation, match="does not authorise"):
        review_delta_scope(routing_plus_sdc, FailureClass.ROUTING)


def test_an_escalated_failure_authorizes_no_configuration_change():
    """An equivalence mismatch is not a knob-tuning situation."""
    assert authorized_sections(FailureClass.LEC_MISMATCH) == frozenset()
    with pytest.raises(SafetyViolation):
        review_delta_scope({"routing": {}}, FailureClass.LEC_MISMATCH)


def test_timing_failures_cannot_reach_the_constraints():
    for fc in (FailureClass.SETUP, FailureClass.HOLD):
        allowed = authorized_sections(fc)
        assert "sdc" not in allowed
        assert "sta" not in allowed
        assert allowed, "a timing failure must still have somewhere to go"


def test_the_causal_chain_of_a_routing_failure_is_authorized():
    """Cross-stage remediation must remain possible."""
    allowed = authorized_sections(FailureClass.ROUTING)
    assert {"routing", "placement", "floorplan"} <= allowed


# ---- P0-01: rollback follows the delta -------------------------------------

def test_rollback_cannot_start_downstream_of_a_changed_section():
    assert earliest_affected_stage({"floorplan": {}}) is StageId.FLOORPLAN
    assert earliest_affected_stage(
        {"routing": {}, "floorplan": {}}) is StageId.FLOORPLAN
    assert earliest_affected_stage({}) is None


def test_a_floorplan_change_reruns_from_floorplan(cfg, toolchain):
    """Codex: an upstream field changed while only a downstream stage reran.

    The diagnosis blames routing and proposes a floorplan change. Whatever it
    claims, the floorplan is what changed, so floorplan is where the run must
    resume -- otherwise placement, CTS and routing all describe a floorplan
    that no longer exists.
    """
    agent = ScriptedAgent(diagnoses=[
        Diagnosis(
            failure=FailureClass.ROUTING, evidence="7 violations",
            implicated_stage=StageId.ROUTING,      # shallow claim ...
            confidence=0.9,
            config_delta={"floorplan": {"core_utilization": 0.30}},  # ... deep change
        )
    ])
    fail = {StageId.ROUTING: [ToolRun(argv=[], returncode=0,
                                      stdout=ROUTED_DIRTY, stderr="")]}
    orch = build(cfg, toolchain, fail=fail, agent=agent)
    assert orch.run() == 0

    for sid in (StageId.FLOORPLAN, StageId.PDN, StageId.PLACEMENT,
                StageId.CTS, StageId.ROUTING):
        assert orch.invoker.stage_calls[sid] >= 2, (
            f"{sid} did not re-run after an upstream change")


# ---- P0-02: attempt isolation ----------------------------------------------

def _silent_second_attempt(toolchain, orch):
    """Attempt 1 writes outputs and fails; attempt 2 writes nothing and 'passes'.

    This is Codex's reproduction exactly: the second invocation returns a clean
    terminal routing log without producing a DEF.
    """
    inner = toolchain(orch)

    class SilentRetry:
        stage_calls = inner.stage_calls

        def available(self, tool):
            return inner.available(tool)

        def run(self, tool, argv, *, cwd, timeout_s=3600, env=None, log_path=None):
            sid = inner._stage_for(Path(cwd))
            if sid is StageId.ROUTING:
                n = inner.stage_calls.get(sid, 0) + 1
                inner.stage_calls[sid] = n
                if n == 1:
                    inner._make_outputs(sid, Path(cwd))    # writes a real DEF
                    return ToolRun(argv=argv, returncode=0,
                                   stdout=ROUTED_DIRTY, stderr="")
                # Second attempt: clean log, no artifacts written at all.
                return ToolRun(argv=argv, returncode=0,
                               stdout=ROUTED_OK, stderr="")
            return inner.run(tool, argv, cwd=cwd, timeout_s=timeout_s, env=env,
                             log_path=log_path)

    return SilentRetry()


def test_a_retry_that_writes_nothing_cannot_certify_the_previous_attempt(cfg, toolchain):
    """The reproduced false certification.

    Before: routing attempt 1 wrote a DEF and failed; attempt 2 emitted a clean
    log and wrote nothing; the run certified attempt 1's DEF as attempt 2's
    result, under attempt 2's changed IR, and reported `clean: true`.
    """
    agent = ScriptedAgent(diagnoses=[
        Diagnosis(
            failure=FailureClass.ROUTING, evidence="7 violations",
            implicated_stage=StageId.ROUTING, confidence=0.9,
            config_delta={"routing": {"droute_iters": 48}},
        )
    ])
    orch = Orchestrator(cfg, agent=agent)
    orch.invoker = _silent_second_attempt(toolchain, orch)
    rc = orch.run()

    assert rc != 0, "a stage that produced no output must not certify"
    bundle_path = orch.run_dir / "signoff.json"
    if bundle_path.is_file():
        assert json.loads(bundle_path.read_text())["clean"] is False


def _writes_then_fails_once(toolchain, orch):
    """Attempt 1 writes real outputs and fails; attempt 2 writes and passes.

    The mock's queued-failure path deliberately writes nothing, so it cannot
    exercise retirement -- there is no stale file to retire. This wrapper
    produces the situation that matters: a failed attempt that *did* leave
    artifacts behind.
    """
    inner = toolchain(orch)

    class WritesThenFails:
        stage_calls = inner.stage_calls
        openlane_image = inner.openlane_image

        def available(self, tool):
            return inner.available(tool)

        def run(self, tool, argv, *, cwd, timeout_s=3600, env=None, log_path=None):
            sid = inner._stage_for(Path(cwd))
            if sid is StageId.ROUTING:
                n = inner.stage_calls.get(sid, 0) + 1
                inner.stage_calls[sid] = n
                inner._make_outputs(sid, Path(cwd))
                return ToolRun(argv=argv, returncode=0,
                               stdout=ROUTED_DIRTY if n == 1 else ROUTED_OK,
                               stderr="")
            return inner.run(tool, argv, cwd=cwd, timeout_s=timeout_s, env=env,
                             log_path=log_path)

    return WritesThenFails()


def test_declared_outputs_are_retired_before_every_attempt(cfg, toolchain):
    """Same-stage retries retire outputs too, not only rollbacks."""
    agent = ScriptedAgent(diagnoses=[
        Diagnosis(
            failure=FailureClass.ROUTING, evidence="7 violations",
            implicated_stage=StageId.ROUTING, confidence=0.9,
            config_delta={"routing": {"droute_iters": 48}},
        )
    ])
    orch = Orchestrator(cfg, agent=agent)
    orch.invoker = _writes_then_fails_once(toolchain, orch)
    assert orch.run() == 0

    attic = orch.run_dir / "stages" / "12_routing" / "superseded"
    assert attic.is_dir(), "the failed attempt's outputs should be kept aside"
    assert any(attic.rglob("*")), "nothing was retired"

    # What the ledger holds is the re-run's output, not the retired one.
    routed = orch.ledger.get("routed_def")
    assert "superseded" not in str(routed.path)
    routed.assert_unchanged()
