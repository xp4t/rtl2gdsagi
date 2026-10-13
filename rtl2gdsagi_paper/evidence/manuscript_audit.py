"""Audit the numerical/source/input claims of the frozen revision."""
from pathlib import Path
import csv, hashlib, json, re, tarfile
import sys
import xml.etree.ElementTree as ET
PAPER=Path(__file__).resolve().parents[1];ROOT=PAPER.parent
sys.path.insert(0,str(ROOT/'scripts'))
from extract_signoff_metrics import extract
from run_signoff_benchmark import source_identity
from manuscript_materials import manuscript_materials
load=lambda n:json.loads((PAPER/'evidence'/n).read_text())
main=(PAPER/'main.tex').read_text();supp=(PAPER/'supplement.tex').read_text()
data=load('frozen_results.json');live=load('live_results.json');manifest=load('experiment_manifest.json')
assert data['implementation_source_sha256']==manifest['source_sha256']==source_identity()
assert data['primary_manifest']['consistent_source'] and len(data['primary_manifest']['trials'])==14
assert len(live['runs'])==7 and all(r['clean'] and r['stages_passed']==21 for r in live['runs'])
for selection in manifest['selected_runs']:
 for key in ['run_dir','repeat_run_dir']:
  row=extract(ROOT/selection[key])
  assert row['route_violations']==row['drc_violations']==0
  assert row['antenna_net_violations']==row['antenna_pin_violations']==0
  assert row['setup_wns_ns']>=0 and row['hold_wns_ns']>=0
  assert row['setup_tns_ns']==row['hold_tns_ns']==0
  assert row['lvs_match'] and row['spef_coverage']==1 and row['authoritative_testbenches']>0
  assert row['drc_categories']==211 and row['model_calls']==0
  assert row['lec_synthesis_partitions']>0 and row['lec_route_partitions']>0
repeat=data['primary_reproducibility']
assert repeat['exact_route_pairs']==repeat['normalized_gds_pairs']==7
assert all(p['route_bundle_equal'] and p['gds_date_neutral_equal'] for p in repeat['pairs'])
rendered=(PAPER/'generated/reproducibility_table.tex').read_text()
for pair in repeat['pairs']:
 raw='Same' if pair['artifacts']['final_gds']['equal'] else 'Different'
 assert pair['design'].replace('_',r'\_')+' & Same & Same & '+raw+' & Same' in rendered

assert all(v['identities'][0]['implementation_id']==v['identities'][1]['implementation_id'] for v in data['implementation_identities'])
for selection in manifest['selected_runs']:
 if selection['run_dir'].endswith('/shift1024'):
  for key in ['run_dir','repeat_run_dir']:
   b=json.loads((ROOT/selection[key]/'signoff.json').read_text());assert b['ir']['routing']['num_threads']==1
csv_rows=list(csv.DictReader((PAPER/'evidence/signoff_metrics.csv').open()))
assert len(csv_rows)==7
for row,record in zip(live['runs'],csv_rows):
 assert row['design']==record['design']
 for key in ['setup_wns_ns','hold_wns_ns','die_area_um2','synthesis_area_um2']:assert row[key]==float(record[key])
for kind,count in [('drc',3),('pdn',3),('timing',14)]:
 v=data['class_replay'][kind];assert v['proposals']==count
 assert v['frozen_native_failures']==(14 if kind=='timing' else 0)
 assert v['frozen_certified']==(0 if kind=='timing' else 3)
assert data['class_replay']['timing']['archived_native_failures']==11
assert data['class_replay']['timing']['archived_target_unavailable']==2
replay=data['proposal_replay_manifest'];assert len(replay['trials'])==20 and replay['consistent_source']
assert sum(v['status']=='ok' for v in replay['trials'].values())==6
assert sum(any(e['stage']=='sta_signoff' for e in v['failed_checks']) for v in replay['trials'].values())==13
assert sum(any(e['stage']=='placement' for e in v['failed_checks']) for v in replay['trials'].values())==1
ablation=data['padding_thread_ablation'];assert len(ablation['trials'])==8 and ablation['consistent_production_source']
for v in ablation['trials'].values():
 assert v['routed_timing'] and (v['routed_timing']['setup_wns']<0)==v['cts_padding']
 cfg=(ROOT/v['config']).read_text();assert 'default_clock_period_ns: 3.0' in cfg
assert data['cts_intervention_artifact_comparison']['netlist'] and data['cts_intervention_artifact_comparison']['placement_def']
assert not data['cts_intervention_artifact_comparison']['cts_def']
fault=data['fault_coverage'];assert fault['attack_classes']==6 and len(fault['results'])==fault['candidate_blocked']==18
assert all(r['blocked'] and r['reasons'] for r in fault['results'])
for path,expected in [(manifest['source_archive'],manifest['source_sha256']),('rtl2gdsagi_paper/evidence/source_repair_cohort.tar.gz',manifest['archived_repair_source_sha256'])]:
 h=hashlib.sha256()
 with tarfile.open(ROOT/path) as tar:
  for m in sorted(tar.getmembers(),key=lambda m:m.name):
   if m.isfile() and m.name.endswith('.py'):h.update(m.name.encode()+b'\0'+tar.extractfile(m).read())
 assert h.hexdigest()==expected,path
large=data['large_cases'];assert len(large)==4 and sum(r['model_calls'] for r in large)==23
assert not any(r['fully_verified'] for r in large)
assert sum(r['terminal_outcome']=='policy_escalation' for r in large)==2
assert len([r for r in large if r['terminal_outcome']!='policy_escalation'])==2
for key,expected in [('counter_grouped','PASS'),('shift_grouped','PASS'),('counter_mutant','FAIL')]:
 p=ROOT/manifest['formal_controls'][key];assert p.is_file() and p.name==expected
suite=ET.parse(ROOT/manifest['pytest_report']).getroot().find('testsuite')
assert int(suite.get('failures'))==int(suite.get('errors'))==0
assert int(suite.get('tests'))-int(suite.get('skipped'))==955
refs=re.findall(r'\\bibitem\{([^}]+)\}',main);first=[]
for group in re.findall(r'\\cite\{([^}]+)\}',main):
 for key in group.split(','):
  if key not in first:first.append(key)
assert first==refs and len(refs)==16
assert r'\documentclass[runningheads]{llncs}' in main
assert r'\titlerunning{Candidate-Bound Evidence for RTL-to-GDS Signoff}' in main
for token in ['IEEEtran','Authors should confirm','recovered from','pre-deletion','quota','API usage limit']:
 assert token.lower() not in (main+supp).lower(),token
for doc in ['main','supplement']:
 log=(PAPER/(doc+'.log')).read_text();assert not re.search(r'Overfull|LaTeX Warning|Undefined|! LaTeX Error',log)
 for name in re.findall(r'\\label\{([^}]+)\}',(PAPER/(doc+'.tex')).read_text()):
  assert re.search(r'\\(?:ref|eqref)\{'+re.escape(name)+r'\}',(PAPER/(doc+'.tex')).read_text()),name
assert all(p.exists() for p in manuscript_materials(PAPER))
base=load('scripted_baseline.json');assert base['source_sha256']==manifest['source_sha256'] and len(base['states'])==24
assert base['new_model_calls']==0
assert len(base['setup_toggle_outcome_equivalent_pairs'])==8
assert [(base['groups'][k]['states'],base['groups'][k]['certified']) for k in ('drc','pdn','timing','period')]==[(4,3),(2,1),(16,0),(2,1)]
assert base['groups']['timing']['best_setup_wns_ns']==-0.000653699335387172
for row in base['states']:
 events=[json.loads(l) for l in (ROOT/row['run_dir']/'run.jsonl').read_text().splitlines()]
 assert not any(e.get('event') in ('api_call','config_generated') for e in events)
 if row['fully_certified']:assert extract(ROOT/row['run_dir'])['clean']
 else:assert any(e.get('event')=='result_check' and not e.get('ok',True) for e in events)
replay_split=load('replay_stratified_audit.json')['summary']
assert replay_split['reconstruction_consistency_matches']==20
assert replay_split['independent_archived_full_ir_matches']==7
assert replay_split['timing_failure_classes_after_exclusion']=={'signoff_setup_sta':12,'placement_DPL-0036':1}
assert 'live repair was not re-executed on the frozen' in main
assert 'verified repair' not in re.search(r'\\keywords\{([\s\S]*?)\}',main)[1].lower()
assert 'credit-interrupted' in main and '0 of 4' in main
assert 'Not designed for' in (PAPER/'generated/checker_obligations_table.tex').read_text()

report={'source_sha256':source_identity(),'primary_designs':7,'primary_native_runs':14,'primary_exact_route_pairs':7,'primary_date_normalized_gds_pairs':7,'fresh_replayed_proposals':20,'class_replay':data['class_replay'],'ablation_runs':8,'fault_classes':6,'fault_executions':18,'original_live_episodes':9,'original_live_verified':7,'larger_cases':4,'larger_certified':0,'larger_controller_stops':2,'larger_incomplete':2,'references':len(refs),'tests_passed':955,'tests_skipped':15,'scripted_baseline_states':24,'scripted_baseline_certified':5,'timing_excluding_cts_affected_state':replay_split['timing_failure_classes_after_exclusion'],'independent_archived_full_ir_matches':7,'scope':'Deterministic numerical/source/input audit; internal semantic reviews are separate.'}
(PAPER/'evidence/manuscript_audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
