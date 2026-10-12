#!/usr/bin/env python3
"""Rehash paired native runs and normalize only GDS date payloads."""
import hashlib
import json
from pathlib import Path
from extract_signoff_metrics import extract
from run_signoff_benchmark import source_identity

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / 'rtl2gdsagi_paper'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def date_neutral_gds(path):
    data = bytearray(path.read_bytes())
    pos = 0
    dates = 0
    while pos < len(data):
        size = int.from_bytes(data[pos:pos+2], 'big')
        assert size >= 4 and pos + size <= len(data)
        if data[pos+2] in (1, 5):  # BGNLIB / BGNSTR only
            assert size == 28 and data[pos+3] == 2
            data[pos+4:pos+size] = bytes(size-4)
            dates += 1
        pos += size
    assert pos == len(data) and dates > 0
    return digest(data), dates

def main():
    manifest = json.loads((PAPER/'evidence/experiment_manifest.json').read_text())
    rows = []
    for selection in manifest['selected_runs']:
        paths = [ROOT/selection[k] for k in ('run_dir', 'repeat_run_dir')]
        metrics = [extract(p) for p in paths]
        states = [json.loads((p/'run_state.json').read_text()) for p in paths]
        artifacts = {}
        for key in sorted(set(states[0]['artifacts']) & set(states[1]['artifacts'])):
            values = [s['artifacts'][key] for s in states]
            hashes = [v['sha256'] for v in values]
            for value in values:
                path = Path(value['path'])
                if path.is_file():
                    assert digest(path.read_bytes()) == value['sha256'], path
            artifacts[key] = {'hash_a': hashes[0], 'hash_b': hashes[1], 'equal': hashes[0] == hashes[1]}
        norm = [date_neutral_gds(Path(s['artifacts']['final_gds']['path'])) for s in states]
        rows.append({'design':metrics[0]['design'], 'runs':[str(p.relative_to(ROOT)) for p in paths],
                     'certification_ids':[m['certification_id'] for m in metrics],
                     'artifacts':artifacts, 'gds_date_record_counts':[n[1] for n in norm],
                     'gds_date_neutral_hashes':[n[0] for n in norm],
                     'gds_date_neutral_equal':norm[0][0] == norm[1][0],
                     'route_bundle_equal':all(artifacts[k]['equal'] for k in ('routed_def','netlist','routed_netlist','spef'))})
    result = {'source_sha256':manifest['source_sha256'], 'current_source_sha256':source_identity(),
              'normalization':'Only 24-byte BGNLIB and BGNSTR date payloads set to zero; all other GDS bytes retained.',
              'pairs':rows, 'exact_route_pairs':sum(r['route_bundle_equal'] for r in rows),
              'raw_gds_pairs':sum(r['artifacts']['final_gds']['equal'] for r in rows),
              'normalized_gds_pairs':sum(r['gds_date_neutral_equal'] for r in rows)}
    assert result['source_sha256'] == result['current_source_sha256']
    (PAPER/'evidence/reproducibility_final.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='pairs'},indent=2))

if __name__ == '__main__': main()
