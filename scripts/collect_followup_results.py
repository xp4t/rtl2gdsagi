#!/usr/bin/env python3
"""Validate and report every declared reviewer follow-up experiment."""
import hashlib
import json
from pathlib import Path
from extract_signoff_metrics import extract
from compare_repeated_runs import date_neutral_gds
from generate_extended_results import table
from implementation_identity import implementation_identity

ROOT=Path(__file__).resolve().parents[1]
PAPER=ROOT/'rtl2gdsagi_paper'
BASE=ROOT/'runs/reviewer_followup_20261013'

def main():
    manifest=json.loads((BASE/'experiment_manifest.json').read_text())
    assert manifest['consistent_source'] and len(manifest['trials'])==len(manifest['declared_cases'])==12
    rows=[]
    for key,row in sorted(manifest['trials'].items()):
        folder=ROOT/row['run_dir'];state=json.loads((folder/'run_state.json').read_text())
        assert state['status'] in ('ok','failed')
        events=[json.loads(l) for l in (folder/'run.jsonl').read_text().splitlines()]
        checks=[e for e in events if e.get('event')=='result_check']
        calls=[e for e in events if e.get('event')=='api_call' and e.get('model')!='scripted']
        failed=[e for e in checks if not e.get('ok',True)]
        sta=[e for e in checks if e['stage']=='sta_signoff']
        metric=extract(folder) if state['status']=='ok' else None
        r={**row,'trial':key,'fully_verified':metric is not None,'model_calls':len(calls),
           'input_tokens':sum(e['input_tokens'] for e in calls),'output_tokens':sum(e['output_tokens'] for e in calls),
           'provider_errors':[e for e in events if e.get('agent_error')],
           'initial_failure':failed[0] if failed else None,'last_failure':failed[-1] if failed else None,
           'last_routed_check':sta[-1] if sta else None,'metrics':metric,
           'proposals':[e for e in events if e.get('event')=='config_generated' and e.get('delta')]}
        if r['kind'].startswith('timing'):
            assert r['last_routed_check']
            sdc=Path(state['artifacts']['sdc']['path']).read_text();assert '-period 3.0000' in sdc
        if r['live_api']:
            assert r['initial_failure'],'live scale cases must really encounter a native failure'
        r['terminal_outcome']=('verified' if r['fully_verified'] else
                               'provider_interrupted' if r['provider_errors'] else 'policy_escalation')
        rows.append(r)
    data={'manifest':manifest,'trials':rows,'cohort_scope':'Follow-up only; never pooled with original nine repair episodes.'}
    one=[r for r in rows if r['kind']=='shift_single'];assert len(one)==2 and all(r['fully_verified'] for r in one)
    states=[json.loads((ROOT/r['run_dir']/'run_state.json').read_text()) for r in one]
    pair={'runs':[r['run_dir'] for r in one],
          'artifacts':{k:{'sha256':[s['artifacts'][k]['sha256'] for s in states],
                          'equal':states[0]['artifacts'][k]['sha256']==states[1]['artifacts'][k]['sha256']} for k in ['routed_def','routed_netlist','netlist','spef','final_gds']},
          'date_neutral_gds':[date_neutral_gds(Path(s['artifacts']['final_gds']['path']))[0] for s in states],
          'implementation_identities':[implementation_identity(ROOT/r['run_dir']) for r in one]}
    pair['date_neutral_equal']=pair['date_neutral_gds'][0]==pair['date_neutral_gds'][1]
    probe=json.loads((BASE/'thread_probe/manifest.json').read_text())
    for item in probe['files']:
        assert hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest()==item['sha256']
    probe_log=(BASE/'thread_probe/default.log').read_text()
    assert 'GLOBAL_THREAD_COUNT=1' in probe_log and 'ORD_THREAD_COUNT=1' in probe_log
    pair['native_default_thread_probe']=probe
    control_ir=json.loads((ROOT/'runs/shift_scale_pair_a/shift1024/signoff.json').read_text())['ir']
    ablation_ir=json.loads((ROOT/one[0]['run_dir']/'signoff.json').read_text())['ir']
    assert control_ir['routing']['num_threads']==8 and ablation_ir['routing']['num_threads']==1
    control_ir['routing']['num_threads']=1
    assert control_ir==ablation_ir,'worker count must be the only typed-setting change'
    data['single_worker_pair']=pair
    original_manifest=json.loads((PAPER/'evidence/experiment_manifest.json').read_text())
    ids=[]
    for selection in original_manifest['selected_runs']:
        values=[implementation_identity(ROOT/selection[k]) for k in ['run_dir','repeat_run_dir']]
        ids.append({'runs':[selection[k] for k in ['run_dir','repeat_run_dir']],
                    'identities':values,'equal':values[0]['implementation_id']==values[1]['implementation_id']})
    data['original_pair_implementation_ids']=ids
    (PAPER/'evidence/reviewer_followup.json').write_text(json.dumps(data,indent=2)+'\n')
    timing=[]
    for kind,label in [('timing_original','Archived repair source'),('timing_current','Current source')]:
        group=[r for r in rows if r['kind']==kind];assert len(group)==3
        values=[r['last_routed_check']['setup_wns'] for r in group]
        timing.append((label,3,sum(r['fully_verified'] for r in group),f'{min(values):.6f}',f'{max(values):.6f}'))
    old_slack=[r['last_routed_check']['setup_wns'] for r in rows if r['kind']=='timing_original']
    new_slack=[r['last_routed_check']['setup_wns'] for r in rows if r['kind']=='timing_current']
    assert len(set(old_slack))==len(set(new_slack))==1 and old_slack[0]>0>new_slack[0]
    table('followup_timing_table.tex','Fresh executions of the repaired configuration at unchanged 3 ns. Signed routed setup slack is in ns. Sources are checked separately; the narrow result is not robust across controller revisions.','tab:timingrepeat','lrrrr','Controller & Runs & Certified & Min slack & Max slack',timing)
    timing_text=r'''\subsection{Narrow-margin repeat and source sensitivity}
The repaired ALU configuration is run three times using the archived repair
source and three times using the current controller, without further model
changes. Table~\ref{tab:timingrepeat} preserves both arms. The original source
repeats at OLD_SLACK ps, while the current source reaches $NEW_SLACK$ ps and blocks
signoff in all three runs. Reapplying placement padding in later tool processes
is part of the source change; its isolated timing effect is not separately
measured. The result demonstrates a constraint-preserving repair within its
recorded source version, and sensitivity of its narrow margin to controller
changes. It does not establish robust timing closure.
\input{generated/followup_timing_table}
'''
    (PAPER/'generated/followup_timing_text.tex').write_text(timing_text.replace('OLD_SLACK',f'{old_slack[0]*1000:+.3f}').replace('NEW_SLACK',f'{new_slack[0]*1000:.3f}'))
    live=[r for r in rows if r['live_api']];assert len(live)==4
    scale=[]
    for r in live:
        fail=r['initial_failure'];desc=fail.get('summary') or fail.get('reason') or fail.get('stage')
        stage=fail['stage'].replace('_','\\_')
        label=('Spacing' if r['kind']=='accum_spacing' else 'Antenna')+f" {r['replicate']}"
        outcome={'verified':'Verified','provider_interrupted':'API credit interruption','policy_escalation':'Policy escalation'}[r['terminal_outcome']]
        scale.append((label,stage,r['model_calls'],outcome))
    table('followup_scale_table.tex','All four declared live repair episodes for the 1,995-cell accumulator, separate from the original nine-case cohort. Responses count valid model returns; credit-rejected requests are separate.','tab:largerepair','llrl','Case & Initial failed stage & Responses & Outcome',scale)
    success=sum(r['fully_verified'] for r in live)
    calls=sum(r['model_calls'] for r in live)
    interrupted=sum(r['terminal_outcome']=='provider_interrupted' for r in live)
    escalated=sum(r['terminal_outcome']=='policy_escalation' for r in live)
    errors=sum(len(r['provider_errors']) for r in live)
    (PAPER/'generated/followup_scale_text.tex').write_text('\\subsection{Live repair of larger failed implementations}\n'
        'Four additional episodes start from the retained accumulator spacing\n'
        'and antenna configurations, with two declared repeats per configuration.\n'
        'The design, \\code{accum\\_bank32}, contains 32 eight-bit accumulator\n'
        'lanes and a read-selection multiplexer. The antenna configuration selects\n'
        'passive fillers; the spacing configuration retains default fillers.\n'
        'Table~\\ref{tab:largerepair} lists every episode.\n'
        f'Of four episodes, {success} complete the full contract, {escalated} end in policy\n'
        f'escalation and {interrupted} are interrupted by insufficient provider credit.\n'
        f'They record {calls} valid model responses and {errors} rejected provider\n'
        'requests. Each first encounters an actual native\n'
        'failure. These exploratory episodes retain all outcomes and are reported\n'
        'separately from the original injected-fault cohort. The initial failure,\n'
        'every authorized update and native recheck, provider errors and final\n'
        'candidate or failure state are retained in the follow-up catalog.\n'
        'Provider interruptions are not interpreted as algorithmic repair failures.\n'
        'Policy escalation denotes the controller stopping when a proposed\n'
        'remediation would repeat previously failed stage inputs and configuration.\n'
        '\\input{generated/followup_scale_table}\n')
    same=pair['date_neutral_equal'] and all(pair['artifacts'][k]['equal'] for k in ['routed_def','routed_netlist','netlist','spef'])
    (PAPER/'generated/followup_repeat_text.tex').write_text('The one-worker ablation runs shift1024 twice with all other typed settings\n'
        'unchanged. '+('Both runs certify and reproduce routed DEF, mapped/routed netlists, SPEF\nand date-neutral GDS exactly. ' if same else 'Both runs certify, but exact route/GDS reproduction remains incomplete. ')+
        'Raw GDS dates still differ. The pinned binary reports a default thread\n'
        'count of one with the same initialization flags, as confirmed by a retained\n'
        'native query. This controlled pair supports worker-count\n'
        'sensitivity in the observed repeat behavior; it does not isolate a native\n'
        'algorithmic race or establish universal determinism from two executions.\n')
    normsame=pair['implementation_identities'][0]['implementation_id']==pair['implementation_identities'][1]['implementation_id']
    (PAPER/'generated/implementation_identity_text.tex').write_text(
        f'The supplemental fingerprint matches in {sum(r["equal"] for r in ids)} of seven\noriginal pairs and '+('matches' if normsame else 'differs')+' in the one-worker pair. Native release IDs\nremain distinct, because they also bind raw GDS, reports and path-bearing\ncharacterization records. Timestamp-only normalization of GDS therefore cannot\nstabilize the entire release identity by itself.\n')
    print(json.dumps({'timing':timing,'single_worker_exact':same,'large_verified':success,'large_calls':calls},indent=2))

if __name__=='__main__':main()
