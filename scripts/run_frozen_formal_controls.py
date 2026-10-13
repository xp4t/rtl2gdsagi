#!/usr/bin/env python3
"""Fresh EQY positive controls and retained functional mutant on frozen inputs."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/frozen_formal_controls_20261013'
assert not OUT.exists()
OUT.mkdir()
env = {**os.environ, 'PATH': '/home/vlsi/Documents/rtl2gdsagi/.venv/bin' + os.pathsep + os.environ.get('PATH', '')}
cases = [('counter', 'counter', 'PASS'), ('shift', 'shift_reg', 'PASS'), ('counter_mutant', 'counter', 'FAIL')]

def execute(case):
    name, design, expected = case
    stage = ROOT / f'runs/frozen_evaluation_20261013/pair_a/{design}/stages/05_lec_synth'
    text = (stage / 'lec_synth.tcl').read_text()
    text = text.replace(str(stage / 'formal_pdk.v'), str(OUT / (name + '_formal_pdk.v')))
    if expected == 'FAIL':
        state = json.loads((stage.parents[1] / 'run_state.json').read_text())
        path = state['artifacts']['netlist']['path']
        assert path in text
        text = text.replace(path, str(ROOT / 'runs/formal_debug/counter_mutant.v'))
    config = OUT / (name + '.eqy'); config.write_text(text)
    cmd = ['eqy', '-f', '-d', str(OUT / name), str(config)]
    with (OUT / (name + '.console.log')).open('w') as log:
        result = subprocess.run(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    assert (OUT / name / expected).is_file(), name
    return name, {'command': cmd, 'expected': expected, 'exit_code': result.returncode,
                  'marker': str((OUT / name / expected).relative_to(ROOT))}

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    rows = dict(pool.map(execute, cases))
(OUT / 'experiment_manifest.json').write_text(json.dumps(rows, indent=2) + '\n')
print(json.dumps(rows, indent=2))
