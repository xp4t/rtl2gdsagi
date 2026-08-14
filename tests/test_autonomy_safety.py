"""Adversarial remediation proposals, driven from the benchmark ground truth.

This executes `benchmarks/autonomy/case_90_safety_forbidden_proposals.yaml`
against the real schema and the real safety validator. Every listed proposal is
one a model could plausibly make when it is trying to close a design, and each
must be refused *structurally* -- either impossible to express in the schema, or
rejected by deterministic code before anything runs.

None of this depends on the model choosing to behave. That distinction is the
whole point: prompt compliance is not a safety mechanism.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from rtl2gdsagi.ir import IR, SchemaViolation
from rtl2gdsagi.safety import SafetyViolation, review_diagnosis
from rtl2gdsagi.stages import StageId, stage_index
from rtl2gdsagi.taxonomy import Diagnosis, FailureClass, responsible_stage

CASE = (Path(__file__).parent.parent / "benchmarks" / "autonomy"
        / "case_90_safety_forbidden_proposals.yaml")


def load_proposals():
    case = yaml.safe_load(CASE.read_text())
    return case["proposals"]


def ids(proposals):
    return [p["name"] for p in proposals]


PROPOSALS = load_proposals()


@pytest.mark.parametrize("prop", PROPOSALS, ids=ids(PROPOSALS))
def test_every_forbidden_proposal_is_refused(prop):
    """Each case's `must` says *how* it has to be refused."""
    must = prop["must"]

    if must == "reject_schema":
        # Not expressible: the schema itself has to say no.
        with pytest.raises(SchemaViolation):
            IR().apply_delta(prop["delta"], agent=True)
        return

    if must == "refuse_target":
        # Expressible, but the causal policy must not follow it forward.
        failing = StageId(prop["failing_stage"])
        proposed = StageId(prop["implicated_stage"])
        assert stage_index(proposed) > stage_index(failing), "case must aim forward"
        policy = responsible_stage(
            FailureClass(prop["failure_class"]), failing_stage=failing)
        # The runner accepts a proposal only at or before the failing stage.
        accepted = (proposed if stage_index(proposed) <= stage_index(failing)
                    else policy)
        assert accepted is not proposed
        assert stage_index(accepted) <= stage_index(failing)
        return

    assert must == "reject", f"unknown expectation {must!r}"
    diag = Diagnosis(
        failure=FailureClass(prop["failure_class"]),
        evidence="benchmark",
        implicated_stage=None,
        confidence=0.9,
        config_delta=prop["delta"],
    )
    with pytest.raises(SafetyViolation):
        review_diagnosis(diag, policy_failure=FailureClass(prop["failure_class"]))


def test_the_benchmark_case_is_not_silently_empty():
    """A safety suite that stopped loading its cases would pass vacuously."""
    assert len(PROPOSALS) >= 6
    musts = {p["must"] for p in PROPOSALS}
    assert {"reject", "reject_schema", "refuse_target"} <= musts


#: The one field whose name looks like a waiver and is allowed to exist.
#:
#: `lint.waived_rules` suppresses *Verilator warning codes* (-Wno-WIDTH). It
#: cannot waive a signoff check, and it cannot waive a structural error either:
#: check_lint fails on any %Error regardless of what is listed, and -Wno- only
#: governs warnings. It is bounded to an identifier so it cannot smuggle
#: additional arguments onto the command line.
#:
#: Any *new* entry to this set is a decision to widen the model's ability to
#: turn a check off, and should be argued for on its own merits.
ALLOWED_WAIVER_FIELDS = {("lint", "waived_rules")}


def test_no_ir_field_can_disable_a_signoff_check():
    """The structural claim: 'skip this rule' is unrepresentable.

    Not "rejected" -- there is no field to put it in. This walks the whole
    schema rather than trusting the sections we happen to remember, so a field
    added later cannot quietly become a way to switch a check off.
    """
    from rtl2gdsagi.ir import SCHEMA

    banned = ("waive", "skip", "disable", "ignore", "suppress", "bypass",
              "force_pass", "override")
    for section, fields in SCHEMA.items():
        for f in fields:
            if (section, f.name) in ALLOWED_WAIVER_FIELDS:
                continue
            name = f.name.lower()
            assert not any(b in name for b in banned), (
                f"{section}.{f.name} looks like a way to switch a check off")


def test_the_one_permitted_waiver_cannot_reach_a_hard_gate():
    """lint.waived_rules is bounded, and cannot suppress an error."""
    from rtl2gdsagi.checks.tools import ToolRun, check_lint
    from rtl2gdsagi.checks.verdict import VerdictKind

    # Bounded: no flags, no separators, no substitutions.
    for payload in ("WIDTH -Wno-lint", "--flag", "a;b", "$(id)"):
        with pytest.raises(SchemaViolation):
            IR().update("lint", {"waived_rules": [payload]})

    # And a real Verilator error fails the stage no matter what is waived.
    err = ToolRun(argv=[], returncode=1, stdout="",
                  stderr="%Error-WIDTH: widget.v:3: bad width\n")
    assert check_lint(err).kind is VerdictKind.FAIL


def test_no_signoff_section_exposes_anything_but_performance_knobs():
    """drc/lvs/antenna must stay incapable of changing what is checked."""
    from rtl2gdsagi.ir import SCHEMA

    allowed = {"threads", "deep_mode"}
    for section in ("drc", "lvs", "antenna"):
        names = {f.name for f in SCHEMA[section]}
        assert names <= allowed, (
            f"{section} exposes {names - allowed}, which is more than a "
            "performance knob")


def test_rtl_is_not_reachable_from_any_ir_section():
    """No schema field points at the design's logic."""
    from rtl2gdsagi.ir import SCHEMA

    for section, fields in SCHEMA.items():
        for f in fields:
            assert "rtl" not in f.name.lower() or section == "sim", (
                f"{section}.{f.name} may expose RTL to remediation")


# ---- P1-06/P1-07: harness attribution and path safety ----------------------

def test_benchmark_refuses_a_run_dir_outside_its_results_root(tmp_path):
    """The harness deletes this path recursively.

    It previously accepted any --run-dir with no containment check, so one
    typo could remove the repository, the source RTL, or a writable PDK tree.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "benchmarks" / "autonomy"))
    import run_case

    for bad in ("/", str(Path.home()), str(tmp_path),
                str(Path(__file__).parent.parent), "/tmp"):
        with pytest.raises(SystemExit) as exc:
            run_case._safe_run_dir(bad, "case")
        assert "refusing" in str(exc.value)

    # The results root itself is refused; a case directory under it is fine.
    with pytest.raises(SystemExit):
        run_case._safe_run_dir(str(run_case.RUNS_ROOT), "case")
    ok = run_case._safe_run_dir(None, "case_probe")
    assert run_case.RUNS_ROOT in ok.parents
    ok.rmdir()


def test_benchmark_requires_an_explicit_diagnosis_source():
    """Attribution must be declared, never inferred from a credential.

    A run with no failures and a key in the environment would otherwise be
    labelled `live` while no model was ever consulted.
    """
    import subprocess
    import sys

    repo = Path(__file__).parent.parent
    r = subprocess.run(
        [sys.executable, str(repo / "benchmarks" / "autonomy" / "run_case.py"),
         str(repo / "benchmarks" / "autonomy" / "case_03_routing_layer_range.yaml")],
        capture_output=True, text=True, timeout=60,
    )
    assert r.returncode != 0
    assert "--diagnosis-source" in (r.stderr + r.stdout)
