"""Deterministic repair verification and design-certification domains."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping

from ..stages import StageId
from .models import ActionType, RepairAction


class VerificationScope(str, Enum):
    FUNCTIONAL = "functional"
    LOGICAL = "logical"
    CONSTRAINT = "constraint"
    PHYSICAL = "physical"
    PHYSICAL_SIGNOFF = "physical_signoff"
    TOOL_RUNTIME = "tool_runtime"
    FULL = "full"


class CertificationLevel(str, Enum):
    FAILED = "failed"
    PARTIALLY_VERIFIED = "partially_verified"
    PHYSICAL_SIGNOFF_VERIFIED = "physical_signoff_verified"
    FUNCTIONALLY_VERIFIED = "functionally_verified"
    FULLY_CERTIFIED = "fully_certified"


LOGICAL_GATES = (StageId.LEC_SYNTH, StageId.LEC_ROUTE)
PHYSICAL_GATES = (
    StageId.FLOORPLAN, StageId.PDN, StageId.PLACEMENT, StageId.CTS,
    StageId.STA_POSTCTS, StageId.ROUTING, StageId.EXTRACTION,
    StageId.STA_SIGNOFF, StageId.GDSOUT, StageId.DRC, StageId.LVS,
    StageId.ANTENNA, StageId.LEC_ROUTE,
)
PHYSICAL_REPAIR_GATES = (StageId.LEC_SYNTH, *PHYSICAL_GATES)
EVIDENCE_REQUIRED = {
    StageId.SIM, StageId.LEC_SYNTH, StageId.PDN, StageId.STA_POSTCTS,
    StageId.EXTRACTION, StageId.STA_SIGNOFF, StageId.GDSOUT, StageId.DRC,
    StageId.LVS, StageId.ANTENNA, StageId.LEC_ROUTE,
}
SURFACE_GATES: dict[str, tuple[StageId, ...]] = {
    "rtl": (StageId.LINT, StageId.SIM, StageId.SYNTHESIS, StageId.LEC_SYNTH,
            StageId.STA_PRE, *PHYSICAL_GATES),
    "sdc": (StageId.SDC, StageId.SYNTHESIS, StageId.LEC_SYNTH,
            StageId.STA_PRE, *PHYSICAL_GATES),
    "synthesis": (StageId.SYNTHESIS, StageId.LEC_SYNTH, StageId.STA_PRE,
                  *PHYSICAL_GATES),
    # Physical changes retain the earlier synthesis-equivalence boundary as
    # provenance, then rerun from the first artifact the change can affect.
    "floorplan": PHYSICAL_REPAIR_GATES,
    "pdn": (StageId.LEC_SYNTH, *PHYSICAL_GATES[1:]),
    "placement": (StageId.LEC_SYNTH, *PHYSICAL_GATES[2:]),
    "cts": (StageId.LEC_SYNTH, *PHYSICAL_GATES[3:]),
    "routing": (StageId.LEC_SYNTH, *PHYSICAL_GATES[5:]),
    "extraction": (StageId.LEC_SYNTH, *PHYSICAL_GATES[6:]),
    "gdsout": (StageId.GDSOUT, StageId.DRC, StageId.LVS),
    "tool_runtime": (StageId.GDSOUT, StageId.DRC, StageId.LVS),
}


@dataclass(frozen=True)
class VerificationRequirement:
    scope: VerificationScope
    modified_surfaces: tuple[str, ...]
    required_gates: tuple[StageId, ...]
    rtl_modified: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "verification_scope": self.scope.value,
            "modified_surfaces": list(self.modified_surfaces),
            "required_gates": [g.value for g in self.required_gates],
            "rtl_modified": self.rtl_modified,
        }


@dataclass(frozen=True)
class RepairVerification:
    repair_verified: bool
    requirement: VerificationRequirement
    passed_gates: tuple[StageId, ...] = ()
    unavailable_gates: tuple[StageId, ...] = ()
    failed_gates: tuple[StageId, ...] = ()
    functional_spec_verified: bool = False
    physical_signoff_verified: bool = False
    logical_identity_verified: bool = False
    verification_basis: tuple[str, ...] = ()
    promotion_reason: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "repair_verified": self.repair_verified,
            **self.requirement.to_dict(),
            "passed_gates": [g.value for g in self.passed_gates],
            "unavailable_gates": [g.value for g in self.unavailable_gates],
            "failed_gates": [g.value for g in self.failed_gates],
            "functional_spec_verified": self.functional_spec_verified,
            "physical_signoff_verified": self.physical_signoff_verified,
            "logical_identity_verified": self.logical_identity_verified,
            "verification_basis": list(self.verification_basis),
            "promotion_reason": list(self.promotion_reason),
        }


@dataclass(frozen=True)
class CertificationSummary:
    level: CertificationLevel
    functional_spec_verified: bool
    logical_identity_verified: bool
    physical_signoff_verified: bool
    full_certification: bool
    functional_reason: str
    logical_reason: str
    physical_reason: str
    overall_reason: str
    repair_verifications: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "certification_level": self.level.value,
            "functional_spec_verified": self.functional_spec_verified,
            "logical_identity_verified": self.logical_identity_verified,
            "physical_signoff_verified": self.physical_signoff_verified,
            "full_certification": self.full_certification,
            "functional_reason": self.functional_reason,
            "logical_reason": self.logical_reason,
            "physical_reason": self.physical_reason,
            "overall_reason": self.overall_reason,
            "repair_verifications": list(self.repair_verifications),
        }


def action_surface(action: RepairAction | Mapping[str, Any]) -> str:
    kind = action.action_type.value if isinstance(action, RepairAction) else str(action.get("action_type", ""))
    target = action.target if isinstance(action, RepairAction) else str(action.get("target", ""))
    if kind == ActionType.PATCH_WORKING_RTL.value:
        return "rtl"
    if kind == ActionType.SELECT_TOOL_BACKEND.value:
        return "tool_runtime"
    if kind == ActionType.SET_IR_VALUE.value:
        return target.split(".", 1)[0]
    return "unknown"


def derive_verification_requirement(
    actions: Iterable[RepairAction | Mapping[str, Any]],
) -> VerificationRequirement:
    surfaces = tuple(dict.fromkeys(action_surface(a) for a in actions))
    gates: list[StageId] = []
    for surface in surfaces:
        for gate in SURFACE_GATES.get(surface, tuple(StageId)):
            if gate not in gates:
                gates.append(gate)
    rtl_modified = "rtl" in surfaces
    if rtl_modified:
        scope = VerificationScope.FULL
    elif "tool_runtime" in surfaces and len(surfaces) == 1:
        scope = VerificationScope.TOOL_RUNTIME
    elif "sdc" in surfaces:
        scope = VerificationScope.CONSTRAINT
    elif any(s in surfaces for s in SURFACE_GATES if s not in {"rtl", "sdc", "synthesis", "tool_runtime"}):
        scope = VerificationScope.PHYSICAL_SIGNOFF
    else:
        scope = VerificationScope.LOGICAL
    return VerificationRequirement(scope, surfaces, tuple(gates), rtl_modified)


def evaluate_repair(
    record: Mapping[str, Any], *, stage_results: Mapping[StageId, str],
    evidence_gates: set[StageId], integrity_problems: Iterable[str] = (),
    authoritative_simulation: bool = False,
) -> RepairVerification:
    actions = record.get("actions") or record.get("repair_actions") or []
    requirement = derive_verification_requirement(actions)
    passed: list[StageId] = []
    unavailable: list[StageId] = []
    failed: list[StageId] = []
    for gate in requirement.required_gates:
        result = stage_results.get(gate, "unavailable")
        has_evidence = gate not in EVIDENCE_REQUIRED or gate in evidence_gates
        if result == "pass" and has_evidence:
            passed.append(gate)
        elif result in {"skipped", "unavailable", "pending"}:
            unavailable.append(gate)
        else:
            failed.append(gate)
    logical = all(stage_results.get(g) == "pass" and g in evidence_gates for g in LOGICAL_GATES)
    physical = all(stage_results.get(g) == "pass" for g in PHYSICAL_GATES)
    physical &= all(g in evidence_gates for g in PHYSICAL_GATES if g in EVIDENCE_REQUIRED)
    integrity = tuple(integrity_problems)
    physical &= not integrity
    rtl_identity_ok = (
        requirement.rtl_modified
        or record.get("rtl_identity_preserved", True) is True
    )
    runtime_ok = True
    if "tool_runtime" in requirement.modified_surfaces:
        probes = record.get("health_probes") or []
        selected = str((record.get("new_values") or {}).get("tool.klayout.backend", ""))
        runtime_ok = any(p.get("healthy") and p.get("backend") == selected for p in probes)
    verified = (
        record.get("result") == "resolved" and not failed and not unavailable
        and not integrity and runtime_ok and rtl_identity_ok
        and (authoritative_simulation if requirement.rtl_modified else True)
    )
    basis = [f"{g.value}: deterministic PASS" for g in passed]
    if "tool_runtime" in requirement.modified_surfaces and runtime_ok:
        basis.append("selected backend health probe: PASS")
    reasons: list[str] = []
    if verified:
        reasons.append(f"all {len(requirement.required_gates)} action-derived gates passed")
        if not requirement.rtl_modified:
            reasons.append("RTL unchanged; specification simulation is outside this repair scope")
    else:
        if failed:
            reasons.append("failed gates: " + ", ".join(g.value for g in failed))
        if unavailable:
            reasons.append("unavailable gates: " + ", ".join(g.value for g in unavailable))
        reasons.extend(integrity)
        if requirement.rtl_modified and not authoritative_simulation:
            reasons.append("RTL repair lacks authoritative simulation evidence")
        if not runtime_ok:
            reasons.append("selected runtime backend has no passing health probe")
        if not rtl_identity_ok:
            reasons.append("working RTL identity changed outside this repair scope")
    return RepairVerification(
        verified, requirement, tuple(passed), tuple(unavailable), tuple(failed),
        authoritative_simulation, physical, logical, tuple(basis), tuple(reasons),
    )


def evaluate_certification(
    *, stage_results: Mapping[StageId, str], authoritative_simulation: bool,
    integrity_problems: Iterable[str] = (),
    repair_verifications: Iterable[Mapping[str, Any]] = (),
) -> CertificationSummary:
    integrity = tuple(integrity_problems)
    logical = all(stage_results.get(g) == "pass" for g in LOGICAL_GATES) and not integrity
    physical = all(stage_results.get(g) == "pass" for g in PHYSICAL_GATES) and not integrity
    full = authoritative_simulation and logical and physical
    if full:
        level = CertificationLevel.FULLY_CERTIFIED
    elif physical and logical:
        level = CertificationLevel.PHYSICAL_SIGNOFF_VERIFIED
    elif authoritative_simulation:
        level = CertificationLevel.FUNCTIONALLY_VERIFIED
    elif logical or physical:
        level = CertificationLevel.PARTIALLY_VERIFIED
    else:
        level = CertificationLevel.FAILED
    return CertificationSummary(
        level, authoritative_simulation, logical, physical, full,
        "authoritative simulation evidence passed" if authoritative_simulation else "authoritative simulation evidence unavailable",
        "synthesis and post-route equivalence passed" if logical else "required logical equivalence evidence is incomplete",
        "timing, GDS integrity, DRC, LVS and antenna gates passed" if physical else "one or more physical signoff or provenance gates did not pass",
        "all certification domains passed" if full else "full certification is incomplete",
        tuple(dict(x) for x in repair_verifications),
    )
