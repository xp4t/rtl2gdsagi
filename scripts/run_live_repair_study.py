#!/usr/bin/env python3
"""Run predeclared live repair cases and retain the entire trial denominator."""
import concurrent.futures
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from run_signoff_benchmark import source_identity

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"runs/live_repair_study"
PDK="/home/vlsi/.volare/volare/sky130/versions/bdc9412b3e468c102d01b7cf6337be06ec6e9c9a/sky130A"

def main():
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root",type=Path,default=OUT)
    parser.add_argument("--kinds",nargs="+",choices=("timing","pdn","drc"),default=["timing","pdn"])
    args=parser.parse_args()
    OUT=args.run_root.resolve()
    OUT.mkdir(exist_ok=True)
    cases=[(kind,index) for kind in args.kinds for index in (1,2,3)]
    configs={"timing":"alu8_timing_3ns.yaml","pdn":"register_pdn_fault.yaml","drc":"alu8_unpadded.yaml"}
    manifest={"source_sha256":source_identity(),"started_at":time.time(),
              "model":"claude-sonnet-5","provider":"Anthropic","trials":{}}
    path=OUT/"experiment_manifest.json"
    path.write_text(json.dumps(manifest,indent=2)+"\n")
    def execute(case):
        kind,index=case; key=f"{kind}_{index}"; folder=OUT/key
        if folder.exists(): raise RuntimeError(f"refusing to overwrite {folder}")
        cmd=[sys.executable,"-m","rtl2gdsagi.cli","run","--config",str(ROOT/"benchmarks/signoff"/configs[kind]),
             "--pdk-root",PDK,"--model","claude-sonnet-5","--repair-policy","auto",
             "--retry-limit","3","--klayout-backend","container","--run-dir",str(folder)]
        env={**os.environ,"PYTHONPATH":str(ROOT/"src")}
        start=time.time()
        with (OUT/f"{key}.console.log").open("w") as out:
            proc=subprocess.run(cmd,cwd=ROOT,env=env,stdout=out,stderr=subprocess.STDOUT)
        state=json.loads((folder/"run_state.json").read_text())
        return key,{"failure_type":kind,"replicate":index,"command":cmd,
                    "run_dir":str(folder.relative_to(ROOT)),"exit_code":proc.returncode,
                    "status":state["status"],"elapsed_s":time.time()-start}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(execute,c) for c in cases]
        for future in concurrent.futures.as_completed(futures):
            key,row=future.result(); manifest["trials"][key]=row
            path.write_text(json.dumps(manifest,indent=2)+"\n")
            print(json.dumps({"trial":key,**row}),flush=True)
    manifest.update(ended_at=time.time(),consistent_source=manifest["source_sha256"]==source_identity())
    path.write_text(json.dumps(manifest,indent=2)+"\n")

if __name__=="__main__": main()
