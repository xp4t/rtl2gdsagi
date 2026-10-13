#!/usr/bin/env python3
"""Validate the complete frozen cohorts and render their measured paper tables."""
import hashlib
import json
from pathlib import Path
from compare_repeated_runs import date_neutral_gds
from extract_signoff_metrics import extract
from generate_extended_results import table
from implementation_identity import implementation_identity
from run_signoff_benchmark import source_identity

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / 'rtl2gdsagi_paper'
EVIDENCE = PAPER / 'evidence'
load = lambda path: json.loads((ROOT / path).read_text())


def main():
    source = source_identity()
    manifest = load('runs/frozen_evaluation_20261013/experiment_manifest.json')
    assert manifest['source_sha256'] == source and manifest['consistent_source']
    assert len(manifest['declared_cases']) == len(manifest['trials']) == 14
    assert all(v['status'] == 'ok' for v in manifest['trials'].values())
    repeat = load('rtl2gdsagi_paper/evidence/reproducibility_final.json')
    assert repeat['source_sha256'] == source and repeat['exact_route_pairs'] == repeat['normalized_gds_pairs'] == 7
    repeat_rows=[]
    for pair in repeat['pairs']:
        repeat_rows.append((pair['design'].replace('_','\\_'),
                            'Same' if pair['artifacts']['routed_def']['equal'] else 'Different',
                            'Same' if pair['artifacts']['spef']['equal'] else 'Different',
                            'Same' if pair['artifacts']['final_gds']['equal'] else 'Different',
                            'Same' if pair['gds_date_neutral_equal'] else 'Different'))
    table('reproducibility_table.tex','Seven frozen primary pairs. Date normalization zeros only BGNLIB/BGNSTR payloads; all other GDS bytes remain unchanged. Both netlists also match in every pair.','tab:reproducibility','lllll','Design & Routed DEF & SPEF & Raw GDS & Dates zeroed',repeat_rows)
    identities = []
    for pair in repeat['pairs']:
        values = [implementation_identity(ROOT / p) for p in pair['runs']]
        assert values[0]['implementation_id'] == values[1]['implementation_id']
        identities.append({'design': pair['design'], 'identities': values})
    ablation = load('runs/padding_thread_ablation_20261013/experiment_manifest.json')
    assert ablation['base_source_sha256'] == source and ablation['consistent_production_source']
    assert len(ablation['trials']) == len(ablation['declared_cases']) == 8
    matrix = []
    for cts in (False, True):
        for routing in (False, True):
            group = [v for v in ablation['trials'].values() if v['cts_padding'] == cts and v['routing_padding'] == routing]
            assert len(group) == 2 and {v['routing_workers'] for v in group} == {1, 8}
            values = [v['routed_timing']['setup_wns'] for v in group]
            assert values[0] == values[1]
            matrix.append(('On' if cts else 'Off', 'On' if routing else 'Off', '1, 8', f'{values[0]*1000:+.3f}', f"{sum(v['status']=='ok' for v in group)}/2"))
    table('padding_thread_table.tex', 'Controlled padding and thread ablation at unchanged 3 ns. Each row contains one run at each worker count. Padding refers to reapplication after placement; placement padding itself stays at one site. Slack is measured after routing.', 'tab:paddingthread', 'lllrr', 'CTS padding & Route padding & Workers & Setup (ps) & Certified', matrix)
    before = load('runs/padding_thread_ablation_20261013/cts0_route1_workers1/run_state.json')['artifacts']
    after = load('runs/padding_thread_ablation_20261013/cts1_route1_workers1/run_state.json')['artifacts']
    assert before['netlist']['sha256'] == after['netlist']['sha256']
    assert before['placement_def']['sha256'] == after['placement_def']['sha256']
    assert before['cts_def']['sha256'] != after['cts_def']['sha256']
    archived = load('rtl2gdsagi_paper/evidence/repair_study.json')
    replay = load('runs/frozen_proposal_replay_complete_ir_20261013/experiment_manifest.json')
    assert replay['source_sha256'] == source and replay['consistent_source'] and len(replay['trials']) == 20
    rows = []
    class_results = {}
    for kind, label in [('drc','Spacing'), ('pdn','PDN'), ('timing','Timing')]:
        old = [p for r in archived['trials'] if r['failure_type'] == kind for p in r['proposals']]
        fresh = [r for r in replay['trials'].values() if r['failure_type'] == kind]
        assert len(old) == len(fresh)
        failure = sum(p['native_recheck'] == 'native_failure' for p in old)
        missing = sum(p['native_recheck'] == 'required_target_unavailable' for p in old)
        new_failure = sum(bool(r['failed_checks']) for r in fresh)
        certified = 0
        for r in fresh:
            assert r['status'] in ('ok','failed')
            if r['status'] == 'ok':
                assert extract(ROOT / r['run_dir'])['clean']; certified += 1
            else: assert r['failed_checks']
        n = len(old)
        class_results[kind] = {'proposals': n, 'archived_native_failures': failure,
                              'archived_target_unavailable': missing, 'frozen_native_failures': new_failure,
                              'frozen_certified': certified,
                              'archived_failure_fraction': failure/n, 'frozen_failure_fraction': new_failure/n}
        rows.append((label, n, f'{failure}/{n}', f'{missing}/{n}', f'{new_failure}/{n}', f'{certified}/{n}'))
    table('class_replay_table.tex', 'Proposal replay by originating fixture class. A hypothetical gate accepting each proposal without rechecks would promote every row state. Failed means a native hard check failed; missing evidence is separate. Frozen outcomes are separate native executions of the same proposal states.', 'tab:classreplay', 'lrrrrr', r'Class & Proposals & \shortstack{Archived\\failed} & \shortstack{Archived\\missing} & \shortstack{Frozen\\failed} & \shortstack{Frozen\\certified}', rows)
    fault = load('rtl2gdsagi_paper/evidence/native_fault_injection_frozen.json')
    assert fault['source_sha256'] == source and fault['attack_classes'] == 6 and fault['candidate_blocked'] == 18
    by_class = {}
    for r in fault['results']: by_class.setdefault(r['attack'], []).append(r)
    assert len(by_class) == 6 and all(len(v)==3 and all(r['blocked'] for r in v) for v in by_class.values())
    labels = {'stale_gds_fed_to_drc':'Stale same-top GDS','drc_deck_missing_feol_rules':'Missing FEOL rules',
              'lvs_no_real_compare':'LVS without compare','missing_pdn_via_connection':'Missing PDN vias',
              'missing_layer_map_streamout':'Missing layer map','artifact_swap_after_verified_repair':'Artifact swap after repair'}
    mechanism = {'stale_gds_fed_to_drc':'Selected input hash and invocation binding',
                 'drc_deck_missing_feol_rules':'Approved deck and active category inventory',
                 'lvs_no_real_compare':'Executable comparison and circuit cross-references',
                 'missing_pdn_via_connection':'Structural supply and vertical connection checks',
                 'missing_layer_map_streamout':'Bound map and routed-layer geometry checks',
                 'artifact_swap_after_verified_repair':'Cached gate lineage and artifact rehashing'}
    table('frozen_fault_table.tex', 'Coverage of six constructed fault classes on the frozen controller. Three executions per class establish consistent fixture behavior, not independent samples.', 'tab:frozenfaults', 'p{0.28\\linewidth}p{0.54\\linewidth}r', 'Constructed class & Blocking obligation & Blocks', [(labels[k], mechanism[k], '3/3') for k in by_class])
    audit = load('rtl2gdsagi_paper/evidence/openlane_invocation_audit.json')
    assert audit['status'] == 'completed'
    for execution in audit['executions']:
        for key in ('stdout','stderr'):
            item = execution[key]
            assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() == item['sha256']
    supplied = {(r['configuration'],r['obligation']):r['classification'] for r in audit['obligations']}
    assert supplied[('legacy_native','report_m1.1')] == 'SUPPORTED'
    assert supplied[('legacy_native','report_poly.1a')] == 'NOTSUPPORTED'
    # The raw stock-wrapper diagnostics are retained, but are not an active-DRC
    # baseline. The table reports supported obligations of executed interfaces.
    support = [
        ('Configured geometric marker reporting','Supported','Positive/clean controls; deck and options specified'),
        ('Missing PDN via connectivity','Supported','Native supply checks with untouched DEF controls'),
        ('Selected candidate and cached lineage','Not designed for','No release-manifest interface in these checker calls'),
        ('Approved deck / active inventory','Not designed for','Rule execution differs from inventory approval'),
        ('Retained KLayout no-compare fixture via Netgen','Not assessed','Report formats are incompatible'),
        ('Mapping provenance','Not designed for','Required map option does not establish selected-map identity'),
    ]
    table('checker_obligations_table.tex', 'Obligation remit of the executed OpenLane interfaces and configured native controls. These are stage/checker observations, not a complete-flow detection comparison.', 'tab:checkerobligations', r'>{\raggedright\arraybackslash}p{0.30\linewidth}>{\raggedright\arraybackslash}p{0.17\linewidth}>{\raggedright\arraybackslash}p{0.43\linewidth}', 'Obligation & Checker remit & Executed scope', support)
    controls = audit['controls']
    control_rows = []
    for name, label in [('legacy_native','Legacy native deck'),('modern_direct_pdk_options','Modern deck, PDK options'),('modern_adapter_native','Modern wrapper adapter')]:
        group = [r for r in controls if r['configuration'] == name]
        if not group: continue
        positives = {r['fixture']:r for r in group}
        # Individual counts and native category inventories remain in the JSON;
        # a separate source-derived control table is created from verified rows.
        control_rows.append({'configuration':name,'label':label,'controls':group})
    measured_controls = []
    for row in control_rows:
        by_fixture = {r['fixture']: r for r in row['controls']}
        positive = [by_fixture[k+'_positive']['metrics']['markers'] for k in ('metal','poly','grid')]
        negative = [by_fixture[k+'_negative']['metrics']['markers'] for k in ('metal','poly','grid')]
        categories = {r['metrics']['categories'] for r in row['controls']}
        assert len(categories)==1 and negative==[0,0,0]
        measured_controls.append((row['label'],categories.pop(),'/'.join(map(str,positive)),'/'.join(map(str,negative))))
    table('configured_drc_controls_table.tex','Paired synthetic DRC controls. Marker columns list metal/poly/off-grid fixtures. Modern controls use the PDK runtime options; the adapter is an explicit sidecar change. The inactive prior wrapper is a configuration diagnostic, excluded from this active-checker table.','tab:drccontrols','lrrr','Executed configuration & Categories & Violating markers & Clean markers',measured_controls)
    followup = load('rtl2gdsagi_paper/evidence/reviewer_followup.json')
    large = [r for r in followup['trials'] if r['live_api']]
    assert len(large)==4 and sum(r['model_calls'] for r in large)==23
    policy = {}
    for name in ('accum_spacing_2','accum_antenna_1'):
        folder = ROOT / 'runs/reviewer_followup_20261013' / name
        events = [json.loads(l) for l in (folder/'run.jsonl').read_text().splitlines()]
        updates = [e for e in events if e.get('event')=='config_generated' and e.get('delta')]
        policy[name] = {'last_delta':updates[-1]['delta'], 'failure_report':str((folder/'failure_report.md').relative_to(ROOT))}
    result = {'implementation_source_sha256':source,'primary_manifest':manifest,'primary_reproducibility':repeat,
              'implementation_identities':identities,'padding_thread_ablation':ablation,
              'cts_intervention_artifact_comparison':{k:before[k]['sha256']==after[k]['sha256'] for k in ['netlist','placement_def','cts_def','routed_netlist','routed_def','spef']},
              'proposal_generation_source_sha256':replay['proposal_generation_source_sha256'],
              'class_replay':class_results,'proposal_replay_manifest':replay,
              'fault_coverage':fault,'native_checker_audit':'rtl2gdsagi_paper/evidence/openlane_invocation_audit.json',
              'native_control_rows':control_rows,'large_cases':large,'policy_proposals':policy,
              'scope':'Fresh native evaluation and fixed recorded proposals; no new model calls. Original live cohorts and incomplete outcomes retained separately.'}
    (EVIDENCE/'frozen_results.json').write_text(json.dumps(result,indent=2)+'\n')
    macros = {'FrozenSourceShort':source[:12], 'ProposalSourceShort':replay['proposal_generation_source_sha256'][:12],
              'FrozenPrimaryPairs':len(repeat['pairs']),'FrozenRawGDSPairs':repeat['raw_gds_pairs'],
              'ArchivedTimingWrong':class_results['timing']['archived_native_failures'],
              'ArchivedTimingWrongPct':f"{100*class_results['timing']['archived_failure_fraction']:.1f}",
              'ArchivedTimingMissing':class_results['timing']['archived_target_unavailable'],
              'TimingProposalCount':class_results['timing']['proposals'],
              'FrozenTimingWrong':class_results['timing']['frozen_native_failures'],
              'FrozenTimingWrongPct':f"{100*class_results['timing']['frozen_failure_fraction']:.1f}"}
    (PAPER/'generated/frozen_macros.tex').write_text('% Generated from validated frozen cohorts.\n'+''.join(f'\\newcommand{{\\{k}}}{{{v}}}\n' for k,v in macros.items()))
    print(json.dumps({'source':source,'primary_pairs':7,'class_replay':class_results,'fault_classes':6},indent=2))


if __name__ == '__main__':
    main()
