"""Timestamp-neutral comparison must retain geometry and raw release binding."""
import importlib
import json
from pathlib import Path
import struct
from dataclasses import asdict
from rtl2gdsagi.artifacts import ArtifactLedger
from rtl2gdsagi.manifest import ReleaseCandidateManifest
from rtl2gdsagi.state import RunState

def record(kind,datatype,payload):
    return struct.pack('>HBB',len(payload)+4,kind,datatype)+payload

def test_date_normalization_does_not_reuse_release_identity_or_hide_geometry(tmp_path,monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'scripts'))
    module=importlib.import_module('implementation_identity')
    rtl=tmp_path/'rtl';rtl.mkdir();(rtl/'design.v').write_text('module d; endmodule')
    def fingerprint(stamp,coordinate):
        folder=tmp_path/f'run_{stamp}_{coordinate}';folder.mkdir()
        ledger=ArtifactLedger()
        ledger.register('rtl_dir',rtl,stage='prepare',allow_dir=True)
        for key in module.STABLE_KEYS:
            if key=='rtl_dir':continue
            p=folder/key;p.write_text('same content '+key);ledger.register(key,p,stage='fixture')
        gds=folder/'layout.gds'
        gds.write_bytes(record(1,2,struct.pack('>12h',*([stamp]*12)))+
                        record(5,2,struct.pack('>12h',*([stamp]*12)))+
                        record(16,3,struct.pack('>2i',coordinate,100)))
        ledger.register('final_gds',gds,stage='gdsout')
        candidate=ReleaseCandidateManifest.build(top='d',ledger=ledger,
            pdk={'name':'fixture','std_cell_lib':'fixture','corner':'tt'},
            config={},ir_fingerprint='same',tools={})
        (folder/'signoff.json').write_text(json.dumps({'release_candidate':asdict(candidate)}))
        monkeypatch.setattr(RunState,'load',lambda ignored:type('State',(),{'artifacts':ledger})())
        return module.implementation_identity(folder)
    original=fingerprint(1,10);dates=fingerprint(2,10);geometry=fingerprint(3,20)
    assert original['implementation_id']==dates['implementation_id']
    assert original['release_candidate_id']!=dates['release_candidate_id']
    assert dates['implementation_id']!=geometry['implementation_id']
    assert not original['certification_authority']
