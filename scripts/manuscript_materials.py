"""Resolve the TeX inputs and graphics actually used by the delivery documents."""
from pathlib import Path
import re


def manuscript_materials(paper):
    paper = Path(paper)
    documents = [paper / 'main.tex']
    if (paper / 'supplement.tex').is_file(): documents.append(paper / 'supplement.tex')
    files = set(documents)
    pending = list(documents)
    while pending:
        path = pending.pop()
        text = path.read_text()
        for name in re.findall(r'\\input\{([^}]+)\}', text):
            child = paper / name
            if not child.suffix: child = child.with_suffix('.tex')
            assert child.is_file(), child
            if child not in files:
                files.add(child); pending.append(child)
        for name in re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', text):
            child = paper / name
            if not child.suffix: child = child.with_suffix('.pdf')
            assert child.is_file(), child
            files.add(child)
    return sorted(files)
