"""Verdicts. Written by deterministic code, never by the agent.

Review 14.1 makes this an architectural constraint rather than a prompt-level
instruction: the orchestrator reads exit codes and parses reports, and it alone
constructs a Verdict. The agent is handed already-computed metrics and may write
only a Diagnosis (:class:`rtl2gdsagi.taxonomy.Diagnosis`). There is no code path
by which a model response becomes a Verdict, so "Claude says PASS" can never be
mistaken for "the EDA tool says PASS".

The three-way outcome also fixes review 4.6: a tool crash and a
quality-below-target result are different situations needing different
remediation, so they are different verdict kinds rather than one boolean.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..stages import Gate, StageId, get_stage
from ..taxonomy import FailureClass


class VerdictKind(str, Enum):
    #: Hard constraints met.
    PASS = "pass"
    #: Ran correctly, but a soft objective is below target. Never blocks;
    #: feeds the optimizer.
    QOR_BELOW_TARGET = "qor_below_target"
    #: A hard constraint failed, or the tool errored.
    FAIL = "fail"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Verdict:
    stage: StageId
    kind: VerdictKind
    summary: str
    #: Structured metrics for the state store and the optimizer.
    metrics: dict[str, Any] = field(default_factory=dict)
    #: Set only when kind is FAIL.
    failure: FailureClass | None = None
    #: Compact, token-cheap evidence handed to the agent for diagnosis.
    evidence: str = ""
    #: True when this must go to a human rather than be retried.
    escalate: bool = False

    def __post_init__(self) -> None:
        if self.kind is VerdictKind.FAIL and self.failure is None:
            raise ValueError(
                f"a FAIL verdict for {self.stage} must name a FailureClass so the "
                "taxonomy can resolve a responsible stage"
            )
        if self.kind is not VerdictKind.FAIL and self.failure is not None:
            raise ValueError("only a FAIL verdict may carry a FailureClass")

    @property
    def ok(self) -> bool:
        """Does the flow proceed?

        An advisory stage proceeds even on FAIL -- that is what advisory means.
        Pre-layout STA reporting negative slack is information, not a stop
        (review 4.9).
        """
        if self.kind is not VerdictKind.FAIL:
            return True
        return get_stage(self.stage).gate is Gate.ADVISORY

    @property
    def blocks(self) -> bool:
        return not self.ok

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage.value,
            "kind": self.kind.value,
            "summary": self.summary,
            "metrics": self.metrics,
            "failure_class": self.failure.value if self.failure else None,
            "escalate": self.escalate,
        }


def passed(stage: StageId, summary: str, **metrics: Any) -> Verdict:
    return Verdict(stage=stage, kind=VerdictKind.PASS, summary=summary, metrics=metrics)


def qor_low(stage: StageId, summary: str, *, evidence: str = "", **metrics: Any) -> Verdict:
    return Verdict(
        stage=stage,
        kind=VerdictKind.QOR_BELOW_TARGET,
        summary=summary,
        metrics=metrics,
        evidence=evidence,
    )


def failed(
    stage: StageId,
    failure: FailureClass,
    summary: str,
    *,
    evidence: str = "",
    escalate: bool = False,
    **metrics: Any,
) -> Verdict:
    return Verdict(
        stage=stage,
        kind=VerdictKind.FAIL,
        summary=summary,
        metrics=metrics,
        failure=failure,
        evidence=evidence,
        escalate=escalate,
    )
