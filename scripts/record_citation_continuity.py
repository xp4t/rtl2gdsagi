#!/usr/bin/env python3
"""Map final bibliography/claim anchors to retained primary-source audit receipts."""
import datetime
import hashlib
import json
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
PAPER=ROOT/'rtl2gdsagi_paper'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    old_path=PAPER/'evidence/citation_audit_frozen.json';fresh_path=PAPER/'evidence/citation_baseline_audit.json'
    old=json.loads(old_path.read_text());fresh=json.loads(fresh_path.read_text())
    old_refs={r['citation_key']:r for r in old['references']}
    new_refs={r['key']:r for r in fresh['papers']+fresh['baselines']}
    new_sources={r['id']:r for r in fresh['sources']}
    text=(PAPER/'main.tex').read_text();rows=[]
    for key,entry in re.findall(r'\\bibitem\{([^}]+)\}([\s\S]*?)(?=\\bibitem|\\end\{thebibliography\})',text):
        contexts=[]
        for match in re.finditer(r'\\cite\{([^}]+)\}',text):
            if key not in match.group(1).split(','):continue
            start=text.rfind('\n\n',0,match.start())+2;end=text.find('\n\n',match.end());end=len(text) if end<0 else end
            contexts.append({'line':text.count('\n',0,match.start())+1,'paragraph':text[start:end]})
        row={'key':key,'current_entry':entry.strip(),'current_line':text.count('\n',0,text.index(r'\bibitem{'+key+'}'))+1,'current_contexts':contexts}
        if key in new_refs:
            r=new_refs[key];row.update(audit='citation_baseline_audit.json',audit_record=r,source_receipts=[new_sources[s] for s in r['sources']])
        else:
            r=old_refs[key];row.update(audit='citation_audit_frozen.json',audit_record=r,source_receipts=r['sources'])
        row['continuity_scope']='Current bibliography/context anchors mapped to retained primary-source evidence. Prior reading/access limits remain; no new full-body or external review claimed.'
        rows.append(row)
    assert len(rows)==16 and all(r['current_contexts'] for r in rows)
    receipt={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'main_sha256':sha(PAPER/'main.tex'),'source_audits':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in (old_path,fresh_path)],'references':rows,'reference_count':16,'execution':'Final author continuity mapping to original and fresh separate-context citation audit; internal writing workflow, not external review.','scope':'Identity, bounded claim contexts, current exact bibliography and inherited primary-source receipts/read scopes. Unresolved future AuDoPEDA conference DOI excluded from bibliography; author manuscript explicitly to appear.'}
    (PAPER/'evidence/citation_continuity_frozen.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Mapped 16 current references to retained primary-source receipts')
if __name__=='__main__':main()
