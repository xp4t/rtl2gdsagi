#!/usr/bin/env python3
"""Build the delivery ZIP in a fresh directory and compare its PDF text."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / 'rtl2gdsagi_paper'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', type=Path, default=PAPER / 'rtl2gdsagi_overleaf.zip')
    args = parser.parse_args()
    folder = Path(tempfile.mkdtemp(prefix='rtl2gdsagi-overleaf-followup-'))
    with zipfile.ZipFile(args.zip) as archive:
        archive.extractall(folder)
    with (folder / 'build.log').open('w') as log:
        result = subprocess.run(['latexmk', '-pdf', '-interaction=nonstopmode',
                                 '-halt-on-error', 'main.tex'], cwd=folder,
                                stdout=log, stderr=subprocess.STDOUT)
    assert result.returncode == 0, folder / 'build.log'
    log = (folder / 'main.log').read_text()
    assert not any(t in log for t in ('Overfull', 'LaTeX Warning', 'Undefined', '! LaTeX Error'))
    content = subprocess.check_output(['pdftotext', '-layout', str(folder / 'main.pdf'), '-'])
    assert content == (PAPER / 'evidence/manuscript.txt').read_bytes(), 'Packaged text differs'
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    record = {'build_directory': str(folder), 'tested_zip_sha256': sha(args.zip),
              'returncode': result.returncode, 'pages': content.count(b'\f'),
              'warnings': 0, 'pdf_text_matches_manuscript': True,
              'pdf_text_sha256': hashlib.sha256(content).hexdigest(),
              'fresh_pdf_sha256': sha(folder / 'main.pdf'),
              'manuscript_sha256': sha(PAPER / 'main.tex')}
    (PAPER / 'evidence/fresh_overleaf_build.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
