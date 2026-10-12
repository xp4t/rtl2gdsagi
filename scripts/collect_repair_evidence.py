#!/usr/bin/env python3
"""Collect the complete live trial denominator and proposal recheck outcomes."""
from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from rtl2gdsagi.stages import StageId,get_stage,Gate
from extract_signoff_metrics import extract

def events(folder):
    return [json.loads(line) for line in (folder/"run.jsonl").read_text().splitlines()]

def trial(folder,kind,replicate):
    stream=events(folder)
    state=json.loads((folder/"run_state.json").read_text())
    assert state["status"] in ("ok","failed")
    calls=[e for e in stream if e.get("event")=="api_call" and e.get("model")!="scripted"]
    checks=[e for e in stream if e.get("event")=="result_check"]
    origin={"timing":"sta_signoff","pdn":"pdn","drc":"drc"}[kind]
    original=[e for e in checks if e.get("stage")==origin]
    assert original and not original[0]["ok"], "every declared trial must really inject a failure"
    updates=[(i,e) for i,e in enumerate(stream) if e.get("event")=="config_generated" and e.get("delta")]
    proposals=[]
    for index,(position,update) in enumerate(updates):
        end=updates[index+1][0] if index+1<len(updates) else len(stream)
        segment=stream[position+1:end]
        hard=[e for e in segment if e.get("event")=="result_check" and
              get_stage(StageId(e["stage"])).gate is Gate.HARD]
        failed=[e for e in hard if not e["ok"]]
        objectives=[e for e in hard if e["stage"]==update["stage"]]
        outcome=("native_failure" if failed else "target_pass" if objectives and objectives[-1]["ok"]
                 else "required_target_unavailable")
        proposals.append({"delta":update["delta"],"origin_stage":update["stage"],
                          "naive_no_recheck_promotes":True,"native_recheck":outcome,
                          "native_failure":failed[0] if failed else None,
                          "target_result":objectives[-1] if objectives else None})
    verified=False
    metrics=None
    if state["status"]=="ok":
        metrics=extract(folder)
        verified=bool(metrics["repair_verifications"]) and all(
            r.get("repair_verified") for r in metrics["repair_verifications"] if r.get("result")=="resolved")
        assert verified and metrics["clean"]
    return {"failure_type":kind,"replicate":replicate,"run_dir":str(folder.relative_to(ROOT)),
            "state":state["status"],"fully_verified":verified,"model_calls":len(calls),
            "input_tokens":sum(e["input_tokens"] for e in calls),
            "output_tokens":sum(e["output_tokens"] for e in calls),
            "initial_check":original[0],"latest_target_check":original[-1],
            "proposals":proposals,"metrics":metrics,
            "terminal_failures":[k for k,v in state["stages"].items() if v["status"]=="failed"]}

def main():
    rows=[]; manifests=[]
    for name in ("live_repair_study","live_drc_study"):
        manifest=json.loads((ROOT/"runs"/name/"experiment_manifest.json").read_text())
        assert manifest["consistent_source"]
        manifests.append(manifest)
        for key,record in manifest["trials"].items():
            rows.append(trial(ROOT/record["run_dir"],record["failure_type"],record["replicate"]))
    rows.sort(key=lambda r:(r["failure_type"],r["replicate"]))
    assert len(rows)==9
    by_kind={kind:{"trials":sum(r["failure_type"]==kind for r in rows),
                         "verified":sum(r["fully_verified"] for r in rows if r["failure_type"]==kind),
                         "escalated":sum(not r["fully_verified"] for r in rows if r["failure_type"]==kind)}
             for kind in ("drc","pdn","timing")}
    all_proposals=[p for r in rows for p in r["proposals"]]
    result={"protocol":"three repeats per failure type; retained native rechecks; no API errors excluded from this prospective cohort",
            "source_manifests":manifests,"trials":rows,"by_failure_type":by_kind,
            "episodes":len(rows),"verified":sum(r["fully_verified"] for r in rows),
            "escalated":sum(not r["fully_verified"] for r in rows),
            "provider_calls":sum(r["model_calls"] for r in rows),
            "input_tokens":sum(r["input_tokens"] for r in rows),
            "output_tokens":sum(r["output_tokens"] for r in rows),
            "no_recheck_baseline":{"promotions":len(all_proposals),
                "confirmed_native_failures":sum(p["native_recheck"]=="native_failure" for p in all_proposals),
                "required_target_unavailable":sum(p["native_recheck"]=="required_target_unavailable" for p in all_proposals)}}
    # Earlier development and transport failures are reported alongside, never
    # silently pooled into the prospectively repeated final-protocol cohort.
    catalog=[]
    prospective={r["run_dir"] for r in rows}
    for log in sorted((ROOT/"runs").rglob("run.jsonl")):
        folder=log.parent
        try: stream=events(folder)
        except (json.JSONDecodeError,OSError): continue
        calls=[e for e in stream if e.get("event")=="api_call" and e.get("model")!="scripted"]
        errors=[e for e in stream if e.get("agent_error")]
        if not calls and not errors: continue
        ends=[e for e in stream if e.get("event")=="run_end"]
        signoff=folder/"signoff.json"
        clean=json.loads(signoff.read_text()).get("clean",False) if signoff.exists() else False
        catalog.append({"run_dir":str(folder.relative_to(ROOT)),"prospective":str(folder.relative_to(ROOT)) in prospective,
                        "clean":clean,"valid_provider_responses":len(calls),"provider_errors":errors,
                        "input_tokens":sum(e["input_tokens"] for e in calls),
                        "output_tokens":sum(e["output_tokens"] for e in calls),
                        "requested_stages":[e["stage"] for e in calls],
                        "terminal_status":ends[-1].get("status") if ends else "incomplete"})
    result["all_retained_live_episodes"]=catalog
    out=ROOT/"rtl2gdsagi_paper/evidence/repair_study.json";out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:result[k] for k in ("episodes","verified","escalated","provider_calls","by_failure_type","no_recheck_baseline")},indent=2))

if __name__=="__main__": main()
