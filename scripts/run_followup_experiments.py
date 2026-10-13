#!/usr/bin/env python3
"""Run declared timing, worker-count and large-repair follow-up cases."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time
from run_signoff_benchmark import source_identity

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runs/reviewer_followup_20261013'
PDK='/home/vlsi/.volare/volare/sky130/versions/bdc9412b3e468c102d01b7cf6337be06ec6e9c9a/sky130A'
BIN='/home/vlsi/Documents/rtl2gdsagi/.venv/bin'

def main():
    OUT.mkdir(exist_ok=True)
    if (OUT/'experiment_manifest.json').exists():raise RuntimeError('refusing to overwrite follow-up cohort')
    old=OUT/'repair_cohort_source';old.mkdir(exist_ok=True)
    with tarfile.open(ROOT/'rtl2gdsagi_paper/evidence/source_repair_cohort.tar.gz') as tar:tar.extractall(old)
    # Non-Python resource files are unchanged from the base used by that cohort.
    # Retain the exact bytes and verify the premise against Git, rather than
    # silently combining historical code with modified runtime resources.
    resources=[]
    for p in (ROOT/'src/rtl2gdsagi/resources').rglob('*'):
        if not p.is_file() or p.suffix=='.py' or '__pycache__' in p.parts:continue
        rel=p.relative_to(ROOT)
        base=subprocess.check_output(['git','show',f'a006861:{rel}'],cwd=ROOT)
        assert base==p.read_bytes(),rel
        dest=old/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(base)
        resources.append({'path':str(rel),'sha256':hashlib.sha256(base).hexdigest(),'verified_base':'a006861'})
    cases=[]
    for kind,config,repeats,live,legacy in [
        ('timing_original','alu8_repaired_3ns.yaml',3,False,True),
        ('timing_current','alu8_repaired_3ns.yaml',3,False,False),
        ('shift_single','shift1024_one_worker.yaml',2,False,False),
        ('accum_spacing','accum_spacing_live.yaml',2,True,False),
        ('accum_antenna','accum_antenna_live.yaml',2,True,False)]:
        for index in range(1,repeats+1):
            cases.append({'kind':kind,'replicate':index,'config':config,'live_api':live,'historical_source':legacy})
    prior=json.loads((ROOT/'runs/live_repair_study/experiment_manifest.json').read_text())['source_sha256']
    manifest={'current_source_sha256':source_identity(),'historical_source_sha256':prior,
              'resource_files':resources,'declared_cases':cases,'started_at':time.time(),'trials':{}}
    path=OUT/'experiment_manifest.json';path.write_text(json.dumps(manifest,indent=2)+'\n')
    def execute(case):
        key=f"{case['kind']}_{case['replicate']}";folder=OUT/key
        env={**os.environ,'PYTHONPATH':str(old/'src' if case['historical_source'] else ROOT/'src'),
             'PATH':BIN+os.pathsep+os.environ.get('PATH','')}
        cmd=[sys.executable,'-m','rtl2gdsagi.cli','run','--config',str(ROOT/'benchmarks/followup'/case['config']),
             '--pdk-root',PDK,'--klayout-backend','container','--run-dir',str(folder)]
        if case['live_api']:cmd+=['--model','claude-sonnet-5','--repair-policy','auto','--retry-limit','3']
        else:cmd+=['--no-api']
        start=time.time();print('starting '+key,flush=True)
        with (OUT/f'{key}.console.log').open('w') as log:
            result=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        state=json.loads((folder/'run_state.json').read_text())
        row={**case,'command':cmd,'run_dir':str(folder.relative_to(ROOT)),'source_sha256':prior if case['historical_source'] else manifest['current_source_sha256'],
             'exit_code':result.returncode,'status':state['status'],'elapsed_s':time.time()-start}
        print(json.dumps({'trial':key,**row}),flush=True)
        return key,row
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(execute,c) for c in cases]
        for f in concurrent.futures.as_completed(futures):
            key,row=f.result();manifest['trials'][key]=row
            path.write_text(json.dumps(manifest,indent=2)+'\n')
    manifest.update(ended_at=time.time(),consistent_source=source_identity()==manifest['current_source_sha256'])
    path.write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__':main()
