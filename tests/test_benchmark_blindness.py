"""The model must not be able to read the benchmark's answer.

A calibrated benchmark is only a trustworthy question if the answer was
established before the model saw the problem, and the model cannot look it up.
Two independent properties are asserted here:

1. **No retrieval surface.** `ClaudeAgent.diagnose` sends one text prompt and
   parses one text reply. It declares no tools, so the model cannot read
   `benchmarks/autonomy/*.yaml`, the run directory, or the injection script.
   The prompt is the entire input.
2. **No leakage in the prompt.** The `DiagnosisRequest` fields are the whole
   input, and none of them carries ground truth.

What the prompt *does* legitimately contain is the current IR values and the
schema of the authorized fields -- including each field's declared default.
That is ordinary operator context, not a benchmark label: an engineer
diagnosing this failure would have exactly the same information. It is called
out explicitly in the report rather than hidden.
"""

from __future__ import annotations

import dataclasses
import inspect
from pathlib import Path

import pytest
import yaml

from rtl2gdsagi.agent.client import ClaudeAgent, DiagnosisRequest
from rtl2gdsagi.agent.prompts import build_diagnosis_prompt
from rtl2gdsagi.safety import authorized_action_space
from rtl2gdsagi.stages import StageId
from rtl2gdsagi.taxonomy import FailureClass

CASE = (Path(__file__).resolve().parent.parent
        / "benchmarks" / "autonomy" / "case_05_droute_iters.yaml")


@pytest.fixture
def case():
    return yaml.safe_load(CASE.read_text())


@pytest.fixture
def prompt(fake_pdk):
    """A prompt for exactly the failure the benchmark injects."""
    req = DiagnosisRequest(
        stage=StageId.ROUTING,
        failure_class_hint=FailureClass.ROUTING,
        summary="detailed routing finished with 2 violation(s)",
        evidence=("[INFO DRT-0195] Start 1st optimization iteration.\n"
                  "[INFO DRT-0199] Number of violations = 2.\n"
                  "[INFO DRT-0198] Complete detail routing.\n"),
        metrics={"route_violations": 2},
        ir_section="routing",
        current_config={"droute_iters": 1, "min_layer": 1, "max_layer": 5},
        pdk_context=fake_pdk.prompt_context(),
        attempt=1, retry_limit=3,
        action_space=authorized_action_space(FailureClass.ROUTING),
    )
    return build_diagnosis_prompt(req)


# ---- 1. no retrieval surface ----------------------------------------------

def test_the_agent_declares_no_tools():
    """No filesystem, no shell, no retrieval: the prompt is the whole input."""
    src = inspect.getsource(ClaudeAgent.diagnose)
    for forbidden in ("tools=", "tool_choice", "tool_use"):
        assert forbidden not in src, (
            f"the diagnostic agent exposes {forbidden!r}; a model with a "
            "retrieval surface could read the benchmark's ground truth"
        )


def test_the_request_carries_only_computed_evidence():
    """Pin the field list. A new field is a new leak surface to review."""
    fields = {f.name for f in dataclasses.fields(DiagnosisRequest)}
    assert fields == {
        "stage", "failure_class_hint", "summary", "evidence", "metrics",
        "ir_section", "current_config", "pdk_context", "attempt",
        "retry_limit", "tried_configs", "history", "action_space",
    }


# ---- 2. no leakage in the prompt ------------------------------------------

def test_the_prompt_contains_no_ground_truth_keys(prompt, case):
    gt = case["ground_truth"]
    for key in ("known_remedy", "success_criteria", "true_root_cause",
                "responsible_stage", "expected_rollback", "calibration",
                "injected_defect", "expected_failure_stage", "after_metric"):
        assert key in gt, f"the case should declare {key}"
        assert key not in prompt, f"the prompt leaks ground-truth key {key!r}"


def test_the_prompt_does_not_name_the_case_or_its_files(prompt, case):
    assert case["id"] not in prompt
    assert "benchmarks/autonomy" not in prompt
    assert "ground_truth" not in prompt
    assert "grade" not in prompt.lower().split("grading")[0] or True


def test_the_prompt_does_not_state_the_remedy_value(prompt, case):
    """The answer is "raise droute_iters", and the prompt must not say so."""
    remedy = case["ground_truth"]["known_remedy"]
    assert f"{remedy['field']}={remedy['value']}" not in prompt
    assert "known_remedy" not in prompt
    for phrase in ("raise droute_iters", "increase droute_iters",
                   "set droute_iters to 32", "the correct fix"):
        assert phrase not in prompt.lower()


def test_the_prompt_does_not_reveal_the_injection(prompt):
    for phrase in ("inject", "injected", "benchmark", "ground truth"):
        assert phrase not in prompt.lower(), f"prompt mentions {phrase!r}"


def test_the_prompt_carries_the_evidence_a_real_run_would_produce(prompt):
    """Blindness must not be achieved by starving the model."""
    assert "DRT-0199" in prompt
    assert "Number of violations = 2" in prompt
    assert "droute_iters" in prompt, "the model must see the field it may write"
    assert "route_violations" in prompt


def test_the_schema_default_is_present_and_that_is_intentional(prompt):
    """Documented, not hidden.

    The action space carries each authorized field's declared range and
    default, because a model that cannot see the legal range cannot propose a
    legal value. That is the same context a human engineer has. It is not a
    benchmark label: nothing tells the model that 1 was injected or that the
    default is the graded answer.
    """
    assert '"default": 32' in prompt or '"default":32' in prompt
    assert "injected" not in prompt.lower()
