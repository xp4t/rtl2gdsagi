"""N1: the model only sees current values for fields it may actually write.

The action space was already correct, but `current_config` carried the failing
stage's raw IR section, so the prompt showed frozen and no-op fields --
`routing.global_effort` among them. The validator rejects such a proposal, so
the failure mode was fail-closed; but a model that spends the one allowed live
diagnosis on a field we showed it and forbade has been misled by us.

Both now come from `authorized_action_space`, so there is no second permission
list that can drift.
"""

from __future__ import annotations

import json

import pytest

from rtl2gdsagi.agent.client import DiagnosisRequest
from rtl2gdsagi.agent.prompts import build_diagnosis_prompt
from rtl2gdsagi.ir import IR, SCHEMA
from rtl2gdsagi.safety import authorized_action_space, authorized_current_values
from rtl2gdsagi.stages import StageId
from rtl2gdsagi.taxonomy import FailureClass

FROZEN = [
    ("routing", "global_effort"),
    ("floorplan", "io_mode"),
    ("placement", "effort"),
    ("placement", "max_displacement_um"),
    ("placement", "congestion_overflow_limit"),
]


def _request(ir, failure, pdk):
    return DiagnosisRequest(
        stage=StageId.ROUTING, failure_class_hint=failure,
        summary="detailed routing finished with 2 violation(s)",
        evidence="[INFO DRT-0199] Number of violations = 2.\n",
        metrics={"route_violations": 2}, ir_section="routing",
        current_config=authorized_current_values(ir, failure),
        pdk_context=pdk.prompt_context(), attempt=1, retry_limit=3,
        action_space=authorized_action_space(failure),
    )


@pytest.fixture
def case05_ir():
    return IR({"routing": {"droute_iters": 1}})


@pytest.mark.parametrize("section,field", FROZEN)
def test_frozen_fields_are_not_in_the_current_values(case05_ir, section, field):
    values = authorized_current_values(case05_ir, FailureClass.ROUTING)
    assert field not in values.get(section, {}), (
        f"{section}.{field} is shown to the model but cannot be written"
    )


@pytest.mark.parametrize("section,field", FROZEN)
def test_frozen_fields_are_nowhere_in_the_prompt(case05_ir, section, field, fake_pdk):
    prompt = build_diagnosis_prompt(_request(case05_ir, FailureClass.ROUTING, fake_pdk))
    assert field not in prompt, f"the prompt mentions {section}.{field}"


@pytest.mark.parametrize("failure", list(FailureClass))
def test_every_visible_current_value_is_authorized(failure):
    """The invariant, for every failure class -- not just routing."""
    ir = IR({})
    space = authorized_action_space(failure)
    for section, values in authorized_current_values(ir, failure).items():
        assert section in space, f"{section} is visible but not authorized"
        extra = set(values) - set(space[section])
        assert not extra, f"{section}.{sorted(extra)} visible but not writable"


@pytest.mark.parametrize("failure", list(FailureClass))
def test_every_authorized_field_has_its_actual_current_value(failure):
    ir = IR({})
    space = authorized_action_space(failure)
    values = authorized_current_values(ir, failure)
    for section, fields in space.items():
        for field in fields:
            assert field in values.get(section, {}), (
                f"{section}.{field} is writable but has no current value"
            )
            assert values[section][field] == ir.section(section)[field]


def test_freezing_a_field_removes_it_from_both_without_touching_prompt_code(
        monkeypatch, case05_ir, fake_pdk):
    """One permission source: flipping the schema flag is sufficient."""
    import dataclasses

    assert "droute_iters" in authorized_current_values(
        case05_ir, FailureClass.ROUTING)["routing"]

    # Field is frozen, so swap the object rather than mutating it -- the point
    # is that flipping the schema flag is the *only* change needed.
    frozen_schema = tuple(
        dataclasses.replace(f, agent_writable=False)
        if f.name == "droute_iters" else f
        for f in SCHEMA["routing"]
    )
    monkeypatch.setitem(SCHEMA, "routing", frozen_schema)

    space = authorized_action_space(FailureClass.ROUTING)
    values = authorized_current_values(case05_ir, FailureClass.ROUTING)
    assert "droute_iters" not in space.get("routing", {})
    assert "droute_iters" not in values.get("routing", {})
    prompt = build_diagnosis_prompt(_request(case05_ir, FailureClass.ROUTING, fake_pdk))
    assert "droute_iters" not in prompt


def test_case_05_still_shows_the_injected_value_and_alternatives(
        case05_ir, fake_pdk):
    values = authorized_current_values(case05_ir, FailureClass.ROUTING)
    assert values["routing"]["droute_iters"] == 1
    # Legitimate alternatives remain visible; the surface is not narrowed to
    # the known answer.
    for alt in ("min_layer", "max_layer", "insert_diodes", "insert_filler"):
        assert alt in values["routing"]
    assert "placement" in values and "floorplan" in values

    prompt = build_diagnosis_prompt(_request(case05_ir, FailureClass.ROUTING, fake_pdk))
    assert '"droute_iters": 1' in prompt


def test_the_runner_does_not_pass_a_raw_ir_section(case05_ir):
    """Guard the actual production call site."""
    from pathlib import Path

    import rtl2gdsagi.runner as runner_mod

    src = Path(runner_mod.__file__).read_text()
    assert "current_config=authorized_current_values(" in src
    assert "current_config=self.ir.section(" not in src
