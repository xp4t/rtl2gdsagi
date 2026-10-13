#!/usr/bin/env python3
"""Declare and run the 2x2x2 CTS-padding/routing-padding/worker experiment."""
import concurrent.futures
import hashlib
import itertools
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import yaml
from run_signoff_benchmark import source_identity

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/padding_thread_ablation_20261013'
PDK = '/home/vlsi/.volare/volare/sky130/versions/bdc9412b3e468c102d01b7cf6337be06ec6e9c9a/sky130A'
BIN = '/home/vlsi/Documents/rtl2gdsagi/.venv/bin'
PADDING = '''        f"set_placement_padding -global -left {int(ir.section('placement')['padding_sites'])}"
        f" -right {int(ir.section('placement')['padding_sites'])}",
'''


def snapshot_hash(src):
    h = hashlib.sha256()
    for p in sorted(src.rglob('*.py')):
        h.update(('src/' + str(p.relative_to(src))).encode() + b'\0' + p.read_bytes())
    return h.hexdigest()


def main():
    assert not OUT.exists(), 'Never overwrite an experiment'
    OUT.mkdir()
    baseline = source_identity()
    cases = []
    for cts, route in itertools.product((0, 1), repeat=2):
        overlay = OUT / f'source_cts{cts}_route{route}' / 'src'
        shutil.copytree(ROOT / 'src', overlay, ignore=shutil.ignore_patterns('__pycache__'))
        path = overlay / 'rtl2gdsagi/render.py'
        text = path.read_text()
        for function, enabled in [('render_cts', cts), ('render_routing', route)]:
            start = text.index('def ' + function + '(')
            end = text.find('\ndef ', start + 1)
            if end < 0: end = len(text)
            segment = text[start:end]
            assert segment.count(PADDING) == 1
            if not enabled:
                text = text[:start] + segment.replace(PADDING, '') + text[end:]
        path.write_text(text)
        for threads in (1, 8):
            key = f'cts{cts}_route{route}_workers{threads}'
            cfg = yaml.safe_load((ROOT / 'benchmarks/followup/alu8_repaired_3ns.yaml').read_text())
            cfg['ir']['routing']['num_threads'] = threads
            config = OUT / (key + '.yaml')
            config.write_text(yaml.safe_dump(cfg, sort_keys=False))
            cases.append({'trial': key, 'cts_padding': bool(cts), 'routing_padding': bool(route),
                          'routing_workers': threads, 'config': str(config.relative_to(ROOT)),
                          'source_dir': str(overlay.relative_to(ROOT)), 'source_sha256': snapshot_hash(overlay)})
    manifest = {'base_source_sha256': baseline, 'declared_cases': cases,
                'scope': 'Controlled source interventions remove only CTS/routing padding statements; worker count changes only routing IR. Production source is unchanged.',
                'started_at': time.time(), 'trials': {}}
    output = OUT / 'experiment_manifest.json'
    output.write_text(json.dumps(manifest, indent=2) + '\n')

    def execute(case):
        folder = OUT / case['trial']
        cmd = [sys.executable, '-m', 'rtl2gdsagi.cli', 'run', '--config', str(ROOT / case['config']),
               '--pdk-root', PDK, '--no-api', '--klayout-backend', 'container', '--run-dir', str(folder)]
        env = {**os.environ, 'PYTHONPATH': str(ROOT / case['source_dir']), 'PATH': BIN + os.pathsep + os.environ.get('PATH', '')}
        start = time.time()
        with (OUT / (case['trial'] + '.console.log')).open('w') as log:
            process = subprocess.run(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        stream = [json.loads(l) for l in (folder / 'run.jsonl').read_text().splitlines()]
        checks = [e for e in stream if e.get('event') == 'result_check' and e.get('stage') == 'sta_signoff']
        state = json.loads((folder / 'run_state.json').read_text())
        return case['trial'], {**case, 'command': cmd, 'run_dir': str(folder.relative_to(ROOT)),
                              'exit_code': process.returncode, 'status': state['status'],
                              'elapsed_s': time.time() - start, 'routed_timing': checks[-1] if checks else None}

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for f in concurrent.futures.as_completed([pool.submit(execute, c) for c in cases]):
            key, row = f.result()
            manifest['trials'][key] = row
            output.write_text(json.dumps(manifest, indent=2) + '\n')
            print(json.dumps(row), flush=True)
    manifest.update(ended_at=time.time(), consistent_production_source=source_identity() == baseline)
    output.write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
