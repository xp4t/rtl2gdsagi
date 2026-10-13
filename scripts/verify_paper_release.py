#!/usr/bin/env python3
"""Verify published paper assets and record actual public release evidence."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
PAPER=ROOT/'rtl2gdsagi_paper'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def api(path):
    return json.loads(subprocess.check_output(['gh','api',path],text=True))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag',required=True)
    parser.add_argument('--commit',required=True)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--verified-archive-files',type=int,required=True)
    args=parser.parse_args()
    repo='xp4t/rtl2gdsagi'
    release=api(f'repos/{repo}/releases/tags/{args.tag}')
    assert not release['draft'] and release['published_at']
    assert api(f'repos/{repo}')['private'] is False
    target=api(f'repos/{repo}/git/ref/tags/{args.tag}')['object']
    if target['type']=='tag':target=api(f'repos/{repo}/git/tags/{target["sha"]}')['object']
    assert target['sha']==args.commit
    paths=[PAPER/'main.pdf',PAPER/'supplement.pdf',PAPER/'rtl2gdsagi_overleaf.zip',
           args.archive,PAPER/'evidence/review_bindings.json']
    remote={a['name']:a for a in release['assets']};assets=[]
    for path in paths:
        item=remote[path.name];digest=sha(path)
        assert item['size']==path.stat().st_size
        assert item['digest']=='sha256:'+digest,(path.name,item['digest'],digest)
        entry={'name':path.name,'url':item['browser_download_url'],'bytes':item['size'],
               'sha256':digest,'github_digest_verified':True}
        if path.suffix in ('.pdf','.zip'):
            with urllib.request.urlopen(item['browser_download_url'],timeout=20) as response:
                content=response.read()
            assert len(content)==item['size'] and hashlib.sha256(content).hexdigest()==digest
            entry['anonymous_https_download_verified']=True
        assets.append(entry)
    fresh=json.loads((PAPER/'evidence/fresh_overleaf_build.json').read_text())
    assert fresh['tested_zip_sha256']==sha(PAPER/'rtl2gdsagi_overleaf.zip')
    assert fresh['warnings']==0 and fresh['pdf_text_matches_manuscript']
    bindings=json.loads((PAPER/'evidence/review_bindings.json').read_text())
    for row in bindings['bound_files']+bindings['reviews']:assert sha(ROOT/row['path'])==row['sha256']
    manifest=json.loads((PAPER/'evidence/experiment_manifest.json').read_text())
    record={'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'release_url':release['html_url'],'public':True,'published_at':release['published_at'],
            'tag':args.tag,'code_commit':args.commit,
            'implementation_source_sha256':manifest['source_sha256'],
            'proposal_generation_source_sha256':manifest['archived_repair_source_sha256'],
            'manuscript_sha256':sha(PAPER/'main.tex'),'supplement_sha256':sha(PAPER/'supplement.tex'),
            'main_pdf_sha256':sha(PAPER/'main.pdf'),'supplement_pdf_sha256':sha(PAPER/'supplement.pdf'),
            'fresh_overleaf_documents':fresh['documents'],'fresh_overleaf_warnings':0,
            'fresh_overleaf_tested_zip_sha256':fresh['tested_zip_sha256'],
            'archive_file_hashes_verified':args.verified_archive_files,'assets':assets,
            'review_execution':bindings['execution'],'criteria_binding':bindings['criteria_binding'],
            'calibration_status':bindings['calibration_status'],
            'venue_status':'Springer LNCS format; no exact venue or publication acceptance asserted.'}
    (PAPER/'evidence/publication_receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'tag':args.tag,'public':True,'verified_assets':len(assets)},indent=2))

if __name__=='__main__':main()
