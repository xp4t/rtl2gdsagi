"""The orchestrator.

Deterministic control. It renders configs, invokes tools, parses reports,
authors verdicts, and decides what to re-run. The agent is consulted only for
diagnosis, and only after a verdict already exists.

The main loop is index-based rather than a for-loop over stages, because
rollback moves the index *backwards*. That single generic mechanism -- resolve a
responsible stage from the taxonomy, invalidate everything downstream, jump --
is what makes every stage reachable from every failure, replacing the hand-drawn
arrows that only ever connected two of eight gates (review 9.0, 20.5).
"""

from __future__ import annotations

import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .agent.client import (
    Agent,
    DiagnosisRequest,
    ScriptedAgent,
    write_audit,
)
from .artifacts import ArtifactError, ArtifactLedger
from .characterize import DesignFacts, characterize, suggest_starting_ir
from .checkpoints import CheckpointStore, fingerprint_attempt
from .checks import gds as gdsread, klayout_drc, klayout_lvs
from .checks.deck_guard import audit_deck
from .checks.pdn import SKY130_MINIMUM_PDN, check_pdn_def
from .checks.spef import validate_spef
from .checks.tools import (
    ToolRun,
    check_lec,
    check_lint,
    check_openroad,
    check_sim,
    check_sta,
    check_synthesis,
)
from .checks.verdict import Verdict, VerdictKind, failed, passed, qor_low
from .config import RunConfig
from .errors import AgentError, Escalated, Rtl2GdsError
from .error_knowledge.context import pdn_context
from .error_knowledge.known_fixes import lookup_known_fix
from .error_knowledge.matcher import match_openroad_messages
from .error_knowledge.runtime_failures import classify_runtime_failure
from .evidence import (
    CERTIFYING_GATES,
    GateEvidence,
    certification_id,
    evidence_for,
    lineage_problems,
    missing_evidence,
)
from .ir import IR, SchemaViolation
from .manifest import ReleaseCandidateManifest
from .render import RenderContext, render
from .runlog import RunLog
from .safety import (
    BudgetExhausted,
    authorized_action_space,
    authorized_current_values,
    earliest_affected_stage,
    ImmutableZones,
    IterationBudget,
    SafetyViolation,
    review_delta_scope,
    review_diagnosis,
)
from .stages import (
    REQUIRED_VERIFICATION,
    Gate,
    STAGE_ORDER,
    SIGNOFF_GATES,
    StageId,
    StageSpec,
    Tool,
    get_stage,
    stage_index,
)
from .state import RunState, RunStatus, StageState, StageStatus, new_run_id
from .taxonomy import FailureClass, Resolution, lookup, responsible_stage
from .tools.invoker import DEFAULT_OPENLANE_IMAGE, MockInvoker, RealInvoker, ToolInvoker
from .tools.klayout_backend import KLayoutRuntimeManager
from .repair import (
    ActionType, RepairAction, RepairExecutor, RepairPlan,
    evaluate_certification, evaluate_repair,
)


#: Stage -> the artifact key of the report its verdict was read from.
_REPORT_KEY: dict[StageId, str] = {
    StageId.DRC: "drc_report",
    StageId.LVS: "lvs_report",
    StageId.ANTENNA: "antenna_report",
    StageId.SIM: "sim_result",
    StageId.EXTRACTION: "spef",
    StageId.PDN: "pdn_def",
    StageId.GDSOUT: "gds_summary",
}

#: Stage -> the parser that produced its verdict. Recorded so that changing a
#: parser is visible in the evidence rather than silently reinterpreting an
#: old result.
_PARSER_CONTRACT: dict[StageId, str] = {
    StageId.DRC: "klayout_drc.parse_drc_report/v3-deck-bound-aliases",
    StageId.LVS: "klayout_lvs.parse_lvs_report/v2-complete+must-connect",
    StageId.ANTENNA: "tools.check_openroad/antenna-v2-both-halves",
    StageId.SIM: "tools.check_sim/v2-self-checking",
    StageId.LEC_SYNTH: "tools.check_lec/v2-terminal-coherent",
    StageId.LEC_ROUTE: "tools.check_lec/v2-terminal-coherent",
    StageId.STA_POSTCTS: "tools.check_sta/v2-required-metrics",
    StageId.STA_SIGNOFF: "tools.check_sta/v2-annotation-proven",
    StageId.EXTRACTION: "spef.validate_spef/v1",
    StageId.PDN: "pdn.check_pdn_def/v1",
    StageId.GDSOUT: "gds.check_final_gds/v1",
}


class Escalation(Escalated):
    """The flow stopped and is asking for a human. Not a crash.

    Carries the stage and the raw tool evidence so the failure report can
    explain *why* this class of failure has no autonomous resolution.
    """

    def __init__(self, stage: StageId, reason: str, detail: str = "") -> None:
        super().__init__(f"{stage}: {reason}")
        self.stage = stage
        self.reason = reason
        self.detail = detail


@dataclass
class StageOutcome:
    stage: StageId
    verdict: Verdict
    run: ToolRun | None = None
    outputs: dict[str, Path] = field(default_factory=dict)


class Orchestrator:
    def __init__(
        self,
        cfg: RunConfig,
        *,
        agent: Agent | None = None,
        invoker: ToolInvoker | None = None,
        run_dir: Path | None = None,
        global_budget: int | None = None,
        interactive: bool | None = None,
        input_fn: Any = input,
    ) -> None:
        self.cfg = cfg
        self.run_id = new_run_id()
        self.run_dir = Path(run_dir) if run_dir else (cfg.run_root / self.run_id)
        self.run_dir.mkdir(parents=True, exist_ok=True)

        self.log = RunLog(self.run_dir)
        self.ledger = ArtifactLedger()
        self.store = CheckpointStore(self.run_dir / "checkpoints")
        self.state = RunState(run_id=self.run_id, run_dir=self.run_dir, config=cfg.to_dict())
        self.ir = IR()
        self.budget = IterationBudget(
            global_budget if global_budget is not None else cfg.retry_limit * 8
        )
        self.invoker: ToolInvoker = invoker or (
            MockInvoker() if cfg.mock_tools
            else RealInvoker(pdk_root=cfg.pdk.root, run_dir=self.run_dir)
        )
        self.agent: Agent = agent or ScriptedAgent()
        self.interactive = sys.stdin.isatty() if interactive is None else interactive
        self.input_fn = input_fn
        #: Deltas that survived deterministic review and were applied.
        self._accepted: list[dict[str, Any]] = []
        #: Immutable per-call model audit records, in call order.
        self._call_audits: list[Any] = []
        self.facts = DesignFacts(top=cfg.top)

        # The user's RTL and the PDK are read-only for the whole run.
        self.zones = ImmutableZones(pdk_root=cfg.pdk.root, rtl_source=cfg.rtl_dir)
        self.work_rtl = self.run_dir / "work" / "rtl"
        self._history: list[dict[str, Any]] = []
        #: Hard-gate evidence, the only thing signoff may certify on.
        self._evidence: dict[StageId, GateEvidence] = {}
        self._tried: dict[StageId, list[dict[str, Any]]] = {}
        #: Where the main loop resumes after a rollback moves it backwards.
        self._resume_at: StageId = STAGE_ORDER[0]
        self.klayout = KLayoutRuntimeManager(
            invoker=self.invoker, run_dir=self.run_dir, pdk_root=cfg.pdk.root,
            image=getattr(self.invoker, "openlane_image", "") or DEFAULT_OPENLANE_IMAGE,
        )
        self.klayout.set_backend(cfg.klayout_backend)
        self.repair_executor = RepairExecutor(
            ir=self.ir, zones=self.zones, work_rtl=self.work_rtl,
            backend_setter=self.klayout.set_backend,
        )

    # ---- directories -----------------------------------------------------

    def stage_dir(self, stage: StageId) -> Path:
        d = self.run_dir / "stages" / f"{stage_index(stage):02d}_{stage.value}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ---- setup -----------------------------------------------------------

    def prepare(self) -> None:
        """Copy RTL into the run, characterize it, and seed the IR."""
        self.work_rtl.mkdir(parents=True, exist_ok=True)
        copied = 0
        for src in sorted(self.cfg.rtl_dir.rglob("*")):
            if src.is_file() and src.suffix in (".v", ".sv", ".vh", ".svh"):
                rel = src.relative_to(self.cfg.rtl_dir)
                dst = self.work_rtl / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                self.zones.check_write(dst)  # must land outside the source tree
                shutil.copy2(src, dst)
                copied += 1
        self.log.note(
            f"copied {copied} RTL file(s) into the run; {self.cfg.rtl_dir} stays read-only",
            files=copied,
        )
        self.ledger.register("rtl_dir", self.work_rtl, stage="prepare", allow_dir=True)
        # This is the immutable identity copied before any authorized working
        # RTL repair. Physical-only repair records must prove it stayed equal.
        self._initial_work_rtl_sha256 = self.ledger.get("rtl_dir").sha256
        self._register_testbenches("prepare")

        self.facts = characterize(
            self.work_rtl, self.cfg.top,
            default_period_ns=self.ir.get("sdc", "default_clock_period_ns"),
        )
        (self.stage_dir(StageId.CHARACTERIZE) / "facts.json").write_text(
            __import__("json").dumps(self.facts.to_dict(), indent=2), encoding="utf-8"
        )
        for w in self.facts.warnings:
            self.log.warn(w, stage=str(StageId.CHARACTERIZE))

        seed = suggest_starting_ir(self.facts)
        if seed:
            self.ir.apply_delta(seed, agent=False)
            self.log.note(
                "seeded starting knobs from design characterization", delta=seed
            )
        # The user's config wins over anything characterization inferred.
        if self.cfg.ir_overrides:
            self.ir.apply_delta(self.cfg.ir_overrides, agent=False)
            self.log.note(
                "applied ir overrides from the config file",
                delta=self.cfg.ir_overrides,
            )
        self.ledger.register(
            "design_facts",
            self._write(self.stage_dir(StageId.CHARACTERIZE) / "facts.json",
                        __import__("json").dumps(self.facts.to_dict(), indent=2)),
            stage="characterize",
        )
        self.state.stages[StageId.CHARACTERIZE] = StageState(
            status=StageStatus.OK, attempts=1
        )
        self.state.save()

    @staticmethod
    def _write(path: Path, text: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    # ---- rendering + argv ------------------------------------------------

    def _context(self, spec: StageSpec) -> RenderContext:
        sd = self.stage_dir(spec.id)
        inputs = {
            k: self.ledger.get(k).path for k in self.ledger.keys()
        }
        outputs = self._outputs_for(spec, sd)
        facts = self.facts.to_dict()
        facts["sources"] = [str(p) for p in self.facts.sources]
        facts["cell_gds"] = [str(p) for p in self.cfg.pdk.cell_gds()]
        facts["site"] = "unithd" if self.cfg.pdk.name.startswith("sky130") else "core"
        return RenderContext(
            top=self.cfg.top, pdk=self.cfg.pdk, work_dir=sd,
            inputs=inputs, outputs=outputs, facts=facts,
        )

    def _outputs_for(self, spec: StageSpec, sd: Path) -> dict[str, Path]:
        top = self.cfg.top
        table: dict[StageId, dict[str, Path]] = {
            StageId.SDC: {"sdc": sd / f"{top}.sdc"},
            StageId.SYNTHESIS: {
                "netlist": sd / f"{top}.netlist.v",
                "synth_json": sd / f"{top}.synth.json",
            },
            StageId.FLOORPLAN: {"floorplan_def": sd / f"{top}.floorplan.def"},
            StageId.PDN: {"pdn_def": sd / f"{top}.pdn.def"},
            StageId.PLACEMENT: {
                "placement_def": sd / f"{top}.placement.def",
                "placed_netlist": sd / f"{top}.placed.v",
                "congestion_report": sd / "congestion.rpt",
            },
            StageId.CTS: {
                "cts_def": sd / f"{top}.cts.def",
                "cts_netlist": sd / f"{top}.cts.v",
            },
            StageId.ROUTING: {
                "routed_def": sd / f"{top}.routed.def",
                "routed_netlist": sd / f"{top}.routed.v",
                "route_drc": sd / "route.drc.rpt",
            },
            StageId.EXTRACTION: {"spef": sd / f"{top}.spef"},
            StageId.ANTENNA: {"antenna_report": sd / "antenna.rpt"},
            StageId.GDSOUT: {"final_gds": sd / f"{top}.gds",
                             "gds_summary": sd / "gds_summary.json"},
            StageId.DRC: {"drc_report": sd / "drc.lyrdb"},
            StageId.LVS: {
                "lvs_report": sd / "lvs.lvsdb",
                "extracted_netlist": sd / f"{top}.extracted.cir",
            },
        }
        return table.get(spec.id, {})

    def _argv(self, spec: StageSpec, script: Path | None, ctx: RenderContext) -> list[str]:
        sd = ctx.work_dir
        if spec.tool is Tool.VERILATOR:
            argv = ["verilator", "--lint-only", "-Wall", "--timing"]
            if not self.ir.get("lint", "fail_on_warning"):
                # -Wall alone makes Verilator exit non-zero on style warnings.
                # The stage gates on errors; warnings are recorded as QoR.
                argv.append("-Wno-fatal")
            for rule in self.ir.get("lint", "waived_rules"):
                argv.append(f"-Wno-{rule}")
            argv += ["--top-module", self.cfg.top,
                     *[str(p) for p in self.facts.sources]]
            return argv
        if spec.tool is Tool.YOSYS:
            return ["yosys", "-s", str(script)]
        if spec.tool is Tool.EQY:
            return ["eqy", "-f", "-d", str(sd / "eqy"), str(script)]
        if spec.tool is Tool.OPENSTA:
            return ["sta", "-no_splash", "-exit", str(script)]
        if spec.tool is Tool.OPENROAD:
            return ["openroad", "-no_init", "-exit", str(script)]
        if spec.tool is Tool.KLAYOUT:
            if spec.id is StageId.GDSOUT:
                return ["klayout", "-b", "-r", str(script)]
            if spec.id is StageId.DRC:
                s = self.ir.section("drc")
                # The SKY130 runset gates every rule group behind its own
                # switch: without feol/beol/offgrid/floating_met it loads,
                # writes a well-formed report, and checks *nothing*. The
                # variable names are the deck's own ($top_cell, $thr), not
                # guesses -- getting them wrong silently disables the rules.
                return [
                    "klayout", "-b", "-r", str(self.cfg.pdk.drc_deck_path),
                    "-rd", f"input={ctx.inp('final_gds')}",
                    "-rd", f"top_cell={self.cfg.top}",
                    "-rd", f"report={ctx.out('drc_report')}",
                    "-rd", f"thr={s['threads']}",
                    "-rd", "feol=true",
                    "-rd", "beol=true",
                    "-rd", "offgrid=true",
                    "-rd", "floating_met=true",
                ]
            if spec.id is StageId.LVS:
                s = self.ir.section("lvs")
                netlist = (
                    "routed_netlist" if "routed_netlist" in ctx.inputs else "netlist"
                )
                return [
                    "klayout", "-b", "-r", str(self.cfg.pdk.lvs_deck_path),
                    "-rd", f"input={ctx.inp('final_gds')}",
                    "-rd", f"top_cell={self.cfg.top}",
                    "-rd", f"schematic={ctx.inp(netlist)}",
                    "-rd", f"target_netlist={ctx.out('extracted_netlist')}",
                    "-rd", f"report={ctx.out('lvs_report')}",
                    "-rd", f"thr={s['threads']}",
                    "-rd", f"run_mode={'deep' if s['deep_mode'] else 'flat'}",
                ]
        if spec.tool is Tool.IVERILOG:
            # Handled by _run_simulations: each testbench is a separate
            # compile-and-run, so there is no single argv for the stage.
            return []
        return []

    # ---- verdicts --------------------------------------------------------

    def _judge(self, spec: StageSpec, run: ToolRun, ctx: RenderContext) -> Verdict:
        """Author the verdict. Deterministic code only (review 14.1)."""
        sid = spec.id
        outs = ctx.outputs

        if sid is StageId.LINT:
            return check_lint(run, fail_on_warning=self.ir.get("lint", "fail_on_warning"))
        if sid is StageId.SIM:
            return check_sim(run)
        if sid is StageId.SYNTHESIS:
            return check_synthesis(run, outs.get("netlist"))
        if sid in (StageId.LEC_SYNTH, StageId.LEC_ROUTE):
            return check_lec(run, sid)
        if sid in (StageId.STA_PRE, StageId.STA_POSTCTS, StageId.STA_SIGNOFF):
            return check_sta(
                run, sid,
                guardband=self.ir.get("sta", "slack_guardband_ns"),
                # Signoff is the analysis that is supposed to see real wires.
                expect_parasitics=(sid is StageId.STA_SIGNOFF),
            )
        if sid is StageId.PDN:
            return self._judge_pdn(run, ctx)
        if sid is StageId.EXTRACTION:
            return self._judge_extraction(run, ctx)
        if sid is StageId.DRC:
            return self._judge_drc(run, ctx)
        if sid is StageId.LVS:
            return self._judge_lvs(run, ctx)
        if sid is StageId.GDSOUT:
            return self._judge_gds(run, ctx)
        if spec.tool is Tool.OPENROAD:
            return check_openroad(
                run, sid, outputs=outs,
                overflow_limit=self.ir.get("placement", "congestion_overflow_limit"),
            )
        # No checker claimed this stage. Currently unreachable -- every stage
        # above is handled, and sdc/signoff/characterize are judged on their
        # own paths -- but the default used to be `passed(...)`, so adding a
        # hard-gated stage and forgetting to write its checker would have
        # produced a stage that always passes without inspecting anything.
        # A gate with no checker is unknown, and unknown is not a pass.
        if spec.gate is Gate.HARD:
            return failed(
                sid, FailureClass.TOOL_RUNTIME,
                f"{sid} is a hard gate but no result checker is wired up for "
                "it, so nothing about its output was verified",
                evidence=run.tail(2000),
            )
        return passed(sid, f"{sid} completed (no checker; not a gated stage)")

    def _judge_gds(self, run: ToolRun, ctx: RenderContext) -> Verdict:
        """Verify the stream-out actually produced a *merged* final GDS.

        A pre-merge layout still references standard cells that live in the PDK
        GDS rather than in the file itself, so its SREF/AREF names dangle. That
        dangling is a structural signature of "not the final GDS" -- and letting
        such a file reach signoff is exactly how DRC once came back clean while
        thousands of real violations sat in the merged layout.
        """
        path = Path(ctx.out("final_gds"))
        if run.returncode != 0 or not path.is_file() or path.stat().st_size == 0:
            return failed(
                StageId.GDSOUT, FailureClass.GDS,
                f"stream-out failed (exit {run.returncode})", evidence=run.tail(),
            )
        try:
            info = gdsread.read_gds(path)
        except gdsread.GDSError as exc:
            return failed(
                StageId.GDSOUT, FailureClass.GDS,
                f"the written GDS is not readable: {exc}", evidence=run.tail(),
            )

        self._write(
            Path(ctx.out("gds_summary")),
            __import__("json").dumps(info.to_dict(), indent=2, default=str),
        )
        metrics = {
            "gds_bytes": path.stat().st_size,
            "cells": len(info.cells),
            "total_elements": info.total_elements,
        }

        top = info.cell(self.cfg.top)
        if top is None:
            return failed(
                StageId.GDSOUT, FailureClass.GDS,
                f"the GDS does not contain the expected top cell {self.cfg.top!r}; "
                f"it holds {len(info.cells)} cell(s)",
                evidence=", ".join(sorted(info.cells)[:30]), **metrics,
            )
        if top.is_empty:
            return failed(
                StageId.GDSOUT, FailureClass.GDS,
                f"top cell {self.cfg.top!r} is empty", evidence=run.tail(), **metrics,
            )
        # Catch a stream-out that invented its own layer numbers.
        #
        # Without a layer map, KLayout numbers DEF-derived geometry
        # sequentially (3/0, 5/0, 7/0 ...) instead of using the PDK's real
        # layers. The GDS looks perfectly fine in a viewer, but the DRC deck
        # inspects real layer numbers and so never sees the routing at all --
        # it checks only the standard cells and reports a clean result on a
        # layout it never examined. That is a false clean of exactly the kind
        # this flow exists to prevent, so it fails here rather than sailing on.
        mapped = self.cfg.pdk.mapped_layers()
        if mapped and info.layers:
            # Anything numbered below every layer the PDK defines was invented
            # by the reader, not mapped. Deriving the floor from the PDK rather
            # than hardcoding it keeps this working for other processes.
            floor = min(layer for layer, _ in mapped)
            stray = {k: n for k, n in info.layers.items() if k[0] < floor}
            if stray:
                worst = sorted(stray.items(), key=lambda kv: -kv[1])[:8]
                return failed(
                    StageId.GDSOUT, FailureClass.GDS,
                    f"{sum(stray.values())} shape(s) sit on layer numbers below "
                    f"anything {self.cfg.pdk.name} defines, so the stream-out "
                    "did not apply the layer map. Signoff would then inspect "
                    "layers the routing is not on and could report clean having "
                    "examined nothing",
                    evidence=(
                        f"lowest layer the PDK uses: {floor}\n"
                        + "\n".join(f"  layer {l}/{d}: {n} shapes"
                                     for (l, d), n in worst)
                    ),
                    **metrics,
                )

        if info.unresolved_references:
            worst = sorted(
                info.unresolved_references.items(), key=lambda kv: -kv[1]
            )[:15]
            return failed(
                StageId.GDSOUT, FailureClass.GDS,
                f"{len(info.unresolved_references)} referenced cell(s) are not "
                "present in the GDS, so this is a pre-merge layout rather than "
                "the final stream-out; signoff against it would be meaningless",
                evidence="\n".join(f"  {n} referenced {c}x" for n, c in worst),
                **metrics,
            )
        return passed(
            StageId.GDSOUT,
            f"streamed out {path.name}: {len(info.cells)} cells, "
            f"{info.total_elements} elements, all references resolved",
            **metrics,
        )

    def _judge_pdn(self, run: ToolRun, ctx: RenderContext) -> Verdict:
        """Prove the grid actually reaches the cells.

        The stage previously passed on "OpenROAD exited 0 and wrote a file" --
        a one-byte DEF satisfied it. That is the same gate that once shipped a
        power grid floating above the design with a single via in it, which no
        DRC or STA check can see.
        """
        base = check_openroad(run, StageId.PDN, outputs=ctx.outputs)
        if not base.ok:
            return base

        # The postcondition is deliberately NOT read from the IR.
        #
        # It used to take its ring expectation straight from the writable
        # field `pdn.core_ring`, and its strap-layer requirement from a
        # `pdn.strap_layers` field. The first let a PDN
        # diagnosis set `core_ring=false` and thereby switch off the very
        # obligation it was being judged against; the second named a field
        # that does not exist in the schema, so the required strap-layer tuple
        # was always empty and a rails-only grid passed. See
        # `checks.pdn.PDNContract`.
        res = check_pdn_def(Path(ctx.out("pdn_def")), contract=SKY130_MINIMUM_PDN)
        self._write(
            self.stage_dir(StageId.PDN) / "pdn_summary.json",
            __import__("json").dumps(res.to_dict(), indent=2),
        )
        if not res.ok:
            return failed(
                StageId.PDN, FailureClass.PDN, res.summary(),
                evidence="\n".join(res.problems)[:4000],
                via_count=res.via_count,
            )
        return passed(
            StageId.PDN, res.summary(),
            power_nets=res.power_nets, ground_nets=res.ground_nets,
            via_count=res.via_count,
        )

    def _judge_extraction(self, run: ToolRun, ctx: RenderContext) -> Verdict:
        """Prove the SPEF describes this design and contains parasitics.

        The stage previously accepted any non-empty file. A header-only SPEF
        naming a different design with zero nets passed -- and signoff STA then
        read it, warned, and reported the no-parasitics timing numbers as if
        they were extracted ones. Both gates agreed the design met timing with
        interconnect that had never been read.
        """
        base = check_openroad(run, StageId.EXTRACTION, outputs=ctx.outputs)
        if not base.ok:
            return base

        spef = Path(ctx.out("spef"))
        routed_def = (
            self.ledger.get("routed_def").path
            if "routed_def" in self.ledger else None
        )
        res = validate_spef(
            spef, expected_design=self.cfg.top, routed_def=routed_def,
            min_coverage=float(self.ir.get("extraction", "min_net_coverage")),
        )
        self._write(
            self.stage_dir(StageId.EXTRACTION) / "spef_summary.json",
            __import__("json").dumps(res.to_dict(), indent=2),
        )
        if not res.ok:
            return failed(
                StageId.EXTRACTION, FailureClass.EXTRACTION, res.summary(),
                evidence="\n".join(res.problems)[:4000],
                spef_design=res.design, spef_net_count=res.net_count,
                routed_net_count=res.routed_net_count, coverage=res.coverage,
            )
        return passed(
            StageId.EXTRACTION, res.summary(),
            spef_design=res.design, spef_net_count=res.net_count,
            routed_net_count=res.routed_net_count, coverage=res.coverage,
            total_capacitance=res.total_capacitance,
        )

    def _judge_drc(self, run: ToolRun, ctx: RenderContext) -> Verdict:
        """Bind the DRC report to the exact GDS gdsout produced.

        KLayout writes ``<original-file/>`` empty, so the report cannot say which
        layout it read. The binding therefore has to come from the ledger, which
        is the whole reason pre-merge macros could once pass clean.
        """
        # The exit code was previously not even passed in, so a crashed KLayout
        # sitting next to a clean report from an earlier attempt was read as a
        # clean design. A DRC run that did not finish has not checked anything.
        if run.timed_out:
            return failed(
                StageId.DRC, FailureClass.TOOL_RUNTIME,
                f"the DRC run timed out after {run.duration_s:.0f}s; no report "
                "it left behind can be treated as a result",
                evidence=run.tail(2000),
            )
        if run.returncode != 0:
            return failed(
                StageId.DRC, FailureClass.DRC,
                f"the DRC tool exited {run.returncode}; refusing to read a "
                "clean result out of a run that failed",
                evidence=run.tail(2500),
            )
        gds = self.ledger.get("final_gds")
        gds.assert_unchanged()
        report = Path(ctx.out("drc_report"))
        try:
            self.ledger.assert_produced_after(report, gds)
        except Exception as exc:
            return failed(StageId.DRC, FailureClass.DRC, str(exc), evidence=str(exc))

        # The deck that ran decides which rule inventory the report must show.
        # Without this the check was only "at least one category exists", and a
        # report declaring a single dummy rule passed clean.
        deck = audit_deck(self.cfg.pdk.drc_deck_path, kind="drc")
        if not deck.trustworthy:
            return failed(
                StageId.DRC, FailureClass.DRC, deck.summary(),
                evidence="; ".join(deck.problems),
            )
        res = klayout_drc.parse_drc_report(
            report, expected_top=self.cfg.top, checked_gds=gds,
            deck_sha256=deck.sha256,
        )
        drc_record = res.to_dict()
        drc_record["provenance"] = {
            "deck_path": str(deck.path),
            "deck_sha256": deck.sha256,
            "deck_approval": deck.approved_as,
            "pdk": self.cfg.pdk.name,
            "pdk_root": str(self.cfg.pdk.root),
            "pdk_revision": self.cfg.pdk.root.parent.name,
            "klayout_backend": self.klayout.backend.name,
            "klayout_identity": self._tool_identity(Tool.KLAYOUT),
            "argv": list(run.argv),
        }
        self._write(
            self.stage_dir(StageId.DRC) / "drc_summary.json",
            __import__("json").dumps(drc_record, indent=2),
        )
        if res.clean:
            return passed(
                StageId.DRC, res.summary(),
                total_violations=0, declared_categories=res.declared_categories,
                raw_declared_categories=res.raw_declared_categories,
                category_inventory_sha256=res.category_inventory_sha256,
                raw_category_inventory_sha256=res.raw_category_inventory_sha256,
                normalized_duplicate_categories={
                    name: list(descriptions)
                    for name, descriptions in res.normalized_duplicate_categories.items()
                },
                checked_gds_sha256=gds.sha256,
            )
        return failed(
            StageId.DRC, FailureClass.DRC, res.summary(),
            evidence=res.violation_digest(),
            total_violations=res.total_violations,
            violated_categories=res.violated_categories,
            by_category=dict(res.top_categories(15)),
            checked_gds_sha256=gds.sha256,
        )

    def _judge_lvs(self, run: ToolRun, ctx: RenderContext) -> Verdict:
        gds = self.ledger.get("final_gds")
        gds.assert_unchanged()
        deck = audit_deck(self.cfg.pdk.lvs_deck_path, kind="lvs")
        res = klayout_lvs.parse_lvs_report(
            ctx.out("lvs_report"),
            log_text=run.combined,
            exit_code=run.returncode,
            expected_top=self.cfg.top,
            checked_gds=gds,
            deck_trustworthy=deck.trustworthy,
        )
        self._write(
            self.stage_dir(StageId.LVS) / "lvs_summary.json",
            __import__("json").dumps(res.to_dict(), indent=2),
        )
        if res.clean:
            return passed(StageId.LVS, res.summary(), checked_gds_sha256=gds.sha256)
        cls = self._classify_lvs(res)
        return failed(
            StageId.LVS, cls, res.summary(), evidence=res.digest(),
            escalate=cls is FailureClass.LVS_LIBRARY,
            checked_gds_sha256=gds.sha256,
        )

    @staticmethod
    def _classify_lvs(res: "klayout_lvs.LVSResult") -> FailureClass:
        """Triage by the shape of the mismatch, not its name (review 9.4)."""
        msgs = res.message_counts
        if msgs:
            worst, count = max(msgs.items(), key=lambda kv: kv[1])
            # One message dominating across many instances points at the cell
            # library rather than at this design's routing.
            if count > 50 and res.xref_circuits and count >= res.xref_circuits:
                return FailureClass.LVS_LIBRARY
        if res.xref_circuits == 0:
            return FailureClass.LVS_STRUCTURAL
        return FailureClass.LVS_PHYSICAL

    # ---- one stage attempt ----------------------------------------------

    def _execute(self, spec: StageSpec) -> StageOutcome:
        # Tests and embedders may replace the invoker after construction.
        self.klayout.invoker = self.invoker
        ctx = self._context(spec)
        sd = ctx.work_dir
        script: Path | None = None

        # Nothing this attempt produces may be inherited from the last one.
        #
        # Rollback retired stale files, but a *same-stage* retry never called
        # it, so an attempt that exited cleanly while writing nothing left the
        # previous attempt's outputs sitting exactly where the new ones were
        # expected. They were then registered, hashed and certified as this
        # attempt's work, under this attempt's changed IR. Retiring the
        # declared outputs before every invocation is what makes that
        # impossible, and failing to retire one is a hard error rather than a
        # warning -- a stale artifact that cannot be moved is precisely the
        # situation that must not proceed.
        self._retire_expected_outputs(spec, ctx)

        if spec.ir_section and spec.id in self._renderable():
            text = render(spec.id, self.ir, ctx)
            ext = ".py" if spec.id is StageId.GDSOUT else (
                ".ys" if spec.tool is Tool.YOSYS else ".tcl"
            )
            script = self._write(sd / f"{spec.id.value}{ext}", text)
            self._snapshot_attempt(
                spec, ctx, max(1, self.state.stage(spec.id).attempts), text, ext)

        if spec.id is StageId.SDC:
            # Rendered directly to its artifact; there is no tool to invoke.
            sdc = Path(ctx.out("sdc"))
            self._write(sdc, render(StageId.SDC, self.ir, ctx))
            v = self._judge_sdc(sdc)
            return StageOutcome(spec.id, v, None, {"sdc": sdc})

        if spec.id is StageId.SIM:
            return self._run_simulations(spec, ctx)
        if spec.id is StageId.LVS:
            return self._run_lvs(spec, ctx)

        argv = self._argv(spec, script, ctx)
        if spec.tool is Tool.KLAYOUT:
            argv = self.klayout.effective_argv(argv, sd)
        if not argv:
            return StageOutcome(spec.id, passed(spec.id, f"{spec.id}: nothing to run"), None, ctx.outputs)

        attempt_no = max(1, self.state.stage(spec.id).attempts)
        self.log.tool_run(str(spec.id), attempt_no, argv)
        log_path = sd / f"attempt_{attempt_no:02d}.log"
        try:
            run = self.invoker.run(
                spec.tool, argv, cwd=sd,
                timeout_s=self.cfg.timeout_for(spec.id), log_path=log_path,
                env=self.klayout.effective_env() if spec.tool is Tool.KLAYOUT else None,
            )
        except TypeError:
            # Invokers from tests may not accept log_path.
            run = self.invoker.run(
                spec.tool, argv, cwd=sd, timeout_s=self.cfg.timeout_for(spec.id)
            )
        if not log_path.is_file():
            self._write(log_path, run.combined)
        verdict = self._judge(spec, run, ctx)
        if spec.tool is Tool.KLAYOUT and classify_runtime_failure(run) is not None:
            runtime = classify_runtime_failure(run)
            verdict = failed(
                spec.id, FailureClass.TOOL_RUNTIME,
                f"KLayout crashed ({runtime.stack_signature or runtime.failure_class.value}, exit {run.returncode})",
                evidence=run.tail(4000),
                runtime_class=runtime.failure_class.value,
                stack_signature=runtime.stack_signature or "",
            )
        return StageOutcome(spec.id, verdict, run, ctx.outputs)

    def _run_lvs(self, spec: StageSpec, ctx: RenderContext) -> StageOutcome:
        """Build the SPICE reference netlist, then compare it to the layout.

        The runset reads SPICE only, and its subcircuit calls are positional
        with the PDK's own pin order -- which matches neither the Verilog view
        of a cell nor its power-pin view. So the reference is generated here
        from the routed netlist rather than handing the tool a Verilog file it
        will try to parse as SPICE.
        """
        from .spice import SUBSTRATE_NET, SpiceConversionError, write_spice

        sd = ctx.work_dir
        gds = self.ledger.get("final_gds")
        gds.assert_unchanged()

        netlist_key = "routed_netlist" if "routed_netlist" in self.ledger else "netlist"
        try:
            reference = write_spice(
                self.ledger.get(netlist_key).path,
                self.cfg.top,
                self.cfg.pdk.cell_cdl_path,
                sd / f"{self.cfg.top}.reference.spice",
                model_prefix=self.cfg.pdk.device_model_prefix,
                substrate_net=SUBSTRATE_NET,
            )
        except SpiceConversionError as exc:
            return StageOutcome(
                spec.id,
                failed(spec.id, FailureClass.LVS_STRUCTURAL,
                       f"could not build the LVS reference netlist: {exc}",
                       evidence=str(exc)),
                None, {},
            )
        # Bind the generated reference itself. `lvs_reference` was added to
        # BOUND_ARTIFACTS so "which schematic was this layout compared with"
        # is part of the candidate, but nothing registered it, so it appeared
        # in the manifest with no content identity at all.
        self.ledger.register("lvs_reference", reference, stage=str(spec.id))
        self.log.note(
            f"built the LVS reference from {netlist_key}", stage=str(spec.id),
            reference=str(reference),
        )

        s = self.ir.section("lvs")
        argv = [
            "klayout", "-b", "-r", str(self.cfg.pdk.lvs_deck_path),
            "-rd", f"input={gds.path}",
            "-rd", f"schematic={reference}",
            "-rd", f"target_netlist={ctx.out('extracted_netlist')}",
            "-rd", f"report={ctx.out('lvs_report')}",
            "-rd", f"thr={s['threads']}",
            # Give the substrate its own name, matching the reference netlist's
            # explicit substrate node so the bulk terminals are actually
            # compared.
            #
            # This deliberately does NOT reuse the ground net's name. The deck
            # models the substrate as an empty layer promoted to a global net,
            # and `connect_implicit("*")` joins same-named parts by name alone,
            # "without need for a physical connection". Calling the substrate
            # VGND therefore name-joined it to every cell's labelled ground
            # metal and left a must-connect obligation no layout can discharge,
            # since the substrate node has no geometry. That was P0-07.
            "-rd", f"lvs_sub={SUBSTRATE_NET}",
        ]
        argv = self.klayout.effective_argv(argv, sd)
        self.log.tool_run(str(spec.id), max(1, self.state.stage(spec.id).attempts), argv)
        log_path = sd / f"attempt_{max(1, self.state.stage(spec.id).attempts):02d}.log"
        run = self.invoker.run(
            Tool.KLAYOUT, argv, cwd=sd,
            timeout_s=self.cfg.timeout_for(spec.id), log_path=log_path,
            env=self.klayout.effective_env(),
        )
        if not log_path.is_file():
            self._write(log_path, run.combined)
        runtime = classify_runtime_failure(run)
        verdict = self._judge_lvs(run, ctx) if runtime is None else failed(
            spec.id, FailureClass.TOOL_RUNTIME,
            f"KLayout crashed ({runtime.stack_signature or runtime.failure_class.value}, exit {run.returncode})",
            evidence=run.tail(4000), runtime_class=runtime.failure_class.value,
            stack_signature=runtime.stack_signature or "",
        )
        return StageOutcome(spec.id, verdict, run, ctx.outputs)

    def _run_simulations(self, spec: StageSpec, ctx: RenderContext) -> StageOutcome:
        """Compile and *run* every testbench, then report all of them.

        iverilog only compiles; nothing is verified until vvp executes the
        result. A stage that stopped at compilation would be a syntax check
        wearing a simulation's name -- exactly the confusion review 4.5 warns
        about.

        Every testbench is attempted even after one fails, because "3 of 6
        passed, and here is what went wrong with the other 3" is far more
        useful than stopping at the first problem.
        """
        sd = ctx.work_dir
        benches = self._testbenches()
        authorities = {tb: self._testbench_authority(tb) for tb in benches}
        timeout = int(self.ir.get("sim", "timeout_s"))
        plusargs = [str(a) for a in self.ir.get("sim", "plusargs")]

        passes: list[str] = []
        #: Ran to completion but never said whether it passed.
        unproven: list[str] = []
        failures: list[tuple[str, str, str]] = []  # name, why, evidence

        for tb in benches:
            top = tb.stem
            vvp = sd / f"{top}.vvp"
            build = self.invoker.run(
                Tool.IVERILOG,
                ["iverilog", "-g2012", "-o", str(vvp), "-s", top,
                 str(tb), *[str(p) for p in self.facts.sources]],
                cwd=sd, timeout_s=timeout,
            )
            self._write(sd / f"{top}.compile.log", build.combined)
            if build.returncode != 0:
                failures.append((tb.name, "failed to compile", build.tail(1200)))
                continue

            sim = self.invoker.run(
                Tool.IVERILOG, ["vvp", str(vvp), *plusargs], cwd=sd, timeout_s=timeout,
            )
            self._write(sd / f"{top}.sim.log", sim.combined)
            v = check_sim(sim, testbench=tb.name)
            if v.blocks:
                failures.append((tb.name, v.summary, v.evidence[:1200]))
            elif v.kind is VerdictKind.PASS:
                passes.append(tb.name)
            else:
                # Ran clean but printed no verdict: check_sim graded it below
                # target because it proves the design elaborates, not that it
                # is correct. Lumping it in with `passes` discarded that
                # distinction and the stage announced "all testbenches passed".
                unproven.append(tb.name)

        if not benches:
            # Fail closed. This used to return a pass, so a design with no
            # testbench at all reported the simulation gate as satisfied.
            return StageOutcome(
                spec.id,
                failed(
                    spec.id, FailureClass.RTL_FUNCTIONAL,
                    "no testbench was found, so nothing about this design's "
                    "behaviour has been verified",
                    testbenches=0,
                ),
                None, {},
            )

        summary_path = self._write(
            sd / "sim_result.txt",
            "\n".join(
                [f"PASS  {n}" for n in passes]
                + [f"FAIL  {n}: {why}" for n, why, _ in failures]
            ) + "\n",
        )
        metrics = {
            "testbenches": len(benches),
            "passed": len(passes),
            "failed": len(failures),
            "unproven": len(unproven),
            "failing": [n for n, _, _ in failures],
            "not_self_checking": unproven,
            "authoritative_testbenches": [
                tb.name for tb in benches if authorities[tb] == "authoritative"
            ],
            "implementation_derived_testbenches": [
                tb.name for tb in benches
                if authorities[tb] == "implementation_derived"
            ],
            "authoritative_passed": sum(
                name in passes and authorities[tb] == "authoritative"
                for tb in benches for name in [tb.name]
            ),
        }

        if failures:
            detail = "\n\n".join(
                f"--- {n}: {why} ---\n{ev}" for n, why, ev in failures
            )
            return StageOutcome(
                spec.id,
                failed(
                    spec.id, FailureClass.RTL_FUNCTIONAL,
                    f"{len(failures)} of {len(benches)} testbench(es) failed: "
                    + ", ".join(n for n, _, _ in failures),
                    evidence=detail[:6000], escalate=True, **metrics,
                ),
                None, {},
            )
        if unproven:
            # Not a failure -- nothing went wrong -- but not a proof either, so
            # the run continues and signoff refuses to certify on it.
            return StageOutcome(
                spec.id,
                qor_low(
                    spec.id,
                    f"{len(unproven)} of {len(benches)} testbench(es) ran "
                    "without reporting a result ("
                    + ", ".join(unproven[:5])
                    + "); they are not self-checking, so they show the design "
                    "elaborates and runs, not that it behaves correctly",
                    evidence="\n".join(unproven)[:2000], **metrics,
                ),
                None, {"sim_result": summary_path},
            )
        return StageOutcome(
            spec.id,
            passed(spec.id, f"all {len(passes)} testbench(es) passed", **metrics),
            None, {"sim_result": summary_path},
        )

    @staticmethod
    def _renderable() -> set[StageId]:
        return {
            StageId.SYNTHESIS, StageId.LEC_SYNTH, StageId.LEC_ROUTE,
            StageId.STA_PRE, StageId.STA_POSTCTS, StageId.STA_SIGNOFF,
            StageId.FLOORPLAN, StageId.PDN, StageId.PLACEMENT, StageId.CTS,
            StageId.ROUTING, StageId.EXTRACTION, StageId.ANTENNA, StageId.GDSOUT,
        }

    def _judge_sdc(self, sdc: Path) -> Verdict:
        """Semantic completeness, not just syntax (review 4.8)."""
        text = sdc.read_text(encoding="utf-8")
        declared = text.count("create_clock")
        want = max(1, self.facts.clock_domains)
        if declared < want:
            return failed(
                StageId.SDC, FailureClass.SDC,
                f"SDC declares {declared} clock(s) but characterization found "
                f"{self.facts.clock_domains} clock domain(s); the unconstrained "
                "domains would report falsely clean timing",
                evidence=text[:1500],
            )
        return passed(StageId.SDC, f"SDC valid: {declared} clock(s) constrained",
                      clocks=declared)

    # ---- artifact registration ------------------------------------------

    def _register(self, spec: StageSpec, outputs: dict[str, Path]) -> None:
        for key, path in outputs.items():
            p = Path(path)
            if not p.exists() or (p.is_file() and p.stat().st_size == 0):
                continue
            meta = {"top_cell": self.cfg.top} if key == "final_gds" else None
            art = self.ledger.register(key, p, stage=spec.id.value, meta=meta)
            self.log.artifact(str(spec.id), key, str(p), art.sha256)

    # ---- diagnosis + remediation ----------------------------------------

    def _diagnose(self, spec: StageSpec, verdict: Verdict, attempt: int,
                  run: ToolRun | None = None) -> StageId | None:
        """Ask the agent, validate the proposal, apply it. Returns where to resume."""
        st = self.state.stage(spec.id)
        entry = lookup(verdict.failure) if verdict.failure else None

        # Deterministic intelligence precedes model diagnosis.  A catalog hit
        # is only metadata; only a curated recipe can execute a repair.
        known_target = self._known_repair(spec, verdict, attempt)
        if known_target is not None:
            return known_target
        runtime_target = self._runtime_repair(spec, verdict, attempt, run)
        if runtime_target is not None:
            return runtime_target

        if verdict.escalate or (entry and entry.resolution is Resolution.ESCALATE):
            raise Escalation(
                spec.id,
                f"{verdict.failure} is not autonomously resolvable: "
                f"{entry.notes if entry else ''}".strip(),
                verdict.evidence,
            )

        self.budget.spend(what=f"{spec.id} diagnosis")
        agent_evidence = verdict.evidence
        if verdict.failure is FailureClass.RTL_SYNTAX:
            excerpts = []
            for source in sorted(self.work_rtl.rglob("*")):
                if source.suffix not in {".v", ".sv", ".vh", ".svh"} or not source.is_file():
                    continue
                excerpts.append(
                    f"--- {source.relative_to(self.work_rtl)} ---\n"
                    + source.read_text(encoding="utf-8", errors="replace")[:4000]
                )
            if excerpts:
                agent_evidence += "\n\nWorking RTL excerpts:\n" + "\n".join(excerpts)[:6000]
        req = DiagnosisRequest(
            stage=spec.id,
            failure_class_hint=verdict.failure,
            summary=verdict.summary,
            evidence=agent_evidence,
            metrics=verdict.metrics,
            ir_section=spec.ir_section,
            # Only the values for fields the model is actually allowed to
            # write, derived from the same authorization structure as the
            # action space. Never `ir.section(...)` -- that shows frozen and
            # no-op fields the validator will reject (N1).
            current_config=authorized_current_values(self.ir, verdict.failure),
            pdk_context=self.cfg.pdk.prompt_context(),
            attempt=attempt,
            retry_limit=self.cfg.retry_limit_for(spec.id),
            action_space=authorized_action_space(verdict.failure),
            tried_configs=self._tried.get(spec.id, []),
            history=self._history[-12:],
        )
        self.log.fix_attempt(str(spec.id), attempt, verdict.summary)
        try:
            resp = self.agent.diagnose(req)
        except AgentError as exc:
            record = {
                "failure_domain": "agent",
                "stage": spec.id.value,
                "attempt": attempt,
                "agent_error": str(exc),
                "eda_failure": verdict.to_dict(),
            }
            self._write(
                self.stage_dir(spec.id) / f"attempt_{attempt:02d}_agent_failure.json",
                __import__("json").dumps(record, indent=2, default=str),
            )
            self.log.event(
                "agent_failure", stage=str(spec.id), attempt=attempt,
                message=f"agent response failed; EDA failure remains {verdict.summary}",
                agent_error=str(exc), eda_failure_class=(
                    verdict.failure.value if verdict.failure else None),
            )
            raise AgentError(
                f"agent response failure after deterministic EDA failure "
                f"{verdict.summary!r}: {exc}"
            ) from exc
        st.api_calls += 1
        self.log.api_call(
            str(spec.id), attempt, "diagnose", resp.model,
            input_tokens=resp.input_tokens, output_tokens=resp.output_tokens,
            failure_class=resp.diagnosis.failure.value,
            confidence=resp.diagnosis.confidence,
        )
        # The literal string "<prompt recorded by agent>" used to go here,
        # which is not evidence: a reviewer could not establish what the model
        # actually saw. Agents that call a model now return a CallAudit with
        # hashes computed at call time -- before any remediation outcome is
        # known, so it cannot be retrofitted.
        audit = getattr(resp, "audit", None)
        write_audit(
            self.stage_dir(spec.id), attempt,
            prompt=(audit.user_prompt if audit else "<no audit: scripted agent>"),
            response=resp.raw,
            meta={
                "diagnosis": resp.diagnosis.to_dict(),
                "model": resp.model,
                "call_audit": audit.to_dict() if audit else None,
            },
        )
        if audit is not None:
            self._call_audits.append(audit)

        diag = resp.diagnosis
        self.state.stage(spec.id).history.append(
            {"attempt": attempt, "diagnosis": diag.to_dict()}
        )

        if diag.escalated:
            raise Escalation(spec.id, f"agent escalated: {diag.reasoning}", verdict.evidence)

        # Reviewed against the deterministic class, not the model's.
        review_diagnosis(diag, policy_failure=verdict.failure)
        # And the delta may only touch sections this failure authorises, so an
        # unrelated change cannot ride along with a plausible one.
        review_delta_scope(diag.config_delta, verdict.failure)

        # The rollback target is decided by the deterministic taxonomy, from
        # the deterministic failure class -- not from the model's.
        #
        # This used to be `diag.implicated_stage or responsible_stage(...)`,
        # which made the model's choice authoritative and let it both
        # reclassify the failure and name any stage at all, including one
        # *after* the failure. Naming a downstream stage skips the stages in
        # between, so verification would run against artifacts that were never
        # regenerated. The model's suggestion is now a hint that may only
        # narrow the rollback within the window policy already allows.
        policy_target = responsible_stage(
            verdict.failure, escalated=diag.escalated, failing_stage=spec.id
        )
        if policy_target is None:
            raise Escalation(
                spec.id,
                f"{verdict.failure} has no responsible design stage "
                "(environment or library problem)",
                verdict.evidence,
            )
        target = policy_target
        proposed = diag.implicated_stage
        if proposed is not None and proposed != policy_target:
            # Upstream is allowed: rolling back further only means more work
            # and a fuller re-verification, so it cannot manufacture a pass.
            # Forward is refused outright -- resuming after the stage that just
            # failed would leave every stage in between unre-run, and the
            # signoff gates would then grade artifacts nobody regenerated.
            if stage_index(proposed) <= stage_index(spec.id):
                target = proposed
                self.log.note(
                    f"diagnosis moved the rollback target from {policy_target} "
                    f"to {proposed}", stage=str(spec.id),
                )
            else:
                self.log.warn(
                    f"ignoring proposed rollback to {proposed}: it is after the "
                    f"failing stage {spec.id}, which would skip the stages "
                    f"between them; using {policy_target}",
                    stage=str(spec.id),
                )

        # The rollback has to follow the delta.
        #
        # Changing floorplan utilisation while re-running only routing leaves
        # every stage in between describing a floorplan that no longer exists,
        # and the release candidate then binds evidence nobody regenerated. So
        # the earliest stage any changed section can influence becomes a floor
        # on how far back the run goes.
        touched = earliest_affected_stage(diag.config_delta)
        if touched is not None and stage_index(touched) < stage_index(target):
            self.log.note(
                f"rollback target moved from {target} to {touched}: the "
                f"accepted delta changes {', '.join(sorted(diag.config_delta))}, "
                f"which {touched} is the earliest stage to consume",
                stage=str(spec.id),
            )
            target = touched

        if diag.config_delta or diag.recommended_actions:
            rtl_sha256_before_repair = (
                self.ledger.get("rtl_dir").sha256
                if "rtl_dir" in self.ledger else ""
            )
            try:
                if diag.recommended_actions:
                    planned_actions = tuple(
                        RepairAction(
                            ActionType(str(action["action_type"])),
                            str(action["target"]), action.get("value"),
                            str(action.get("reason") or "model-planned bounded repair"),
                            str(action.get("expected_effect") or diag.reasoning),
                        )
                        for action in diag.recommended_actions
                    )
                else:
                    planned_actions = tuple(
                        RepairAction(
                            ActionType.SET_IR_VALUE, f"{section}.{field}", value,
                            reason="model-planned bounded configuration repair",
                            expected_effect=diag.reasoning,
                        )
                        for section, values in diag.config_delta.items()
                        for field, value in values.items()
                    )
                repair_result = self.repair_executor.execute(RepairPlan(
                    failure_fingerprint=str(
                        verdict.metrics.get("attempt_fingerprint") or
                        __import__("hashlib").sha256(verdict.evidence.encode()).hexdigest()),
                    actions=planned_actions, summary=diag.reasoning,
                ))
            except (SchemaViolation, SafetyViolation, ValueError) as exc:
                self.log.error(f"rejected out-of-schema proposal: {exc}", stage=str(spec.id))
                raise
            if repair_result.rollback_stage is not None:
                target = repair_result.rollback_stage
            # A same-stage lint retry does not enter _rollback(), so refresh
            # the directory artifact here. Otherwise the scientific no-op
            # guard sees the pre-patch RTL hash and correctly refuses what
            # appears to be an identical retry even though trusted code did
            # change the working copy.
            if repair_result.changed_files:
                self.ledger.register(
                    "rtl_dir", self.work_rtl, stage="repair", allow_dir=True
                )
            st.configs_generated += 1
            self.log.config_generated(
                str(spec.id), attempt,
                sorted(diag.config_delta) or [a.action_type.value for a in planned_actions],
                delta=diag.config_delta,
            )
            # One source of truth for "what was accepted and applied".
            #
            # The benchmark used to read this back from its own
            # `--scripted-delta` argument, which is the answer it was handed
            # rather than what the system did -- and is unavailable in live
            # mode. This records the delta only after `review_diagnosis`,
            # `review_delta_scope` and `apply_delta` have all accepted it.
            self._accepted.append({
                "stage": spec.id.value,
                "attempt": attempt,
                "delta": {s: dict(f) for s, f in diag.config_delta.items()},
                "deterministic_failure_class": (
                    verdict.failure.value if verdict.failure else None),
                "safety_result": "accepted",
                "rollback_target": target.value,
                "repair_actions": repair_result.actions,
                "rtl_sha256_before_repair": rtl_sha256_before_repair,
                "previous_values": repair_result.previous_values,
                "new_values": repair_result.new_values,
            })
        return target

    def _known_repair(self, spec: StageSpec, verdict: Verdict,
                      attempt: int) -> StageId | None:
        messages = match_openroad_messages(verdict.evidence)
        if not messages:
            return None
        message = next((m for m in messages if m.severity in {"ERROR", "CRITICAL"}), messages[0])
        floorplan = self.ledger.get("floorplan_def").path if "floorplan_def" in self.ledger else None
        context = pdn_context(
            verdict.evidence, facts=self.facts.to_dict(), history=self._history,
            ir=self.ir, floorplan_def=floorplan,
        ) if message.canonical_id == "PDN-0185" else {}
        knowledge = lookup_known_fix(message, context)
        self.log.note(
            f"recognized OpenROAD {message.canonical_id}", stage=str(spec.id),
            known_error_id=message.canonical_id, catalog_severity=message.severity,
            catalog_source=f"{message.source_file}:{message.source_line}",
            curated_repair=knowledge is not None,
        )
        if knowledge is None:
            return None

        self.log.note(knowledge.design_context_explanation, stage=str(spec.id),
                      event_detail="design_context", **knowledge.evidence)
        if not knowledge.proposed_delta:
            return None
        policy = self.cfg.repair_policy
        choice = "auto" if policy == "auto" else "manual"
        if policy == "ask" and self.interactive:
            choice = self._ask_known_repair(spec, knowledge)
        elif policy == "ask":
            self.log.warn("repair policy ask resolved to manual because stdin is not a TTY",
                          stage=str(spec.id))
        self.log.event(
            "repair_decision", stage=str(spec.id), attempt=attempt,
            message=f"repair choice: {choice}", known_error_id=message.canonical_id,
            repair_policy=policy, choice=choice,
        )
        self.state.stage(spec.id).history.append({
            "attempt": attempt, "known_error_id": message.canonical_id,
            "repair_choice": choice, "evidence": knowledge.evidence,
        })
        self.state.save()
        if choice == "abort":
            raise Escalation(spec.id, f"user aborted repair of {message.canonical_id}", verdict.evidence)
        if choice == "manual":
            raise Escalation(
                spec.id,
                f"{message.canonical_id} has a safe executable repair, but repair policy is manual",
                knowledge.design_context_explanation + "\n\nProposed: " + str(knowledge.proposed_delta),
            )

        actions = tuple(
            RepairAction(ActionType.SET_IR_VALUE, f"{section}.{field}", value,
                         reason="curated PDN-0185 geometry repair",
                         expected_effect="make the VDD/VSS strap geometry fit")
            for section, values in knowledge.proposed_delta.items()
            for field, value in values.items()
        )
        import hashlib
        failure_fp = str(verdict.metrics.get("attempt_fingerprint") or
                         hashlib.sha256(verdict.evidence.encode()).hexdigest())
        plan = RepairPlan(failure_fp, actions,
                          known_error_id=message.canonical_id,
                          summary=knowledge.title)
        result = self.repair_executor.execute(plan)
        for key, new in result.new_values.items():
            self.log.note(
                f"{key} {result.previous_values.get(key)!r} -> {new!r}",
                stage="repair", known_error_id=message.canonical_id,
            )
        record = {
            "stage": spec.id.value, "attempt": attempt,
            "known_error_id": message.canonical_id,
            "failure_fingerprint": plan.failure_fingerprint,
            "actions": result.actions, "previous_values": result.previous_values,
            "new_values": result.new_values,
            "rollback_target": result.rollback_stage.value if result.rollback_stage else None,
            "rollback_reason": result.rollback_reason,
            "safety_result": "accepted", "deterministic_failure_class": verdict.failure.value,
            "before_metrics": dict(verdict.metrics),
            "rtl_sha256_before_repair": self.ledger.get("rtl_dir").sha256,
            "failure_geometry_evidence": dict(knowledge.evidence),
        }
        self._accepted.append(record)
        self.state.stage(spec.id).history.append({"repair": record})
        self.state.stage(spec.id).configs_generated += 1
        self.state.save()
        return result.rollback_stage

    def _ask_known_repair(self, spec: StageSpec, knowledge: Any) -> str:
        while True:
            print(f"\n[{spec.id.value}] Known OpenROAD failure: {knowledge.key}")
            print(f"\nWhat happened:\n  {knowledge.design_context_explanation}")
            print("\nRecommended repair:")
            for section, values in knowledge.proposed_delta.items():
                for field, value in values.items():
                    print(f"  {section}.{field} -> {value}")
            print(f"\nEarliest stage that must be rerun: {knowledge.earliest_rollback_stage.value}")
            print("\nChoose:\n  [1] Let rtl2gdsagi fix it\n  [2] I will fix it manually"
                  "\n  [3] Show technical evidence\n  [4] Abort")
            answer = str(self.input_fn("choice> ")).strip()
            if answer == "1":
                return "auto"
            if answer == "2":
                return "manual"
            if answer == "3":
                print(__import__("json").dumps(knowledge.evidence, indent=2, default=str))
                continue
            if answer == "4":
                return "abort"
            print("enter 1, 2, 3, or 4")

    def _runtime_repair(self, spec: StageSpec, verdict: Verdict, attempt: int,
                        run: ToolRun | None) -> StageId | None:
        if verdict.failure is not FailureClass.TOOL_RUNTIME or spec.tool is not Tool.KLAYOUT or run is None:
            return None
        failure = classify_runtime_failure(run)
        if failure is None:
            return None
        self.log.warn(
            f"KLayout crashed with exit {failure.exit_status}; stack signature: "
            f"{failure.stack_signature or 'unknown'}", stage=str(spec.id),
            runtime_class=failure.failure_class.value,
            environment_fingerprint=failure.environment_fingerprint,
        )
        self.log.note("running minimal KLayout health probe", stage="repair")
        probes = [self.klayout.probe(self.klayout.backend)]
        self.log.note(
            f"{self.klayout.backend.name} backend health probe "
            f"{'passed' if probes[0].healthy else 'failed'}: {probes[0].reason}",
            stage="repair", **probes[0].to_dict(),
        )
        if probes[0].healthy and failure.stack_signature != "SaltDownloadManager":
            return None
        for candidate in self.klayout.repair_candidates():
            if candidate.name == self.klayout.backend.name:
                continue
            probe = self.klayout.probe(candidate)
            probes.append(probe)
            self.log.note(
                f"{candidate.name} backend health probe "
                f"{'passed' if probe.healthy else 'failed'}: {probe.reason}",
                stage="repair", **probe.to_dict(),
            )
            if not probe.healthy:
                continue
            action = RepairAction(
                ActionType.SELECT_TOOL_BACKEND, "klayout", candidate.name,
                reason=f"native KLayout is unhealthy ({failure.stack_signature or failure.failure_class.value})",
                expected_effect="run stream-out and signoff checks in a health-probed runtime",
            )
            import hashlib
            failure_fp = str(verdict.metrics.get("attempt_fingerprint") or
                             hashlib.sha256(verdict.evidence.encode()).hexdigest())
            result = self.repair_executor.execute(RepairPlan(
                failure_fp, (action,),
                summary="KLayout runtime fallback",
            ))
            record = {
                "stage": spec.id.value, "attempt": attempt,
                "failure_fingerprint": failure_fp,
                "runtime_failure": {"class": failure.failure_class.value,
                                    "stack_signature": failure.stack_signature,
                                    "exit_status": failure.exit_status,
                                    "signal": failure.signal,
                                    "executable": failure.executable,
                                    "version": failure.version,
                                    "argv": list(failure.argv),
                                    "environment_fingerprint": failure.environment_fingerprint},
                "health_probes": [p.to_dict() for p in probes],
                "rtl_sha256_before_repair": self.ledger.get("rtl_dir").sha256,
                "actions": result.actions, "previous_values": result.previous_values,
                "new_values": result.new_values,
                "rollback_target": result.rollback_stage.value,
                "rollback_reason": result.rollback_reason,
                "safety_result": "accepted",
            }
            self._accepted.append(record)
            self.state.stage(spec.id).history.append({"repair": record})
            self.state.save()
            self.log.note(f"selected validated KLayout backend {candidate.name}; retrying from gdsout",
                          stage="repair")
            return result.rollback_stage
        raise Escalation(
            spec.id,
            "KLayout runtime repair exhausted safe installed/isolated/container backends; "
            "installing or upgrading system software requires user action",
            __import__("json").dumps([p.to_dict() for p in probes], indent=2),
        )

    def _rollback(self, to_stage: StageId, why: str) -> None:
        """Re-run from ``to_stage``, leaving nothing downstream that looks current.

        Rebuilding the ledger from checkpoints already prevents a downstream
        artifact from being *selected* as an input. Three things were still
        surviving a rollback, though, and each of them could make a later
        signoff describe work that no longer exists:

        * stages with no checkpoint -- a SKIPPED or FAILED stage keeps its
          status, because ``invalidate_from`` only knows about stages it
          checkpointed;
        * ``self._history`` -- signoff reads it to cross-check which GDS each
          gate verified, so evidence from a superseded attempt stayed in the
          record;
        * the files themselves -- a re-run whose tool exits 0 without writing
          would find last attempt's output sitting exactly where the new one
          was expected.

        The files are kept for audit under ``superseded/`` rather than deleted,
        but they are moved out of the way so nothing can consume them as
        current.
        """
        restore, killed = self.store.rollback_to(to_stage)
        self.ledger = ArtifactLedger()
        # prepare()-time artifacts survive a rollback: the design and its
        # characterization are what the run is *about*, and rolling back a
        # physical stage does not change them. They are re-registered because
        # the ledger is rebuilt from stage checkpoints, which never held them.
        self.ledger.register("rtl_dir", self.work_rtl, stage="prepare", allow_dir=True)
        self._register_testbenches("prepare")
        facts = self.stage_dir(StageId.CHARACTERIZE) / "facts.json"
        if facts.is_file():
            self.ledger.register("design_facts", facts, stage="characterize")
        self.store.restore_artifacts(self.ledger, upto=to_stage)

        # Everything causally downstream, whether or not it left a checkpoint.
        first = stage_index(to_stage)
        invalidated: list[StageId] = []
        for sid in STAGE_ORDER[first:]:
            if sid is StageId.SIGNOFF:
                continue
            st = self.state.stage(sid)
            if st.status is not StageStatus.PENDING or st.attempts:
                invalidated.append(sid)
            self.state.stages[sid] = StageState(status=StageStatus.PENDING)
            self._retire_stage_outputs(sid)

        # Evidence from superseded attempts is not evidence about what the run
        # now holds.
        self._history = [
            h for h in self._history
            if stage_index(h["stage"]) < first
        ]
        for sid in list(self._evidence):
            if stage_index(sid) >= first:
                del self._evidence[sid]

        self.log.warn(
            f"rolling back to {to_stage}: {why}",
            invalidated=[s.value for s in invalidated],
            checkpoints_killed=[s.value for s in killed],
            restored_from=restore.stage.value if restore else None,
        )
        self.state.save()

    def _retire_expected_outputs(self, spec: StageSpec, ctx: RenderContext) -> None:
        """Move this stage's declared outputs aside before an attempt runs.

        Only the declared artifacts are moved; logs and rendered scripts stay
        put so the attempt history remains readable in place.
        """
        stale = [Path(p) for p in ctx.outputs.values() if Path(p).exists()]
        if not stale:
            return
        attic = ctx.work_dir / "superseded"
        attic.mkdir(exist_ok=True)
        slot = attic / f"{len(list(attic.iterdir())):03d}"
        slot.mkdir()
        for path in stale:
            try:
                shutil.move(str(path), str(slot / path.name))
            except OSError as exc:
                raise Escalation(
                    spec.id,
                    f"could not retire the previous attempt's {path.name}: "
                    f"{exc}. Refusing to run: if the old artifact survives and "
                    "this attempt does not overwrite it, the run would verify "
                    "and certify the previous attempt's output as this one's.",
                ) from exc
            if path.exists():  # pragma: no cover - defensive
                raise Escalation(
                    spec.id,
                    f"{path.name} still exists after being retired; refusing "
                    "to run an attempt that could inherit it",
                )
        self.log.note(
            f"retired {len(stale)} artifact(s) from the previous attempt",
            stage=str(spec.id), retired=[p.name for p in stale],
        )

    def _retire_stage_outputs(self, sid: StageId) -> None:
        """Move a stage's files aside so a re-run cannot inherit them."""
        sd = self.run_dir / "stages" / f"{stage_index(sid):02d}_{sid.value}"
        if not sd.is_dir():
            return
        live = [p for p in sd.iterdir() if p.name != "superseded"]
        if not live:
            return
        attic = sd / "superseded"
        attic.mkdir(exist_ok=True)
        slot = attic / f"{len(list(attic.iterdir())):03d}"
        slot.mkdir()
        for p in live:
            try:
                shutil.move(str(p), str(slot / p.name))
            except OSError as exc:  # pragma: no cover - filesystem edge case
                self.log.warn(
                    f"could not retire stale artifact {p.name}: {exc}",
                    stage=str(sid),
                )

    # ---- main loop -------------------------------------------------------

    def run(self) -> int:
        self.log.run_start(
            run_id=self.run_id, top=self.cfg.top, pdk=self.cfg.pdk.name,
            rtl=str(self.cfg.rtl_dir), model=self.cfg.model,
            budget=self.budget.total,
        )
        try:
            self.prepare()
            self._main_loop()
        except Escalation as exc:
            self._finish(RunStatus.FAILED, escalation=exc)
            return 3
        except BudgetExhausted as exc:
            self.log.error(str(exc))
            self._finish(RunStatus.FAILED, reason=str(exc))
            return 4
        except (SafetyViolation, SchemaViolation) as exc:
            self.log.error(f"safety boundary: {exc}")
            self._finish(RunStatus.FAILED, reason=str(exc))
            return 5
        except Rtl2GdsError as exc:
            self.log.error(str(exc))
            self._finish(RunStatus.FAILED, reason=str(exc))
            return 1
        self._finish(RunStatus.OK)
        return 0

    def _main_loop(self) -> None:
        start = stage_index(self.cfg.resume_from) if self.cfg.resume_from else 1
        i = max(1, start)  # 0 is characterize, done in prepare()

        while i < len(STAGE_ORDER):
            sid = STAGE_ORDER[i]
            spec = get_stage(sid)
            st = self.state.stage(sid)
            st.retry_limit = self.cfg.retry_limit_for(sid)

            if spec.id is StageId.SIGNOFF:
                self._signoff()
                i += 1
                continue

            if sid in self.cfg.skip_stages:
                st.status = StageStatus.SKIPPED
                st.last_error = "skipped at the user's request (--skip)"
                self.log.warn(
                    f"skipping {sid}: requested with --skip. Signoff will not "
                    "certify a run with a skipped gate.", stage=str(sid),
                )
                self.state.save()
                i += 1
                continue

            if spec.optional and not self._can_run(spec):
                st.status = StageStatus.SKIPPED
                why = self._skip_reason(spec)
                st.last_error = why
                self.log.warn(f"skipping {sid}: {why}", stage=str(sid))
                self.state.save()
                i += 1
                continue

            if spec.needs_pdk:
                self.cfg.pdk.validate(need=spec.pdk_requirements)

            st.status = StageStatus.RUNNING
            if st.started_at is None:
                st.started_at = time.time()
            self.log.stage_start(str(sid), gate=str(spec.gate), tool=str(spec.tool))

            outcome = self._attempt_stage(spec)

            if outcome is None:  # rolled back; i already moved
                i = stage_index(self._resume_at)
                continue

            st.status = StageStatus.OK
            st.last_verdict = outcome.verdict.kind.value
            st.ended_at = time.time()
            self.log.stage_end(str(sid), "ok", st.attempts, verdict=outcome.verdict.kind.value)
            self.state.save()
            i += 1

    def _can_run(self, spec: StageSpec) -> bool:
        if not self.invoker.available(spec.tool):
            return False
        if spec.id is StageId.SIM:
            return bool(self._testbenches())
        return True

    def _skip_reason(self, spec: StageSpec) -> str:
        if spec.tool is Tool.EQY:
            return (
                "no equivalence prover found. Yosys' built-in equiv_* flow cannot "
                "prove a mapped netlist against a real standard-cell library "
                "(the cells are blackboxes), so this gate needs `eqy`. Signoff "
                "will refuse to certify a run whose LEC was skipped rather than "
                "assume equivalence."
            )
        if spec.id is StageId.SIM:
            if not self.invoker.available(spec.tool):
                return "iverilog is not installed, so the RTL cannot be simulated"
            return "no testbench matched the configured pattern"
        return "prerequisites absent"

    def _register_testbenches(self, stage: str) -> None:
        """Bind the testbenches by content, not by path.

        P0-R2/R2.4: a simulation PASS used to bind `rtl_dir` and
        `design_facts` only. Editing a testbench after the fact left the
        recorded PASS untouched and still certifying, because nothing in the
        candidate or the evidence knew what had been simulated.
        """
        benches = self._testbenches()
        if not benches:
            return
        parent = benches[0].parent
        if all(b.parent == parent for b in benches):
            self.ledger.register("testbench_dir", parent, stage=stage,
                                 allow_dir=True)

    def _testbenches(self) -> list[Path]:
        """Find testbenches.

        Searched in the RTL tree first, then a sibling ``tb/`` directory --
        keeping testbenches next to but outside the synthesisable sources is a
        common layout, and characterization already excludes ``*_tb`` from the
        source list so they never reach synthesis.
        """
        pattern = str(self.ir.get("sim", "testbench_glob"))
        explicit = str(self.ir.get("sim", "testbench_dir")).strip()
        if explicit:
            d = Path(explicit).expanduser().resolve()
            if not d.is_dir():
                self.log.warn(
                    f"sim.testbench_dir {d} does not exist", stage=str(StageId.SIM)
                )
                return []
            return sorted(p.resolve() for p in d.rglob(pattern))
        found = sorted(p.resolve() for p in self.cfg.rtl_dir.rglob(pattern))
        if not found:
            for sibling in ("tb", "testbench", "test"):
                d = self.cfg.rtl_dir.parent / sibling
                if d.is_dir():
                    found = sorted(p.resolve() for p in d.rglob(pattern))
                    if found:
                        break
        return found

    @staticmethod
    def _testbench_authority(testbench: Path) -> str:
        """Classify explicit implementation-derived fixtures without guessing.

        A normal user testbench is authoritative by default. Generated or
        implementation-derived benches carry a sidecar named
        ``<stem>.meta.json`` with ``authority=implementation_derived``. A bad
        sidecar fails toward the weaker claim.
        """
        import json

        meta = testbench.with_name(f"{testbench.stem}.meta.json")
        if not meta.is_file():
            return "authoritative"
        try:
            authority = str(json.loads(meta.read_text()).get("authority", ""))
        except (OSError, ValueError, TypeError):
            return "implementation_derived"
        return (
            "authoritative" if authority == "authoritative"
            else "implementation_derived"
        )

    def _tool_identity(self, tool: Tool) -> str:
        """Strongest deterministic identity available for a tool.

        The OpenROAD/OpenSTA container is pinned by digest, which is exact.
        Native binaries report a version string, which is weaker -- two builds
        of the same version are indistinguishable here, and that residual gap
        is recorded rather than papered over.
        """
        from .manifest import probe_tool_versions

        if self.cfg.mock_tools:
            return {
                Tool.KLAYOUT: "KLayout 0.30.3 (fixture)",
                Tool.IVERILOG: "Icarus Verilog 12.0 (fixture)",
                Tool.EQY: "EQY 0.49 (fixture)",
                Tool.YOSYS: "Yosys 0.49 (fixture)",
            }.get(tool, f"container:{getattr(self.invoker, 'openlane_image', 'fixture')}")
        if tool is Tool.KLAYOUT and self.klayout.backend.name == "container":
            return f"KLayout container:{self.klayout.image}"
        if tool in (Tool.OPENROAD, Tool.OPENSTA):
            image = getattr(self.invoker, "openlane_image", "")
            return f"container:{image}" if image else "container:unknown"
        if not hasattr(self, "_tool_versions"):
            self._tool_versions = probe_tool_versions()
        return self._tool_versions.get(str(tool), "unknown")

    def _causal_env(self) -> dict[str, str]:
        """Identity that decides the outcome but lives outside the IR.

        Two attempts with identical knobs against different PDKs, corners or
        designs are different experiments, and the duplicate-attempt guard has
        to be able to tell them apart.
        """
        env = {
            "pdk": self.cfg.pdk.name,
            "pdk_root": str(self.cfg.pdk.root),
            "std_cell_lib": self.cfg.pdk.std_cell_lib,
            "corner": self.cfg.pdk.corner,
            "top": self.cfg.top,
        }
        # Design identity, via the characterization of the RTL actually copied
        # into this run -- it changes whenever the sources materially change.
        if "design_facts" in self.ledger:
            env["design_facts"] = self.ledger.get("design_facts").sha256
        env["klayout_backend"] = self.klayout.backend.name
        return env


    def _snapshot_attempt(self, spec: StageSpec, ctx: RenderContext,
                          attempt: int, text: str, ext: str) -> None:
        """Freeze what this attempt was actually configured with.

        The working script (`routing.tcl`) is rewritten on every retry, so
        after a successful recovery the surviving file describes the *remedy*,
        not the failure. Nothing else preserved it either: retirement moves
        declared outputs into `superseded/`, deliberately leaving scripts and
        logs alone.

        That left the benchmark unable to prove its own first causal link --
        "the failing attempt really ran with the injected value" -- and the
        substitute check (grepping the whole run log for a substring) proved
        only that some record somewhere mentioned the number. Both an
        immutable script copy and an exact structured record are written here,
        per attempt, before the tool is invoked.
        """
        import hashlib
        import json as _json

        sd = ctx.work_dir
        snap = self._write(sd / f"{spec.id.value}.attempt_{attempt:02d}{ext}",
                           text)
        record = {
            "stage": spec.id.value,
            "attempt": attempt,
            "attempt_id": f"{spec.id.value}#{attempt}",
            "ir_section": spec.ir_section,
            # The *effective* IR for this attempt: exact typed values, not a
            # rendering of them. The grader compares these, never substrings.
            "effective_ir": (dict(self.ir.section(spec.ir_section))
                             if spec.ir_section else {}),
            "script": snap.name,
            "script_sha256": hashlib.sha256(text.encode()).hexdigest(),
        }
        self._write(sd / f"attempt_{attempt:02d}_config.json",
                    _json.dumps(record, indent=2, default=str, sort_keys=True))
        self.log.note(
            f"{spec.id} attempt {attempt} configuration frozen",
            stage=str(spec.id), attempt=attempt,
            script_sha256=record["script_sha256"],
        )

    def _render_preview(self, spec: StageSpec) -> str:
        """The script this attempt would run, for fingerprinting only.

        Rendering is pure and deterministic by construction, so producing it
        twice costs nothing and changes nothing. Stages with no rendered script
        contribute an empty string and fall back to their config and inputs.
        """
        if spec.id not in self._renderable():
            return ""
        try:
            return render(spec.id, self.ir, self._context(spec))
        except Exception:
            # Never let fingerprinting break a run; a render that fails here
            # will fail again in _execute, where it is reported properly.
            return ""

    def _attempt_stage(self, spec: StageSpec) -> StageOutcome | None:
        """Run one stage to completion, retrying within its budget.

        Returns None when a rollback moved control to an earlier stage; the
        caller then resumes at ``self._resume_at``.
        """
        st = self.state.stage(spec.id)
        limit = self.cfg.retry_limit_for(spec.id)

        while True:
            inputs = {
                k: self.ledger.get(k) for k in spec.consumes if k in self.ledger
            }
            fp = fingerprint_attempt(
                self.ir, spec.ir_section, {k: a.sha256 for k, a in inputs.items()},
                script=self._render_preview(spec),
                causal_env=self._causal_env(),
            )
            if self.store.already_failed(fp):
                # The previous diagnosis produced no change that affects this
                # stage's inputs or knobs, so re-running would be identical.
                # Escalate instead of burning the remaining budget on a repeat.
                raise Escalation(
                    spec.id,
                    "the proposed remediation did not change this stage's "
                    f"configuration or inputs (fingerprint {fp[:12]}), so the "
                    "next attempt would be identical to the one that just "
                    "failed; stopping rather than looping",
                    st.last_detail,
                )

            st.attempts += 1
            try:
                outcome = self._execute(spec)
            except (KeyError, ArtifactError) as exc:
                # A required upstream artifact is absent -- e.g. --resume-from
                # jumped past the stage that produces it. Fail loudly rather
                # than letting a raw KeyError escape.
                raise Escalation(
                    spec.id,
                    f"required input is unavailable: {exc}. If you used "
                    "--resume-from, the earlier stages' artifacts are not in "
                    "this run directory.",
                ) from exc
            v = outcome.verdict
            self.log.result_check(
                str(spec.id), st.attempts, v.ok, v.summary, kind=v.kind.value,
                **{k: val for k, val in v.metrics.items() if isinstance(val, (int, float, str))},
            )
            self._history.append(
                {"stage": spec.id.value, "attempt": st.attempts, **v.to_dict()}
            )
            self._finalize_repair_attempt(spec, v, fp)

            if v.ok:
                self._register(spec, outcome.outputs)
                if spec.id in CERTIFYING_GATES:
                    self._evidence[spec.id] = evidence_for(
                        stage=spec.id,
                        verdict_kind=v.kind.value,
                        attempt=st.attempts,
                        ledger=self.ledger,
                        outputs=outcome.outputs,
                        report_key=_REPORT_KEY.get(spec.id),
                        tool=str(spec.tool),
                        tool_identity=self._tool_identity(spec.tool),
                        parser_contract=_PARSER_CONTRACT.get(spec.id, ""),
                        metrics=v.metrics,
                    )
                if v.kind is VerdictKind.QOR_BELOW_TARGET:
                    self.log.warn(f"QoR below target: {v.summary}", stage=str(spec.id))
                self.store.save(
                    spec.id, ir=self.ir, section=spec.ir_section, ledger=self.ledger,
                    produces=spec.produces, inputs=inputs, metrics=v.metrics,
                )
                st.last_error = ""
                return outcome

            # Failed a hard gate.
            v.metrics["attempt_fingerprint"] = fp
            self.store.record_failure(fp, v.summary)
            self._tried.setdefault(spec.id, []).append(
                {"config": self.ir.section(spec.ir_section) if spec.ir_section else {},
                 "result": v.summary}
            )
            st.last_error = v.summary
            st.last_detail = v.evidence[:8000]
            self.state.save()

            if st.attempts >= limit:
                target = (
                    responsible_stage(v.failure, escalated=True, failing_stage=spec.id)
                    if v.failure else None
                )
                if target is not None and stage_index(target) < stage_index(spec.id):
                    # Shallow retries are spent; escalate to the deeper stage
                    # rather than giving up (review 9.1 step 4).
                    self._rollback(target, f"{spec.id} exhausted {limit} attempts")
                    self._resume_at = target
                    return None
                raise Escalation(
                    spec.id,
                    f"exhausted {limit} attempt(s); last error: {v.summary}",
                    v.evidence,
                )

            target = self._diagnose(spec, v, st.attempts, outcome.run)
            if target != spec.id:
                self._rollback(target, f"diagnosed root cause of {spec.id} failure")
                self._resume_at = target
                return None

    def _finalize_repair_attempt(self, spec: StageSpec, verdict: Verdict,
                                 attempt_fingerprint: str) -> None:
        """Attach objective rerun evidence to the repair that caused it."""
        import hashlib

        for repair in reversed(self._accepted):
            if repair.get("stage") != spec.id.value or "result" in repair:
                continue
            script = self._render_preview(spec)
            repair.update({
                "result": "resolved" if verdict.ok else "failed",
                "new_failure_fingerprint": None if verdict.ok else attempt_fingerprint,
                "after_metrics": dict(verdict.metrics),
                "rerun_verdict": verdict.kind.value,
                "rerun_summary": verdict.summary,
                "generated_script_sha256": hashlib.sha256(script.encode()).hexdigest() if script else "",
                "tool_backend": self.klayout.backend.name if spec.tool is Tool.KLAYOUT else str(spec.tool),
                "tool_identity": self._tool_identity(spec.tool),
            })
            self.log.note(
                f"repair {'resolved' if verdict.ok else 'did not resolve'} "
                f"{repair.get('known_error_id') or spec.id.value}",
                stage="repair", result=repair["result"],
                failure_fingerprint=repair.get("failure_fingerprint"),
                new_failure_fingerprint=repair.get("new_failure_fingerprint"),
            )
            self.state.stage(spec.id).history.append({"repair_result": dict(repair)})
            self.state.save()
            break

    # ---- signoff ---------------------------------------------------------

    def _verification_stage_results(self) -> dict[StageId, str]:
        out: dict[StageId, str] = {}
        for sid in STAGE_ORDER:
            state = self.state.stage(sid)
            if state.status is StageStatus.SKIPPED:
                out[sid] = "skipped"
            elif state.status is StageStatus.OK and state.last_verdict == VerdictKind.PASS.value:
                out[sid] = "pass"
            elif state.status is StageStatus.OK:
                out[sid] = state.last_verdict or "completed"
            elif state.status is StageStatus.FAILED:
                out[sid] = "failed"
            else:
                out[sid] = state.status.value
        return out

    def _authoritative_simulation_passed(self) -> bool:
        if self.state.stage(StageId.SIM).last_verdict != VerdictKind.PASS.value:
            return False
        for item in reversed(self._history):
            if item.get("stage") == StageId.SIM.value:
                return int(item.get("metrics", {}).get("authoritative_passed", 0)) > 0
        return False

    @staticmethod
    def _print_verification_summary(summary: Any) -> None:
        print("\nVerification summary\n")
        print("Functional specification     " + (
            "VERIFIED" if summary.functional_spec_verified else "NOT VERIFIED"
        ))
        print(f"  {summary.functional_reason}\n")
        print("Logical preservation         " + (
            "VERIFIED" if summary.logical_identity_verified else "NOT VERIFIED"
        ))
        print(f"  {summary.logical_reason}\n")
        print("Physical implementation      " + (
            "VERIFIED" if summary.physical_signoff_verified else "NOT VERIFIED"
        ))
        print(f"  {summary.physical_reason}\n")
        for repair in summary.repair_verifications:
            name = repair.get("known_error_id") or repair.get("stage") or "repair"
            result = "VERIFIED" if repair.get("repair_verified") else "NOT VERIFIED"
            print(f"Repair verification          {result}")
            print(f"  {name}; scope: {repair.get('verification_scope', 'unknown')}\n")
        print("Overall certification        " + (
            "COMPLETE" if summary.full_certification else "INCOMPLETE"
        ))
        print(f"  {summary.overall_reason}")

    def _signoff(self) -> None:
        """Re-verify every hard constraint against one exact GDS hash.

        Review 4.10: "a GDS file exists" is not signoff. Every signoff report
        must be bound to the same final GDS, not to a patchwork of artifacts
        that passed at different points in the run.
        """
        st = self.state.stage(StageId.SIGNOFF)
        st.attempts += 1
        st.started_at = st.started_at or time.time()
        self.log.stage_start(str(StageId.SIGNOFF), gate="hard", tool="none")

        integrity_problems: list[str] = []
        functional_problems: list[str] = []
        problems = integrity_problems
        if "final_gds" not in self.ledger:
            problems.append("no final GDS was produced")
        else:
            gds = self.ledger.get("final_gds")
            if not gds.unchanged():
                problems.append(
                    f"the final GDS changed after streamout (sha256 {gds.sha256[:12]})"
                )
            for gate in SIGNOFF_GATES:
                gs = self.state.stage(gate)
                if gs.status is StageStatus.SKIPPED:
                    problems.append(f"{gate} was skipped; signoff requires it")
                elif gs.status is not StageStatus.OK:
                    problems.append(f"{gate} did not pass ({gs.status})")

            # Every required gate, however it came to be skipped.
            #
            # Checking only cfg.skip_stages covered the explicit --skip case
            # and missed the automatic one: a design with no matching testbench
            # had `sim` marked SKIPPED by the runner itself, and since sim is
            # not bound to the final GDS it appeared in no other check. The run
            # then certified clean having never simulated the design. An
            # automatic skip is a missing proof exactly like a requested one --
            # the reason it happened does not make the evidence exist.
            for gate in REQUIRED_VERIFICATION:
                gs = self.state.stage(gate)
                why = gs.last_error or "no reason recorded"
                target_problems = (
                    functional_problems if gate is StageId.SIM
                    else integrity_problems
                )
                if gs.status is StageStatus.SKIPPED:
                    target_problems.append(
                        f"{gate} was skipped ({why}); signoff requires it"
                    )
                elif gs.status is not StageStatus.OK:
                    target_problems.append(f"{gate} did not pass ({gs.status})")
                elif gs.last_verdict and gs.last_verdict != VerdictKind.PASS.value:
                    # "Ran without complaining" is not proof. A testbench that
                    # completes while printing no result grades as
                    # qor_below_target: enough to continue the flow, not enough
                    # to certify that the design does what it is supposed to.
                    target_problems.append(
                        f"{gate} completed as {gs.last_verdict} rather than a "
                        f"pass ({gs.last_error or 'nothing was proved'}); "
                        "signoff needs an explicit pass"
                    )
            for sid in sorted(self.cfg.skip_stages, key=stage_index):
                target_problems = (
                    functional_problems if sid is StageId.SIM
                    else integrity_problems
                )
                target_problems.append(
                    f"{sid} was skipped at the user's request; a run with a "
                    "skipped stage is a measurement, not a signoff"
                )
            for h in self._history:
                sha = h.get("metrics", {}).get("checked_gds_sha256")
                if sha and sha != gds.sha256:
                    problems.append(
                        f"{h['stage']} was verified against GDS {sha[:12]} but the "
                        f"final GDS is {gds.sha256[:12]}"
                    )

        # Bind everything that was verified into one release candidate, then
        # re-verify it. Building the manifest is bookkeeping; re-hashing every
        # bound artifact from disk is the part that can actually catch a
        # signoff describing files that have since changed.
        from .manifest import probe_tool_versions
        manifest_tools = probe_tool_versions()
        manifest_tools["klayout"] = self._tool_identity(Tool.KLAYOUT)
        manifest = ReleaseCandidateManifest.build(
            top=self.cfg.top,
            ledger=self.ledger,
            pdk=self.cfg.pdk.to_dict(),
            config=self.cfg.to_dict(),
            ir_fingerprint=self.ir.fingerprint(),
            tools=manifest_tools,
        )
        problems += manifest.verify(self.ledger)
        problems += manifest.required_present(
            ("final_gds", "sdc", "routed_netlist", "spef", "routed_def")
        )
        problems += manifest.gate_binding_problems(self._history)

        # Certify on evidence, not on StageState.
        #
        # A stage reaching OK answers "did this finish", which is an
        # orchestration question. Whether the design is verified is a
        # different one, and the two come apart whenever a report is
        # regenerated, an upstream artifact changes, or a retry grades an
        # earlier attempt's file. Each hard gate therefore has to produce a
        # record naming the artifacts it consumed and the report it read, and
        # every one of those must still match this candidate.
        physical_evidence_gates = tuple(
            gate for gate in CERTIFYING_GATES if gate is not StageId.SIM
        )
        problems += missing_evidence(
            self._evidence, required=physical_evidence_gates
        )
        functional_problems += missing_evidence(
            self._evidence, required=(StageId.SIM,)
        )
        for gate in sorted(self._evidence, key=stage_index):
            evidence_problems = self._evidence[gate].problems_against(
                manifest_artifacts=manifest.artifacts, ledger=self.ledger,
            )
            if gate is StageId.SIM:
                functional_problems += evidence_problems
            else:
                integrity_problems += evidence_problems
        # Causal coherence across gates. Every individual record can be
        # internally valid while the set describes two different physical
        # generations -- which is exactly how two organically clean candidates
        # were combined into one "clean" signoff.
        problems += lineage_problems(self._evidence)

        cert_id = certification_id(manifest.candidate_id, self._evidence)
        stage_results = self._verification_stage_results()
        authoritative_simulation = self._authoritative_simulation_passed()
        if (
            self.state.stage(StageId.SIM).status is StageStatus.OK
            and not authoritative_simulation
        ):
            functional_problems.append(
                "simulation passed only implementation-derived testbenches; "
                "no authoritative specification testbench was verified"
            )
        repair_verifications: list[dict[str, Any]] = []
        verified_repairs: list[dict[str, Any]] = []
        for repair in self._accepted:
            verified_rtl_sha256 = self.ledger.get("rtl_dir").sha256
            rtl_before = str(repair.get("rtl_sha256_before_repair", ""))
            evaluation_record = {
                **repair,
                "verified_working_rtl_sha256": verified_rtl_sha256,
                "rtl_identity_preserved": bool(rtl_before) and (
                    rtl_before == verified_rtl_sha256
                ),
            }
            verification = evaluate_repair(
                evaluation_record,
                stage_results=stage_results,
                evidence_gates=set(self._evidence),
                integrity_problems=integrity_problems,
                authoritative_simulation=authoritative_simulation,
            )
            record = {
                **evaluation_record,
                **verification.to_dict(),
                "original_working_rtl_sha256": getattr(
                    self, "_initial_work_rtl_sha256", ""
                ),
                "design_features": {
                    **self.facts.to_dict(),
                    "failure_geometry": repair.get(
                        "failure_geometry_evidence", {}
                    ),
                    "successful_ir": self.ir.as_dict(),
                },
                "successful_ir_fingerprint": self.ir.fingerprint(),
                "pdk": self.cfg.pdk.name,
                "tool_backend": self.klayout.backend.name,
                "tool_identity": self._tool_identity(Tool.KLAYOUT),
                "candidate_id": manifest.candidate_id,
                "certification_id": cert_id,
            }
            repair_verifications.append(record)
            if verification.repair_verified:
                verified_repairs.append(record)

        certification = evaluate_certification(
            stage_results=stage_results,
            authoritative_simulation=authoritative_simulation,
            integrity_problems=integrity_problems,
            repair_verifications=repair_verifications,
        )
        self._write(
            self.run_dir / "verification_summary.json",
            __import__("json").dumps(
                certification.to_dict(), indent=2, default=str
            ),
        )
        self._print_verification_summary(certification)
        problems = [*integrity_problems, *functional_problems]

        self._write(
            self.run_dir / "gate_evidence.json",
            __import__("json").dumps(
                {
                    "certification_id": cert_id,
                    "candidate_id": manifest.candidate_id,
                    "gates": {
                        g.value: e.to_dict() for g, e in
                        sorted(self._evidence.items(),
                               key=lambda kv: stage_index(kv[0]))
                    },
                },
                indent=2, default=str,
            ),
        )
        self.log.note(
            f"release candidate {manifest.short()}",
            stage=str(StageId.SIGNOFF),
            candidate_id=manifest.candidate_id,
        )
        self._write(
            self.run_dir / "release_candidate.json",
            __import__("json").dumps(manifest.to_dict(), indent=2, default=str),
        )

        bundle = {
            "run_id": self.run_id,
            "candidate_id": manifest.candidate_id,
            "release_candidate": manifest.to_dict(),
            "top": self.cfg.top,
            "pdk": self.cfg.pdk.to_dict(),
            "final_gds": self.ledger.get("final_gds").to_dict()
            if "final_gds" in self.ledger else None,
            "gates": {
                g.value: self.state.stage(g).status.value for g in SIGNOFF_GATES
            },
            # Functional verification is not bound to the GDS the way the
            # signoff gates are, but a bundle that hid whether the design was
            # ever simulated or formally checked would overstate what was
            # verified. Recorded explicitly so the answer is always visible.
            "verification": {
                g.value: self.state.stage(g).status.value
                for g in (StageId.SIM, StageId.LEC_SYNTH, StageId.LEC_ROUTE)
            },
            "certification": certification.to_dict(),
            "ir": self.ir.as_dict(),
            "ir_fingerprint": self.ir.fingerprint(),
            "problems": problems,
            "clean": not problems,
        }
        self._write(
            self.run_dir / "signoff.json",
            __import__("json").dumps(bundle, indent=2, default=str),
        )

        if verified_repairs:
            self._write(
                self.run_dir / "verified_repairs.json",
                __import__("json").dumps(
                    verified_repairs, indent=2, default=str
                ),
            )
            self.log.note(
                f"promoted {len(verified_repairs)} repair(s) under action-derived verification scopes",
                stage="repair", candidate_id=manifest.candidate_id,
            )

        if problems:
            st.status = StageStatus.FAILED
            st.last_error = "; ".join(problems)
            self.state.save()
            raise Escalation(
                StageId.SIGNOFF,
                "signoff aggregation failed: " + "; ".join(problems),
            )
        st.status = StageStatus.OK
        st.ended_at = time.time()
        self.log.stage_end(str(StageId.SIGNOFF), "ok", st.attempts)
        self.state.save()

    # ---- teardown --------------------------------------------------------

    def _finish(
        self, status: RunStatus, *, escalation: Escalation | None = None,
        reason: str = "",
    ) -> None:
        self.state.status = status
        self.state.ended_at = time.time()
        self.state.artifacts = self.ledger
        self.state.save()

        if status is not RunStatus.OK:
            self._write(
                self.run_dir / "failure_report.md",
                self._failure_report(escalation, reason),
            )
        self.log.run_end(
            status.value,
            budget=self.budget.to_dict(),
            stages_ok=len(self.state.completed_stages()),
        )
        self.log.close()

    def _failure_report(self, esc: Escalation | None, reason: str) -> str:
        lines = [
            f"# rtl2gdsagi failure report", "",
            f"- run: `{self.run_id}`",
            f"- top: `{self.cfg.top}`",
            f"- pdk: `{self.cfg.pdk.name}` at `{self.cfg.pdk.root}`",
            f"- budget: {self.budget.spent}/{self.budget.total} attempts spent",
            "",
        ]
        if esc is not None:
            lines += [
                f"## Stopped at `{esc.stage}`", "",
                esc.reason, "",
            ]
            entry = None
            for h in reversed(self._history):
                if h["stage"] == esc.stage.value and h.get("failure_class"):
                    entry = lookup(FailureClass(h["failure_class"]))
                    break
            if entry is not None:
                lines += [
                    f"**Failure class:** `{entry.failure}`  ",
                    f"**Resolution:** `{entry.resolution}`  ",
                    f"**Evidence source:** {entry.evidence}", "",
                ]
                if entry.notes:
                    lines += [f"> {entry.notes}", ""]
                if entry.forbids:
                    lines += [
                        "**Not auto-fixable because the following are immutable:** "
                        + ", ".join(f"`{f}`" for f in entry.forbids), "",
                    ]
            if esc.detail:
                lines += ["### Tool evidence", "", "```", esc.detail[:6000], "```", ""]
        elif reason:
            lines += ["## Stopped", "", reason, ""]

        verification_path = self.run_dir / "verification_summary.json"
        if verification_path.is_file():
            try:
                summary = __import__("json").loads(verification_path.read_text())
            except (OSError, ValueError):
                summary = None
            if summary:
                def mark(value: bool) -> str:
                    return "VERIFIED" if value else "NOT VERIFIED"
                lines += [
                    "## Verification summary", "",
                    f"- Functional specification: **{mark(summary['functional_spec_verified'])}** — {summary['functional_reason']}",
                    f"- Logical preservation: **{mark(summary['logical_identity_verified'])}** — {summary['logical_reason']}",
                    f"- Physical implementation: **{mark(summary['physical_signoff_verified'])}** — {summary['physical_reason']}",
                ]
                for repair in summary.get("repair_verifications", []):
                    name = repair.get("known_error_id") or repair.get("stage", "repair")
                    lines.append(
                        f"- Repair {name}: **{mark(repair.get('repair_verified', False))}** "
                        f"(scope `{repair.get('verification_scope', 'unknown')}`)"
                    )
                lines += [
                    f"- Overall certification: **{'COMPLETE' if summary['full_certification'] else 'INCOMPLETE'}** — {summary['overall_reason']}",
                    "",
                ]

        lines += ["## Stage status", "", "| stage | status | attempts | last error |",
                  "|---|---|---|---|"]
        for sid in STAGE_ORDER:
            s = self.state.stage(sid)
            if s.status is StageStatus.PENDING and s.attempts == 0:
                continue
            lines.append(
                f"| `{sid}` | {s.status} | {s.attempts} | {(s.last_error or '')[:80]} |"
            )
        lines += ["", "## Reproduce", "", "```", f"IR fingerprint: {self.ir.fingerprint()}",
                  "```", "",
                  f"Full log: `{self.log.jsonl_path}`", ""]
        return "\n".join(lines)


def run_pipeline(cfg: RunConfig, **kw: Any) -> int:
    return Orchestrator(cfg, **kw).run()
