#!/usr/bin/env python3
"""Declare a finite no-model sweep and execute every state through frozen checks."""
import concurrent.futures
import copy
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import yaml
from run_signoff_benchmark import source_identity

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runs/scripted_baseline_bounded_20261013'
FROZEN=ROOT/'runs/frozen_evaluation_20261013/frozen_source/src'
ARCHIVED=ROOT/'runs/reviewer_followup_20261013/repair_cohort_source/src'
BIN='/home/vlsi/Documents/rtl2gdsagi/.venv/bin'
PDK='/home/vlsi/.volare/volare/sky130/versions/bdc9412b3e468c102d01b7cf6337be06ec6e9c9a/sky130A'

def initial_states():
    study=json.loads((ROOT/'rtl2gdsagi_paper/evidence/repair_study.json').read_text())
    defaults=json.loads(subprocess.check_output([sys.executable,'-c','from rtl2gdsagi.ir import IR; import json; print(json.dumps(IR().as_dict()))'],env={**os.environ,'PYTHONPATH':str(ARCHIVED)},cwd=ROOT,text=True))
    states={}
    for kind in ('drc','pdn','timing'):
        ep=next(r for r in study['trials'] if r['failure_type']==kind and r['replicate']==1)
        folder=ROOT/ep['run_dir'];state=json.loads((folder/'run_state.json').read_text());ir=copy.deepcopy(defaults)
        for e in [json.loads(l) for l in (folder/'run.jsonl').read_text().splitlines()]:
            if e.get('event')=='result_check' and not e.get('ok',True):break
            if e.get('delta'):
                for section,values in e['delta'].items():ir[section].update(values)
        ir.setdefault('routing',{})['num_threads']=1
        states[kind]={'origin':ep['run_dir'],'ir':ir,'config':state['config']}
    return states

def main():
    assert not OUT.exists(),'Never overwrite outcomes'
    source=source_identity();assert source==json.loads((FROZEN.parents[1]/'experiment_manifest.json').read_text())['source_sha256']
    OUT.mkdir();states=initial_states();cases=[]
    def add(name,kind,delta,scope='fixed_constraints'):
        seed=states[kind];ir=copy.deepcopy(seed['ir'])
        for section,values in delta.items():ir[section].update(values)
        cfg={'top':seed['config']['top'],'rtl':seed['config']['rtl_dir'],'pdk':{k:seed['config']['pdk'][k] for k in ('name','std_cell_lib','corner')},'retry_limit':1,'ir':ir}
        path=OUT/(name+'.yaml');path.write_text(yaml.safe_dump(cfg,sort_keys=False))
        cases.append({'trial':name,'class':kind,'scope':scope,'origin':seed['origin'],'delta':delta,'config':str(path.relative_to(ROOT)),'config_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'period_ns':ir['sdc']['default_clock_period_ns']})
    for padding in range(4):add(f'spacing_pad{padding}','drc',{'placement':{'padding_sites':padding}})
    for offset in (50.0,2.0):add(f'pdn_offset{int(offset)}','pdn',{'pdn':{'strap_offset_um':offset}})
    # Declared before native execution; full Cartesian product, no early success stop.
    for strategy,density,padding,setup in itertools.product(('DELAY0','DELAY1'),(.45,.55),(1,2),(False,True)):
        name=f'timing_{strategy}_density{int(density*100)}_pad{padding}_setup{int(setup)}'
        add(name,'timing',{'synthesis':{'strategy':strategy},'placement':{'target_density':density,'padding_sites':padding},'cts':{'fix_setup':setup,'setup_margin_ns':.05}},'fixed_3ns')
    for period in (3.25,3.5):add('period_control_'+str(period).replace('.','p'),'timing',{'sdc':{'default_clock_period_ns':period}},'relaxed_period_control')
    assert len(cases)==24
    manifest={'source_sha256':source,'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'declared_cases':cases,'initial_states':states,'started_at':time.time(),'trials':{},'harness_sha256':hashlib.sha256((ROOT/'scripts/run_baseline_candidate.py').read_bytes()).hexdigest(),'pilot':'runs/scripted_baseline_20261013','scope':'Predeclared finite scripted search with no model calls or automatic repair. A study-only harness stops at first native hard failure; frozen native checks and successful certification are unchanged. Same archived initial fixture IRs, frozen executor, routing1, native full-contract acceptance. Two slower-clock controls are excluded from timing-repair success. All candidates run; no claim of optimality or independent model comparison.'}
    target=OUT/'experiment_manifest.json';target.write_text(json.dumps(manifest,indent=2)+'\n')
    def execute(case):
        folder=OUT/case['trial'];cmd=[sys.executable,str(ROOT/'scripts/run_baseline_candidate.py'),'--config',str(ROOT/case['config']),'--pdk-root',PDK,'--run-dir',str(folder)]
        env={**os.environ,'PYTHONPATH':str(FROZEN),'PATH':BIN+os.pathsep+os.environ.get('PATH','')};start=time.time()
        with (OUT/(case['trial']+'.console.log')).open('w') as f:proc=subprocess.run(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
        state=json.loads((folder/'run_state.json').read_text());events=[json.loads(l) for l in (folder/'run.jsonl').read_text().splitlines()];checks=[e for e in events if e.get('event')=='result_check']
        assert not any(e.get('event') in ('api_call','config_generated') for e in events),'Unexpected model/proposal event'
        assert not any(e.get('event')=='repair_applied' for e in events)
        return case['trial'],{**case,'command':cmd,'run_dir':str(folder.relative_to(ROOT)),'status':state['status'],'exit_code':proc.returncode,'elapsed_s':time.time()-start,'failed_checks':[e for e in checks if not e.get('ok',True)],'target_checks':[e for e in checks if e['stage'] in ('sta_signoff','drc','pdn')],'stages_ok':sum(s['status']=='ok' for s in state['stages'].values())}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for future in concurrent.futures.as_completed([pool.submit(execute,c) for c in cases]):
            key,row=future.result();manifest['trials'][key]=row;target.write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'trial':key,'status':row['status'],'failed':[e['stage'] for e in row['failed_checks']]}),flush=True)
    manifest.update(ended_at=time.time(),consistent_source=source_identity()==source);target.write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':main()
