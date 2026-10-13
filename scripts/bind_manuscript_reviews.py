#!/usr/bin/env python3
"""Bind the corrected manuscript, generated material and three internal reviews."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / 'rtl2gdsagi_paper'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    main_hash = digest(PAPER / 'main.tex')
    reviews = []
    for scope in ('EVIDENCE', 'METHODS', 'PRESENTATION'):
        path = PAPER / 'evidence' / f'REVIEW_FOLLOWUP_{scope}.md'
        content = path.read_text()
        assert main_hash in content, f'Final revision not reviewed by {scope}'
        assert 'NOT_CALIBRATED' in content and 'criteria_binding_unavailable' in content
        reviews.append({'scope': scope, 'path': str(path.relative_to(ROOT)),
                        'sha256': digest(path)})
    paths = [PAPER / 'main.tex', PAPER / 'README.md',
             PAPER / 'main.pdf', PAPER / 'figures/timing_stress.pdf',
             PAPER / 'evidence/manuscript.txt',
             *sorted((PAPER / 'generated').glob('*.tex'))]
    bound = [{'path': str(p.relative_to(ROOT)), 'sha256': digest(p)} for p in paths]
    aggregate = hashlib.sha256()
    for p in sorted((PAPER / 'generated').glob('*.tex')):
        aggregate.update(str(p.relative_to(PAPER)).encode() + b'\0' + p.read_bytes())
    data = {'release_tag': 'rtl2gdsagi-paper-20261013',
            'manuscript_sha256': main_hash,
            'main_pdf_sha256': digest(PAPER / 'main.pdf'),
            'generated_tex_aggregate_sha256': aggregate.hexdigest(),
            'reviews': reviews, 'bound_files': bound,
            'execution': 'Three separate internal review contexts in the same Codex writing workflow; not independent external peer review.',
            'criteria_binding': 'criteria_binding_unavailable',
            'calibration_status': 'NOT_CALIBRATED',
            'publication_verification': 'Separate release receipt; reviews do not verify remote availability.'}
    dest = PAPER / 'evidence/review_bindings.json'
    dest.write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps({'reviews': len(reviews), 'bound_files': len(bound),
                      'manuscript_sha256': main_hash}, indent=2))


if __name__ == '__main__':
    main()
