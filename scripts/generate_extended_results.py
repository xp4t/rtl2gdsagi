#!/usr/bin/env python3
"""Generate manuscript attack, repair, repeat and stress results from live JSON."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT/'rtl2gdsagi_paper'
OUT = PAPER/'generated'
def read(name): return json.loads((PAPER/'evidence'/name).read_text())
def table(name, caption, label, columns, header, rows):
    text = '\\begin{table}[htbp]\\centering\\small\\setlength{\\tabcolsep}{4pt}\n'
    text += f'\\caption{{{caption}}}\\label{{{label}}}\n'
    text += '\\begin{tabular}{@{}'+columns+'@{}}\\toprule\n'+header+' \\\\\n\\midrule\n'
    text += ''.join(' & '.join(str(v) for v in row)+' \\\\\n' for row in rows)
    text += '\\bottomrule\\end{tabular}\\end{table}\n'
    (OUT/name).write_text(text)

def main():
    live=read('live_results.json'); repair=read('repair_study.json')
    fault=read('native_fault_injection.json'); repeat=read('reproducibility_final.json')
    success=next(t for t in repair['trials'] if t['failure_type']=='timing' and t['fully_verified'])
    counter=ROOT/'runs/counter_timing_stress_1p5ns/run.jsonl'
    checks=[json.loads(l) for l in counter.read_text().splitlines()]
    counter_check=next(e for e in reversed(checks) if e.get('event')=='result_check' and e.get('stage')=='sta_signoff')
    assert not counter_check['ok'] and counter_check['setup_wns']<0
    macros={'NativeAttackTrials':len(fault['results']), 'NativeBlocked':fault['candidate_blocked'],
            'NativeFalseClean':fault['naive_clean'], 'DegradedRuleCount':next(r['categories'] for r in fault['results'] if r['attack']=='drc_deck_missing_feol_rules'),
            'StudyEpisodes':repair['episodes'],'StudyVerified':repair['verified'],'StudyEscalated':repair['escalated'],
            'StudySuccessPct':f"{100*repair['verified']/repair['episodes']:.1f}",
            'StudyEscalationPct':f"{100*repair['escalated']/repair['episodes']:.1f}",
            'StudyModelCalls':repair['provider_calls'],'StudyInputTokens':repair['input_tokens'],'StudyOutputTokens':repair['output_tokens'],
            'ProposalPromotions':repair['no_recheck_baseline']['promotions'],
            'ConfirmedBadProposals':repair['no_recheck_baseline']['confirmed_native_failures'],
            'UncheckedProposals':repair['no_recheck_baseline']['required_target_unavailable'],
            'TimingBefore':f"{success['initial_check']['setup_wns']:.6f}",
            'TimingAfter':f"{success['metrics']['setup_wns_ns']:.6f}",
            'CounterStressWNS':f"{counter_check['setup_wns']:.6f}",
            'LargeCells':max(r['synthesis_cells'] for r in live['runs']),
            'RepairSourceShort':repair['source_manifests'][0]['source_sha256'][:12],
            'ExactRoutePairs':repeat['exact_route_pairs'], 'NormalizedGDSPairs':repeat['normalized_gds_pairs']}
    (OUT/'extended_results.tex').write_text('% Generated from native attack, repair and repeat evidence.\n'+''.join(f'\\newcommand{{\\{k}}}{{{v}}}\n' for k,v in macros.items()))
    attacks=[('stale_gds_fed_to_drc','Stale same-top GDS','DRC 0; input mismatch'),
             ('drc_deck_missing_feol_rules','Missing FEOL rules','DRC 0; 152 categories'),
             ('lvs_no_real_compare','LVS without compare','Match; zero cross-refs'),
             ('missing_pdn_via_connection','Missing PDN connections','Nonempty DEF; zero vias'),
             ('missing_layer_map_streamout','Missing layer map','DRC 0; invalid layer shapes'),
             ('swapped_artifact_after_repair','GDS swap after repair','Cached pass; digest mismatch')]
    actual=set(r['attack'] for r in fault['results'])
    # Permit the exact event spelling retained by the study, never a guessed row.
    swap=actual-set(a[0] for a in attacks[:-1]);assert len(swap)==1
    attacks[-1]=(swap.pop(),attacks[-1][1],attacks[-1][2])
    rows=[]
    for key,label,native in attacks:
        trials=[r for r in fault['results'] if r['attack']==key];assert len(trials)==3
        rows.append((label,native,f"{sum(r['blocked'] for r in trials)}/3"))
    table('fault_table.tex','Detection coverage for six author-constructed fault classes. Three executions per class check consistent behavior; they are not independent trials.','tab:faults','p{0.30\\linewidth}p{0.46\\linewidth}r','Fault class & Native observation & Blocks',rows)
    rows=[]
    for kind,label in [('drc','Spacing: padding 0'),('pdn','PDN: offset 50 $\\mu$m'),('timing','Setup: period 3 ns')]:
        group=[t for t in repair['trials'] if t['failure_type']==kind]; counts=repair['by_failure_type'][kind]
        rows.append((label,counts['trials'],counts['verified'],counts['escalated'],sum(t['model_calls'] for t in group)))
    table('repair_table.tex','All declared live repair episodes. Verified means the complete native signoff contract passed.','tab:repairs','lrrrr','Injected failure & Trials & Verified & Escalated & Calls',rows)
    episodes=[]
    for t in repair['trials']:
        outcome='Verified' if t['fully_verified'] else 'Escalated'
        kind={'drc':'Spacing','pdn':'PDN','timing':'Setup'}[t['failure_type']]
        initial=(f"{t['initial_check']['setup_wns']:.6f} ns" if t['failure_type']=='timing' else '1 marker' if t['failure_type']=='drc' else 'PDN-0185')
        final=(f"{t['metrics']['setup_wns_ns']:.6f} ns" if t['failure_type']=='timing' and t['fully_verified'] else 'Not certified' if not t['fully_verified'] else 'Full signoff')
        episodes.append((f"{kind} {t['replicate']}",initial,final,t['model_calls'],outcome))
    table('episode_table.tex','All nine original live repair episodes on source 18d948815ac6. These archived outcomes are separate from frozen replay and larger episodes.','tab:episodes','lllll','Episode & Initial failure & Final evidence & Calls & Outcome',episodes)
    history=[]
    catalog=[]
    for i,c in enumerate([c for c in repair['all_retained_live_episodes'] if not c['prospective']],1):
        stage=(c['requested_stages'][0] if c['requested_stages'] else c['provider_errors'][0].get('stage','transport'))
        status='Verified' if c['clean'] else 'Stopped; API error' if c['provider_errors'] else 'Stopped; action rejected'
        history.append((f'H{i}',stage.replace('_','\\_'),c['valid_provider_responses'],status))
        catalog.append({'table_id':f'H{i}',**c})
    table('history_table.tex','All retained earlier live API episodes. API errors include authentication, transport and response validation. The catalog preserves their distinct protocols.','tab:history','llrl','Case & First requested stage & Responses & Outcome',history)
    (PAPER/'evidence/historical_episode_map.json').write_text(json.dumps(catalog,indent=2)+'\n')
    yes=lambda v:'Same' if v else 'Different'
    rows=[(r['design'].replace('_','\\_'),yes(r['artifacts']['routed_def']['equal']),yes(r['artifacts']['spef']['equal']),yes(r['artifacts']['final_gds']['equal']),yes(r['gds_date_neutral_equal'])) for r in repeat['pairs']]
    table('reproducibility_table.tex','Paired hashes. GDS (dates zeroed) changes only library/structure date payloads; full digests are supplied in the artifact.','tab:reproducibility','lllll','Design & Routed DEF & SPEF & Raw GDS & Dates zeroed',rows)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'serif','font.size':8,'pdf.fonttype':42})
    fig,ax=plt.subplots(figsize=(4.7,2.35))
    for t,color in zip([t for t in repair['trials'] if t['failure_type']=='timing'],['#0072B2','#D55E00','#009E73']):
        events=[json.loads(l) for l in (ROOT/t['run_dir']/'run.jsonl').read_text().splitlines()]
        values=[e['setup_wns'] for e in events if e.get('event')=='result_check' and e.get('stage')=='sta_signoff' and e.get('setup_wns') is not None]
        ax.plot(range(len(values)),values,'o-',color=color,label=f"Trial {t['replicate']}: "+('verified' if t['fully_verified'] else 'escalated'),markersize=3)
    ax.axhline(0,color='0.4',linestyle='--',linewidth=.7)
    ax.set(xlabel='Native routed check index (0 = injected failure)',ylabel='Setup WNS (ns)')
    ax.xaxis.get_major_locator().set_params(integer=True)
    ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',color='0.9',linewidth=.5)
    ax.legend(frameon=False,fontsize=7,loc='lower right');fig.tight_layout()
    fig.savefig(PAPER/'figures/timing_stress.pdf');plt.close(fig)
    print(json.dumps(macros,indent=2))

if __name__=='__main__':main()
