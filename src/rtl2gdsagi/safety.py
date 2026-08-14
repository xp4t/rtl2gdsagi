"""Safety boundaries, enforced structurally.

Review 14.2 lists things the agent must never do. Stating them in a prompt is
not enforcement, so they are enforced here instead:

* **Immutable paths.** The PDK tree, the DRC/LVS decks and the user's original
  RTL directory are read-only. Any attempt to write inside them raises.
  RTL repair happens on the run's private copy, never the source.
* **Forbidden remediation targets.** Each taxonomy row lists what must not be
  touched in response to that failure class; a diagnosis proposing such a change
  is rejected before anything is applied.
* **Iteration budget.** The budget object has no method to increase itself, so
  "self-extending the attempt cap" is not an expressible action.
* **Verdict authority.** Enforced in :mod:`rtl2gdsagi.checks.verdict` -- the
  agent has no code path that produces a Verdict.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .errors import Rtl2GdsError
from .stages import StageId
from .taxonomy import (
    CHECK_DECKS,
    EXTRACTED_NETLIST,
    PDK_FILES,
    RTL_LOGIC,
    SDC_TARGETS,
    TEMPLATES,
    Diagnosis,
    FailureClass,
    forbidden_targets,
)


class SafetyViolation(Rtl2GdsError):
    """A proposed action crosses an architectural boundary. Never auto-resolved."""


class BudgetExhausted(Rtl2GdsError):
    """The global iteration budget ran out. Stops the run; cannot be extended."""


@dataclass(frozen=True)
class ImmutableZones:
    """Paths that must never be written during a run."""

    pdk_root: Path
    rtl_source: Path
    extra: tuple[Path, ...] = ()

    def all_zones(self) -> tuple[Path, ...]:
        return (self.pdk_root.resolve(), self.rtl_source.resolve(), *(
            p.resolve() for p in self.extra
        ))

    def check_write(self, target: str | os.PathLike[str]) -> None:
        """Raise if ``target`` lies inside an immutable zone."""
        t = Path(target).resolve()
        for zone in self.all_zones():
            if t == zone or zone in t.parents:
                raise SafetyViolation(
                    f"refusing to write {t}: it is inside the immutable zone {zone}. "
                    "PDK files, signoff decks and the user's original RTL are ground "
                    "truth; a mismatch involving them is a human-escalation case, "
                    "never an auto-fix target."
                )

    def is_immutable(self, target: str | os.PathLike[str]) -> bool:
        try:
            self.check_write(target)
        except SafetyViolation:
            return True
        return False


@dataclass
class IterationBudget:
    """Global attempt budget. Deliberately has no way to grant itself more.

    ``spend`` is the only mutator and it only ever decreases the remaining
    count, so review 14.2's "self-extending the iteration budget" is not an
    action the system can perform.
    """

    total: int
    _spent: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if self.total < 1:
            raise ValueError("iteration budget must be at least 1")

    @property
    def spent(self) -> int:
        return self._spent

    @property
    def remaining(self) -> int:
        return max(0, self.total - self._spent)

    @property
    def exhausted(self) -> bool:
        return self.remaining == 0

    def spend(self, n: int = 1, *, what: str = "attempt") -> int:
        if n < 1:
            raise ValueError("must spend at least one unit")
        if self.remaining < n:
            raise BudgetExhausted(
                f"global iteration budget exhausted ({self.total} attempts used) "
                f"while trying to spend {n} on {what}; stopping rather than looping"
            )
        self._spent += n
        return self.remaining

    def to_dict(self) -> dict[str, int]:
        return {"total": self.total, "spent": self._spent, "remaining": self.remaining}


#: Maps a forbidden-target token to a human explanation used in the error.
_EXPLAIN = {
    RTL_LOGIC: (
        "modifying RTL functional logic in response to a timing, DRC or physical "
        "problem. There is no real ASIC flow where fixing hold means touching RTL"
    ),
    SDC_TARGETS: (
        "relaxing an SDC constraint target purely to make a check pass, with no "
        "physical justification"
    ),
    PDK_FILES: "editing PDK, standard-cell, LEF or Liberty files",
    CHECK_DECKS: "editing or weakening a DRC/LVS/antenna deck",
    EXTRACTED_NETLIST: "editing the extracted netlist to make LVS agree",
    TEMPLATES: "rewriting a renderer template (that is a system bug, not a design iteration)",
}

#: IR sections whose modification would amount to a forbidden action.
_SECTION_GUARD: dict[str, str] = {
    "drc": CHECK_DECKS,
    "lvs": CHECK_DECKS,
    "antenna": CHECK_DECKS,
    # Timing is the target, not the result. A setup or hold failure answered by
    # lengthening the clock period does not fix the design, it moves the goal --
    # and since the sdc fields are model-writable, that was a working way to
    # turn failing timing into a pass. The token existed and the SDC class
    # already named it; the section was simply never mapped here, so for a
    # setup or hold failure the guard never fired.
    "sdc": SDC_TARGETS,
}


def review_diagnosis(
    diag: Diagnosis,
    *,
    allowed_stage: StageId | None = None,
    policy_failure: FailureClass | None = None,
) -> None:
    """Reject a proposed remediation that crosses a boundary.

    Called before any config delta is applied. Raises SafetyViolation rather
    than silently dropping the offending part, because a partially-applied
    remediation is harder to reason about than a refused one.

    ``policy_failure`` is the *deterministic* classification of the failure.
    What a class forbids must be decided from that rather than from
    ``diag.failure``, which the model chooses: otherwise relabelling a hold
    violation as, say, a congestion problem hands back exactly the IR sections
    the hold policy exists to protect.
    """
    forbidden = set(forbidden_targets(policy_failure or diag.failure))

    for section in diag.config_delta:
        token = _SECTION_GUARD.get(section)
        if token and token in forbidden:
            raise SafetyViolation(
                f"diagnosis for {diag.failure} proposes changing IR section "
                f"{section!r}, which would amount to {_EXPLAIN[token]}"
            )

    if allowed_stage is not None and diag.implicated_stage not in (None, allowed_stage):
        raise SafetyViolation(
            f"diagnosis implicates {diag.implicated_stage} but remediation was "
            f"authorised only for {allowed_stage}"
        )

    if not 0.0 <= diag.confidence <= 1.0:
        raise SafetyViolation(f"confidence {diag.confidence} is outside [0, 1]")


def explain(token: str) -> str:
    return _EXPLAIN.get(token, token)


# ---------------------------------------------------------------------------
# Per-failure authorization: which knobs may answer which failure
# ---------------------------------------------------------------------------
#
# Freezing verification intent (ir.agent_writable=False) stops the model
# redefining success. This stops something different and just as important: a
# schema-valid change that has nothing to do with the failure being fixed.
#
# A routing failure answered by "raise the synthesis effort" is not a fix, it
# is a shot in the dark that invalidates every downstream artifact. Worse, a
# multi-section delta lets an unrelated change ride along with a plausible one.
# So each failure class authorises an explicit set of IR sections, and anything
# outside it is refused before it is applied.
AUTHORIZED_SECTIONS: dict[FailureClass, frozenset[str]] = {
    # Physical implementation failures: the knobs that shape the layout.
    #
    # These sets say what can *cause* the failure, not what we suspect. A route
    # that will not close is caused by its own settings, by a placement that
    # spread badly, or by a floorplan with no room in it -- and the taxonomy's
    # own escalation chain walks exactly that path (routing -> placement ->
    # floorplan). Authorising the chain is what lets genuine cross-stage
    # remediation happen. What is still refused is the thing that matters: any
    # section that defines what success *means*.
    FailureClass.CONGESTION: frozenset({"placement", "floorplan", "routing"}),
    FailureClass.ROUTING: frozenset({"routing", "placement", "floorplan"}),
    FailureClass.PLACEMENT: frozenset({"placement", "floorplan"}),
    FailureClass.FLOORPLAN: frozenset({"floorplan"}),
    FailureClass.CTS: frozenset({"cts"}),
    FailureClass.PDN: frozenset({"pdn", "floorplan"}),
    FailureClass.ANTENNA: frozenset({"routing"}),
    FailureClass.DRC: frozenset({"routing", "placement", "gdsout"}),
    # Timing. Note what is absent: sdc and sta are frozen verification intent,
    # so hold is answered by the clock tree and setup by placement/synthesis --
    # never by moving the target.
    FailureClass.HOLD: frozenset({"cts", "placement", "routing"}),
    FailureClass.SETUP: frozenset({"placement", "synthesis", "cts", "routing"}),
    # Synthesis-side.
    FailureClass.SYNTH_ERROR: frozenset({"synthesis"}),
    FailureClass.ELABORATION: frozenset({"synthesis"}),
    FailureClass.SYNTH_QOR: frozenset({"synthesis"}),
    FailureClass.TIMING_PRELAYOUT: frozenset({"synthesis", "floorplan", "placement"}),
    FailureClass.EXTRACTION: frozenset({"routing"}),
    FailureClass.GDS: frozenset({"gdsout"}),
    # Everything else authorises nothing: an equivalence mismatch, an LVS
    # mismatch or a library problem is not a knob-tuning situation, and the
    # taxonomy already escalates them.
}


def authorized_sections(failure: FailureClass | str | None) -> frozenset[str]:
    if failure is None:
        return frozenset()
    key = failure if isinstance(failure, FailureClass) else FailureClass(failure)
    return AUTHORIZED_SECTIONS.get(key, frozenset())


def review_delta_scope(
    delta: dict[str, dict[str, object]],
    policy_failure: FailureClass | None,
) -> None:
    """Refuse a proposal touching sections this failure does not authorise."""
    if not delta:
        return
    allowed = authorized_sections(policy_failure)
    unauthorised = sorted(set(delta) - allowed)
    if not unauthorised:
        return
    if not allowed:
        raise SafetyViolation(
            f"{policy_failure} authorises no configuration change at all "
            f"(it is escalated or resolved elsewhere), but the diagnosis "
            f"proposes changing {', '.join(unauthorised)}"
        )
    raise SafetyViolation(
        f"diagnosis for {policy_failure} proposes changing "
        f"{', '.join(unauthorised)}, which that failure does not authorise. "
        f"Authorised for {policy_failure}: {', '.join(sorted(allowed))}. A "
        "change unrelated to the failure is not a remediation, and riding one "
        "along with a plausible change is how verification intent leaks."
    )


#: IR section -> the earliest stage whose output that section can change.
#:
#: Used to force the rollback to follow the delta. Changing floorplan
#: utilisation while re-running only routing leaves every intermediate artifact
#: describing a floorplan that no longer exists, and the candidate then binds
#: evidence that was never regenerated.
SECTION_EARLIEST_STAGE: dict[str, StageId] = {
    "lint": StageId.LINT,
    "sim": StageId.SIM,
    "sdc": StageId.SDC,
    "synthesis": StageId.SYNTHESIS,
    "lec": StageId.LEC_SYNTH,
    "sta": StageId.STA_PRE,
    "floorplan": StageId.FLOORPLAN,
    "pdn": StageId.PDN,
    "placement": StageId.PLACEMENT,
    "cts": StageId.CTS,
    "routing": StageId.ROUTING,
    "extraction": StageId.EXTRACTION,
    "gdsout": StageId.GDSOUT,
    "drc": StageId.DRC,
    "lvs": StageId.LVS,
    "antenna": StageId.ANTENNA,
}


def earliest_affected_stage(delta: dict[str, dict[str, object]]) -> StageId | None:
    """Earliest stage any changed section can influence, or None if empty."""
    from .stages import stage_index

    stages = [
        SECTION_EARLIEST_STAGE[sec] for sec in delta
        if sec in SECTION_EARLIEST_STAGE
    ]
    return min(stages, key=stage_index) if stages else None


def authorized_action_space(
    failure: FailureClass | str | None,
) -> dict[str, dict[str, object]]:
    """The exact write surface a given failure class permits.

    **This is the single source of truth for both the prompt and the
    validator.** `review_delta_scope` refuses any section outside
    `authorized_sections(failure)`, and the IR schema refuses any field that is
    not `agent_writable`; composing the two here means the model is shown
    precisely the fields its proposal can survive, and the two cannot drift
    because there is only one definition.

    P1-AUTH-01: the prompt used to inject `describe_section(failing_stage)` --
    the failing stage's whole schema, locked fields included, and nothing from
    the other authorized sections. A signoff hold failure therefore advertised
    frozen STA fields while withholding the CTS and placement knobs it was
    actually allowed to use.
    """
    from .ir import writable_fields

    out: dict[str, dict[str, object]] = {}
    for section in sorted(authorized_sections(failure)):
        fields = writable_fields(section)
        if fields:
            out[section] = fields
    return out


def authorized_current_values(ir, failure: FailureClass | str | None
                              ) -> dict[str, dict[str, object]]:
    """Current IR values, restricted to the fields the model may write.

    N1: the prompt used to carry `ir.section(failing_stage)` verbatim, so it
    showed frozen and no-op fields -- `routing.global_effort` among them -- that
    the validator will always reject. Fail-closed is not the same as
    well-instrumented: a model that spends the one allowed diagnosis proposing
    a field it was shown but may not write has been misled by us.

    Derived from `authorized_action_space`, the same structure the validator
    enforces, so there is no second permission list to drift. A field that
    becomes `agent_writable=False` disappears from both at once, with no change
    to prompt code.
    """
    out: dict[str, dict[str, object]] = {}
    for section, fields in authorized_action_space(failure).items():
        try:
            current = ir.section(section)
        except Exception:
            continue
        values = {name: current[name] for name in fields if name in current}
        if values:
            out[section] = values
    return out
