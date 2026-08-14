"""The agent boundary.

Review 14.1 makes verdict authority architectural: the model reads
already-computed metrics and writes only a Diagnosis. These tests check that
the parsing layer refuses anything outside that contract, so a fluent-but-wrong
model response cannot become an applied change.
"""

from __future__ import annotations

import json

import pytest

from rtl2gdsagi.agent.client import (
    DiagnosisRequest,
    ScriptedAgent,
    parse_diagnosis,
    resolve_model,
)
from rtl2gdsagi.agent.prompts import SYSTEM_PROMPT, build_diagnosis_prompt
from rtl2gdsagi.errors import AgentError
from rtl2gdsagi.ir import SchemaViolation
from rtl2gdsagi.stages import StageId
from rtl2gdsagi.safety import authorized_action_space
from rtl2gdsagi.taxonomy import FailureClass


@pytest.fixture
def req(fake_pdk) -> DiagnosisRequest:
    return DiagnosisRequest(
        stage=StageId.ROUTING,
        failure_class_hint=FailureClass.ROUTING,
        summary="detailed routing left 12 violations",
        evidence="[ERROR DRT-0001] ...",
        metrics={"route_violations": 12},
        ir_section="routing",
        current_config={"droute_iters": 32},
        pdk_context=fake_pdk.prompt_context(),
        attempt=1,
        retry_limit=3,
        # P1-AUTH-01: the prompt is generated from the authorization table, so
        # the fixture supplies the same thing the runner does.
        action_space=authorized_action_space(FailureClass.ROUTING),
    )


def _resp(**kw) -> str:
    base = {
        "failure_class": "routing",
        "implicated_stage": "routing",
        "confidence": 0.8,
        "evidence": "12 violations",
        "reasoning": "raise iterations",
        "config_delta": {"routing": {"droute_iters": 48}},
        "escalate": False,
    }
    base.update(kw)
    return "```json\n" + json.dumps(base) + "\n```"


# ---- parsing --------------------------------------------------------------

def test_valid_response_parses(req):
    d = parse_diagnosis(_resp(), req)
    assert d.failure is FailureClass.ROUTING
    assert d.implicated_stage is StageId.ROUTING
    assert d.config_delta == {"routing": {"droute_iters": 48}}


def test_json_without_a_fence_is_accepted(req):
    raw = json.dumps({
        "failure_class": "routing", "implicated_stage": "routing",
        "confidence": 0.5, "config_delta": {},
    })
    assert parse_diagnosis(raw, req).confidence == 0.5


def test_prose_without_json_is_rejected(req):
    with pytest.raises(AgentError, match="no JSON object"):
        parse_diagnosis("I think you should increase the iterations.", req)


def test_unknown_failure_class_is_rejected(req):
    with pytest.raises(AgentError, match="unknown failure_class"):
        parse_diagnosis(_resp(failure_class="vibes"), req)


def test_unknown_stage_is_rejected(req):
    with pytest.raises(AgentError, match="unknown stage"):
        parse_diagnosis(_resp(implicated_stage="polishing"), req)


def test_delta_naming_an_unknown_section_is_rejected(req):
    with pytest.raises(SchemaViolation, match="unknown section"):
        parse_diagnosis(_resp(config_delta={"pdk": {"root": "/tmp"}}), req)


def test_model_cannot_return_tcl_as_a_config_delta(req):
    """The model has no channel for tool syntax at all."""
    with pytest.raises((SchemaViolation, AgentError)):
        parse_diagnosis(
            _resp(config_delta={"routing": "detailed_route -droute_end_iter 64"}), req
        )


def test_model_cannot_set_a_verdict(req):
    """A 'verdict' key is simply not read; it can never reach a Verdict."""
    d = parse_diagnosis(_resp(verdict="pass", clean=True), req)
    assert not hasattr(d, "verdict")
    assert d.failure is FailureClass.ROUTING


def test_escalation_flag_is_carried(req):
    d = parse_diagnosis(_resp(escalate=True, confidence=0.1), req)
    assert d.escalated is True


def test_non_numeric_confidence_is_rejected(req):
    with pytest.raises(AgentError, match="confidence"):
        parse_diagnosis(_resp(confidence="high"), req)


# ---- prompt ---------------------------------------------------------------

def test_prompt_includes_the_schema_the_model_may_write(req):
    p = build_diagnosis_prompt(req)
    assert "droute_iters" in p
    assert "`routing`" in p
    # A routing failure is authorised to touch placement and floorplan too;
    # the prompt used to withhold them.
    assert "`placement`" in p and "`floorplan`" in p


def test_prompt_states_the_forbidden_targets(req):
    p = build_diagnosis_prompt(req)
    assert "must NOT propose changes to" in p
    assert "pdk_and_library_files" in p


def test_prompt_includes_the_rollback_table(req):
    p = build_diagnosis_prompt(req)
    assert "congestion" in p and "placement" in p


def test_prompt_lists_already_tried_configs(req):
    req.tried_configs = [{"config": {"droute_iters": 48}, "result": "still 9 violations"}]
    p = build_diagnosis_prompt(req)
    assert "Already tried and failed" in p
    assert "48" in p


def test_system_prompt_forbids_tool_syntax_and_waivers():
    for phrase in ("never write TCL", "cannot waive", "never propose changes to RTL",
                   "immutable ground truth", "escalate"):
        assert phrase.lower() in SYSTEM_PROMPT.lower()


def test_prompt_never_contains_the_api_key(req, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret-value")
    assert "sk-ant" not in build_diagnosis_prompt(req)


# ---- model resolution -----------------------------------------------------

def test_model_defaults_and_env_override(monkeypatch):
    monkeypatch.delenv("RTL2GDSAGI_MODEL", raising=False)
    assert resolve_model() == "claude-opus-4-8"
    monkeypatch.setenv("RTL2GDSAGI_MODEL", "claude-sonnet-5")
    assert resolve_model() == "claude-sonnet-5"
    assert resolve_model("claude-opus-5") == "claude-opus-5"  # explicit wins


def test_scripted_agent_records_requests(req):
    a = ScriptedAgent()
    a.diagnose(req)
    assert a.calls[0].stage is StageId.ROUTING
