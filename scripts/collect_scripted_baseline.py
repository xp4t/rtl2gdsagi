#!/usr/bin/env python3
"""Validate the completed scripted cohort and generate its data/table/macro inputs."""
import csv
import hashlib
import json
import yaml
from pathlib import Path
from extract_signoff_metrics import extract
from generate_extended_results import table
from run_signoff_benchmark import source_identity
ROOT=Path(__file__).resolve().parents[1]
PAPER=ROOT/'rtl2gdsagi_paper'

def main():
    path=ROOT/'runs/scripted_baseline_bounded_20261013/experiment_manifest.json'
    manifest=json.loads(path.read_text())
    assert 'ended_at' in manifest and manifest['consistent_source']
    assert manifest['harness_sha256']==hashlib.sha256((ROOT/'scripts/run_baseline_candidate.py').read_bytes()).hexdigest()
    assert manifest['source_sha256']==source_identity() and len(manifest['trials'])==len(manifest['declared_cases'])==24
    rows=[];groups={}
    for declared in manifest['declared_cases']:
        r=manifest['trials'][declared['trial']];assert r['status'] in ('ok','failed')
        cfg=ROOT/r['config'];assert hashlib.sha256(cfg.read_bytes()).hexdigest()==r['config_sha256']
        events=[json.loads(l) for l in (ROOT/r['run_dir']/'run.jsonl').read_text().splitlines()]
        assert not any(e.get('event') in ('api_call','config_generated') for e in events)
        state=json.loads((ROOT/r['run_dir']/'run_state.json').read_text());assert yaml.safe_load(cfg.read_text())['ir']['sta']['slack_guardband_ns']==0
        if r['status']=='ok':
            metrics=extract(ROOT/r['run_dir']);assert metrics['clean'] and metrics['stages_passed']==21
        else:
            assert r['failed_checks'] and not (ROOT/r['run_dir']/'signoff.json').exists()
            metrics={'clean':False}
        drc=[e for e in events if e.get('event')=='result_check' and e.get('stage')=='drc']
        drc_count=drc[-1].get('total_violations') if drc else None
        timing=[e for e in events if e.get('event')=='result_check' and e.get('stage')=='sta_signoff']
        value=timing[-1] if timing else {}
        row={'trial':r['trial'],'class':r['class'],'scope':r['scope'],'period_ns':r['period_ns'],'fully_certified':metrics['clean'],'failed_stages':sorted(set(e['stage'] for e in r['failed_checks'])),'setup_wns_ns':value.get('setup_wns'),'hold_wns_ns':value.get('hold_wns'),'native_drc_violations':drc_count,'elapsed_s':r['elapsed_s'],'run_dir':r['run_dir'],'delta':r['delta']}
        rows.append(row)
        key='period' if r['scope']=='relaxed_period_control' else r['class'];groups.setdefault(key,[]).append(row)
    pairs=[]
    timing_rows=[r for r in rows if r['scope']=='fixed_3ns']
    for off in [r for r in timing_rows if r['trial'].endswith('_setup0')]:
        on=next(r for r in timing_rows if r['trial']==off['trial'][:-1]+'1')
        a=json.loads((ROOT/off['run_dir']/'run_state.json').read_text())['artifacts']
        b=json.loads((ROOT/on['run_dir']/'run_state.json').read_text())['artifacts']
        keys=('cts_def','routed_def','spef')
        assert all(a[k]['sha256']==b[k]['sha256'] for k in keys)
        assert off['setup_wns_ns']==on['setup_wns_ns'] and off['hold_wns_ns']==on['hold_wns_ns']
        pairs.append({'off':off['trial'],'on':on['trial'],'artifact_hashes':{k:a[k]['sha256'] for k in keys},'setup_wns_ns':off['setup_wns_ns'],'hold_wns_ns':off['hold_wns_ns']})
    assert len(pairs)==8
    summaries={}
    for key,values in groups.items():
        timing=[r['setup_wns_ns'] for r in values if r['setup_wns_ns'] is not None]
        summaries[key]={'states':len(values),'certified':sum(r['fully_certified'] for r in values),'sta_states':len(timing),'best_setup_wns_ns':max(timing) if timing else None,'worst_setup_wns_ns':min(timing) if timing else None,'failed_stage_counts':{s:sum(s in r['failed_stages'] for r in values) for s in sorted({s for r in values for s in r['failed_stages']})}}
    assert [summaries[k]['states'] for k in ('drc','pdn','timing','period')]==[4,2,16,2]
    result={'source_sha256':source_identity(),'manifest':str(path.relative_to(ROOT)),'manifest_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'states':rows,'groups':summaries,'setup_toggle_outcome_equivalent_pairs':pairs,'new_model_calls':0,'wall_elapsed_s':manifest['ended_at']-manifest['started_at'],'candidate_elapsed_s_sum':sum(r['elapsed_s'] for r in rows),'protocol':'Finite predeclared Cartesian sweep; same archived initial fixture configurations, frozen source, one routing worker, full native certification. Owner-declared period controls excluded from fixed-target repair counts. A study-only wrapper stops after the first hard failure; successful certification remains frozen. The earlier no-model CLI pilot and a failed harness import are retained but excluded. No model benefit or optimality estimate.'}
    (PAPER/'evidence/scripted_baseline.json').write_text(json.dumps(result,indent=2)+'\n')
    columns=['trial','class','scope','period_ns','fully_certified','failed_stages','setup_wns_ns','hold_wns_ns','native_drc_violations','elapsed_s','run_dir']
    with (PAPER/'evidence/scripted_baseline_metrics.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
        for r in rows:writer.writerow({k:','.join(r[k]) if k=='failed_stages' else ('not reached' if r[k] is None else r[k]) for k in columns})
    table_rows=[]
    for key,label,knobs in [('drc','Spacing','Padding 0--3 sites'),('pdn','PDN','Offset 50 or 2 $\\mu$m'),('timing','Timing, 3 ns','Strategy/density/padding/CTS grid'),('period','Slower-clock controls','3.25 or 3.50 ns')]:
        g=summaries[key];best='--' if g['best_setup_wns_ns'] is None else f"{g['best_setup_wns_ns']:+.6f}"
        table_rows.append((label,knobs,f"{g['certified']}/{g['states']}",best))
    table('scripted_baseline_table.tex','Finite scripted baseline through the same frozen native contract. Counts are configurations, not independent repair episodes. Slower-clock controls change the requirement and are excluded from 3 ns repair success. Best setup is the maximum over all candidates reaching routed STA, including later hard failures. The spacing maximum is DRC-failed padding 0.','tab:scriptedbaseline','p{.23\\linewidth}p{.39\\linewidth}rr',r'Fixture & Scripted choices & Certified & \shortstack{Best setup\\all STA (ns)}',table_rows)
    macros={'ScriptedStates':24,'ScriptedTimingStates':16,'ScriptedTimingCertified':summaries['timing']['certified'],'ScriptedTimingBest':f"{summaries['timing']['best_setup_wns_ns']:+.6f}",'ScriptedSpacingCertified':summaries['drc']['certified'],'ScriptedPDNCertified':summaries['pdn']['certified'],'ScriptedPeriodCertified':summaries['period']['certified']}
    (PAPER/'generated/scripted_baseline_macros.tex').write_text('% Generated from completed native no-model sweep.\n'+''.join(f'\\newcommand{{\\{k}}}{{{v}}}\n' for k,v in macros.items()))
    print(json.dumps(summaries,indent=2))
if __name__=='__main__':main()
