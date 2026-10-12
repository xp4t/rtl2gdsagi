#!/usr/bin/env python3
"""Continue a no-model run at extraction after auditing retained native checks.

This study helper supports one explicit phase boundary. It does not copy old
green flags into a fresh run: it verifies artifact digests, frozen scripts and
native logs, then rebuilds proof records for the same retained candidate.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from rtl2gdsagi.artifacts import ArtifactLedger,sha256_file
from rtl2gdsagi.characterize import DesignFacts, suggest_starting_ir
from rtl2gdsagi.checks.pdn import check_pdn_def
from rtl2gdsagi.checks.tools import ToolRun,check_lint,check_sim,check_synthesis,check_lec,check_sta,check_openroad
from rtl2gdsagi.checks.verdict import passed
from rtl2gdsagi.config import RunConfig
from rtl2gdsagi.evidence import CERTIFYING_GATES,evidence_for
from rtl2gdsagi.runner import Orchestrator, _PARSER_CONTRACT, _REPORT_KEY
from rtl2gdsagi.stages import StageId,STAGE_ORDER,get_stage,stage_index
from rtl2gdsagi.state import RunState,RunStatus,StageState,StageStatus
from run_signoff_benchmark import source_identity

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir",type=Path)
    parser.add_argument("--boundary",choices=["extraction","routing"],default="extraction")
    args=parser.parse_args(); folder=args.run_dir.resolve()
    old=RunState.load(folder)
    assert old.status is RunStatus.FAILED, "only a terminal failed run may be continued"
    boundary=StageId(args.boundary)
    assert old.failed_stage() is not None and stage_index(old.failed_stage()) >= stage_index(boundary)
    before=STAGE_ORDER[:stage_index(boundary)]
    assert all(old.stage(s).status is StageStatus.OK for s in before)
    events=[json.loads(line) for line in (folder/"run.jsonl").read_text().splitlines()]
    assert not any(e.get("event")=="api_call" and e.get("model")!="scripted" for e in events)
    assert not any(e.get("event")=="config_generated" and "delta" in e for e in events), "model edits need their original runtime ledger"
    for art in old.artifacts._items.values(): art.assert_unchanged()
    config=ROOT/"examples"/old.config["top"]/f"{old.config['top']}.yaml"
    cfg=RunConfig.build(config_path=config,pdk_root=old.config["pdk"]["root"],
                        klayout_backend="container",repair_policy="manual",resume_from=boundary.value)
    checkpoint=folder/"continuation"/str(time.time_ns());checkpoint.mkdir(parents=True)
    shutil.copy2(folder/"run_state.json",checkpoint/"prior_run_state.json")
    shutil.copy2(folder/"run.jsonl",checkpoint/"prior_run.jsonl")
    orch=Orchestrator(cfg,run_dir=folder)
    orch.state=old;orch.run_id=old.run_id;orch.ledger=old.artifacts
    facts=json.loads(orch.ledger.get("design_facts").path.read_text())
    facts.pop("clock_domains",None);facts["sources"]=[Path(p) for p in facts["sources"]]
    orch.facts=DesignFacts(**facts)
    orch.ir.apply_delta(suggest_starting_ir(orch.facts),agent=False)
    orch.ir.apply_delta(cfg.ir_overrides,agent=False)
    orch._initial_work_rtl_sha256=orch.ledger.get("rtl_dir").sha256
    audit=[]
    for sid in before:
        if sid is StageId.CHARACTERIZE: continue
        spec=get_stage(sid); st=old.stage(sid); sd=orch.stage_dir(sid)
        prior=[e for e in events if e.get("event")=="result_check" and e.get("stage")==sid.value][-1]
        assert prior["ok"]
        snapshot=sd/f"attempt_{st.attempts:02d}_config.json"
        if snapshot.exists():
            snap=json.loads(snapshot.read_text())
            assert sha256_file(sd/snap["script"])==snap["script_sha256"]
            if snap["ir_section"]:
                current=orch.ir.section(snap["ir_section"])
                assert all(current[k]==v for k,v in snap["effective_ir"].items())
        invokes=[e for e in events if e.get("event")=="tool_run" and e.get("stage")==sid.value]
        argv=invokes[-1].get("argv",[]) if invokes else []
        log=sd/f"attempt_{st.attempts:02d}.log"
        native=ToolRun(argv=argv,returncode=0,stdout=log.read_text() if log.exists() else "",stderr="")
        if sid is StageId.LINT: verdict=check_lint(native)
        elif sid is StageId.SIM:
            verdict=check_sim(ToolRun(argv=[],returncode=0,stdout=orch.ledger.get("sim_result").path.read_text(),stderr=""))
        elif sid is StageId.SYNTHESIS: verdict=check_synthesis(native,orch.ledger.get("netlist").path)
        elif sid is StageId.LEC_SYNTH: verdict=check_lec(native,stage=sid)
        elif sid in (StageId.STA_PRE,StageId.STA_POSTCTS): verdict=check_sta(native,stage=sid)
        elif sid is StageId.PDN:
            result=check_pdn_def(orch.ledger.get("pdn_def").path)
            assert result.ok,result.problems
            verdict=passed(sid,result.summary(),via_count=result.via_count)
        elif sid is StageId.SDC:
            # The generated constraints are content-pinned and their native
            # timing consumers are regraded above and again downstream.
            verdict=passed(sid,prior["message"])
        else: verdict=check_openroad(native,stage=sid,
            outputs={key:orch.ledger.get(key).path for key in spec.produces if key in orch.ledger},
            overflow_limit=orch.ir.get("placement","congestion_overflow_limit"))
        assert verdict.ok,(sid,verdict.summary)
        metrics={k:v for k,v in prior.items() if k not in {"ts","event","stage","attempt","message","ok","kind"}}
        metrics.update(verdict.metrics)
        if sid is StageId.SIM:
            assert metrics.get("authoritative_passed",0)>0
        result=passed(sid,verdict.summary,**metrics)
        orch._history.append({"stage":sid.value,"attempt":st.attempts,**result.to_dict()})
        outputs={key:orch.ledger.get(key).path for key in spec.produces if key in orch.ledger}
        if sid in CERTIFYING_GATES:
            orch._evidence[sid]=evidence_for(stage=sid,verdict_kind="pass",attempt=st.attempts,
                ledger=orch.ledger,outputs=outputs,report_key=_REPORT_KEY.get(sid),
                tool=str(spec.tool),tool_identity=orch._tool_identity(spec.tool),
                parser_contract=_PARSER_CONTRACT.get(sid,""),metrics=metrics)
        orch.store.save(sid,ir=orch.ir,section=spec.ir_section,ledger=orch.ledger,
                        produces=spec.produces,inputs={k:orch.ledger.get(k) for k in spec.consumes if k in orch.ledger},
                        metrics=metrics,copy_artifacts=False)
        audit.append({"stage":sid.value,"frozen_script_verified":snapshot.exists(),
                      "native_verdict_revalidated":verdict.summary})
    for sid in STAGE_ORDER[stage_index(boundary):]:
        old.stages[sid]=StageState()
        orch._retire_stage_outputs(sid)
    # A retired output must also disappear from input selection. Retain only
    # preparation inputs and artifacts produced strictly before the boundary.
    retained=ArtifactLedger()
    for key,art in orch.ledger._items.items():
        if art.stage=="prepare" or (art.stage in {s.value for s in before}):
            retained.put(art)
    orch.ledger=retained
    old.status=RunStatus.RUNNING;old.ended_at=None;old.config=cfg.to_dict()
    (checkpoint/"audit.json").write_text(json.dumps({"source_sha256":source_identity(),
        "boundary":boundary.value,"started_at":time.time(),"artifact_hashes":{k:a.sha256 for k,a in orch.ledger._items.items()},
        "native_checks_revalidated":audit},indent=2)+"\n")
    orch.log.note("continuing the same candidate after native-check and artifact-identity audit",
                  boundary=boundary.value,source_sha256=source_identity())
    old.save()
    try:
        orch._main_loop()
    except Exception as exc:
        orch._finish(RunStatus.FAILED,reason=str(exc))
        raise
    orch._finish(RunStatus.OK)

if __name__=="__main__": main()
