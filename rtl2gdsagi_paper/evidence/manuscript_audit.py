"""Check registered numerical and file assertions; semantic review is separate."""
from pathlib import Path
import csv, hashlib, json, re, tarfile
import xml.etree.ElementTree as ET
PAPER=Path(__file__).resolve().parents[1];ROOT=PAPER.parent
load=lambda name:json.loads((PAPER/'evidence'/name).read_text())
data=load('live_results.json');rows=data['runs']
repair=load('repair_study.json');fault=load('native_fault_injection.json');repeat=load('reproducibility_final.json')
assert len(rows)>=5 and len({r['design'] for r in rows})==len(rows)
assert max(r['synthesis_cells'] for r in rows)>=1000
for r in rows:
    assert r['clean'] and r['stages_passed']==21
    assert r['route_violations']==r['drc_violations']==0
    assert r['lvs_match'] and r['lec_synthesis_partitions']>0 and r['lec_route_partitions']>0
    assert r['setup_wns_ns']>=0 and r['hold_wns_ns']>=0
    assert r['setup_tns_ns']==r['hold_tns_ns']==0
    assert r['spef_coverage']==1 and r['authoritative_testbenches']>0
    assert r['antenna_net_violations']==r['antenna_pin_violations']==0
    assert r['drc_categories']==211 and r['model_calls']==0
    run=ROOT/r['run_dir']
    for script in ['stages/10_cts/cts.tcl','stages/12_routing/routing.tcl']:
        assert 'set_placement_padding' in (run/script).read_text()
    lec=(run/'stages/05_lec_synth/lec_synth.tcl').read_text()
    assert '[options]\nsplitnets on' in lec and '[collect *]\ngroup *' in lec
csv_rows=list(csv.DictReader((PAPER/'evidence/signoff_metrics.csv').open()))
assert len(csv_rows)==len(rows)
for r,c in zip(rows,csv_rows):
    assert r['design']==c['design']
    for k in ('synthesis_area_um2','setup_wns_ns','hold_wns_ns','die_area_um2'):assert float(c[k])==r[k]
assert repair['episodes']==9 and repair['verified']==7 and repair['escalated']==2 and repair['provider_calls']==20
assert all(t['initial_check']['ok'] is False and t['model_calls']>0 for t in repair['trials'])
for t in repair['trials']:
    if t['failure_type']=='timing':
        assert t['initial_check']['setup_wns']<0
        files=list((ROOT/t['run_dir']/'stages/03_sdc').glob('*.sdc'));assert len(files)==1
        assert '-period 3.0000' in files[0].read_text()
        if t['fully_verified']:
            assert t['metrics']['setup_wns_ns']>0
            assert all(v['rtl_identity_preserved'] and v['repair_verified'] for v in t['metrics']['repair_verifications'] if v.get('result')=='resolved')
assert len(fault['results'])==18 and fault['naive_clean']==fault['candidate_blocked']==18
assert len({r['attack'] for r in fault['results']})==6
assert all(r['naive_clean'] and r['blocked'] and r['reasons'] for r in fault['results'])
assert len(repeat['pairs'])==len(rows)
assert repeat['exact_route_pairs']==sum(r['route_bundle_equal'] for r in repeat['pairs'])
for name,expected in [('source_final.tar.gz',data['manifest']['source_sha256']),('source_repair_cohort.tar.gz',data['manifest']['repair_source_sha256'])]:
    h=hashlib.sha256()
    with tarfile.open(PAPER/'evidence'/name) as archive:
        for m in sorted(archive.getmembers(),key=lambda m:m.name):
            if m.isfile() and m.name.endswith('.py'):
                h.update(m.name.encode()+b'\0');h.update(archive.extractfile(m).read())
    assert h.hexdigest()==expected,(name,h.hexdigest(),expected)
suite=ET.parse(ROOT/data['manifest'].get('pytest_report','rtl2gdsagi_paper/evidence/pytest_final_release.xml')).getroot().find('testsuite')
assert int(suite.get('failures'))==int(suite.get('errors'))==0 and data['source_matches_extraction']
main=(PAPER/'main.tex').read_text()
refs=set(re.findall(r'\\bibitem\{([^}]+)\}',main));cites={k for group in re.findall(r'\\cite\{([^}]+)\}',main) for k in group.split(',')}
assert refs==cites and len(refs)>=12
ordered_refs=re.findall(r'\\bibitem\{([^}]+)\}',main)
first=[]
for group in re.findall(r'\\cite\{([^}]+)\}',main):
    for key in group.split(','):
        if key not in first:first.append(key)
assert ordered_refs==first,'Springer references must follow the requested first-citation order'
assert r'\titlerunning{Candidate-Bound Evidence for RTL-to-GDS Signoff}' in main
followup=load('reviewer_followup.json')
assert len(followup['trials'])==12 and followup['manifest']['consistent_source']
for kind,clean in [('timing_original',True),('timing_current',False)]:
    group=[r for r in followup['trials'] if r['kind']==kind]
    assert len(group)==3 and all(r['fully_verified']==clean for r in group)
    assert all((r['last_routed_check']['setup_wns']>0)==clean for r in group)
single=followup['single_worker_pair']
assert single['date_neutral_equal'] and all(single['artifacts'][k]['equal'] for k in ['routed_def','routed_netlist','netlist','spef'])
assert single['implementation_identities'][0]['implementation_id']==single['implementation_identities'][1]['implementation_id']
assert single['implementation_identities'][0]['release_candidate_id']!=single['implementation_identities'][1]['release_candidate_id']
large=[r for r in followup['trials'] if r['live_api']]
assert len(large)==4 and all(r['initial_failure'] for r in large)
assert sum(r['model_calls'] for r in large)==23
assert sum(len(r['provider_errors']) for r in large)==2
assert sum(r['terminal_outcome']=='policy_escalation' for r in large)==2
assert sum(r['terminal_outcome']=='provider_interrupted' for r in large)==2
assert not any(r['fully_verified'] for r in large)
assert single['native_default_thread_probe']['native_default_thread_count']==1
external=load('external_fault_coverage.json')
assert external['status']=='completed' and len(external['coverage'])==6
assert all(r['result'] in ('detected','not_detected','not_checked') for r in external['coverage'])
assert r'\documentclass[runningheads]{llncs}' in main
for token in ('IEEEtran','Authors should confirm','pre-deletion','restored benchmark','recovered from','ContinuationSourceShort'):assert token not in main
log=(PAPER/'main.log').read_text();assert not re.search(r'Overfull|Undefined|LaTeX Warning|! LaTeX Error',log)
report={'designs':len(rows),'largest_cells':max(r['synthesis_cells'] for r in rows),'stages':21,'fault_coverage_classes':6,'fault_consistency_executions':18,'live_episodes':9,'verified_repairs':7,'provider_calls':20,'references':len(refs),'tests':data['tests'],'followup_executions':12,'large_live_episodes':4,'large_verified':sum(r['fully_verified'] for r in large),'large_policy_escalations':2,'large_provider_interruptions':2,'large_valid_responses':23,'large_credit_rejections':2,'single_worker_native_default':1,'scope':'Registered numerical and file assertions; semantic review is separately disclosed.'}
(PAPER/'evidence/manuscript_audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
