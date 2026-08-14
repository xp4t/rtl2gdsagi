"""Checkpoint store and rollback manager.

Review 10. Two properties matter and both are load-bearing:

1. **Downstream invalidation.** Rolling back to stage R invalidates every
   checkpoint from R onward, not just R's. Anything causally after a changed
   stage is stale by construction even if its own config did not change.
2. **Config fingerprinting.** Every attempt is fingerprinted by the IR that
   produced it plus the hashes of its real inputs. The store refuses to
   re-execute a configuration that has already failed, which is what stops
   "iterate until it works" from becoming "iterate forever".
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .artifacts import Artifact, ArtifactLedger
from .errors import Rtl2GdsError
from .ir import IR
from .stages import STAGE_ORDER, StageId, downstream_of, stage_index


class CheckpointError(Rtl2GdsError):
    pass


class DuplicateAttempt(Rtl2GdsError):
    """This exact configuration was already tried and failed."""

    def __init__(self, stage: StageId, fingerprint: str, previous_error: str) -> None:
        super().__init__(
            f"{stage} has already been attempted with configuration "
            f"{fingerprint[:12]} and it failed ({previous_error}); refusing to "
            "repeat an identical attempt"
        )
        self.stage = stage
        self.fingerprint = fingerprint


@dataclass
class Checkpoint:
    """A durable, restorable point in the flow."""

    stage: StageId
    #: Fingerprint of the IR sections that produced it.
    config_fingerprint: str
    #: sha256 of every input artifact, so we can tell if inputs really changed.
    input_hashes: dict[str, str]
    artifacts: dict[str, Artifact]
    metrics: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    #: Directory holding the copied artifacts and the rendered scripts.
    store_dir: Path | None = None
    valid: bool = True

    @property
    def index(self) -> int:
        return stage_index(self.stage)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage.value,
            "config_fingerprint": self.config_fingerprint,
            "input_hashes": self.input_hashes,
            "artifacts": {k: a.to_dict() for k, a in self.artifacts.items()},
            "metrics": self.metrics,
            "created_at": self.created_at,
            "store_dir": str(self.store_dir) if self.store_dir else None,
            "valid": self.valid,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Checkpoint":
        return cls(
            stage=StageId(d["stage"]),
            config_fingerprint=d["config_fingerprint"],
            input_hashes=dict(d.get("input_hashes") or {}),
            artifacts={
                k: Artifact.from_dict(v) for k, v in (d.get("artifacts") or {}).items()
            },
            metrics=dict(d.get("metrics") or {}),
            created_at=float(d.get("created_at") or 0.0),
            store_dir=Path(d["store_dir"]) if d.get("store_dir") else None,
            valid=bool(d.get("valid", True)),
        )


def fingerprint_attempt(
    ir: IR,
    section: str | None,
    inputs: dict[str, str],
    *,
    script: str = "",
    causal_env: dict[str, str] | None = None,
) -> str:
    """Identity of one attempt: everything that decides what it will actually do.

    Including input hashes is what lets the store distinguish "same knobs, but
    upstream actually changed" from "genuinely the same attempt".

    ``script`` is the *rendered* tool script, and it is the strongest component
    here: it is literally what will be executed. The stage's own IR section is
    not sufficient alone, because renderers legitimately read other sections --
    routing reads ``cts.fix_hold``, placement reads its padding -- so two
    attempts could differ materially while their section config stayed
    byte-identical. Hashing the script captures every cross-section input
    without having to enumerate them.

    ``causal_env`` carries identity that lives outside the IR entirely: which
    PDK, which standard-cell library and corner, which design. A different PDK
    is a different experiment even with identical knobs.

    Deliberately excluded: timestamps, run ids, paths, and anything else that
    varies between runs without changing what the tool does. The question this
    answers is "have we already run this exact effective experiment?", and a
    clock tick is not part of the experiment.
    """
    payload = {
        "section": section,
        "config": ir.section(section) if section else {},
        "inputs": dict(sorted(inputs.items())),
        "script_sha256": (
            hashlib.sha256(script.encode("utf-8")).hexdigest() if script else ""
        ),
        "causal_env": dict(sorted((causal_env or {}).items())),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class CheckpointStore:
    """Linear DAG of checkpoints with downstream invalidation."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._cps: dict[StageId, Checkpoint] = {}
        #: fingerprint -> failure summary, for attempts already known bad.
        self._failed: dict[str, str] = {}

    # ---- recording -------------------------------------------------------

    def save(
        self,
        stage: StageId,
        *,
        ir: IR,
        section: str | None,
        ledger: ArtifactLedger,
        produces: Iterable[str],
        inputs: dict[str, Artifact] | None = None,
        metrics: dict[str, Any] | None = None,
        copy_artifacts: bool = True,
    ) -> Checkpoint:
        """Record a checkpoint after ``stage`` passed."""
        inputs = inputs or {}
        input_hashes = {k: a.sha256 for k, a in inputs.items()}
        arts: dict[str, Artifact] = {}
        store_dir = self.root / f"{stage_index(stage):02d}_{stage.value}"

        if copy_artifacts:
            store_dir.mkdir(parents=True, exist_ok=True)
        for key in produces:
            if key not in ledger:
                continue
            art = ledger.get(key)
            if copy_artifacts and not art.is_dir and art.path.is_file():
                dest = store_dir / art.path.name
                if dest.resolve() != art.path.resolve():
                    shutil.copy2(art.path, dest)
            arts[key] = art

        cp = Checkpoint(
            stage=stage,
            config_fingerprint=fingerprint_attempt(ir, section, input_hashes),
            input_hashes=input_hashes,
            artifacts=arts,
            metrics=dict(metrics or {}),
            store_dir=store_dir if copy_artifacts else None,
        )
        self._cps[stage] = cp
        return cp

    def record_failure(self, fingerprint: str, summary: str) -> None:
        self._failed[fingerprint] = summary

    # ---- duplicate suppression ------------------------------------------

    def assert_not_tried(self, stage: StageId, fingerprint: str) -> None:
        if fingerprint in self._failed:
            raise DuplicateAttempt(stage, fingerprint, self._failed[fingerprint])

    def already_failed(self, fingerprint: str) -> bool:
        return fingerprint in self._failed

    # ---- querying --------------------------------------------------------

    def get(self, stage: StageId) -> Checkpoint | None:
        cp = self._cps.get(stage)
        return cp if cp is not None and cp.valid else None

    def valid_stages(self) -> list[StageId]:
        return [s for s in STAGE_ORDER if (c := self._cps.get(s)) and c.valid]

    def last_valid_before(self, stage: StageId) -> Checkpoint | None:
        """The most recent still-valid checkpoint strictly before ``stage``."""
        i = stage_index(stage)
        for s in reversed(STAGE_ORDER[:i]):
            cp = self._cps.get(s)
            if cp is not None and cp.valid:
                return cp
        return None

    def is_fresh(self, stage: StageId, *, ir: IR, section: str | None,
                 inputs: dict[str, Artifact]) -> bool:
        """True if ``stage``'s checkpoint still matches its config and inputs.

        Lets the orchestrator skip re-running a stage after a rollback when its
        true inputs did not actually change (review 10).
        """
        cp = self.get(stage)
        if cp is None:
            return False
        want = fingerprint_attempt(ir, section, {k: a.sha256 for k, a in inputs.items()})
        return cp.config_fingerprint == want

    # ---- rollback --------------------------------------------------------

    def invalidate_from(self, stage: StageId) -> list[StageId]:
        """Invalidate ``stage`` and everything downstream. Returns what changed."""
        killed: list[StageId] = []
        for sid in downstream_of(stage, inclusive=True):
            cp = self._cps.get(sid)
            if cp is not None and cp.valid:
                cp.valid = False
                killed.append(sid)
        return killed

    def rollback_to(self, stage: StageId) -> tuple[Checkpoint | None, list[StageId]]:
        """Prepare to re-run from ``stage``.

        Returns the checkpoint to restore from (the last valid one *before*
        ``stage``) and the list of invalidated stages.
        """
        restore_from = self.last_valid_before(stage)
        killed = self.invalidate_from(stage)
        return restore_from, killed

    def restore_artifacts(self, ledger: ArtifactLedger, upto: StageId) -> list[str]:
        """Re-register artifacts from every valid checkpoint before ``upto``."""
        restored: list[str] = []
        i = stage_index(upto)
        for sid in STAGE_ORDER[:i]:
            cp = self._cps.get(sid)
            if cp is None or not cp.valid:
                continue
            for key, art in cp.artifacts.items():
                ledger.put(art)
                restored.append(key)
        return restored

    # ---- persistence -----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoints": {s.value: c.to_dict() for s, c in self._cps.items()},
            "failed_fingerprints": dict(self._failed),
        }

    def load_dict(self, d: dict[str, Any] | None) -> None:
        for name, raw in ((d or {}).get("checkpoints") or {}).items():
            try:
                sid = StageId(name)
            except ValueError:
                continue
            self._cps[sid] = Checkpoint.from_dict(raw)
        self._failed.update((d or {}).get("failed_fingerprints") or {})
