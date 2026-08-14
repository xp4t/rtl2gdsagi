"""The IR is the agent's entire write surface. These tests pin that boundary.

The review's argument (7, 14.2) is that safety here must be *structural*: the
model cannot propose waiving a DRC rule because no such field exists, not
because a prompt asked it not to. If any of these tests starts failing by
accepting a value, that guarantee is gone.
"""

from __future__ import annotations

import pytest

from rtl2gdsagi.ir import IR, SchemaViolation, describe_section
from rtl2gdsagi.safety import (
    BudgetExhausted,
    ImmutableZones,
    IterationBudget,
    SafetyViolation,
    review_diagnosis,
)
from rtl2gdsagi.stages import StageId
from rtl2gdsagi.taxonomy import Diagnosis, FailureClass


# ---- schema bounds --------------------------------------------------------

@pytest.mark.parametrize(
    "section,field,value",
    [
        ("floorplan", "core_utilization", 0.99),   # above max 0.90
        ("floorplan", "core_utilization", 0.01),   # below min 0.05
        ("floorplan", "aspect_ratio", 99.0),
        ("placement", "target_density", 1.5),
        ("cts", "target_skew_ns", -1.0),
        ("routing", "max_layer", 99),
        ("sta", "slack_guardband_ns", 100.0),
        ("lec", "induction_steps", 0),
    ],
)
def test_out_of_range_values_are_rejected(section, field, value):
    with pytest.raises(SchemaViolation):
        IR().update(section, {field: value})


@pytest.mark.parametrize(
    "section,field,value",
    [
        ("synthesis", "strategy", "TURBO"),
        ("placement", "effort", "maximum"),
        ("extraction", "corner", "typical"),
        ("floorplan", "io_mode", "wherever"),
    ],
)
def test_invalid_enum_choices_are_rejected(section, field, value):
    with pytest.raises(SchemaViolation):
        IR().update(section, {field: value})


def test_in_range_values_are_accepted():
    ir = IR()
    ir.update("floorplan", {"core_utilization": 0.62, "aspect_ratio": 1.5})
    assert ir.get("floorplan", "core_utilization") == pytest.approx(0.62)


# ---- the safety property: checks cannot be weakened ------------------------

@pytest.mark.parametrize(
    "section,field",
    [
        ("drc", "skip_rule"),
        ("drc", "waive_violations"),
        ("drc", "max_allowed_violations"),
        ("drc", "disable"),
        ("lvs", "ignore_mismatch"),
        ("lvs", "force_pass"),
        ("antenna", "waive"),
        ("sta", "ignore_negative_slack"),
    ],
)
def test_check_weakening_fields_do_not_exist(section, field):
    """There must be no way to express 'make this check pass without fixing it'."""
    with pytest.raises(SchemaViolation) as exc:
        IR().update(section, {field: True})
    assert "not a field in the schema" in str(exc.value)


def test_signoff_sections_expose_only_performance_knobs():
    for section in ("drc", "lvs", "antenna"):
        fields = set(describe_section(section))
        assert fields <= {"threads", "deep_mode"}, (
            f"{section} gained a field beyond performance tuning: {fields}"
        )


def test_unknown_section_is_rejected():
    with pytest.raises(SchemaViolation):
        IR().update("pdk", {"root": "/tmp/evil"})


# ---- atomicity ------------------------------------------------------------

def test_multi_section_delta_is_all_or_nothing():
    ir = IR()
    before = ir.fingerprint()
    with pytest.raises(SchemaViolation):
        ir.apply_delta({
            "placement": {"target_density": 0.70},   # valid
            "cts": {"target_skew_ns": -5.0},         # invalid
        })
    assert ir.fingerprint() == before
    assert ir.get("placement", "target_density") != 0.70


# ---- fingerprinting -------------------------------------------------------

def test_fingerprint_is_stable_and_sensitive():
    a, b = IR(), IR()
    assert a.fingerprint() == b.fingerprint()
    b.update("floorplan", {"core_utilization": 0.5001})
    assert a.fingerprint() != b.fingerprint()


def test_fingerprint_can_scope_to_sections():
    a, b = IR(), IR()
    b.update("cts", {"target_skew_ns": 0.9})
    assert a.fingerprint(["floorplan"]) == b.fingerprint(["floorplan"])
    assert a.fingerprint(["cts"]) != b.fingerprint(["cts"])


# ---- immutable zones ------------------------------------------------------

def test_pdk_and_source_rtl_are_unwritable(tmp_path):
    pdk = tmp_path / "pdk"
    rtl = tmp_path / "rtl"
    work = tmp_path / "run" / "work" / "rtl"
    for d in (pdk, rtl, work):
        d.mkdir(parents=True)
    zones = ImmutableZones(pdk_root=pdk, rtl_source=rtl)

    with pytest.raises(SafetyViolation, match="immutable zone"):
        zones.check_write(pdk / "libs.tech" / "klayout" / "drc" / "sky130A_mr.drc")
    with pytest.raises(SafetyViolation, match="immutable zone"):
        zones.check_write(rtl / "cam_top.v")
    zones.check_write(work / "cam_top.v")  # the run copy is fine


# ---- iteration budget -----------------------------------------------------

def test_budget_cannot_be_extended():
    b = IterationBudget(3)
    assert not hasattr(b, "extend")
    assert not hasattr(b, "grant")
    # total is a plain field, but nothing in the agent path can reach it: the
    # only mutator is spend(), which strictly decreases what remains.
    b.spend(); b.spend(); b.spend()
    assert b.exhausted
    with pytest.raises(BudgetExhausted):
        b.spend()


def test_budget_reports_progress():
    b = IterationBudget(5)
    b.spend(2, what="test")
    assert (b.spent, b.remaining) == (2, 3)


# ---- diagnosis review -----------------------------------------------------

def test_diagnosis_touching_check_deck_is_refused():
    """A DRC failure must not be 'fixed' by editing the DRC section."""
    diag = Diagnosis(
        failure=FailureClass.DRC,
        evidence="4743 violations",
        implicated_stage=StageId.ROUTING,
        confidence=0.9,
        config_delta={"drc": {"threads": 8}},
    )
    with pytest.raises(SafetyViolation, match="weakening|deck"):
        review_diagnosis(diag)


def test_diagnosis_within_bounds_is_allowed():
    diag = Diagnosis(
        failure=FailureClass.CONGESTION,
        evidence="overflow 0.08",
        implicated_stage=StageId.PLACEMENT,
        confidence=0.7,
        config_delta={"placement": {"target_density": 0.45}},
    )
    review_diagnosis(diag)  # must not raise


def test_diagnosis_confidence_must_be_a_probability():
    diag = Diagnosis(
        failure=FailureClass.ROUTING, evidence="x",
        implicated_stage=StageId.ROUTING, confidence=1.7,
    )
    with pytest.raises(SafetyViolation, match="confidence"):
        review_diagnosis(diag)


def test_diagnosis_cannot_implicate_an_unauthorised_stage():
    diag = Diagnosis(
        failure=FailureClass.ROUTING, evidence="x",
        implicated_stage=StageId.SYNTHESIS, confidence=0.5,
    )
    with pytest.raises(SafetyViolation, match="authorised"):
        review_diagnosis(diag, allowed_stage=StageId.ROUTING)
