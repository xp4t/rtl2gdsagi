#!/usr/bin/env python3
"""Package the manuscript and selected native evidence, with a portable hash index."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PAPER=ROOT/'rtl2gdsagi_paper'
DEST=ROOT/'dist/paper-20261013'

def main():
    global DEST
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-date',default='20261013')
    args=parser.parse_args()
    assert len(args.release_date)==8 and args.release_date.isdigit()
    DEST=ROOT/'dist'/f'paper-{args.release_date}'
    DEST.mkdir(parents=True,exist_ok=True)
    archive=PAPER/'rtl2gdsagi_overleaf.zip'
    cls=Path(subprocess.check_output(['kpsewhich','llncs.cls'],text=True).strip())
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in [PAPER/'main.tex',PAPER/'README.md',*(PAPER/'generated').glob('*.tex'),PAPER/'figures/timing_stress.pdf']:
            z.write(p,str(p.relative_to(PAPER)))
        z.write(cls,'llncs.cls')
    manifest=json.loads((PAPER/'evidence/experiment_manifest.json').read_text())
    repair=json.loads((PAPER/'evidence/repair_study.json').read_text())
    folders=set()
    for row in manifest['selected_runs']:
        folders.update(row[k] for k in ('run_dir','repeat_run_dir'))
    folders.update(t['run_dir'] for t in repair['trials'])
    folders.update(t['run_dir'] for t in repair['all_retained_live_episodes'])
    folders.update(manifest['failed_attempts'])
    folders.update(['runs/native_fault_injection','runs/formal_controls_final',
                    'runs/counter_timing_stress_1p5ns','runs/alu8_timing_api_v4'])
    followup=PAPER/'evidence/reviewer_followup.json'
    if followup.is_file():
        folders.add('runs/reviewer_followup_20261013')
    external=PAPER/'evidence/external_fault_coverage.json'
    if external.is_file():
        folders.add('runs/external_fault_coverage')
    # These native clean fixtures were used by the fault study.
    folders.update('runs/signoff_final_v5/'+n for n in ['register','alu8','fifo_buf'])
    files=set()
    for directory in ['src','scripts','examples','benchmarks','tests']:
        files.update(p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for name in ['README.md','pyproject.toml','LICENSE','.gitignore','.gitattributes']:
        if (ROOT/name).is_file():files.add(ROOT/name)
    files.update(p for p in PAPER.rglob('*') if p.is_file() and p.suffix not in ['.aux','.out','.fls','.fdb_latexmk'] and '__pycache__' not in p.parts and 'legacy' not in p.relative_to(PAPER).parts and p.name not in ['package_build.log','publication_receipt.json','delivery_checks.json'])
    for folder in folders:
        base=ROOT/folder
        assert base.is_dir(),base
        for p in base.rglob('*'):
            if not p.is_file() or '__pycache__' in p.parts:continue
            # Keep native EQY terminal markers/logs, configs and proof models;
            # exclude strategy work caches, not final candidate-bound artifacts.
            rel=p.relative_to(base)
            if 'eqy' in rel.parts and any(v in rel.parts for v in ['strategies','partitions','fragments','gold','gate']):continue
            if p.stat().st_size>30_000_000 and 'scale' in folder:continue
            files.add(p)
    for name in manifest['batch_manifests']:
        files.add(ROOT/name)
    for name in ['runs/live_repair_study/experiment_manifest.json','runs/live_drc_study/experiment_manifest.json']:
        files.add(ROOT/name)
    files.add(ROOT/'runs/formal_debug/counter_mutant.v')
    # For independent hash auditing, include the exact three small bound PDK
    # verification files; the rest of the PDK is acquired by recorded revision.
    pdk_files={}
    for row in manifest['selected_runs']:
        state=json.loads((ROOT/row['run_dir']/'run_state.json').read_text())
        for key in ['layer_map','drc_deck','lvs_deck']:
            p=Path(state['artifacts'][key]['path'])
            pdk_files['external_pdk/'+key+'/'+p.name]=p
    entries={str(p.relative_to(ROOT)):p for p in files}
    entries.update(pdk_files)
    key=os.environ.get('ANTHROPIC_API_KEY','').encode()
    assert len(key)>10,'source refreshed bashrc before packaging to verify the active key is absent'
    index=[]
    for name,p in sorted(entries.items()):
        assert p.is_file(),p
        data=p.read_bytes()
        assert key not in data,f'Active credential found in {name}; do not publish'
        index.append({'path':name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
    index_path=DEST/'ARTIFACT_INDEX.json'
    index_path.write_text(json.dumps({'files':index,'excluded':'EQY strategy work caches and large interrupted solver dumps; no environment files or credentials.'},indent=2)+'\n')
    verifier=DEST/'verify_artifact.py'
    verifier.write_text('''"""Verify the extracted public experiment archive without EDA dependencies."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
index=json.loads((root/'ARTIFACT_INDEX.json').read_text())
for row in index['files']:
    p=root/row['path'];data=p.read_bytes()
    assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],p
print(f"Verified {len(index['files'])} archived file hashes")
''')
    output=DEST/'rtl2gdsagi_experiments.tar.gz'
    with tarfile.open(output,'w:gz',compresslevel=6) as tar:
        for name,p in sorted(entries.items()):tar.add(p,arcname=name,recursive=False)
        tar.add(index_path,arcname=index_path.name)
        tar.add(verifier,arcname=verifier.name)
    print(json.dumps({'overleaf':str(archive.relative_to(ROOT)),'experiments':str(output.relative_to(ROOT)),
                      'files':len(index),'archive_bytes':output.stat().st_size},indent=2))

if __name__=='__main__':main()
