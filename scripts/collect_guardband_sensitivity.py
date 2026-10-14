#!/usr/bin/env python3
"""Post-hoc 50 ps threshold analysis of retained native timing, no reruns."""
import csv
import hashlib
import json
import math
from pathlib import Path
from run_signoff_benchmark import source_identity

ROOT=Path(__file__).resolve().parents[1]
PAPER=ROOT/'rtl2gdsagi_paper'
G=0.05
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    frozen=json.loads((PAPER/'evidence/frozen_results.json').read_text())
    baseline=json.loads((PAPER/'evidence/scripted_baseline.json').read_text())
    repairs=json.loads((PAPER/'evidence/repair_study.json').read_text())
    cases=[]
    for r in frozen['primary_manifest']['declared_cases']:
        cases.append(('primary',r['trial'],r['run_dir']))
    # Archived terminal certifications give final candidate timing; excluded
    # nonterminal live episodes do not have comparable final signoff states.
    for r in repairs['trials']:
        if r['fully_verified']:cases.append(('archived_live_certified',Path(r['run_dir']).name,r['run_dir']))
    for r in frozen['proposal_replay_manifest']['declared_cases']:
        completed=frozen['proposal_replay_manifest']['trials'][r['trial']]
        cases.append(('frozen_replay',r['trial'],completed['run_dir']))
    for r in baseline['states']:cases.append(('scripted_baseline',r['trial'],r['run_dir']))
    for r in frozen['padding_thread_ablation']['trials'].values():
        cases.append(('padding_ablation',r['trial'],r['run_dir']))
    rows=[]
    for cohort,trial,directory in cases:
        run=ROOT/directory; log=run/'run.jsonl'
        events=[json.loads(l) for l in log.read_text().splitlines()]
        checks={s:next((e for e in reversed(events) if e.get('event')=='result_check' and e.get('stage')==s),{}) for s in ('sta_postcts','sta_signoff')}
        vals={'postcts_hold_wns_ns':checks['sta_postcts'].get('hold_wns'),
              'routed_setup_wns_ns':checks['sta_signoff'].get('setup_wns'),
              'routed_hold_wns_ns':checks['sta_signoff'].get('hold_wns')}
        available=all(v is not None and math.isfinite(v) for v in vals.values())
        certified=(run/'signoff.json').is_file()
        minimum=min(vals.values()) if available else None
        rows.append({'cohort':cohort,'trial':trial,'run_dir':directory,'run_log_sha256':sha(log),
                     'certified_at_recorded_g0':certified,**vals,
                     'minimum_required_slack_ns':minimum,
                     'timing_pass_g0':minimum>=0 if available else None,
                     'timing_pass_g50ps':minimum>=G if available else None,
                     'retained_certification_eligible_g50ps':certified and available and minimum>=G,
                     'failing_g50ps_obligations':[k for k,v in vals.items() if v is not None and v<G],
                     'metric_scope':'Last recorded timing checkpoints; eligibility only for already certified terminal states.'})
    summaries={}
    for cohort in sorted({r['cohort'] for r in rows}):
        values=[r for r in rows if r['cohort']==cohort]
        summaries[cohort]={'states':len(values),'recorded_certifications_g0':sum(r['certified_at_recorded_g0'] for r in values),
                           'complete_timing_states':sum(r['timing_pass_g50ps'] is not None for r in values),
                           'certified_states_eligible_g50ps':sum(r['retained_certification_eligible_g50ps'] for r in values)}
    primary=[r for r in rows if r['cohort']=='primary']
    assert len(primary)==14 and sum(r['retained_certification_eligible_g50ps'] for r in primary)==12
    assert {r['trial'] for r in primary if not r['retained_certification_eligible_g50ps']}=={'shift1024_a','shift1024_b'}
    archived=next(r for r in rows if r['cohort']=='archived_live_certified' and r['trial']=='timing_1')
    assert archived['routed_setup_wns_ns']==0.0015860646578364705 and not archived['retained_certification_eligible_g50ps']
    result={'source_sha256':source_identity(),'guardband_ns':G,'guardband_ps':50,
            'scope':'Post-hoc threshold sensitivity of existing slacks: post-CTS hold and routed setup/hold must all meet g. Other gates held at recorded outcomes; no modified constraints, native reruns or new certificates.',
            'excluded_archived_live_episodes':'Two noncertified episodes lack terminal certified candidate timing and are not reclassified.',
            'summaries':summaries,'rows':rows,'script_sha256':sha(Path(__file__))}
    (PAPER/'evidence/guardband_sensitivity.json').write_text(json.dumps(result,indent=2)+'\n')
    columns=[k for k in rows[0] if k!='metric_scope']
    with (PAPER/'evidence/guardband_sensitivity_metrics.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns);w.writeheader()
        for row in rows:w.writerow({k:(';'.join(row[k]) if isinstance(row[k],list) else 'not reached' if row[k] is None else row[k]) for k in columns})
    macros={'GuardbandPrimaryDesigns':6,'GuardbandPrimaryRuns':12,
            'GuardbandShiftHoldPs':f"{next(r for r in primary if r['trial']=='shift1024_a')['routed_hold_wns_ns']*1000:.3f}",
            'GuardbandShiftShortfallPs':f"{(G-next(r for r in primary if r['trial']=='shift1024_a')['routed_hold_wns_ns'])*1000:.3f}"}
    diagnostic=json.loads((PAPER/'evidence/setup_repair_diagnostic.json').read_text())
    assert len(diagnostic['trials'])==8 and diagnostic['consistent_source']
    for r in diagnostic['trials']:
        assert sha(ROOT/r['log'])==r['log_sha256']
        assert r['command_entered_and_returned'] and r['setup_repair_def_unchanged'] and r['setup_repair_netlist_unchanged'] and r['final_cts_def_matches_archived']
        assert r['before_setup']==r['after_setup'] and r['before_setup']['setup_wns_ns']>G
        assert r['zero_wire_capacitance_warning'] and r['wire_load_fallback_warning']
    setup=[r['before_setup']['setup_wns_ns']*1000 for r in diagnostic['trials']]
    macros.update(SetupRepairPreMinPs=f'{min(setup):.3f}',SetupRepairPreMaxPs=f'{max(setup):.3f}')
    (PAPER/'generated/guardband_macros.tex').write_text('% Generated from retained native checkpoints; post-hoc sensitivity only.\n'+''.join(f'\\newcommand{{\\{k}}}{{{v}}}\n' for k,v in macros.items()))
    selected=[next(r for r in primary if r['trial']==d+'_a') for d in ('register','mux4to1','alu8','counter','shift_reg','fifo_buf','shift1024')]+[archived]
    lines=[r'\begin{table}[!htbp]\centering\small',
           r'\caption{Post-hoc 50 ps guardband sensitivity. All listed candidates were certified at $g=0$; both primary repeats have these same slacks. Eligibility also requires post-CTS hold. No new certificates are issued.}\label{tab:guardband}',
           r'\begin{tabular}{@{}lrrrr@{}}\toprule',
           r'Candidate & \shortstack{Post-CTS\\hold (ps)} & \shortstack{Routed\\setup (ps)} & \shortstack{Routed\\hold (ps)} & $g=50$ ps\\\midrule']
    for row in selected:
        label=row['trial'].removesuffix('_a').replace('_',r'\_') if row['cohort']=='primary' else 'Archived timing repair'
        numbers=[f"{row[k]*1000:.3f}" for k in ('postcts_hold_wns_ns','routed_setup_wns_ns','routed_hold_wns_ns')]
        lines.append(' & '.join([label,*numbers,'Pass' if row['retained_certification_eligible_g50ps'] else 'Fail'])+r'\\')
    lines += [r'\bottomrule\end{tabular}\end{table}']
    (PAPER/'generated/guardband_table.tex').write_text('\n'.join(lines)+'\n')
    print(json.dumps(summaries,indent=2))


if __name__=='__main__':main()
