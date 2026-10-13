#!/usr/bin/env python3
"""Study-only first-failure stopping harness; native gates/source remain frozen."""
import argparse
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runs/frozen_evaluation_20261013/frozen_source/src'))
from rtl2gdsagi.agent.client import ScriptedAgent
from rtl2gdsagi.config import RunConfig
from rtl2gdsagi.runner import Orchestrator, Escalation
from rtl2gdsagi.stages import StageId
class FirstFailureController(Orchestrator):
    def _rollback(self,to_stage,why):
        last=self._history[-1]
        raise Escalation(StageId(last['stage']),
            'Baseline first-failure stop after native rejection: '+why,
            str(last.get('evidence','')))
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--pdk-root',required=True)
    parser.add_argument('--run-dir',type=Path,required=True)
    a=parser.parse_args()
    os.environ['PATH']='/home/vlsi/Documents/rtl2gdsagi/.venv/bin'+os.pathsep+os.environ.get('PATH','')
    cfg=RunConfig.build(config_path=a.config,pdk_root=a.pdk_root,klayout_backend='container',repair_policy='manual',retry_limit=1)
    raise SystemExit(FirstFailureController(cfg,agent=ScriptedAgent(),run_dir=a.run_dir,interactive=False).run())
