"""Artifact ledger with content identity.

Every file a stage produces is registered here under a stable key together with
its sha256, size and mtime. Downstream stages ask for artifacts *by key*, so
they physically cannot pick up a stale or intermediate file that happens to
share a name.

This exists because of a specific real failure in the SKY130/OpenLane flow:
signoff DRC reported clean while actually checking pre-merge macro GDS instead
of the final streamed-out layout, hiding thousands of violations. The KLayout
report itself cannot save you here -- its ``<original-file/>`` field is written
empty, so the report does not record which GDS it read. The only place that
knowledge can live is the orchestrator, which is why it lives here.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .errors import Rtl2GdsError

_CHUNK = 1 << 20  # 1 MiB


def tree_sha256(root: str | os.PathLike[str]) -> tuple[str, int]:
    """Deterministic content identity of a directory tree.

    Hashes each file's path relative to the root plus its bytes, in sorted
    order, so the result depends on what the tree contains and nothing else --
    not timestamps, not ownership, not the absolute location.
    """
    base = Path(root)
    h = hashlib.sha256()
    total = 0
    for f in sorted(p for p in base.rglob("*") if p.is_file()):
        rel = f.relative_to(base).as_posix()
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        data = f.read_bytes()
        h.update(hashlib.sha256(data).digest())
        total += len(data)
    return h.hexdigest(), total


def sha256_file(path: str | os.PathLike[str]) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(_CHUNK):
            h.update(chunk)
    return h.hexdigest()


class ArtifactError(Rtl2GdsError):
    """An artifact is missing, changed underfoot, or was never registered."""


@dataclass(frozen=True)
class Artifact:
    """A produced file, pinned to its content at registration time."""

    key: str
    path: Path
    stage: str
    sha256: str
    size: int
    mtime: float
    #: Free-form facts the producing stage wants downstream stages to know,
    #: e.g. the top cell name written into a GDS.
    meta: dict[str, Any] | None = None

    @classmethod
    def capture(
        cls,
        key: str,
        path: str | os.PathLike[str],
        stage: str,
        *,
        meta: dict[str, Any] | None = None,
        allow_dir: bool = False,
    ) -> "Artifact":
        p = Path(path)
        if not p.exists():
            raise ArtifactError(f"cannot register artifact {key!r}: {p} does not exist")
        if p.is_dir():
            if not allow_dir:
                raise ArtifactError(f"artifact {key!r} is a directory: {p}")
            st = p.stat()
            # A directory artifact gets a real content identity too.
            #
            # It used to get sha256="", which meant the RTL tree -- the design
            # itself -- was bound to a signoff by *path*. Two different designs
            # at the same path were indistinguishable, and a source edit
            # mid-run was invisible. The tree hash covers relative paths and
            # file contents; mtimes and ownership are deliberately excluded so
            # that a copy of the same sources hashes the same.
            digest, total = tree_sha256(p)
            return cls(key, p, stage, sha256=digest, size=total,
                       mtime=st.st_mtime, meta=meta)
        st = p.stat()
        if st.st_size == 0:
            raise ArtifactError(f"artifact {key!r} is empty: {p}")
        return cls(
            key=key,
            path=p,
            stage=stage,
            sha256=sha256_file(p),
            size=st.st_size,
            mtime=st.st_mtime,
            meta=meta,
        )

    @property
    def is_dir(self) -> bool:
        return self.sha256 == "" and self.path.is_dir()

    def unchanged(self) -> bool:
        """True if the file on disk still matches what we registered."""
        if self.is_dir:
            return self.path.is_dir()
        if not self.path.is_file():
            return False
        if self.path.stat().st_size != self.size:
            return False
        return sha256_file(self.path) == self.sha256

    def assert_unchanged(self) -> None:
        if not self.unchanged():
            raise ArtifactError(
                f"artifact {self.key!r} changed on disk since {self.stage} produced it: "
                f"{self.path} (expected sha256 {self.sha256[:12]}..., size {self.size})"
            )

    def short(self) -> str:
        return f"{self.key}={self.path.name}@{self.sha256[:12]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "path": str(self.path),
            "stage": self.stage,
            "sha256": self.sha256,
            "size": self.size,
            "mtime": self.mtime,
            "meta": self.meta or {},
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Artifact":
        return cls(
            key=d["key"],
            path=Path(d["path"]),
            stage=d["stage"],
            sha256=d.get("sha256", ""),
            size=int(d.get("size", 0)),
            mtime=float(d.get("mtime", 0.0)),
            meta=d.get("meta") or None,
        )


class ArtifactLedger:
    """Keyed store of artifacts, survives across stages and across resume."""

    def __init__(self) -> None:
        self._items: dict[str, Artifact] = {}

    def __contains__(self, key: object) -> bool:
        return key in self._items

    def __len__(self) -> int:
        return len(self._items)

    def keys(self) -> Iterable[str]:
        return self._items.keys()

    def register(
        self,
        key: str,
        path: str | os.PathLike[str],
        stage: str,
        *,
        meta: dict[str, Any] | None = None,
        allow_dir: bool = False,
    ) -> Artifact:
        art = Artifact.capture(key, path, stage, meta=meta, allow_dir=allow_dir)
        self._items[key] = art
        return art

    def put(self, art: Artifact) -> Artifact:
        self._items[art.key] = art
        return art

    def get(self, key: str) -> Artifact:
        try:
            return self._items[key]
        except KeyError:
            known = ", ".join(sorted(self._items)) or "<none>"
            raise ArtifactError(
                f"required artifact {key!r} was never produced; available: {known}"
            ) from None

    def require(self, keys: Iterable[str], *, verify: bool = True) -> dict[str, Artifact]:
        """Fetch several artifacts, optionally re-verifying their content.

        ``verify`` re-hashes, which is what catches a downstream stage reading a
        file that some other step quietly rewrote.
        """
        out: dict[str, Artifact] = {}
        for k in keys:
            art = self.get(k)
            if verify:
                art.assert_unchanged()
            out[k] = art
        return out

    def assert_produced_after(self, report: str | os.PathLike[str], source: Artifact) -> None:
        """Assert ``report`` was written after ``source`` existed.

        Cheap ordering check that catches the classic stale-report case: a
        report file left over from a previous run being parsed as if it
        described the GDS we just streamed out.
        """
        rp = Path(report)
        if not rp.is_file():
            raise ArtifactError(f"report does not exist: {rp}")
        if rp.stat().st_mtime + 1e-6 < source.mtime:
            raise ArtifactError(
                f"report {rp.name} is older than the {source.key} it claims to describe "
                f"({rp.stat().st_mtime:.3f} < {source.mtime:.3f}); it is stale, "
                "not a result for this run"
            )

    def to_dict(self) -> dict[str, Any]:
        return {k: a.to_dict() for k, a in sorted(self._items.items())}

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> "ArtifactLedger":
        led = cls()
        for key, raw in (d or {}).items():
            led._items[key] = Artifact.from_dict(raw)
        return led
