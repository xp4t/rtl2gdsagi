"""P1-AUTH-01: the prompt's action space equals the validator's.

The validator was already strong -- the deterministic failure class governs
authorization and no model relabel bypasses it. The prompt was the problem: it
injected `describe_section(failing_stage)`, which is the *whole* schema for one
section. So a signoff hold failure advertised frozen STA fields the validator
always rejects, while withholding the CTS/placement/routing knobs it would
have accepted. A model working from that prompt is guessing.

Both sides now derive from `safety.authorized_action_space`, so there is no
second list to keep in step.
"""

from __future__ import annotations

import json

import pytest

from rtl2gdsagi.agent.client import DiagnosisRequest
from rtl2gdsagi.agent.prompts import build_diagnosis_prompt

from rtl2gdsagi.ir import SCHEMA, writable_fields
from rtl2gdsagi.safety import (
    SafetyViolation,
    AUTHORIZED_SECTIONS,
    authorized_action_space,
    authorized_sections,
    review_delta_scope,
)
from rtl2gdsagi.stages import StageId
from rtl2gdsagi.taxonomy import FailureClass

FAILURES = sorted(AUTHORIZED_SECTIONS, key=lambda f: f.value)


def _request(failure, pdk):
    return DiagnosisRequest(
        stage=StageId.ROUTING, failure_class_hint=failure,
        summary="x", evidence="y", metrics={},
        ir_section="routing", current_config={},
        pdk_context=pdk.prompt_context(), attempt=1, retry_limit=3,
        action_space=authorized_action_space(failure),
    )


# ---- the equality that matters --------------------------------------------

@pytest.mark.parametrize("failure", FAILURES)
def test_prompt_field_set_equals_validator_field_set(failure, fake_pdk):
    """Field-for-field, for every failure class in the table."""
    space = authorized_action_space(failure)

    # What the validator would accept: authorised section x agent-writable field.
    expected: dict[str, set[str]] = {}
    for section in authorized_sections(failure):
        fields = set(writable_fields(section))
        if fields:
            expected[section] = fields

    assert {s: set(f) for s, f in space.items()} == expected

    # And the prompt carries exactly that, verbatim.
    prompt = build_diagnosis_prompt(_request(failure, fake_pdk))
    if not space:
        return
    marker = "Your authorised write surface"
    assert marker in prompt, "the prompt does not state an action space"
    block = prompt.split(marker, 1)[1].split("```json", 1)[1].split("```", 1)[0]
    payload = json.loads(block)
    assert {s: set(f) for s, f in payload.items()} == expected


@pytest.mark.parametrize("failure", FAILURES)
def test_no_locked_field_is_ever_advertised(failure, fake_pdk):
    """Verification intent must never appear in the action space."""
    space = authorized_action_space(failure)
    for section, fields in space.items():
        locked = {f.name for f in SCHEMA[section] if not f.agent_writable}
        assert not (set(fields) & locked), (
            f"{failure.value} advertises locked {section} field(s): "
            f"{sorted(set(fields) & locked)}"
        )


@pytest.mark.parametrize("failure", FAILURES)
def test_every_advertised_section_survives_the_validator(failure):
    """Anything the prompt offers must actually pass scope review."""
    space = authorized_action_space(failure)
    for section, fields in space.items():
        delta = {section: {next(iter(fields)): SCHEMA[section][0].default}}
        review_delta_scope(delta, failure)          # must not raise


@pytest.mark.parametrize("failure", FAILURES)
def test_sections_outside_the_space_are_refused(failure):
    offered = set(authorized_action_space(failure))
    for section in sorted(set(SCHEMA) - offered):
        with pytest.raises(SafetyViolation):
            review_delta_scope({section: {}}, failure)


# ---- the specific complaints ----------------------------------------------

def test_hold_sees_its_cross_stage_knobs_and_no_timing_intent(fake_pdk):
    space = authorized_action_space(FailureClass.HOLD)
    assert "cts" in space and "hold_margin_ns" in space["cts"]
    assert "placement" in space
    # Timing intent is frozen: neither section may appear at all.
    assert "sdc" not in space and "sta" not in space


def test_drc_sees_physical_knobs_not_the_drc_section(fake_pdk):
    space = authorized_action_space(FailureClass.DRC)
    assert "routing" in space and "placement" in space
    assert "drc" not in space, "a DRC section would be a waiver surface"


def test_an_unknown_failure_class_offers_nothing():
    assert authorized_action_space(None) == {}


def test_writable_fields_excludes_locked_ones():
    fields = writable_fields("sim")
    assert "timeout_s" not in fields
    assert "testbench_glob" not in fields
