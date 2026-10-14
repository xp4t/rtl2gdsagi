#!/usr/bin/env python3
"""Trace eight existing CTS scripts around setup repair, without replacing runs."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from run_signoff_benchmark import source_identity

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / 'rtl2gdsagi_paper'
OUT = ROOT / 'runs/setup_repair_diagnostic_20261013'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not OUT.exists(), 'Refuse to overwrite diagnostic evidence'
    OUT.mkdir()
    baseline = json.loads((PAPER/'evidence/scripted_baseline.json').read_text())
    environment = json.loads((PAPER/'evidence/experiment_manifest.json').read_text())['environment']
    cases = [r for r in baseline['states'] if r['scope']=='fixed_3ns' and r['trial'].endswith('_setup1')]
    assert len(cases)==8
    manifest = {'source_sha256':source_identity(), 'script_sha256':sha(Path(__file__)),
                'scope':'Diagnostic CTS re-execution of the eight setup-on scripts with WNS markers and output snapshots. Original native runs, source, constraints and certificates remain unchanged.',
                'declared_cases':[r['trial'] for r in cases], 'started_at':time.time(), 'trials':[]}
    dest = OUT/'experiment_manifest.json'
    dest.write_text(json.dumps(manifest,indent=2)+'\n')
    for case in cases:
        directory = OUT/case['trial']; directory.mkdir()
        original = ROOT/case['run_dir']/'stages/10_cts/cts.tcl'
        text = original.read_text()
        command = 'repair_timing -setup -setup_margin 0.0500'
        assert text.count(command)==1
        # Markers prove the native call was reached and returned. Snapshots
        # test whether repair modified the design, independently of final CTS.
        before = '\n'.join(['puts "DIAG before_setup [sta::worst_slack -max] [sta::worst_slack -min]"',
                            f'write_def {directory}/before.def', f'write_verilog {directory}/before.v',
                            'puts "DIAG setup_enter"'])
        after = '\n'.join(['puts "DIAG setup_return"',
                           'puts "DIAG after_setup [sta::worst_slack -max] [sta::worst_slack -min]"',
                           f'write_def {directory}/after.def', f'write_verilog {directory}/after.v'])
        # Redirect original final writers before introducing new diagnostic writers.
        text = re.sub(r'^write_def .*$',f'write_def {directory}/final.def',text,flags=re.M)
        text = re.sub(r'^write_verilog .*$',f'write_verilog {directory}/final.v',text,flags=re.M)
        text = text.replace(command,before+'\n'+command+'\n'+after)
        script = directory/'diagnostic.tcl'; script.write_text(text)
        argv = ['docker','run','--rm','-u',f'{os.getuid()}:{os.getgid()}',
                '-v',f'{ROOT}/runs:{ROOT}/runs',
                '-v',f'{environment["pdk_root"]}:{environment["pdk_root"]}:ro',
                '-w',str(directory),'--entrypoint','openroad',environment['container_image'],
                '-no_init','-exit',str(script)]
        log = directory/'native.log'
        with log.open('w') as f:
            result = subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,timeout=120)
        content = log.read_text(); assert result.returncode==0,log
        assert 'DIAG setup_enter\n' in content and 'DIAG setup_return\n' in content
        values = {}
        for point in ('before_setup','after_setup'):
            match = re.search(r'^DIAG '+point+r' (\S+) (\S+)$',content,re.M); assert match,log
            values[point] = {'setup_wns_ns':float(match[1]),'hold_wns_ns':float(match[2])}
        state = json.loads((ROOT/case['run_dir']/'run_state.json').read_text())
        row = {'trial':case['trial'],'original_script':str(original.relative_to(ROOT)),
               'original_script_sha256':sha(original),'instrumented_script':str(script.relative_to(ROOT)),
               'instrumented_script_sha256':sha(script),'argv':argv,'returncode':result.returncode,
               'log':str(log.relative_to(ROOT)),'log_sha256':sha(log),'command_entered_and_returned':True,
               **values,'setup_margin_ns':0.05,
               'setup_repair_def_unchanged':sha(directory/'before.def')==sha(directory/'after.def'),
               'setup_repair_netlist_unchanged':sha(directory/'before.v')==sha(directory/'after.v'),
               'final_cts_def_matches_archived':sha(directory/'final.def')==state['artifacts']['cts_def']['sha256'],
               'zero_wire_capacitance_warning':'RSZ-0014' in content,
               'wire_load_fallback_warning':'RSZ-0021' in content,
               'snapshot_hashes':{p.name:sha(p) for p in directory.glob('*') if p.suffix in ('.def','.v')}}
        manifest['trials'].append(row); dest.write_text(json.dumps(manifest,indent=2)+'\n')
        print(case['trial'],values,flush=True)
    manifest.update(ended_at=time.time(),consistent_source=manifest['source_sha256']==source_identity())
    assert manifest['consistent_source']
    dest.write_text(json.dumps(manifest,indent=2)+'\n')
    (PAPER/'evidence/setup_repair_diagnostic.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__': main()
