#!/usr/bin/env python3
"""Freeze one implementation and rerun all seven designs twice from RTL."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
import yaml
from run_signoff_benchmark import source_identity

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/frozen_evaluation_20261013'
PDK = '/home/vlsi/.volare/volare/sky130/versions/bdc9412b3e468c102d01b7cf6337be06ec6e9c9a/sky130A'
BIN = '/home/vlsi/Documents/rtl2gdsagi/.venv/bin'


def main():
    assert not OUT.exists(), 'Never overwrite a declared cohort'
    OUT.mkdir()
    frozen = OUT / 'frozen_source'
    shutil.copytree(ROOT / 'src', frozen / 'src', ignore=shutil.ignore_patterns('__pycache__'))
    source = source_identity()
    configs = ROOT / 'benchmarks/frozen_20261013'
    configs.mkdir()
    prior = json.loads((ROOT / 'rtl2gdsagi_paper/evidence/experiment_manifest.json').read_text())
    cases = []
    for selection in prior['selected_runs']:
        bundle = json.loads((ROOT / selection['run_dir'] / 'signoff.json').read_text())
        design = bundle['top']
        config = yaml.safe_load((ROOT / f'examples/{design}/{design}.yaml').read_text())
        config['ir'] = bundle['ir']
        if design == 'shift1024': config['ir']['routing']['num_threads'] = 1
        config_path = configs / (design + '.yaml')
        config_path.write_text(yaml.safe_dump(config, sort_keys=False))
        for pair in ('a', 'b'):
            folder = OUT / ('pair_' + pair) / design
            folder.parent.mkdir(exist_ok=True)
            cases.append({'trial': f'{design}_{pair}', 'design': design, 'pair': pair,
                          'config': str(config_path.relative_to(ROOT)),
                          'config_sha256': hashlib.sha256(config_path.read_bytes()).hexdigest(),
                          'run_dir': str(folder.relative_to(ROOT))})
    archive = ROOT / 'rtl2gdsagi_paper/evidence/source_frozen_20261013.tar.gz'
    with tarfile.open(archive, 'w:gz') as tar:
        for p in sorted((frozen / 'src').rglob('*')):
            if p.is_file(): tar.add(p, arcname=str(p.relative_to(frozen)))
    manifest = {'source_sha256': source, 'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                'source_archive': str(archive.relative_to(ROOT)), 'declared_cases': cases,
                'scope': 'Seven primary designs, two complete executions each; shift1024 uses one worker. Frozen implementation includes all Python and non-Python resources.',
                'started_at': time.time(), 'trials': {}}
    path = OUT / 'experiment_manifest.json'
    path.write_text(json.dumps(manifest, indent=2) + '\n')

    def execute(case):
        folder = ROOT / case['run_dir']
        cmd = [sys.executable, '-m', 'rtl2gdsagi.cli', 'run', '--config', str(ROOT / case['config']),
               '--pdk-root', PDK, '--no-api', '--klayout-backend', 'container', '--run-dir', str(folder)]
        env = {**os.environ, 'PYTHONPATH': str(frozen / 'src'), 'PATH': BIN + os.pathsep + os.environ.get('PATH', '')}
        start = time.time()
        with (OUT / (case['trial'] + '.console.log')).open('w') as log:
            result = subprocess.run(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        state = json.loads((folder / 'run_state.json').read_text())
        return case['trial'], {**case, 'command': cmd, 'status': state['status'],
                              'exit_code': result.returncode, 'elapsed_s': time.time() - start}

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for f in concurrent.futures.as_completed([pool.submit(execute, c) for c in cases]):
            key, row = f.result(); manifest['trials'][key] = row
            path.write_text(json.dumps(manifest, indent=2) + '\n')
            print(json.dumps(row), flush=True)
    manifest.update(ended_at=time.time(), consistent_source=source_identity() == source)
    path.write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
