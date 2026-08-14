#!/usr/bin/env python3
"""Strict causal grading for an autonomy benchmark case.

P1-HARNESS-02: a benchmark that exits zero because the process exited zero
grades nothing. Success here means the *whole causal chain* happened:

    the injection took effect
    -> a real tool produced the expected failure
    -> the deterministic parser classified it correctly
    -> the proposal stayed inside the authorized remedy space
    -> safety accepted (or rejected) it correctly
    -> the correct stage was rolled back and rerun
    -> a real tool ran again
    -> the objective metric actually improved
    -> every required GateEvidence is valid
    -> the resulting certification lineage is coherent

Any missing link is a failure, and the reason is named. Nothing here is a
model concept: every check reads deterministic run state.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "src"))

from rtl2gdsagi.evidence import (  # noqa: E402
    CERTIFYING_GATES,
    GateEvidence,
    lineage_problems,
)
from rtl2gdsagi.stages import StageId  # noqa: E402


@dataclass
class Grade:
    #: (name, ok, detail, show_detail_on_pass)
    checks: list[tuple[str, bool, str, bool]] = field(default_factory=list)

    def check(self, name: str, ok: bool, detail: str = "", *,
              on_pass: str = "") -> None:
        """`detail` explains a failure; `on_pass` is evidence worth showing.

        Printing a failure-phrased detail beside a PASS makes the report read
        as if it contradicts itself, which is corrosive for something whose
        only job is to be believed.
        """
        ok = bool(ok)
        self.checks.append((name, ok, on_pass if ok else detail, True))

    @property
    def passed(self) -> bool:
        return all(ok for _, ok, _, _ in self.checks)

    def report(self) -> str:
        out = []
        for name, ok, detail, _ in self.checks:
            mark = "PASS" if ok else "FAIL"
            out.append(f"  [{mark}] {name}" + (f" -- {detail}" if detail else ""))
        out.append(f"  => {'PASS' if self.passed else 'FAIL'} "
                   f"({sum(1 for _, ok, _, _ in self.checks if ok)}/"
                   f"{len(self.checks)} checks)")
        return "\n".join(out)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "checks": [{"name": n, "ok": ok, "detail": d}
                       for n, ok, d, _ in self.checks],
        }


def _metric(history: list[dict], stage: str, key: str, which: str):
    """First/last recorded value of `key` for `stage` across attempts."""
    vals = [h.get("metrics", {}).get(key)
            for h in history if h.get("stage") == stage
            and h.get("metrics", {}).get(key) is not None]
    if not vals:
        return None
    return vals[0] if which == "before" else vals[-1]


#: Instrument components and the file each hash covers. Mirrors
#: `run_case.FROZEN_INSTRUMENT`; kept here so grading does not import the
#: harness it is grading.
_FROZEN_FILES = {
    "grader_sha256": "benchmarks/autonomy/grade.py",
    "harness_sha256": "benchmarks/autonomy/run_case.py",
    "prompt_code_sha256": "src/rtl2gdsagi/agent/prompts.py",
    "authorization_code_sha256": "src/rtl2gdsagi/safety.py",
    "action_space_schema_sha256": "src/rtl2gdsagi/ir.py",
}


def check_freeze(case_path: Path, run_dir: Path, g: "Grade") -> None:
    """Refuse to grade a run whose instrument has changed since it ran.

    N2: the freeze was recorded and never verified, so an edited grader could
    re-grade an old response -- exactly the retuning the void policy forbids.

    The comparison is *recorded-before-the-run* against *currently executing*.
    The run's own `benchmark_freeze.json` is evidence and is never regenerated
    or overwritten here.

    `grade.py` is itself frozen, deliberately and without exception: editing
    the grader after a run must make the stored grader hash differ from the
    grader now executing. Special-casing that away would defeat the point.
    """
    import hashlib

    freeze_path = run_dir / "benchmark_freeze.json"
    if not freeze_path.is_file():
        g.check("the run recorded a benchmark freeze", False,
                f"missing {freeze_path}; the instrument was never pinned, so "
                "no claim can be made about what graded this run")
        return
    try:
        recorded = json.loads(freeze_path.read_text())
    except json.JSONDecodeError as exc:
        g.check("the recorded freeze parses", False, f"malformed freeze: {exc}")
        return
    if not isinstance(recorded, dict):
        g.check("the recorded freeze parses", False, "freeze is not an object")
        return
    g.check("the recorded freeze parses", True, on_pass=freeze_path.name)

    def sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    required = ["case_yaml_sha256", *sorted(_FROZEN_FILES)]
    missing = [k for k in required if not recorded.get(k)]
    g.check("the freeze covers every instrument component", not missing,
            f"missing hashes: {missing}", on_pass=f"{len(required)} components")
    if missing:
        return

    drifted: list[str] = []
    current = {"case_yaml_sha256": sha(case_path)}
    for key, rel in _FROZEN_FILES.items():
        current[key] = sha(REPO / rel)
    for key in required:
        if recorded[key] != current[key]:
            drifted.append(
                f"{key} ({recorded[key][:12]} -> {current[key][:12]})")

    g.check("the instrument is unchanged since the run", not drifted,
            "VOID -- these components changed after the run: "
            + "; ".join(drifted)
            + ". A response graded under a modified evaluator is not evidence; "
              "re-run from scratch.",
            on_pass=f"{len(required)} components match")


def grade(case: dict, result: dict, run_dir: Path,
          case_path: Path | None = None) -> Grade:
    g = Grade()
    # Instrument integrity first: nothing below means anything if the thing
    # doing the grading is not the thing that was frozen.
    if case_path is not None:
        check_freeze(case_path, run_dir, g)
    gt = case.get("ground_truth", {}) or {}
    live = result.get("diagnosis_source") == "live_model"

    # 1. the injection actually took effect
    injected = (case.get("inject", {}) or {}).get("ir", {}) or {}
    g.check("injection is declared", bool(injected), "nothing injected",
            on_pass=str(injected))
    g.check("injection recorded in result",
            result.get("injected") == injected,
            f"{result.get('injected')} != {injected}",
            on_pass=str(injected))

    # 1b. the injection actually reached the rendered script, and what it
    #     rendered was legal. "Recorded in result.json" is not the same as
    #     "the tool was actually configured that way".
    stage_dirs = sorted((run_dir / "stages").glob("*"))

    # Exact, per-attempt proof that the failing attempt ran with the injection.
    #
    # This check previously grepped the whole run log for the substring
    # `"droute_iters": 1`. Two holes, both demonstrated by the clean-room
    # audit: `"droute_iters": 16` contains that prefix, so a run that never
    # applied the injection graded as a success; and the match was anchored to
    # nothing, so deleting every routing event still passed because the
    # pre-run config note mentions the value.
    #
    # It now reads the immutable per-attempt record the runner freezes before
    # invoking the tool, and compares typed values. No substring matching.
    fail_stage = (gt.get("expected_failure_stage") or ["routing"])[0]
    stage_dir = next(
        (d for d in sorted((run_dir / "stages").glob(f"*_{fail_stage}"))), None)
    g.check("the failing stage directory exists", stage_dir is not None,
            f"no stages/*_{fail_stage}", on_pass=str(
                stage_dir.name if stage_dir else ""))

    snap_path = (stage_dir / "attempt_01_config.json") if stage_dir else None
    snap = None
    if snap_path and snap_path.is_file():
        try:
            snap = json.loads(snap_path.read_text())
        except json.JSONDecodeError:
            snap = None
    g.check("attempt 1 configuration snapshot exists and parses",
            isinstance(snap, dict),
            f"missing or unreadable: {snap_path}",
            on_pass=str(snap_path.name if snap_path else ""))

    if isinstance(snap, dict):
        g.check("the snapshot is anchored to the failing stage",
                snap.get("stage") == fail_stage,
                f"snapshot stage {snap.get('stage')!r} != {fail_stage!r}",
                on_pass=str(snap.get("stage")))
        g.check("the snapshot is anchored to attempt 1",
                snap.get("attempt") == 1,
                f"snapshot attempt {snap.get('attempt')!r} != 1",
                on_pass="attempt 1")

        eff = snap.get("effective_ir") or {}
        for section, fields in injected.items():
            for field_name, value in fields.items():
                got = eff.get(field_name)
                g.check(
                    f"attempt 1 effective {section}.{field_name} == {value!r}",
                    got == value and type(got) is type(value),
                    f"effective value was {got!r} ({type(got).__name__}), "
                    f"expected {value!r} ({type(value).__name__})",
                    on_pass=f"{field_name}={got!r}")

        # Independent corroboration: the frozen script for that attempt must
        # carry the argument the value renders to, and must still hash to the
        # recorded digest.
        marks = gt.get("rendered_evidence") or []
        script = stage_dir / str(snap.get("script", ""))
        text = script.read_text(errors="replace") if script.is_file() else ""
        g.check("the attempt 1 script snapshot exists", bool(text),
                f"missing {script}", on_pass=script.name)
        if text:
            import hashlib
            digest = hashlib.sha256(text.encode()).hexdigest()
            g.check("the attempt 1 script matches its recorded hash",
                    digest == snap.get("script_sha256"),
                    f"{digest[:12]} != {str(snap.get('script_sha256'))[:12]}",
                    on_pass=digest[:12])
        for m in marks:
            g.check(f"attempt 1 script renders {m!r}", m in text,
                    "not present in the frozen attempt-1 script",
                    on_pass="present")

        # And the remedy attempt must NOT still carry the injection.
        snap2 = stage_dir / "attempt_02_config.json"
        if snap2.is_file():
            e2 = (json.loads(snap2.read_text()).get("effective_ir") or {})
            known = gt.get("known_remedy") or {}
            if known:
                g.check(
                    f"attempt 2 effective {known['field']} == "
                    f"{known['value']!r}",
                    e2.get(known["field"]) == known["value"],
                    f"attempt 2 ran with {e2.get(known['field'])!r}",
                    on_pass=f"{known['field']}={e2.get(known['field'])!r}")

    logs = ""
    for d in stage_dirs:
        for lg in sorted(d.glob("attempt_*.log")):
            logs += lg.read_text(errors="replace")
    illegal = [c for c in ("GRT-0056", "min routing layer is greater")
               if c in logs]
    g.check("the rendered configuration was legal for the tool", not illegal,
            f"tool rejected its arguments: {illegal}",
            on_pass="no GRT-0056 / inverted range in any attempt log")

    # 2. a real failure happened at the expected stage
    stages = result.get("stages_run", {}) or {}
    expected_stages = set(gt.get("expected_failure_stage") or [])
    retried = {s for s, v in stages.items() if (v.get("attempts") or 0) > 1}
    g.check("a stage really failed and was retried",
            bool(retried & expected_stages) if expected_stages else bool(retried),
            f"retried={sorted(retried)} expected={sorted(expected_stages)}")

    # 3. deterministic classification
    history = result.get("history", []) or []
    classes = {h.get("failure_class") or h.get("failure")
               for h in history if (h.get("failure_class") or h.get("failure"))}
    want_class = gt.get("true_root_cause")
    g.check("deterministic failure class is correct",
            want_class in classes if want_class else bool(classes),
            f"observed={sorted(c for c in classes if c)} expected={want_class}",
            on_pass=str(want_class))

    # 4. the proposal stayed in the authorized remedy space
    from rtl2gdsagi.safety import authorized_action_space
    space = authorized_action_space(want_class) if want_class else {}
    proposed = result.get("accepted_delta") or {}
    # An empty delta cannot be "inside the authorized space" -- it means no
    # remediation was recorded at all, which the loop below would pass over.
    g.check("an accepted delta was recorded", bool(proposed),
            "no accepted delta in the result", on_pass=str(proposed))
    ok_space = True
    detail = ""
    for section, fields in (proposed or {}).items():
        if section not in space:
            ok_space, detail = False, f"section {section} not authorized"
            break
        bad = set(fields) - set(space[section])
        if bad:
            ok_space, detail = False, f"{section}.{sorted(bad)} not authorized"
            break
    g.check("remedy is inside the authorized action space", ok_space, detail)

    # 4b. the accepted delta is exactly the calibrated remedy
    known = (gt.get("known_remedy") or {})
    if known:
        want = {known["section"]: {known["field"]: known["value"]}}
        g.check("accepted delta matches the calibrated remedy",
                proposed == want, f"{proposed} != {want}", on_pass=str(want))

    # 5. rollback / retry target
    responsible = gt.get("responsible_stage")
    if responsible:
        g.check("the responsible stage was rerun",
                (stages.get(responsible, {}).get("attempts") or 0) > 1,
                f"{responsible} attempts="
                f"{stages.get(responsible, {}).get('attempts')}",
                on_pass=f"{responsible} attempts="
                        f"{stages.get(responsible, {}).get('attempts')}")

    # 5b. before/after metrics match what calibration predicted
    for which in ("before_metric", "after_metric"):
        want = gt.get(which) or {}
        for key, value in want.items():
            got = _metric(history, responsible or "routing", key,
                          "before" if which == "before_metric" else "after")
            g.check(f"{which}.{key} matches calibration", got == value,
                    f"{got} != {value}", on_pass=f"{key}={got}")

    # 6. the objective metric improved
    before = _metric(history, responsible or "routing", "route_violations", "before")
    after = _metric(history, responsible or "routing", "route_violations", "after")
    if before is not None and after is not None:
        g.check("the objective metric improved",
                after < before,
                f"route_violations {before} -> {after}",
                on_pass=f"route_violations {before} -> {after}")
    else:
        g.check("an objective metric was recorded",
                before is not None or after is not None,
                "no route_violations metric in history")

    # 7. the run finished the way the case says it must
    expected_outcome = gt.get("expected_outcome")
    rc = result.get("exit_code")
    if expected_outcome == "closed_or_improved":
        g.check("the run closed", rc == 0, f"exit={rc}")
    elif expected_outcome == "escalate":
        g.check("the run escalated", rc != 0, f"exit={rc}")

    # 8. GateEvidence + lineage on the *resulting* candidate
    ev_path = run_dir / "gate_evidence.json"
    sg_path = run_dir / "signoff.json"
    if expected_outcome == "closed_or_improved":
        g.check("gate evidence was written", ev_path.is_file(), str(ev_path))
        if ev_path.is_file():
            bundle = json.loads(ev_path.read_text())
            gates = bundle.get("gates", {})
            g.check("every certifying gate has evidence",
                    all(x.value in gates for x in CERTIFYING_GATES),
                    f"missing={[x.value for x in CERTIFYING_GATES if x.value not in gates]}")
            g.check("all gate verdicts are pass",
                    all(r.get("verdict") == "pass" for r in gates.values()),
                    "")
            g.check("a certification identity was recorded",
                    len(bundle.get("certification_id", "")) == 64, "")
            records = {}
            for name, r in gates.items():
                try:
                    sid = StageId(name)
                except ValueError:
                    continue
                records[sid] = GateEvidence(
                    gate=r["gate"], verdict=r["verdict"],
                    attempt_id=r.get("attempt_id", ""),
                    report_key=r.get("report_key"),
                    report_sha256=r.get("report_sha256"),
                    consumed=r.get("consumed", {}),
                    produced=r.get("produced", {}),
                    tool_identity=r.get("tool_identity", ""),
                    parser_contract=r.get("parser_contract", ""),
                )
            probs = lineage_problems(records)
            g.check("certification lineage is coherent", not probs,
                    "; ".join(probs[:2]))
        if sg_path.is_file():
            g.check("signoff is clean",
                    json.loads(sg_path.read_text()).get("clean") is True, "")

    # 9. attribution
    if live:
        g.check("a real non-scripted model call was recorded",
                (result.get("non_scripted_model_calls") or 0) >= 1, "")
        g.check("autonomy evidence is complete",
                result.get("autonomy_evidence") is True,
                ", ".join(result.get("attribution_missing", [])))
    else:
        g.check("scripted mode does not claim autonomy",
                result.get("autonomy_evidence") is not True, "")
    return g


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("case")
    ap.add_argument("run_dir")
    args = ap.parse_args()

    import yaml

    case = yaml.safe_load(Path(args.case).read_text())
    run_dir = Path(args.run_dir)
    result = json.loads((run_dir / "result.json").read_text())
    g = grade(case, result, run_dir, case_path=Path(args.case))
    print(g.report())
    (run_dir / "grade.json").write_text(json.dumps(g.to_dict(), indent=2))
    return 0 if g.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
