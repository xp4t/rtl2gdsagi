#!/usr/bin/env python3
"""Run one injected-failure benchmark case and record what the agent did.

    python benchmarks/autonomy/run_case.py benchmarks/autonomy/case_03_*.yaml \
        [--run-dir DIR] [--scripted-delta 'routing.max_layer=5']

The harness never decides anything about the design. It injects the defect,
starts the production orchestrator, and records the loop:

    real failure -> deterministic parser -> deterministic verdict
                 -> diagnosis -> safety review -> rollback -> rerun
                 -> deterministic reverification

Whether that constitutes *autonomy* depends entirely on where the diagnosis
came from, so the result records `agent` explicitly:

    live      ANTHROPIC_API_KEY present; the production diagnostic path ran
    scripted  no key; the answer was supplied by the harness

A `scripted` result validates the machinery. It is **not** evidence that the
system can diagnose anything, and must never be reported as such.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "src"))

import yaml  # noqa: E402

from rtl2gdsagi.agent.client import ScriptedAgent  # noqa: E402
from rtl2gdsagi.config import RunConfig  # noqa: E402
from rtl2gdsagi.runner import Orchestrator  # noqa: E402
from rtl2gdsagi.stages import StageId  # noqa: E402
from rtl2gdsagi.taxonomy import Diagnosis, FailureClass  # noqa: E402


def parse_delta(text: str) -> dict:
    """'routing.max_layer=5' -> {'routing': {'max_layer': 5}}"""
    out: dict = {}
    for part in filter(None, (p.strip() for p in text.split(","))):
        path, _, raw = part.partition("=")
        section, _, field = path.partition(".")
        try:
            value: object = json.loads(raw)
        except json.JSONDecodeError:
            value = raw
        out.setdefault(section, {})[field] = value
    return out


#: Everything this harness may create or delete lives under here.
RUNS_ROOT = (REPO / "benchmarks" / "autonomy" / "runs").resolve()


def _safe_run_dir(requested: str | None, case_id: str) -> Path:
    """Resolve a run directory, refusing anything outside the runs root.

    The harness deletes this path recursively. It previously accepted any
    `--run-dir` with no containment check at all, so one typo could remove the
    repository, the source RTL, or a writable PDK tree.
    """
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    target = (Path(requested).resolve() if requested
              else (RUNS_ROOT / case_id).resolve())

    if target == RUNS_ROOT or RUNS_ROOT not in target.parents:
        raise SystemExit(
            f"refusing to use {target} as a benchmark run directory: it is not "
            f"inside {RUNS_ROOT}. This path gets deleted recursively, so it is "
            "restricted to the benchmark results root."
        )
    if target.exists():
        import shutil
        shutil.rmtree(target)
    target.mkdir(parents=True)
    return target


#: Files whose content defines the benchmark instrument. If any of these
#: changes after a model has answered, the run is VOID (see README policy):
#: re-grading the same response under a modified evaluator is exactly the
#: retuning this project forbids.
FROZEN_INSTRUMENT = (
    ("case_yaml_sha256", None),                      # filled per case
    ("grader_sha256", "benchmarks/autonomy/grade.py"),
    ("harness_sha256", "benchmarks/autonomy/run_case.py"),
    ("prompt_code_sha256", "src/rtl2gdsagi/agent/prompts.py"),
    ("authorization_code_sha256", "src/rtl2gdsagi/safety.py"),
    ("action_space_schema_sha256", "src/rtl2gdsagi/ir.py"),
)


def freeze_instrument(case_path: Path) -> dict:
    """Hash the benchmark instrument before the model is allowed to answer."""
    import hashlib
    import time

    def sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    out = {"case_yaml_sha256": sha(case_path)}
    for key, rel in FROZEN_INSTRUMENT:
        if rel:
            out[key] = sha(REPO / rel)
    out["frozen_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return out


def build_live_agent(model: str | None):
    """Construct the production diagnostic agent, or return None.

    Kept separate so tests can assert *which class* live mode selects without
    contacting Anthropic: the object is built, its type is checked, and no
    request is issued.
    """
    from rtl2gdsagi.agent.client import ClaudeAgent

    return ClaudeAgent(model)


#: Everything an `autonomy_evidence: true` claim requires. Absence of any one
#: of these makes the claim false -- it is never inferred from a mode flag or
#: from a credential being present in the environment.
ATTRIBUTION_FIELDS = (
    "diagnosis_source",
    "agent_class",
    "provider",
    "model",
    "non_scripted_model_calls",
    "prompt_sha256",
    "evidence_sha256",
    "response_sha256",
    "failure_class",
    "safety_result",
    "accepted_delta",
    "rollback_target",
    "rerun_stages",
    "before_metrics",
    "after_metrics",
    "ground_truth_pass",
    "candidate_valid",
)


def attribution_complete(result: dict) -> tuple[bool, list[str]]:
    """`(ok, missing)` for the autonomy-evidence contract."""
    missing = [
        f for f in ATTRIBUTION_FIELDS
        if result.get(f) in (None, "", [], {}, 0, False)
    ]
    if result.get("diagnosis_source") != "live_model":
        missing.append("diagnosis_source!=live_model")
    return (not missing), missing


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("case")
    ap.add_argument("--run-dir", default=None,
                    help="must be inside benchmarks/autonomy/runs/")
    ap.add_argument("--diagnosis-source", choices=("scripted", "live_model"),
                    required=True,
                    help="who answers the diagnosis. NEVER inferred from "
                         "credential presence: a run with no failures and a key "
                         "in the environment would otherwise be labelled live")
    ap.add_argument("--scripted-delta", default=None,
                    help="remediation to use when no live model is available")
    ap.add_argument("--scripted-stage", default=None,
                    help="stage the scripted diagnosis implicates")
    ap.add_argument("--scripted-class", default=None,
                    help="failure class the scripted diagnosis claims")
    args = ap.parse_args()

    case = yaml.safe_load(Path(args.case).read_text())
    # Declared, not inferred.
    live = args.diagnosis_source == "live_model"
    if live and not os.environ.get("ANTHROPIC_API_KEY"):
        print("--diagnosis-source live_model requires ANTHROPIC_API_KEY",
              file=sys.stderr)
        return 2

    cfg = RunConfig.build(config_path=str(REPO / case["design"]))
    # Inject the defect on top of the design's own configuration.
    injected = case.get("inject", {}).get("ir", {})

    run_dir = _safe_run_dir(args.run_dir, case["id"])

    # Freeze the instrument BEFORE anything runs, and write it where a
    # reviewer will find it next to the result.
    freeze = freeze_instrument(Path(args.case))
    (run_dir / "benchmark_freeze.json").write_text(
        json.dumps(freeze, indent=2, sort_keys=True))

    # P1-HARNESS-01: live mode used to leave `agent = None`, and the
    # Orchestrator's own default (`agent or ScriptedAgent()`) then quietly
    # substituted the scripted agent. A "live" run was therefore scripted, and
    # the result recorded `agent: live`. Live mode now constructs the real
    # diagnostic agent explicitly, and refuses to run without a credential
    # rather than degrading to a fallback.
    agent = None
    if live:
        from rtl2gdsagi.agent.client import ClaudeAgent

        agent = build_live_agent(cfg.model)
        if agent is None:
            print("could not construct a live diagnostic agent; refusing to "
                  "run rather than fall back to the scripted one",
                  file=sys.stderr)
            return 2
        if isinstance(agent, ScriptedAgent):
            print("live mode resolved to ScriptedAgent; refusing", file=sys.stderr)
            return 2
    if not live:
        diags = []
        if args.scripted_delta:
            diags = [
                Diagnosis(
                    failure=FailureClass(args.scripted_class or "routing"),
                    evidence="supplied by the benchmark harness, not diagnosed",
                    implicated_stage=(StageId(args.scripted_stage)
                                      if args.scripted_stage else None),
                    confidence=0.0,
                    config_delta=parse_delta(args.scripted_delta),
                )
            ] * 4
        agent = ScriptedAgent(diagnoses=diags)

    # RunConfig is frozen, which is the point -- the harness may not mutate a
    # live configuration. Build a new one carrying the injected defect.
    from dataclasses import replace
    merged = {k: dict(v) for k, v in cfg.ir_overrides.items()}
    for section, fields in injected.items():
        merged.setdefault(section, {}).update(fields)
    cfg = replace(cfg, ir_overrides=merged)

    orch = Orchestrator(cfg, agent=agent, run_dir=run_dir)

    started = time.time()
    rc = orch.run()
    elapsed = time.time() - started

    # What actually happened, from the run's own record.
    events = orch.log.read_events()
    rollbacks = [e for e in events if "rolling back" in str(e.get("message", ""))]
    diagnoses = [e for e in events if e.get("event") == "api_call"]

    # A live claim needs an actually recorded non-scripted call, not a mode
    # flag. `model: scripted` in the audit trail is what the ScriptedAgent
    # writes, so a run whose every call is scripted can never be evidence.
    real_calls = [
        e for e in diagnoses
        if e.get("model") and e.get("model") != "scripted"
    ]

    # ---- attribution, built from what the run actually did ----------------
    #
    # F2: the contract required 17 fields and the harness populated four, so
    # `autonomy_evidence: true` was structurally unreachable. Every field below
    # now comes from a runtime record -- the orchestrator's accepted-delta
    # chain, the agent's own call audit, the deterministic verdicts, and the
    # signoff bundle -- not from a mode flag or a CLI answer.
    accepted = list(getattr(orch, "_accepted", []))
    audits = [a.to_dict() for a in getattr(orch, "_call_audits", [])]
    last_accept = accepted[-1] if accepted else {}
    first_audit = audits[0] if audits else {}

    responsible = (case.get("ground_truth", {}) or {}).get(
        "responsible_stage") or "routing"

    def _viol(which: str):
        vals = [h.get("metrics", {}).get("route_violations")
                for h in orch._history
                if h.get("stage") == responsible
                and h.get("metrics", {}).get("route_violations") is not None]
        if not vals:
            return None
        return vals[0] if which == "before" else vals[-1]

    signoff = {}
    sg = run_dir / "signoff.json"
    if sg.is_file():
        signoff = json.loads(sg.read_text())
    evidence_bundle = {}
    ev = run_dir / "gate_evidence.json"
    if ev.is_file():
        evidence_bundle = json.loads(ev.read_text())

    # Computed from the certification state, never from the process exit code.
    candidate_valid = bool(
        signoff.get("clean") is True
        and evidence_bundle.get("certification_id")
        and evidence_bundle.get("gates")
        and all(r.get("verdict") == "pass"
                for r in evidence_bundle.get("gates", {}).values())
    )

    result = {
        "case": case["id"],
        "diagnosis_source": args.diagnosis_source,
        "agent": "live" if live else "scripted",
        "agent_class": type(agent).__name__ if agent is not None else None,
        "provider": first_audit.get("provider") or (None if not live else None),
        "model": first_audit.get("model") or (cfg.model if live else None),
        "recorded_model_calls": len(
            [e for e in orch.log.read_events() if e.get("event") == "api_call"]),
        "non_scripted_model_calls": len(audits),
        "call_audits": audits,
        "synthetic_transport": any(a.get("synthetic_transport") for a in audits),
        "network_call": bool(audits) and not any(
            a.get("synthetic_transport") for a in audits),
        # Hashes of what the model was actually shown and returned.
        "prompt_sha256": first_audit.get("user_prompt_sha256"),
        "system_prompt_sha256": first_audit.get("system_prompt_sha256"),
        "evidence_sha256": first_audit.get("evidence_payload_sha256"),
        "response_sha256": first_audit.get("response_sha256"),
        # Deterministic execution facts.
        "failure_class": last_accept.get("deterministic_failure_class"),
        "safety_result": last_accept.get("safety_result"),
        "accepted_delta": last_accept.get("delta") or {},
        "rollback_target": last_accept.get("rollback_target"),
        "rerun_stages": sorted(
            sid.value for sid in orch.state.stages
            if (orch.state.stage(sid).attempts or 0) > 1
        ),
        "before_metrics": ({"route_violations": _viol("before")}
                           if _viol("before") is not None else {}),
        "after_metrics": ({"route_violations": _viol("after")}
                          if _viol("after") is not None else {}),
        "candidate_valid": candidate_valid,
        "certification_id": evidence_bundle.get("certification_id"),
        "injected": injected,
        "ground_truth": case.get("ground_truth", {}),
        "exit_code": rc,
        "elapsed_s": round(elapsed, 1),
        "benchmark_freeze": freeze,
        "stages_run": {
            sid.value: {
                "status": orch.state.stage(sid).status.value,
                "attempts": orch.state.stage(sid).attempts,
                "verdict": orch.state.stage(sid).last_verdict,
                "last_error": orch.state.stage(sid).last_error[:300],
            }
            for sid in orch.state.stages
        },
        "rollbacks": [
            {"message": e.get("message"), "invalidated": e.get("invalidated"),
             "restored_from": e.get("restored_from")}
            for e in [e for e in orch.log.read_events()
                      if "rolling back" in str(e.get("message", ""))]
        ],
        "history": orch._history[-25:],
    }

    (run_dir / "result.json").write_text(json.dumps(result, indent=2, default=str))

    print(f"\ncase      : {case['id']}")
    print(f"agent     : {result['agent']}"
          + ("" if live else "   (NOT autonomy evidence)"))
    print(f"exit      : {rc}   in {result['elapsed_s']}s")
    print(f"rollbacks : {len(rollbacks)}")
    for r in result["rollbacks"]:
        print(f"    {r['message']}")
    print(f"result    : {run_dir / 'result.json'}")

    # A benchmark that always exits zero cannot fail a CI job or a reviewer's
    # expectations, and "the process exited zero" is not benchmark success.
    # The strict grader checks the whole causal chain -- injection took effect,
    # a real tool failed, the deterministic class was right, the remedy stayed
    # in the authorized space, the right stage reran, the metric improved, and
    # the resulting evidence and lineage are valid.
    from grade import grade, grade_live_attribution

    # A line, not a loop (P0-LIVE-01).
    #
    #   causal criteria -> ground_truth_pass -> attribution -> live criteria
    #
    # The live attribution checks used to sit inside `grade()`, so grading
    # required `autonomy_evidence`, which required `ground_truth_pass`, which
    # came from grading. `autonomy_evidence: true` was unreachable for any
    # genuine live run. Nothing is loosened here; the questions are just asked
    # in an order that can be answered.
    g = grade(case, result, run_dir, case_path=Path(args.case))
    result["ground_truth_pass"] = g.passed

    ok, missing = attribution_complete(result)
    result["autonomy_evidence"] = ok
    result["attribution_missing"] = missing
    if live and not ok:
        print("autonomy_evidence withheld; missing: " + ", ".join(missing),
              file=sys.stderr)

    if live:
        # Extends the same Grade object, so there is exactly one verdict and
        # `result.json` and `grade.json` cannot disagree.
        grade_live_attribution(result, g)

    print("\ngrading:")
    print(g.report())
    (run_dir / "grade.json").write_text(json.dumps(g.to_dict(), indent=2))
    result["grade"] = g.to_dict()
    result["grade_passed"] = g.passed
    (run_dir / "result.json").write_text(json.dumps(result, indent=2, default=str))
    return 0 if g.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
