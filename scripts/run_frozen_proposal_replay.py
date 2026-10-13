#!/usr/bin/env python3
"""Fresh native execution of every recorded authorized proposal on frozen code."""
import concurrent.futures
import copy
import ast
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import time
import yaml
from run_signoff_benchmark import source_identity

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/frozen_proposal_replay_complete_ir_20261013'
FROZEN = ROOT / 'runs/frozen_evaluation_20261013/frozen_source/src'
PDK = '/home/vlsi/.volare/volare/sky130/versions/bdc9412b3e468c102d01b7cf6337be06ec6e9c9a/sky130A'
BIN = '/home/vlsi/Documents/rtl2gdsagi/.venv/bin'


def main():
    assert not OUT.exists(), 'Never overwrite proposal outcomes'
    OUT.mkdir()
    original = json.loads((ROOT / 'rtl2gdsagi_paper/evidence/repair_study.json').read_text())
    frozen = json.loads((FROZEN.parents[1] / 'experiment_manifest.json').read_text())
    assert frozen['source_sha256'] == source_identity()
    archived = ROOT / 'runs/reviewer_followup_20261013/repair_cohort_source/src'
    defaults = json.loads(subprocess.check_output(
        [sys.executable, '-c', 'from rtl2gdsagi.ir import IR; import json; print(json.dumps(IR().as_dict()))'],
        env={**os.environ, 'PYTHONPATH': str(archived)}, cwd=ROOT, text=True))
    cases = []
    for episode in original['trials']:
        folder = ROOT / episode['run_dir']
        config = json.loads((folder / 'run_state.json').read_text())['config']
        ir = copy.deepcopy(defaults)
        proposals = iter(enumerate(episode['proposals'], 1))
        events = [json.loads(l) for l in (folder / 'run.jsonl').read_text().splitlines()]
        for event in events:
            if event.get('delta'):
                for section, changes in event['delta'].items():
                    ir.setdefault(section, {}).update(changes)
            # Curated repairs preceded the PDN model call. Their exact changes
            # are part of the promoted state, not part of the model delta.
            if event.get('event') == 'note' and event.get('stage') == 'repair':
                match = re.fullmatch(r'([a-z_]+)\.([a-z_]+) (.+) -> (.+)', event.get('message', ''))
                if match:
                    section, key, before, after = match.groups()
                    before_value, after_value = ast.literal_eval(before), ast.literal_eval(after)
                    assert ir[section][key] == before_value
                    ir[section][key] = after_value
            if event.get('event') != 'config_generated' or not event.get('delta'): continue
            index, proposal = next(proposals)
            assert proposal['delta'] == event['delta']
            effective = copy.deepcopy(ir)
            effective.setdefault('routing', {})['num_threads'] = 1
            key = f"{episode['failure_type']}_{episode['replicate']}_proposal{index}"
            path = OUT / (key + '.yaml')
            payload = {'top': config['top'], 'rtl': config['rtl_dir'],
                       'pdk': {k: config['pdk'][k] for k in ('name', 'std_cell_lib', 'corner')},
                       'retry_limit': 1, 'ir': effective}
            path.write_text(yaml.safe_dump(payload, sort_keys=False))
            cases.append({'trial': key, 'failure_type': episode['failure_type'],
                          'episode_replicate': episode['replicate'], 'proposal_index': index,
                          'origin_stage': proposal['origin_stage'], 'delta': proposal['delta'],
                          'original_native_outcome': proposal['native_recheck'],
                          'original_run': episode['run_dir'], 'config': str(path.relative_to(ROOT)),
                          'config_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        assert next(proposals, None) is None
        if (folder / 'signoff.json').exists():
            final = json.loads((folder / 'signoff.json').read_text())['ir']
            assert ir == final, f'Reconstructed final IR differs from retained successful episode: {folder}'
    assert len(cases) == 20
    manifest = {'source_sha256': source_identity(), 'proposal_generation_source_sha256': original['source_manifests'][0]['source_sha256'],
                'declared_cases': cases, 'started_at': time.time(), 'trials': {},
                'scope': 'Fixed proposals from native-feedback trajectories, re-executed independently from RTL on frozen HEAD. No new model arm or model calls; no retry repair. Routing workers explicitly match archived effective count of one.'}
    output = OUT / 'experiment_manifest.json'
    output.write_text(json.dumps(manifest, indent=2) + '\n')

    def execute(case):
        folder = OUT / case['trial']
        cmd = [sys.executable, '-m', 'rtl2gdsagi.cli', 'run', '--config', str(ROOT / case['config']),
               '--pdk-root', PDK, '--no-api', '--repair-policy', 'manual', '--klayout-backend', 'container', '--run-dir', str(folder)]
        env = {**os.environ, 'PYTHONPATH': str(FROZEN), 'PATH': BIN + os.pathsep + os.environ.get('PATH', '')}
        start = time.time()
        with (OUT / (case['trial'] + '.console.log')).open('w') as log:
            result = subprocess.run(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        state = json.loads((folder / 'run_state.json').read_text())
        events = [json.loads(l) for l in (folder / 'run.jsonl').read_text().splitlines()]
        checks = [e for e in events if e.get('event') == 'result_check']
        return case['trial'], {**case, 'command': cmd, 'run_dir': str(folder.relative_to(ROOT)),
                              'status': state['status'], 'exit_code': result.returncode,
                              'elapsed_s': time.time() - start,
                              'failed_checks': [e for e in checks if not e.get('ok', True)],
                              'target_checks': [e for e in checks if e['stage'] == case['origin_stage']]}

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for f in concurrent.futures.as_completed([pool.submit(execute, c) for c in cases]):
            key, row = f.result(); manifest['trials'][key] = row
            output.write_text(json.dumps(manifest, indent=2) + '\n')
            print(json.dumps({'trial': key, 'status': row['status'], 'failed_stages': [e['stage'] for e in row['failed_checks']]}), flush=True)
    manifest.update(ended_at=time.time(), consistent_source=source_identity() == manifest['source_sha256'])
    output.write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
