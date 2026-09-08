"""Gate evidence: what a PASS is allowed to rest on.

Signoff used to read ``StageState``. A stage that reached ``OK`` counted as a
gate that passed, which conflates two different questions:

    did this stage finish?          <- orchestration
    is this design verified?        <- certification

Those come apart constantly. A stage is OK after a retry whose report belongs
to the previous attempt; after an upstream artifact was regenerated; after the
report it graded was overwritten. In every one of those the state says OK and
nothing about the design has been established.

So a hard gate now produces a :class:`GateEvidence` record naming, explicitly:

* which artifacts it consumed, by content hash;
* which report produced its verdict, by content hash;
* which tool and parser contract produced it;
* which attempt it belongs to.

At signoff each record is re-checked against the release candidate: the report
must still hash the same, and every consumed artifact must be the candidate's.
Evidence that describes different bytes than the candidate binds is evidence
about a different design.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .artifacts import ArtifactLedger, sha256_file
from .stages import StageId

#: Hard gates that must produce evidence, and the artifacts each must consume.
#:
#: These are the inputs whose identity decides whether the verdict still means
#: anything. A DRC result is about one GDS; change the GDS and the result is
#: about nothing. Only keys the stage genuinely reads are listed -- requiring a
#: key a stage never consumes would be theatre.
@dataclass(frozen=True)
class GateContract:
    """The exact, immutable proof a gate must produce to certify.

    P0-R2: `problems_against()` used to validate only whatever happened to be
    present. Ten PASS records with empty consumed maps were accepted, and a
    record could name no report, no tool and no parser contract and still
    certify. A contract makes the required shape explicit and absence fatal.
    """

    gate: StageId
    #: Artifact keys the stage genuinely reads. Every one must be bound to the
    #: candidate at the hash the gate recorded.
    consumed: tuple[str, ...]
    #: Artifact keys the stage genuinely writes. These are the lineage edges:
    #: a downstream gate consuming one of these must see the same hash.
    produced: tuple[str, ...] = ()
    #: The artifact the verdict was read from. `None` means the verdict comes
    #: from the tool log, which is captured in the attempt log rather than a
    #: registered artifact.
    report_key: str | None = None
    #: Exact parser contract id required; a different parser is a different
    #: claim about the same bytes.
    parser_contract: str = ""
    #: Approved tool identity prefixes for this controlled environment.
    tool_identities: tuple[str, ...] = ()


#: Tool identity prefixes accepted for authoritative gates in this pinned
#: environment. Deliberately narrow: solving general cross-version support is
#: not in scope, and an unknown build must fail closed rather than certify.
APPROVED_TOOL_IDENTITIES: tuple[str, ...] = (
    "container:ghcr.io/the-openroad-project/openlane:",
    "KLayout ",
    "EQY ",
    "Icarus Verilog",
    "Yosys ",
)


#: What each certifying gate must prove.
#:
#: The `consumed` lists were audited against what the generated scripts
#: actually read, not against StageSpec declarations. Corrections made for
#: P0-R2: STA signoff reads the routed DEF (not the routed netlist), LVS binds
#: its generated reference and extracted netlist, simulation binds the
#: testbenches that earned the PASS, route LEC binds its RTL gold side, PDN
#: binds the floorplan it was generated from, and GDSOUT exists at all.
GATE_CONTRACTS: dict[StageId, GateContract] = {
    StageId.SIM: GateContract(
        StageId.SIM,
        consumed=("rtl_dir", "design_facts", "testbench_dir"),
        produced=("sim_result",),
        report_key="sim_result",
        parser_contract="tools.check_sim/v2-self-checking",
        tool_identities=("Icarus Verilog",),
    ),
    StageId.LEC_SYNTH: GateContract(
        StageId.LEC_SYNTH,
        consumed=("rtl_dir", "netlist"),
        parser_contract="tools.check_lec/v2-terminal-coherent",
        tool_identities=("EQY ",),
    ),
    StageId.PDN: GateContract(
        StageId.PDN,
        consumed=("floorplan_def",),
        produced=("pdn_def",),
        report_key="pdn_def",
        parser_contract="pdn.check_pdn_def/v1",
        tool_identities=("container:ghcr.io/the-openroad-project/openlane:",),
    ),
    StageId.STA_POSTCTS: GateContract(
        StageId.STA_POSTCTS,
        consumed=("cts_def", "sdc"),
        parser_contract="tools.check_sta/v2-required-metrics",
        tool_identities=("container:ghcr.io/the-openroad-project/openlane:",),
    ),
    StageId.EXTRACTION: GateContract(
        StageId.EXTRACTION,
        consumed=("routed_def",),
        produced=("spef",),
        report_key="spef",
        parser_contract="spef.validate_spef/v1",
        tool_identities=("container:ghcr.io/the-openroad-project/openlane:",),
    ),
    StageId.STA_SIGNOFF: GateContract(
        StageId.STA_SIGNOFF,
        consumed=("routed_def", "spef", "sdc"),
        parser_contract="tools.check_sta/v2-annotation-proven",
        tool_identities=("container:ghcr.io/the-openroad-project/openlane:",),
    ),
    StageId.GDSOUT: GateContract(
        StageId.GDSOUT,
        consumed=("routed_def",),
        produced=("final_gds",),
        report_key="gds_summary",
        parser_contract="gds.check_final_gds/v1",
        tool_identities=("KLayout ",),
    ),
    StageId.DRC: GateContract(
        StageId.DRC,
        consumed=("final_gds",),
        produced=("drc_report",),
        report_key="drc_report",
        parser_contract="klayout_drc.parse_drc_report/v3-deck-bound-aliases",
        tool_identities=("KLayout ",),
    ),
    StageId.LVS: GateContract(
        StageId.LVS,
        consumed=("final_gds", "routed_netlist"),
        produced=("lvs_report", "extracted_netlist", "lvs_reference"),
        report_key="lvs_report",
        parser_contract="klayout_lvs.parse_lvs_report/v2-complete+must-connect",
        tool_identities=("KLayout ",),
    ),
    StageId.ANTENNA: GateContract(
        StageId.ANTENNA,
        consumed=("routed_def",),
        produced=("antenna_report",),
        report_key="antenna_report",
        parser_contract="tools.check_openroad/antenna-v2-both-halves",
        tool_identities=("container:ghcr.io/the-openroad-project/openlane:",),
    ),
    StageId.LEC_ROUTE: GateContract(
        StageId.LEC_ROUTE,
        consumed=("rtl_dir", "routed_netlist"),
        parser_contract="tools.check_lec/v2-terminal-coherent",
        tool_identities=("EQY ",),
    ),
}

#: Kept for the evidence builder; derived so the two cannot drift.
REQUIRED_EVIDENCE: dict[StageId, tuple[str, ...]] = {
    g: c.consumed for g, c in GATE_CONTRACTS.items()
}

CERTIFYING_GATES: tuple[StageId, ...] = tuple(GATE_CONTRACTS)


@dataclass(frozen=True)
class GateEvidence:
    gate: str
    verdict: str
    attempt_id: str
    #: Artifact key of the report this verdict was read from, if any.
    report_key: str | None
    report_sha256: str | None
    #: Artifact key -> sha256 of everything the gate consumed.
    consumed: dict[str, str] = field(default_factory=dict)
    #: Artifact key -> sha256 of everything the gate produced. These are the
    #: lineage edges: a downstream gate that consumed one of these must have
    #: seen exactly this hash, or the two gates ran on different generations.
    produced: dict[str, str] = field(default_factory=dict)
    tool: str = ""
    #: Strongest deterministic identity available for the tool that ran.
    tool_identity: str = ""
    #: Which parser produced the verdict, so a parser change is visible.
    parser_contract: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate": self.gate,
            "verdict": self.verdict,
            "attempt_id": self.attempt_id,
            "report_key": self.report_key,
            "report_sha256": self.report_sha256,
            "consumed": dict(sorted(self.consumed.items())),
            "produced": dict(sorted(self.produced.items())),
            "tool": self.tool,
            "tool_identity": self.tool_identity,
            "parser_contract": self.parser_contract,
            "metrics": {
                k: v for k, v in self.metrics.items()
                if isinstance(v, (int, float, str, bool, type(None)))
            },
            "created_at": self.created_at,
        }

    # ---- validation ------------------------------------------------------

    def problems_against(
        self,
        *,
        manifest_artifacts: dict[str, dict[str, Any]],
        ledger: ArtifactLedger,
    ) -> list[str]:
        """Everything wrong with this record relative to the candidate."""
        out: list[str] = []

        # ---- exact schema ------------------------------------------------
        #
        # Absence used to be silent: a record with no attempt, no report, no
        # tool identity, no parser contract and an empty consumed map passed
        # every check because every check was conditional on the field being
        # present.
        contract = GATE_CONTRACTS.get(_stage_of(self.gate))
        if contract is None:
            out.append(
                f"{self.gate} has no gate contract, so there is no definition "
                "of what would count as proof for it"
            )
        else:
            if self.gate != contract.gate.value:
                out.append(
                    f"evidence labelled {self.gate!r} was validated as "
                    f"{contract.gate.value!r}"
                )
            if not self.attempt_id:
                out.append(f"{self.gate} evidence records no attempt identity")
            if contract.parser_contract and \
                    self.parser_contract != contract.parser_contract:
                out.append(
                    f"{self.gate} was graded by parser contract "
                    f"{self.parser_contract or '(none)'!r}, not the approved "
                    f"{contract.parser_contract!r}"
                )
            if contract.tool_identities and not any(
                    self.tool_identity.startswith(x)
                    for x in contract.tool_identities):
                out.append(
                    f"{self.gate} ran on unapproved tool identity "
                    f"{self.tool_identity or '(none)'!r}; an unknown build "
                    "cannot certify"
                )
            if contract.report_key and self.report_key != contract.report_key:
                out.append(
                    f"{self.gate} must record its verdict against "
                    f"{contract.report_key!r}, not {self.report_key or '(none)'!r}"
                )
            missing_in = [k for k in contract.consumed if k not in self.consumed]
            if missing_in:
                out.append(
                    f"{self.gate} did not record what it consumed: "
                    f"{', '.join(missing_in)} missing. A gate that does not "
                    "say which inputs it read proves nothing about them"
                )
            missing_out = [k for k in contract.produced if k not in self.produced]
            if missing_out:
                out.append(
                    f"{self.gate} did not record what it produced: "
                    f"{', '.join(missing_out)} missing, so no lineage edge "
                    "ties its output to the generation that made it"
                )

        if self.verdict != "pass":
            out.append(
                f"{self.gate} evidence records verdict {self.verdict!r}, not a pass"
            )

        # The report that produced the verdict must still be those bytes.
        if self.report_key:
            if not self.report_sha256:
                out.append(
                    f"{self.gate} names report {self.report_key} but recorded no "
                    "hash for it, so nothing ties the verdict to its report"
                )
            elif self.report_key in ledger:
                now = ledger.get(self.report_key)
                on_disk = (
                    sha256_file(now.path) if now.path.exists() else None
                )
                if on_disk is None:
                    out.append(
                        f"{self.gate}'s report {self.report_key} no longer exists"
                    )
                elif on_disk != self.report_sha256:
                    out.append(
                        f"{self.gate}'s report changed after the verdict was "
                        f"issued ({self.report_sha256[:12]} -> {on_disk[:12]}); "
                        "the recorded result describes a file that is gone"
                    )
            else:
                out.append(
                    f"{self.gate}'s report {self.report_key} is not registered"
                )

        # Every consumed artifact must be the one the candidate binds.
        for key, sha in sorted(self.consumed.items()):
            bound = manifest_artifacts.get(key, {})
            candidate_sha = bound.get("sha256")
            if candidate_sha is None:
                out.append(
                    f"{self.gate} consumed {key} ({sha[:12]}) but the release "
                    "candidate does not bind it, so the two describe different "
                    "sets of files"
                )
            elif candidate_sha != sha:
                out.append(
                    f"{self.gate} verified {key} {sha[:12]} but the candidate's "
                    f"{key} is {candidate_sha[:12]}: this evidence is about a "
                    "different design"
                )

        for key, sha in sorted(self.produced.items()):
            candidate_sha = manifest_artifacts.get(key, {}).get("sha256")
            if candidate_sha is not None and candidate_sha != sha:
                out.append(
                    f"{self.gate} produced {key} {sha[:12]} but the candidate "
                    f"binds {candidate_sha[:12]}: the certified artifact is "
                    "not the one this gate made"
                )
        return out

    def identity(self) -> str:
        """Canonical digest of what this record claims.

        Folded into the certification identity so "same artifacts, different
        proofs" is a different certification.
        """
        payload = json.dumps(
            {
                "gate": self.gate,
                "verdict": self.verdict,
                "attempt_id": self.attempt_id,
                "report_key": self.report_key,
                "report_sha256": self.report_sha256,
                "consumed": dict(sorted(self.consumed.items())),
                "produced": dict(sorted(self.produced.items())),
                "tool_identity": self.tool_identity,
                "parser_contract": self.parser_contract,
            },
            sort_keys=True, separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()


def missing_evidence(
    records: dict[StageId, GateEvidence],
    required: tuple[StageId, ...] = CERTIFYING_GATES,
) -> list[str]:
    """Gates with no evidence at all.

    This is the check that replaces "StageState says OK". A stage can be
    complete and have produced nothing that certifies anything.
    """
    return [
        f"{gate} produced no verification evidence, so nothing certifies it "
        "(a completed stage is not a verified one)"
        for gate in required
        if gate not in records
    ]


def evidence_for(
    *,
    stage: StageId,
    verdict_kind: str,
    attempt: int,
    ledger: ArtifactLedger,
    outputs: dict[str, Path] | None = None,
    report_key: str | None = None,
    tool: str = "",
    tool_identity: str = "",
    parser_contract: str = "",
    metrics: dict[str, Any] | None = None,
) -> GateEvidence:
    """Build a record from what the stage actually consumed and produced."""
    contract = GATE_CONTRACTS.get(stage)
    consumed: dict[str, str] = {}
    for key in (contract.consumed if contract else ()):
        if key in ledger:
            consumed[key] = ledger.get(key).sha256

    # Lineage edges. Recorded from the ledger after registration, so the hash
    # is the artifact this attempt actually wrote.
    produced: dict[str, str] = {}
    for key in (contract.produced if contract else ()):
        if key in ledger:
            produced[key] = ledger.get(key).sha256

    report_sha: str | None = None
    if report_key:
        path: Path | None = None
        if outputs and report_key in outputs:
            path = Path(outputs[report_key])
        elif report_key in ledger:
            path = ledger.get(report_key).path
        if path is not None and path.exists():
            report_sha = sha256_file(path)

    return GateEvidence(
        gate=stage.value,
        verdict=verdict_kind,
        attempt_id=f"{stage.value}#{attempt}",
        report_key=report_key,
        report_sha256=report_sha,
        consumed=consumed,
        produced=produced,
        tool=tool,
        tool_identity=tool_identity,
        parser_contract=parser_contract,
        metrics=dict(metrics or {}),
    )


def _stage_of(gate: str) -> StageId | None:
    try:
        return StageId(gate)
    except ValueError:
        return None


def lineage_problems(records: dict[StageId, GateEvidence]) -> list[str]:
    """Cross-gate causal coherence.

    P0-R2's decisive reproduction combined two organically clean candidates:
    candidate A supplied the GDS with its DRC and LVS evidence, candidate B
    supplied the routed DEF, SPEF, STA, antenna and LEC evidence. Every file
    hash was internally correct and the aggregator reported clean, because the
    manifest is a *set* of artifacts and nothing asserted that the GDS was made
    from the DEF the timing was measured on.

    Each gate now records what it produced. Wherever one gate consumes an
    artifact another gate produced, the two hashes must agree -- that edge is
    the causal graph, and a hybrid breaks it.
    """
    producer: dict[str, tuple[StageId, str]] = {}
    for gate, rec in records.items():
        for key, sha in rec.produced.items():
            producer[key] = (gate, sha)

    out: list[str] = []
    for gate, rec in sorted(records.items(), key=lambda kv: kv[0].value):
        for key, sha in sorted(rec.consumed.items()):
            if key not in producer:
                continue
            made_by, made_sha = producer[key]
            if made_by == gate or made_sha == sha:
                continue
            out.append(
                f"{gate.value} consumed {key} {sha[:12]} but {made_by.value} "
                f"produced {made_sha[:12]}: these two gates ran on different "
                "physical generations, so their results do not describe one "
                "design"
            )

    # One artifact key, one value, across the whole proof set.
    #
    # The edge rule above only covers keys some certifying gate produces.
    # `routed_def` is written by routing, which is not itself a certifying
    # gate -- and it is exactly the artifact the hybrid attack splits, with
    # GDSOUT/DRC/LVS reading candidate A's and extraction/STA/antenna reading
    # candidate B's. If two gates disagree about what a key's contents were,
    # they did not run on the same design, whoever produced it.
    seen: dict[str, dict[str, list[str]]] = {}
    for gate, rec in sorted(records.items(), key=lambda kv: kv[0].value):
        for source in (rec.consumed, rec.produced):
            for key, sha in source.items():
                seen.setdefault(key, {}).setdefault(sha, []).append(gate.value)
    for key, by_hash in sorted(seen.items()):
        if len(by_hash) < 2:
            continue
        detail = "; ".join(
            f"{sha[:12]} seen by {', '.join(sorted(set(gates)))}"
            for sha, gates in sorted(by_hash.items())
        )
        out.append(
            f"gates disagree about {key}: {detail}. Verification from two "
            "different physical generations cannot certify one candidate"
        )
    return out


def certification_id(
    candidate_id: str,
    records: dict[StageId, GateEvidence],
    required: tuple[StageId, ...] = CERTIFYING_GATES,
) -> str:
    """Identity of *this artifact set proved by exactly these records*.

    The candidate ID commits to the files. On its own it cannot distinguish a
    candidate certified by one set of proofs from the same candidate certified
    by another, which is what let evidence be swapped underneath it.
    """
    payload = json.dumps(
        {
            "candidate_id": candidate_id,
            "gates": {
                g.value: records[g].identity()
                for g in required if g in records
            },
        },
        sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()
