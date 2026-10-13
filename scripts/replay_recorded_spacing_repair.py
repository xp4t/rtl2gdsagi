#!/usr/bin/env python3
"""Replay one recorded model delta through the frozen repair loop; no API call."""
import json
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'runs/frozen_evaluation_20261013/frozen_source/src'))
from rtl2gdsagi.agent.client import ScriptedAgent
from rtl2gdsagi.config import RunConfig
from rtl2gdsagi.runner import Orchestrator
from rtl2gdsagi.stages import StageId
from rtl2gdsagi.taxonomy import Diagnosis, FailureClass

out = ROOT / 'runs/frozen_recorded_spacing_repair_20261013'
assert not out.exists(), 'Never overwrite a recorded repair'
os.environ['PATH'] = '/home/vlsi/Documents/rtl2gdsagi/.venv/bin' + os.pathsep + os.environ.get('PATH', '')
old = json.loads((ROOT / 'rtl2gdsagi_paper/evidence/repair_study.json').read_text())
episode = next(r for r in old['trials'] if r['failure_type'] == 'drc' and r['replicate'] == 1)
delta = episode['proposals'][0]['delta']
assert delta == {'placement': {'padding_sites': 2}}
cfg = RunConfig.build(config_path=ROOT / 'benchmarks/signoff/alu8_unpadded.yaml',
    pdk_root='/home/vlsi/.volare/volare/sky130/versions/bdc9412b3e468c102d01b7cf6337be06ec6e9c9a/sky130A',
    klayout_backend='container', repair_policy='auto', retry_limit=3)
diag = Diagnosis(failure=FailureClass.DRC, evidence='Replay of recorded authorized spacing proposal.',
                 implicated_stage=StageId.PLACEMENT, confidence=0.9,
                 reasoning='Recorded proposal replay, not a new model diagnosis.', config_delta=delta)
controller = Orchestrator(cfg, agent=ScriptedAgent(diagnoses=[diag]), run_dir=out, interactive=False)
rc = controller.run()
(out / 'replay_provenance.json').write_text(json.dumps({'origin_run': episode['run_dir'],
    'proposal_generation_source_sha256': old['source_manifests'][0]['source_sha256'],
    'execution_source_sha256': json.loads((ROOT / 'runs/frozen_evaluation_20261013/experiment_manifest.json').read_text())['source_sha256'],
    'delta': delta, 'new_model_calls': 0, 'exit_code': rc}, indent=2) + '\n')
raise SystemExit(rc)
