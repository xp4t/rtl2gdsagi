"""Scope-safe matching for verified repair-memory records."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .verification import VerificationScope, derive_verification_requirement

PHYSICAL_SURFACES = {
    "floorplan", "pdn", "placement", "cts", "routing", "extraction",
    "gdsout", "tool_runtime",
}


def memory_is_compatible(
    record: Mapping[str, Any], *, failure_code: str | None,
    proposed_actions: Iterable[Mapping[str, Any]],
) -> tuple[bool, str]:
    """Rank a strategy without authorizing or replaying its old values."""
    if not record.get("repair_verified"):
        return False, "memory record was not deterministically verified"
    if failure_code and record.get("known_error_id") != failure_code:
        return False, "failure code differs"
    requirement = derive_verification_requirement(proposed_actions)
    try:
        stored = VerificationScope(str(record.get("verification_scope")))
    except ValueError:
        return False, "memory record has an unknown verification scope"
    requested = set(requirement.modified_surfaces)
    if stored in {
        VerificationScope.PHYSICAL, VerificationScope.PHYSICAL_SIGNOFF,
        VerificationScope.TOOL_RUNTIME,
    } and not requested <= PHYSICAL_SURFACES:
        return False, "physical repair memory cannot support logical or RTL changes"
    stored_surfaces = set(record.get("modified_surfaces") or [])
    if stored_surfaces and not requested <= stored_surfaces:
        return False, "requested surfaces exceed the verified memory scope"
    return True, "compatible strategy; current-design validation remains mandatory"


def rank_compatible(
    records: Iterable[Mapping[str, Any]], *, failure_code: str,
    proposed_actions: Iterable[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    actions = list(proposed_actions)
    accepted = [
        record for record in records
        if memory_is_compatible(
            record, failure_code=failure_code, proposed_actions=actions,
        )[0]
    ]
    return sorted(accepted, key=lambda r: (
        str(r.get("pdk", "")), str(r.get("verification_scope", "")),
        str(r.get("failure_fingerprint", "")),
    ))
