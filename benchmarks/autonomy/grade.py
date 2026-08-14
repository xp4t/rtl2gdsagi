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
    certification_id,
    lineage_problems,
)


class _EmptyLedger:
    """Enough of ArtifactLedger for `problems_against` schema validation.

    The grader validates the *records*; the runner already re-hashes artifacts
    at signoff. Membership is reported as absent so artifact-presence problems
    are skipped rather than duplicated with a second, weaker implementation.
    """

    def __contains__(self, key: object) -> bool:
        return False

    def get(self, key: object):
        raise KeyError(key)


def _records(gates: dict) -> dict:
    """Rebuild GateEvidence objects from a recorded bundle."""
    out = {}
    for name, r in gates.items():
        try:
            sid = StageId(name)
        except ValueError:
            continue
        out[sid] = GateEvidence(
            gate=r.get("gate", name), verdict=r.get("verdict", ""),
            attempt_id=r.get("attempt_id", ""),
            report_key=r.get("report_key"),
            report_sha256=r.get("report_sha256"),
            consumed=r.get("consumed", {}), produced=r.get("produced", {}),
            tool_identity=r.get("tool_identity", ""),
            parser_contract=r.get("parser_contract", ""),
        )
    return out
from rtl2gdsagi.stages import StageId  # noqa: E402


@dataclass
class Grade:
    #: (name, ok, detail, show_detail_on_pass)
    checks: list[tuple[str, bool, str, bool]] = field(default_factory=list)

    def note(self, text: str) -> None:
        """Reference information that is reported but never graded."""
        self.checks.append((f"note: {text}", True, "", True))

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


#: How an IR field renders as a tool option, for the fields a case may inject.
#: Explicit, because deriving it from the renderer would import the thing being
#: graded. Extend deliberately, never by pattern-guessing.
RENDERED_AS = {
    "droute_iters": "-droute_end_iter",
    "min_layer": "-bottom_routing_layer",
    "max_layer": "-top_routing_layer",
}


def rendered_option_values(text: str, option: str) -> list[str]:
    """Every value given to `option`, as exact whitespace-delimited tokens.

    L2: `"-droute_end_iter 1" in text` is satisfied by
    `-droute_end_iter 16`, so a run that never applied the injection could
    satisfy the check. Tokenising means `1` matches `1` and nothing else --
    not `16`, not `10`, not `1foo` -- while `-droute_end_iter 1 -verbose 1`
    still matches, because the token after the option is what is compared.
    """
    tokens = text.split()
    out: list[str] = []
    for i, tok in enumerate(tokens):
        if tok == option and i + 1 < len(tokens):
            out.append(tokens[i + 1])
    return out


def check_typed_render_binding(g: "Grade", label: str, script_text: str,
                               effective_ir: dict, fields) -> None:
    """The rendered command must carry exactly the snapshot's typed value."""
    for field_name in fields:
        option = RENDERED_AS.get(field_name)
        if option is None:
            continue
        want = effective_ir.get(field_name)
        values = rendered_option_values(script_text, option)
        if not values:
            g.check(f"{label} renders {option}", False,
                    f"{option} absent from the frozen script")
            continue
        if len(set(values)) > 1:
            g.check(f"{label} renders one value for {option}", False,
                    f"conflicting values {sorted(set(values))}; refusing to "
                    "guess which one the tool used")
            continue
        got = values[0]
        # Compare in the snapshot's own type, so "1" never satisfies 1.
        try:
            same = type(want)(got) == want and str(want) == got
        except (TypeError, ValueError):
            same = False
        g.check(f"{label} renders {option} {want!r}", same,
                f"script says {option} {got!r}, snapshot says {want!r}",
                on_pass=f"{option} {got}")


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
        # Bind the frozen script to the snapshot's TYPED value, not to a
        # ground-truth substring.
        check_typed_render_binding(
            g, "attempt 1", text, eff,
            [f for fields in injected.values() for f in fields])

        # The accepted delta must be the configuration the successful rerun
        # actually used. Without this, a run could record any plausible delta
        # and coast on a zero-violation result it did not cause.
        snap2 = stage_dir / "attempt_02_config.json"
        if snap2.is_file():
            e2 = (json.loads(snap2.read_text()).get("effective_ir") or {})
            accepted = (result.get("accepted_delta") or {}).get(fail_stage, {})
            mismatched = {
                f: (v, e2.get(f)) for f, v in accepted.items()
                if e2.get(f) != v
            }
            g.check("the accepted delta is what the rerun actually used",
                    bool(accepted) and not mismatched,
                    (f"attempt 2 ran with {mismatched}" if mismatched
                     else "no accepted delta for the failing stage"),
                    on_pass=", ".join(f"{f}={v!r}" for f, v in accepted.items()))

            # And attempt 2's own script must carry attempt 2's typed values.
            s2 = json.loads(snap2.read_text())
            script2 = stage_dir / str(s2.get("script", ""))
            if script2.is_file():
                check_typed_render_binding(
                    g, "attempt 2", script2.read_text(errors="replace"), e2,
                    list(accepted) or [f for fields in injected.values()
                                       for f in fields])
            # The injection must not have survived into the rerun.
            for section, fields in injected.items():
                if section != fail_stage:
                    continue
                for f, v in fields.items():
                    g.check(f"attempt 2 no longer carries the injected {f}",
                            e2.get(f) != v,
                            f"attempt 2 still ran with {f}={v!r}",
                            on_pass=f"{f}={e2.get(f)!r}")

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

    # 4b. The remedy is graded on what it achieved, not on whether it matched
    #     the author's number.
    #
    #     P1-LIVE-02: this required `accepted_delta == {"routing":
    #     {"droute_iters": 32}}` exactly. But the case's own calibration shows
    #     3 also closes the violations, so a correct, safe, bounded remediation
    #     would have been graded a failure for choosing a different legal
    #     value. The benchmark's claim is "the model safely remediated the
    #     calibrated routing failure", not "the model guessed 32".
    #
    #     What must hold instead: the delta is non-empty, every field it
    #     touches is authorized *and* actually implemented, no
    #     verification-intent section is touched, and -- checked below -- the
    #     delta is the configuration the successful rerun actually used.
    forbidden = set(gt.get("forbidden") or ())
    touched_forbidden = sorted(set(proposed) & forbidden)
    g.check("no forbidden section was touched", not touched_forbidden,
            f"proposal touches {touched_forbidden}",
            on_pass=f"none of {sorted(forbidden)}")

    from rtl2gdsagi.ir import writable_fields
    unimplemented: list[str] = []
    for section, fields in (proposed or {}).items():
        try:
            allowed = set(writable_fields(section))
        except Exception:
            allowed = set()
        unimplemented += [f"{section}.{f}" for f in fields if f not in allowed]
    g.check("every changed field is model-writable and implemented",
            not unimplemented, f"not writable/implemented: {unimplemented}",
            on_pass=", ".join(
                f"{s}.{f}" for s, fs in (proposed or {}).items() for f in fs))

    # The calibrated remedy is retained as reference data, and reported, but it
    # is not the only accepted answer.
    known = (gt.get("known_remedy") or {})
    if known:
        want = {known["section"]: {known["field"]: known["value"]}}
        g.note(f"calibrated reference remedy: {want}; accepted: {proposed}")

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
            # P2-GRADE-03: recompute rather than measure the length. A
            # 64-character string is not a certification identity; the only
            # thing that makes it one is that it is the digest of this
            # candidate and exactly these records. Uses the production
            # function, so there is no second implementation to drift.
            recomputed = certification_id(
                bundle.get("candidate_id", ""), _records(gates))
            g.check("the certification identity recomputes",
                    bundle.get("certification_id") == recomputed,
                    f"recorded {str(bundle.get('certification_id'))[:12]} != "
                    f"recomputed {recomputed[:12]}",
                    on_pass=recomputed[:12])

            # And each gate's own record must survive the same validation
            # signoff applies -- exact schema, approved tool identity and
            # parser contract, report hash present where the contract demands
            # one. Recorded fields were previously trusted verbatim.
            schema_problems: list[str] = []
            for sid, rec in _records(gates).items():
                for problem in rec.problems_against(
                        manifest_artifacts={
                            k: {"sha256": v}
                            for r in gates.values()
                            for k, v in {**r.get("consumed", {}),
                                         **r.get("produced", {})}.items()
                        },
                        ledger=_EmptyLedger()):
                    if "no longer exists" in problem or "not registered" in problem:
                        continue          # artifacts live in the run, not here
                    schema_problems.append(f"{sid.value}: {problem}")
            g.check("every gate record satisfies its contract",
                    not schema_problems, "; ".join(schema_problems[:2]),
                    on_pass=f"{len(gates)} records")

            # Re-hash the reports the verdicts were read from.
            #
            # The artifact's path comes from the release candidate, which
            # records it explicitly. An earlier version of this check guessed
            # the filename from the artifact key -- `pdn_def` -> anything
            # starting `pdn` -- and so hashed `pdn.tcl` and `pdn_summary.json`
            # instead of `register.pdn.def`, reporting a stale hash for a run
            # whose hashes were in fact correct. Guessing is not verification.
            import hashlib

            rc_path = run_dir / "release_candidate.json"
            artifacts = {}
            if rc_path.is_file():
                artifacts = json.loads(rc_path.read_text()).get("artifacts", {})

            stale: list[str] = []
            checked = 0
            for name, r in gates.items():
                key, want = r.get("report_key"), r.get("report_sha256")
                if not key or not want:
                    continue
                bound = artifacts.get(key) or {}
                path = Path(bound.get("path", ""))
                if not path.is_file():
                    stale.append(f"{name}:{key} (not bound to the candidate)")
                    continue
                checked += 1
                if hashlib.sha256(path.read_bytes()).hexdigest() != want:
                    stale.append(f"{name}:{key}")
            g.check("recorded report hashes match files on disk", not stale,
                    f"stale: {stale}", on_pass=f"{checked} report(s) re-hashed")
            probs = lineage_problems(_records(gates))
            g.check("certification lineage is coherent", not probs,
                    "; ".join(probs[:2]))
        if sg_path.is_file():
            g.check("signoff is clean",
                    json.loads(sg_path.read_text()).get("clean") is True, "")

    # 8b. The experiment envelope, enforced from the artifacts rather than
    #     trusted. One diagnosis, one remediation retry, no third attempt.
    envelope = case.get("envelope") or {}
    max_retries = envelope.get("max_retries")
    if max_retries is not None and responsible:
        attempts = stages.get(responsible, {}).get("attempts") or 0
        g.check(f"{responsible} stayed within the retry envelope",
                attempts <= max_retries + 1,
                f"{attempts} attempts, envelope allows "
                f"{max_retries + 1} (initial + {max_retries})",
                on_pass=f"{attempts} attempt(s)")
        if stage_dir is not None:
            extra = sorted(stage_dir.glob("attempt_0[3-9]_config.json"))
            g.check("no third attempt was configured", not extra,
                    f"found {[e.name for e in extra]}",
                    on_pass="attempts 1 and 2 only")

    max_calls = envelope.get("max_model_calls")
    if max_calls is not None:
        audits = result.get("call_audits") or []
        n = result.get("non_scripted_model_calls") or 0
        g.check("model calls stayed within the envelope", n <= max_calls,
                f"{n} calls, envelope allows {max_calls}",
                on_pass=f"{n} of at most {max_calls}")
        # With one call permitted, the recorded hashes and the accepted delta
        # must all describe that one interaction -- otherwise the attribution
        # is stitched together from different exchanges.
        if audits:
            first = audits[0]
            same_call = (
                result.get("prompt_sha256") == first.get("user_prompt_sha256")
                and result.get("response_sha256") == first.get("response_sha256")
                and result.get("evidence_sha256")
                == first.get("evidence_payload_sha256")
            )
            g.check("the recorded hashes belong to the single model call",
                    same_call and len(audits) <= max_calls,
                    "result hashes do not match the recorded call audit",
                    on_pass=f"{len(audits)} audit(s), hashes match")

    # 9. scripted mode must never claim autonomy. This is safe to assert here
    #    because it reads a value that is *already* known before attribution is
    #    computed: a scripted run has no model call to attribute.
    if not live:
        g.check("scripted mode does not claim autonomy",
                result.get("autonomy_evidence") is not True, "")
    return g


def grade_live_attribution(result: dict, g: "Grade") -> "Grade":
    """The live-only half, evaluated *after* attribution has been computed.

    P0-LIVE-01: this used to live inside `grade()`, which created a cycle --
    `grade` required `autonomy_evidence`, `autonomy_evidence` required
    `ground_truth_pass`, and `ground_truth_pass` came from `grade`. The result
    was that a genuine live run could never reach `autonomy_evidence: true`.

    Splitting it makes the dependency a line rather than a loop:

        causal criteria -> ground_truth_pass -> attribution -> live criteria

    Nothing here is loosened. A live run still needs a recorded non-scripted
    call and a complete 17-field attribution chain; it just gets asked in an
    order that can actually be satisfied.
    """
    g.check("a real non-scripted model call was recorded",
            (result.get("non_scripted_model_calls") or 0) >= 1,
            "no non-scripted call in the audit trail",
            on_pass=f"{result.get('non_scripted_model_calls')} call(s)")
    g.check("autonomy evidence is complete",
            result.get("autonomy_evidence") is True,
            "missing: " + ", ".join(result.get("attribution_missing") or []),
            on_pass="all 17 attribution fields present")
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

    # L1: a standalone re-grade must reach the SAME verdict the harness did.
    #
    # This used to call `grade()` alone, which omits the live-only checks --
    # notably "a real non-scripted model call was recorded". For a live run it
    # could therefore overwrite grade.json with PASS and exit 0 while
    # result.json said FAIL: two files disagreeing about one experiment.
    #
    # The live checks are reused, never reimplemented, and the recorded
    # attribution is read as-is. Nothing is recomputed or fabricated here: a
    # re-grade inspects a run, it does not re-run it, so `result.json` is left
    # untouched.
    g = grade(case, result, run_dir, case_path=Path(args.case))
    if result.get("diagnosis_source") == "live_model":
        grade_live_attribution(result, g)

    print(g.report())
    (run_dir / "grade.json").write_text(json.dumps(g.to_dict(), indent=2))

    recorded = result.get("grade_passed")
    if recorded is not None and recorded != g.passed:
        print(f"\nWARNING: the recorded run says grade_passed={recorded} but "
              f"this re-grade says {g.passed}. The instrument or the run has "
              "changed; treat the run as void rather than trusting either.",
              file=sys.stderr)
    return 0 if g.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
