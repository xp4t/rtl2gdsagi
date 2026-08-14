"""Tests for the review's structural fixes.

These assert architecture, not behaviour of any one tool: that the stage graph
closed the gaps the review identified, that rollback is table-driven and
reaches every stage, and that advisory gates cannot block.
"""

from __future__ import annotations

import pytest

from rtl2gdsagi.checkpoints import (
    CheckpointStore,
    DuplicateAttempt,
    fingerprint_attempt,
)
from rtl2gdsagi.checks.verdict import Verdict, VerdictKind, failed, qor_low
from rtl2gdsagi.ir import IR
from rtl2gdsagi.stages import (
    STAGE_ORDER,
    STAGES,
    SIGNOFF_GATES,
    Gate,
    StageId,
    downstream_of,
    get_stage,
    stage_index,
)
from rtl2gdsagi.taxonomy import (
    TAXONOMY,
    FailureClass,
    Resolution,
    is_autonomous,
    lookup,
    responsible_stage,
)


# ---- gaps the review said were missing ------------------------------------

def test_signoff_timing_exists_after_cts_and_after_route():
    """Review 4.3: the original flow had exactly one STA, before floorplanning."""
    assert StageId.STA_POSTCTS in STAGE_ORDER
    assert StageId.STA_SIGNOFF in STAGE_ORDER
    assert stage_index(StageId.STA_POSTCTS) > stage_index(StageId.CTS)
    assert stage_index(StageId.STA_SIGNOFF) > stage_index(StageId.ROUTING)
    assert stage_index(StageId.STA_SIGNOFF) > stage_index(StageId.EXTRACTION)


def test_signoff_sta_consumes_real_parasitics():
    """Post-route timing is only authoritative with extracted SPEF."""
    assert "spef" in get_stage(StageId.STA_SIGNOFF).consumes
    assert "spef" in get_stage(StageId.EXTRACTION).produces


def test_pre_layout_sta_is_advisory_not_a_hard_gate():
    """Review 4.9: a pre-placement estimate must not block or roll back."""
    assert get_stage(StageId.STA_PRE).gate is Gate.ADVISORY


def test_lec_brackets_every_netlist_transforming_stage():
    """Review 4.4: nothing may silently change function."""
    assert get_stage(StageId.LEC_SYNTH).gate is Gate.HARD
    assert get_stage(StageId.LEC_ROUTE).gate is Gate.HARD
    transformers = [s.id for s in STAGES if s.transforms_netlist]
    assert StageId.SYNTHESIS in transformers
    assert StageId.CTS in transformers
    # Every transformer is followed by some LEC later in the flow.
    last_lec = stage_index(StageId.LEC_ROUTE)
    for t in transformers:
        assert stage_index(t) < last_lec


def test_drc_lvs_antenna_are_three_separate_gates():
    """Review 4.7: one 'DRC/LVS Completed?' boolean hid which check failed."""
    for sid in (StageId.DRC, StageId.LVS, StageId.ANTENNA):
        assert get_stage(sid).gate is Gate.HARD
    assert len({StageId.DRC, StageId.LVS, StageId.ANTENNA}) == 3


def test_simulation_gate_exists_and_precedes_synthesis():
    """Review 4.5: lint is not functional verification."""
    assert stage_index(StageId.SIM) < stage_index(StageId.SYNTHESIS)


def test_pdn_and_extraction_are_distinct_stages():
    """Review 4.8: both were absent from the original diagram."""
    assert StageId.PDN in STAGE_ORDER
    assert StageId.EXTRACTION in STAGE_ORDER


def test_signoff_is_last_and_aggregates_every_hard_gate():
    """Review 4.10: 'a file was written' is not signoff."""
    assert STAGE_ORDER[-1] is StageId.SIGNOFF
    consumes = set(get_stage(StageId.SIGNOFF).consumes)
    assert "final_gds" in consumes
    for gate in SIGNOFF_GATES:
        assert any(p in consumes for p in get_stage(gate).produces), gate


def test_no_stage_takes_hand_written_tcl():
    """Review 4.1/20.1: the user never supplies a script."""
    for spec in STAGES:
        assert spec.ir_section is None or spec.ir_section in {
            s.ir_section for s in STAGES
        }


# ---- table-driven rollback ------------------------------------------------

def test_every_failure_class_resolves_to_a_stage_or_escalates():
    """No failure may fall through with nowhere to go.

    A class that asks for remediation must name the stage to remediate;
    a class that names no stage must be one that takes no action.
    """
    for entry in TAXONOMY:
        if entry.resolution in (Resolution.RETRY_STAGE, Resolution.ROLLBACK):
            assert (
                entry.responsible_stage is not None or entry.targets_failing_stage
            ), entry.failure
        else:
            assert entry.responsible_stage is None or entry.responsible_stage in STAGE_ORDER


def test_dynamic_target_resolves_to_the_failing_stage():
    """A rejected script implicates whichever stage's script it was."""
    assert responsible_stage(FailureClass.TCL_CONFIG) is None
    assert responsible_stage(
        FailureClass.TCL_CONFIG, failing_stage=StageId.CTS
    ) is StageId.CTS


def test_advisory_failure_class_takes_no_action():
    """Review 4.9: pre-layout timing must not be able to cause a rollback."""
    entry = lookup(FailureClass.TIMING_PRELAYOUT)
    assert entry.resolution is Resolution.RECORD_ONLY
    assert entry.responsible_stage is None
    assert entry.escalate_to is None


def test_rollback_reaches_stages_the_diagram_could_not():
    """Review 2.2: only two of eight gates had a drawn return path.

    Here every physical stage is a resolvable rollback target.
    """
    targets = {e.responsible_stage for e in TAXONOMY if e.responsible_stage}
    targets |= {e.escalate_to for e in TAXONOMY if e.escalate_to}
    for sid in (StageId.FLOORPLAN, StageId.PLACEMENT, StageId.CTS,
                StageId.ROUTING, StageId.GDSOUT, StageId.SYNTHESIS, StageId.SDC):
        assert sid in targets, f"{sid} is unreachable by any failure class"


def test_hold_never_implicates_rtl():
    """Review 9.3 hard rule."""
    entry = lookup(FailureClass.HOLD)
    assert entry.responsible_stage is StageId.CTS
    assert "rtl_functional_logic" in entry.forbids


def test_setup_escalates_from_placement_to_synthesis():
    """Review 9.2 delta analysis: shallow first, then deeper."""
    assert responsible_stage(FailureClass.SETUP) is StageId.PLACEMENT
    assert responsible_stage(FailureClass.SETUP, escalated=True) is StageId.SYNTHESIS


def test_congestion_escalates_from_placement_to_floorplan():
    """Review 9.1: prefer the shallowest rollback consistent with evidence."""
    assert responsible_stage(FailureClass.CONGESTION) is StageId.PLACEMENT
    assert responsible_stage(FailureClass.CONGESTION, escalated=True) is StageId.FLOORPLAN


@pytest.mark.parametrize(
    "failure",
    [
        FailureClass.LIBRARY,
        FailureClass.LVS_LIBRARY,
        FailureClass.LEC_MISMATCH,
        FailureClass.RTL_FUNCTIONAL,
        FailureClass.ENVIRONMENT,
    ],
)
def test_unresolvable_classes_escalate_rather_than_loop(failure):
    """Review 9.4/4.11: some things have no valid autonomous resolution."""
    assert not is_autonomous(failure)
    assert lookup(failure).responsible_stage is None


def test_library_failures_forbid_touching_the_pdk():
    for failure in (FailureClass.LIBRARY, FailureClass.LVS_LIBRARY):
        assert "pdk_and_library_files" in lookup(failure).forbids


def test_lvs_never_permits_editing_the_extracted_netlist():
    for failure in (FailureClass.LVS_PHYSICAL, FailureClass.LVS_LIBRARY,
                    FailureClass.LVS_STRUCTURAL):
        assert "extracted_netlist" in lookup(failure).forbids


# ---- verdict authority ----------------------------------------------------

def test_advisory_failure_does_not_block():
    """Review 4.9: pre-layout STA reporting negative slack is information."""
    v = failed(StageId.STA_PRE, FailureClass.TIMING_PRELAYOUT, "wns -0.4ns")
    assert v.kind is VerdictKind.FAIL
    assert v.ok is True and v.blocks is False


def test_hard_failure_blocks():
    v = failed(StageId.STA_SIGNOFF, FailureClass.SETUP, "wns -0.4ns")
    assert v.blocks is True


def test_qor_below_target_never_blocks():
    v = qor_low(StageId.PLACEMENT, "overflow 0.08 above 0.02")
    assert v.ok is True
    assert v.kind is VerdictKind.QOR_BELOW_TARGET


def test_fail_verdict_must_name_a_failure_class():
    """Otherwise the taxonomy cannot resolve a responsible stage."""
    with pytest.raises(ValueError, match="FailureClass"):
        Verdict(stage=StageId.ROUTING, kind=VerdictKind.FAIL, summary="broken")


def test_pass_verdict_cannot_carry_a_failure_class():
    with pytest.raises(ValueError):
        Verdict(
            stage=StageId.ROUTING, kind=VerdictKind.PASS, summary="ok",
            failure=FailureClass.ROUTING,
        )


# ---- checkpoint invalidation ---------------------------------------------

def test_rollback_invalidates_everything_downstream(tmp_path):
    """Review 10: downstream artifacts are stale by construction."""
    store = CheckpointStore(tmp_path)
    ir = IR()
    from rtl2gdsagi.artifacts import ArtifactLedger

    ledger = ArtifactLedger()
    for sid in (StageId.FLOORPLAN, StageId.PLACEMENT, StageId.CTS, StageId.ROUTING):
        f = tmp_path / f"{sid.value}.def"
        f.write_text(f"DEF for {sid.value}", encoding="utf-8")
        ledger.register(f"{sid.value}_out", f, stage=sid.value)
        store.save(sid, ir=ir, section=sid.value if sid.value in ("floorplan",) else None,
                   ledger=ledger, produces=[f"{sid.value}_out"])

    assert len(store.valid_stages()) == 4
    restore, killed = store.rollback_to(StageId.PLACEMENT)

    assert set(killed) == {StageId.PLACEMENT, StageId.CTS, StageId.ROUTING}
    assert restore is not None and restore.stage is StageId.FLOORPLAN
    assert store.valid_stages() == [StageId.FLOORPLAN]


def test_downstream_of_is_inclusive_and_ordered():
    d = downstream_of(StageId.CTS)
    assert d[0] is StageId.CTS
    assert StageId.ROUTING in d
    assert StageId.FLOORPLAN not in d


def test_duplicate_failed_configuration_is_refused(tmp_path):
    """Review 10: this is what stops 'iterate forever'."""
    store = CheckpointStore(tmp_path)
    ir = IR()
    fp = fingerprint_attempt(ir, "routing", {"cts_def": "abc123"})
    store.record_failure(fp, "detailed routing left 12 violations")

    assert store.already_failed(fp)
    with pytest.raises(DuplicateAttempt, match="already been attempted"):
        store.assert_not_tried(StageId.ROUTING, fp)


def test_changing_a_knob_produces_a_different_fingerprint(tmp_path):
    ir = IR()
    a = fingerprint_attempt(ir, "routing", {"cts_def": "abc"})
    ir.update("routing", {"droute_iters": 40})
    b = fingerprint_attempt(ir, "routing", {"cts_def": "abc"})
    assert a != b


def test_changed_inputs_produce_a_different_fingerprint():
    """Same knobs but a genuinely different upstream artifact is not a duplicate."""
    ir = IR()
    a = fingerprint_attempt(ir, "routing", {"cts_def": "abc"})
    b = fingerprint_attempt(ir, "routing", {"cts_def": "def"})
    assert a != b
