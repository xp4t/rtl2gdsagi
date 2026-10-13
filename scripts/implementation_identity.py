#!/usr/bin/env python3
"""A non-certifying implementation fingerprint alongside raw release identity.

Only GDS date payloads are normalized. Native release and gate identities keep
their exact byte hashes; this fingerprint is never an acceptance predicate.
"""
import hashlib
import json
from pathlib import Path
from compare_repeated_runs import date_neutral_gds
from rtl2gdsagi.manifest import ReleaseCandidateManifest
from rtl2gdsagi.state import RunState

STABLE_KEYS=('rtl_dir','routed_netlist','spef','sdc','layer_map','drc_deck','lvs_deck')

def implementation_identity(run_dir):
    folder=Path(run_dir)
    state=RunState.load(folder)
    bundle=json.loads((folder/'signoff.json').read_text())
    candidate=ReleaseCandidateManifest(**bundle['release_candidate'])
    problems=candidate.verify(state.artifacts)
    assert not problems,problems
    normalized,records=date_neutral_gds(state.artifacts.get('final_gds').path)
    payload={'schema':'implementation-date-neutral-v1','top':candidate.top,
             'date_neutral_gds_sha256':normalized,
             'artifacts':{k:candidate.artifacts[k]['sha256'] for k in STABLE_KEYS},
             'pdk':{k:candidate.pdk[k] for k in ('name','std_cell_lib','corner')}}
    identity=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'implementation_id':identity,'release_candidate_id':candidate.candidate_id,
            'normalization':'Only BGNLIB/BGNSTR 24-byte date payloads zeroed.',
            'normalized_date_records':records,'payload':payload,
            'certification_authority':False}
