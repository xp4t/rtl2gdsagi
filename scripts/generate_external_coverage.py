#!/usr/bin/env python3
"""Render the actual OpenLane stage/checker coverage with unsupported cases visible."""
import hashlib
import json
from pathlib import Path
from generate_extended_results import table
ROOT=Path(__file__).resolve().parents[1]
PAPER=ROOT/'rtl2gdsagi_paper'

def main():
    data=json.loads((PAPER/'evidence/external_fault_coverage.json').read_text())
    assert data['status']=='completed' and len(data['coverage'])==6
    executed={r['id']:r for r in data['executions']}
    for c in data['coverage']:
        assert c['result'] in ('detected','not_detected','not_checked')
        assert all(k in executed for k in c['execution_ids'])
    for e in data['executions']:
        for key in ['stdout','stderr']:
            rec=e[key];p=Path(rec['path']);assert p.is_file()
            assert hashlib.sha256(p.read_bytes()).hexdigest()==rec['sha256']
    labels={'stale_gds_fed_to_drc':'Stale same-top GDS','drc_deck_missing_feol_rules':'Missing FEOL rules',
            'lvs_no_real_compare':'LVS without compare','missing_pdn_via_connection':'Missing PDN connections',
            'missing_layer_map_streamout':'Missing layer map','artifact_swap_after_verified_repair':'GDS swap after repair'}
    notes={'stale_gds_fed_to_drc':'DRC lacks selected-reference identity; optional reference XOR detects geometry differences.',
           'drc_deck_missing_feol_rules':'DRC stage lacks approved-inventory checks; explicit rule flags are required for this deck.',
           'lvs_no_real_compare':'Retained KLayout database is unsupported by the Netgen report checker.',
           'missing_pdn_via_connection':'Native power-grid checks detect missing vias; untouched DEF controls pass.',
           'missing_layer_map_streamout':'Existing wrong-map GDS is not rejected by DRC; stream-out requires its mapping option.',
           'artifact_swap_after_verified_repair':'Cached candidate binding is unsupported; supplied-reference XOR detects foreign geometry.'}
    rows=[(labels[c['fault_class']],c['result'].replace('_',' ').capitalize(),notes[c['fault_class']]) for c in data['coverage']]
    table('external_coverage_table.tex','Actual OpenLane stage/checker coverage for the retained classes. Not checked denotes an unsupported target obligation, not a passing result. No complete OpenLane flow was evaluated.','tab:externalcoverage','p{0.25\\linewidth}p{0.21\\linewidth}p{0.43\\linewidth}','Class & Executed check result & Executed scope / qualification',rows)
    (PAPER/'generated/external_coverage_text.tex').write_text(r'''The follow-up executes actual OpenLane code from the same pinned tool image,
including DRC, optional reference XOR, Netgen report gates and native
post-pdngen power-grid checks. Table~\ref{tab:externalcoverage} separates
detected, not detected and not checked results within the executed scope. Native power-grid
checks detect the missing-via fixtures for register, ALU and FIFO, with paired
untouched DEF controls. Optional XOR detects stale, foreign and wrongly mapped
geometry when an explicit selected reference is supplied. The stream-out
interface requires a mapping option; this differs from checking already
generated GDS. The retained KLayout no-compare database is incompatible with
the Netgen report interface and is not scored as a semantic detection.

These are isolated stage and report-checker runs on externally generated
artifacts, not a full OpenLane rerun. The unmodified DRC stage does not pass
this PDK deck's runtime rule flags. Its known-violating control declares zero
categories and zero markers; the explicitly enabled native-engine control
declares 213 raw categories and four markers. These controls are identified
separately. No detection-rate or full-flow superiority estimate is
derived from this constructed six-class matrix. Commands, stock checker
source hashes, known-fault controls, unsupported obligations and initial
invalid control attempts are retained.
Selected-candidate binding, inventory approval and reference-free map
semantics are unsupported obligations in these executed interfaces. Their
absence is not a measured false-pass rate.
''')
    print(json.dumps({'classes':6,'scope':data['scope'],'results':data['coverage_counts']},indent=2))

if __name__=='__main__':main()
