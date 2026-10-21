"""Offline review prototype. No network, spectra, scientific approval, or status writes."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

STRATA = ('cool_low', 'cool_high', 'warm_low', 'warm_high')
ROLES = ('template', 'calibration', 'holdout')
SALT = 'echolens-sp01-repair-proposed-v03'

class Blocked(ValueError):
    pass

def require(condition, reason):
    if not condition:
        raise Blocked(reason)

def exact_id(s):
    require(isinstance(s, str) and re.fullmatch(r'[1-9][0-9]{8,18}', s)
            and int(s) < 2**63, 'ID must be an exact decimal string')
    return s

def rank(s):
    return hashlib.sha256((SALT + ':' + s).encode()).hexdigest()

def select(raw_bytes, evidence, exposed, per_role=5):
    """Input is a metadata-only, ordinary-eligible, deduplicated full frame.

    group_keys are upstream-verified shared system/reduction-group identifiers.
    They must include all known visits, not merely the chosen representative.
    Completeness assertions are checked for consistency, NOT independently proved.
    """
    require(type(per_role) is int and per_role > 0, 'invalid quota')
    require(evidence.get('scope') == 'full_declared_eligible_frame', 'bounded pool forbidden')
    require(evidence.get('truncated') is False, 'truncation unresolved')
    require(evidence.get('all_pages_complete') is True, 'pagination incomplete')
    require(evidence.get('grouping_reviewed') is True, 'group provenance unreviewed')
    for key in ('source_release', 'query_record', 'completeness_record', 'grouping_record'):
        require(isinstance(evidence.get(key), str) and evidence[key].strip(), 'missing ' + key)
    digest = hashlib.sha256(raw_bytes).hexdigest()
    require(evidence.get('frame_sha256') == digest, 'frame hash mismatch')
    rows = json.loads(raw_bytes)
    require(isinstance(rows, list) and rows, 'empty or invalid frame')
    require(type(evidence.get('expected_rows')) is int and len(rows) == evidence['expected_rows'],
            'row count mismatch')
    ids = [exact_id(r.get('source_id')) for r in rows]
    require(len(set(ids)) == len(ids), 'duplicate source; resolve visits upstream')
    require(isinstance(exposed,dict) and exposed.get('group_mapping_complete') is True,
            'complete exposure-to-group ledger required')
    require(isinstance(exposed.get('record'),str) and exposed['record'].strip(),
            'exposure ledger provenance required')
    exposure_record=exposed
    require(isinstance(exposed.get('group_keys'),list) and
            all(isinstance(k,str) and k.strip() for k in exposed['group_keys']),
            'invalid exposure group keys')
    exposed_groups=set(exposed['group_keys'])
    exposed = {exact_id(s) for s in exposed['source_ids']}
    parent = {s:s for s in ids}

    def root(s):
        while parent[s] != s:
            parent[s] = parent[parent[s]]
            s = parent[s]
        return s

    def union(a, b):
        a,b = root(a),root(b)
        if a != b:
            parent[max(a,b)] = min(a,b)

    first = {}
    for r in rows:
        require(r.get('stratum') in STRATA, 'invalid stratum')
        require(r.get('ordinary_eligible') is True, 'frame includes ineligible source')
        require(r.get('natural_positive') is False, 'positive label unresolved/in null')
        require(r.get('group_metadata_complete') is True, 'group metadata incomplete')
        keys = r.get('group_keys')
        require(isinstance(keys, list) and keys and all(isinstance(k,str) and k.strip() for k in keys),
                'missing group keys')
        for key in keys:
            if key in first:
                union(r['source_id'], first[key])
            else:
                first[key] = r['source_id']
    components = defaultdict(list)
    for r in rows:
        components[root(r['source_id'])].append(r)
    # Exposure propagates through the complete connected component before sampling.
    # One representative per component prevents a known group entering two splits.
    pool = defaultdict(list)
    dropped = Counter()
    for group in components.values():
        if any(r['source_id'] in exposed or exposed_groups.intersection(r['group_keys']) for r in group):
            dropped['exposure_connected_sources'] += len(group)
            continue
        r = min(group, key=lambda x:(rank(x['source_id']), x['source_id']))
        comp_hash = hashlib.sha256('\n'.join(sorted(x['source_id'] for x in group)).encode()).hexdigest()
        pool[r['stratum']].append(dict(r, component_sha256=comp_hash))
        dropped['nonrepresentative_sources'] += len(group)-1
    counts = {k:len(pool[k]) for k in STRATA}
    require(all(n >= len(ROLES)*per_role for n in counts.values()),
            'fixed component-representative rule cannot fill quotas: '+json.dumps(counts))
    chosen=[]
    for stratum in STRATA:
        ordered = sorted(pool[stratum], key=lambda r:(rank(r['source_id']),r['source_id']))
        for i,r in enumerate(ordered[:len(ROLES)*per_role]):
            # Interleave roles in hash order; do not rank roles by original source ID.
            chosen.append({'source_id':r['source_id'], 'stratum':stratum,
                           'role':ROLES[i % len(ROLES)], 'component_sha256':r['component_sha256'],
                           'group_keys':sorted(set(r['group_keys']))})
    return {'status':'PROPOSED_METADATA_SELECTION_ONLY', 'science_ready':False,
            'spectra_opened_by_this_tool':0, 'source_completeness_independently_verified':False,
            'frame_sha256':digest, 'evidence':evidence, 'salt':SALT,
            'exposure_ledger_sha256':hashlib.sha256(json.dumps(exposure_record,sort_keys=True).encode()).hexdigest(),
            'input_sources':len(rows), 'components':len(components), 'excluded':dict(dropped),
            'component_representatives_by_stratum':counts, 'per_role_per_stratum':per_role,
            'selected':chosen}

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--frame',type=Path,required=True)
    p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--exposed',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    result=select(args.frame.read_bytes(),json.loads(args.evidence.read_text()),
                  json.loads(args.exposed.read_text()))
    # Exclusive create: never overwrite a prior proposed manifest.
    with args.output.open('x') as f:
        json.dump(result,f,indent=2,sort_keys=True)
        f.write('\n')
