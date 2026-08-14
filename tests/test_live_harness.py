"""P1-HARNESS-01: live mode must actually use the live agent.

Codex's finding: `--diagnosis-source live_model` left `agent = None`, and the
Orchestrator's own default (`self.agent = agent or ScriptedAgent()`) then
substituted the scripted agent. A future "live" run would have been scripted
end to end while `result.json` recorded `agent: live`.

No request is ever issued here. The agent object is constructed and its type
checked; nothing contacts Anthropic.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parent.parent / "benchmarks" / "autonomy"
sys.path.insert(0, str(BENCH))

import run_case  # noqa: E402

from rtl2gdsagi.agent.client import ClaudeAgent, ScriptedAgent  # noqa: E402


# ---- which class each mode selects ----------------------------------------

def test_live_mode_builds_the_production_agent():
    agent = run_case.build_live_agent("claude-opus-5")
    assert isinstance(agent, ClaudeAgent)
    assert not isinstance(agent, ScriptedAgent)


def test_building_the_live_agent_makes_no_request(monkeypatch):
    """Construction must not touch the network or require a credential."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    agent = run_case.build_live_agent(None)
    assert isinstance(agent, ClaudeAgent)
    assert agent._client is None, "no client should be constructed eagerly"


def test_the_orchestrator_default_is_the_thing_that_used_to_bite():
    """Pin the fallback that made the bug invisible.

    `Orchestrator(cfg, agent=None)` still substitutes ScriptedAgent -- that is
    reasonable for ordinary use. The harness must therefore never hand it None
    in live mode, which is what the source assertion below enforces.
    """
    src = (BENCH / "run_case.py").read_text()
    assert "agent = build_live_agent(cfg.model)" in src
    assert "if isinstance(agent, ScriptedAgent):" in src, (
        "live mode must refuse a scripted agent explicitly"
    )


def test_live_mode_refuses_without_a_credential(monkeypatch, tmp_path, capsys):
    """No silent fallback: it exits non-zero before running anything."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", [
        "run_case.py", str(BENCH / "case_03_routing_layer_range.yaml"),
        "--diagnosis-source", "live_model",
    ])
    rc = run_case.main()
    assert rc == 2
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().err


def test_scripted_mode_never_claims_autonomy():
    ok, missing = run_case.attribution_complete({"diagnosis_source": "scripted"})
    assert ok is False
    assert "diagnosis_source!=live_model" in missing


# ---- the attribution contract ---------------------------------------------

def _complete() -> dict:
    d = {f: "recorded" for f in run_case.ATTRIBUTION_FIELDS}
    d.update({
        "diagnosis_source": "live_model",
        "non_scripted_model_calls": 1,
        "ground_truth_pass": True,
        "candidate_valid": True,
    })
    return d


def test_a_complete_chain_is_accepted():
    ok, missing = run_case.attribution_complete(_complete())
    assert ok is True and missing == []


@pytest.mark.parametrize("field", run_case.ATTRIBUTION_FIELDS)
def test_every_attribution_field_is_individually_required(field):
    d = _complete()
    d[field] = None
    ok, missing = run_case.attribution_complete(d)
    assert ok is False
    assert any(field in m for m in missing), missing


def test_autonomy_is_not_inferred_from_a_credential(monkeypatch):
    """Presence of a key in the environment proves nothing."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-not-a-real-key")
    d = _complete()
    d["non_scripted_model_calls"] = 0
    ok, _ = run_case.attribution_complete(d)
    assert ok is False


def test_the_contract_covers_the_whole_causal_chain():
    """Guards against the list being quietly trimmed."""
    required = set(run_case.ATTRIBUTION_FIELDS)
    for f in ("prompt_sha256", "response_sha256", "safety_result",
              "rollback_target", "rerun_stages", "before_metrics",
              "after_metrics", "ground_truth_pass", "candidate_valid"):
        assert f in required, f
