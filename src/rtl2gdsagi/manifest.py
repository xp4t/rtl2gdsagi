"""The release candidate: one identity every signoff gate must agree on.

Signoff used to be status aggregation. Each gate recorded that it passed, and
two of them (DRC and LVS) happened to also record which GDS they had read.
Nothing tied the rest together, so "the design passed" meant "these stages
each passed at some point", not "these checks all describe the same thing".

A release candidate is the exact set of artifacts a certification refers to:

    candidate_id = sha256(top, every bound artifact hash, PDK identity,
                          tool versions, config, IR)

Two properties matter more than the contents of the list:

* it is derived, not asserted -- change any bound artifact and the id changes;
* it is **re-verified** at signoff by re-hashing every file on disk, so a
  manifest that no longer matches reality is caught rather than believed.

What this does *not* do is make the flow manufacturing-qualified. It binds the
evidence this methodology produces; it does not add corners, OCV, or any of the
other things a production signoff needs.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .artifacts import ArtifactLedger, sha256_file, tree_sha256

#: Artifacts that define what was verified. Anything absent is recorded as
#: absent rather than skipped silently -- a candidate with no SPEF is a
#: different (weaker) candidate than one with a SPEF, and the id must say so.
BOUND_ARTIFACTS: tuple[str, ...] = (
    # The design and its physical realisation.
    "rtl_dir",
    "final_gds",
    "routed_netlist",
    "netlist",
    "spef",
    "sdc",
    "routed_def",
    "cts_def",
    "pdn_def",
    "floorplan_def",
    "design_facts",
    # P0-R2: simulation PASS must be impossible to reuse once the testbench
    # changes. The tree hash covers every bench the simulator actually ran.
    "testbench_dir",
    # The LVS reference and the extraction it was compared against, so "which
    # schematic was this layout checked with" is part of the candidate.
    "lvs_reference",
    "extracted_netlist",
    "gds_summary",
    # The verification outputs themselves. A candidate that binds the layout
    # but not the reports can have its evidence rewritten underneath it.
    "drc_report",
    "lvs_report",
    "antenna_report",
    "sim_result",
)

#: How to ask each tool its version. Cheap, and only run once per manifest.
_VERSION_PROBES: dict[str, list[str]] = {
    "verilator": ["verilator", "--version"],
    "iverilog": ["iverilog", "-V"],
    "yosys": ["yosys", "-V"],
    "eqy": ["eqy", "--version"],
    "klayout": ["klayout", "-v"],
}


def probe_tool_versions() -> dict[str, str]:
    """First line of each tool's version output, or 'absent'.

    Recorded because the same inputs through a different tool version are not
    the same experiment, and a signoff that cannot say which binary produced it
    cannot be reproduced.
    """
    out: dict[str, str] = {}
    for name, argv in _VERSION_PROBES.items():
        if shutil.which(argv[0]) is None:
            out[name] = "absent"
            continue
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=20)
            text = (r.stdout + r.stderr).strip()
            out[name] = text.splitlines()[0][:120] if text else "unknown"
        except Exception:
            out[name] = "unknown"
    return out


@dataclass(frozen=True)
class ReleaseCandidateManifest:
    top: str
    candidate_id: str
    artifacts: dict[str, dict[str, Any]]
    pdk: dict[str, Any]
    tools: dict[str, str]
    config_sha256: str
    ir_sha256: str
    created_at: float = field(default_factory=time.time)

    # ---- construction ----------------------------------------------------

    @classmethod
    def build(
        cls,
        *,
        top: str,
        ledger: ArtifactLedger,
        pdk: dict[str, Any],
        config: dict[str, Any],
        ir_fingerprint: str,
        tools: dict[str, str] | None = None,
        keys: tuple[str, ...] = BOUND_ARTIFACTS,
    ) -> "ReleaseCandidateManifest":
        arts: dict[str, dict[str, Any]] = {}
        for key in keys:
            if key in ledger:
                a = ledger.get(key)
                arts[key] = {
                    "sha256": a.sha256,
                    "path": str(a.path),
                    "stage": a.stage,
                    "size": a.size,
                }
            else:
                arts[key] = {"sha256": None, "absent": True}

        config_sha = hashlib.sha256(
            json.dumps(config, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        tools = tools if tools is not None else probe_tool_versions()

        identity = {
            "top": top,
            "artifacts": {k: v.get("sha256") for k, v in sorted(arts.items())},
            "pdk": {
                k: str(v) for k, v in sorted(pdk.items())
                if k in ("name", "root", "std_cell_lib", "corner")
            },
            "tools": dict(sorted(tools.items())),
            "config_sha256": config_sha,
            "ir_sha256": ir_fingerprint,
        }
        candidate_id = hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        return cls(
            top=top,
            candidate_id=candidate_id,
            artifacts=arts,
            pdk=dict(pdk),
            tools=tools,
            config_sha256=config_sha,
            ir_sha256=ir_fingerprint,
        )

    # ---- verification ----------------------------------------------------

    def verify(self, ledger: ArtifactLedger) -> list[str]:
        """Re-check the candidate against reality. Returns problems, if any.

        Every bound artifact is re-hashed **from disk**, so this catches a file
        that changed after it was registered as well as one the ledger no
        longer agrees with. A manifest that is merely written out and never
        re-read proves nothing.
        """
        problems: list[str] = []
        for key, rec in sorted(self.artifacts.items()):
            if rec.get("absent"):
                continue
            path = Path(rec["path"])
            if not path.exists():
                problems.append(
                    f"{key} is bound to the release candidate but {path} no "
                    "longer exists"
                )
                continue
            try:
                on_disk = (tree_sha256(path)[0] if path.is_dir()
                           else sha256_file(path))
            except OSError as exc:
                problems.append(f"{key} could not be re-hashed: {exc}")
                continue
            if on_disk != rec["sha256"]:
                problems.append(
                    f"{key} changed after it was bound: manifest has "
                    f"{rec['sha256'][:12]}, the file on disk is {on_disk[:12]}"
                )
            if key in ledger and ledger.get(key).sha256 != rec["sha256"]:
                problems.append(
                    f"{key} in the ledger ({ledger.get(key).sha256[:12]}) is not "
                    f"the one bound to the candidate ({rec['sha256'][:12]})"
                )
        return problems

    def binds(self, key: str) -> bool:
        """True when the candidate actually carries a hash for ``key``."""
        return bool(self.artifacts.get(key, {}).get("sha256"))

    def required_present(self, required: tuple[str, ...]) -> list[str]:
        """Problems for any required artifact the candidate does not bind."""
        return [
            f"the release candidate has no {key}; it cannot be certified "
            "without one"
            for key in required
            if not self.binds(key)
        ]

    def gate_binding_problems(self, history: list[dict[str, Any]]) -> list[str]:
        """Gates that verified something other than this candidate's GDS."""
        gds = self.artifacts.get("final_gds", {}).get("sha256")
        if not gds:
            return []
        out: list[str] = []
        for h in history:
            sha = (h.get("metrics") or {}).get("checked_gds_sha256")
            if sha and sha != gds:
                out.append(
                    f"{h.get('stage')} verified GDS {sha[:12]} but the release "
                    f"candidate's GDS is {gds[:12]}"
                )
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "top": self.top,
            "created_at": self.created_at,
            "artifacts": self.artifacts,
            "pdk": {k: str(v) for k, v in self.pdk.items()},
            "tools": self.tools,
            "config_sha256": self.config_sha256,
            "ir_sha256": self.ir_sha256,
        }

    def short(self) -> str:
        return self.candidate_id[:12]
