"""Freeze, explicitly fetch, and replay the AllWISE readiness pilot offline."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import tempfile
import tarfile
import urllib.parse
import urllib.request

import numpy as np
from astropy.time import Time
from scripts.import_gaia import is_reference, parse_snapshot, parse_votable, validate

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT/'data/wise_001b'
SELECTION = ROOT/'reports/experiment_001b/selection.json'
PROTOCOL = ROOT/'docs/EXPERIMENT_001B.md'
AMENDMENT = ROOT/'docs/EXPERIMENT_001B_TRANSPORT_AMENDMENT.md'
GAIA_HASH = 'd193d7e144d5a7fc9f3d877a9323fc3c68ee2baf05b966d997392309a5248fb0'
ENDPOINT = 'https://irsa.ipac.caltech.edu/TAP/sync'


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def gaia_rows():
    payload = gzip.decompress((ROOT/'data/gaia_dr3.raw.gz').read_bytes())
    if digest(payload) != GAIA_HASH:
        raise ValueError('Gaia input changed')
    manifest = json.loads((ROOT/'data/gaia_dr3.manifest.json').read_text())
    _, rows = parse_snapshot(payload, manifest, ROOT/'data')
    validate(rows, 10000)
    return {r['source_id']: r for r in rows}


def propagate(row, mjd):
    """Angular linear motion on a normalized unit vector; pmra includes cos(dec)."""
    dt = Time(mjd, format='mjd', scale='tt').jyear - row['ref_epoch']
    ra, dec = math.radians(row['ra']), math.radians(row['dec'])
    point = np.array([math.cos(dec)*math.cos(ra), math.cos(dec)*math.sin(ra), math.sin(dec)])
    east = np.array([-math.sin(ra), math.cos(ra), 0.])
    north = np.array([-math.sin(dec)*math.cos(ra), -math.sin(dec)*math.sin(ra), math.cos(dec)])
    rate = math.pi/(180*3600*1000)
    moved = point+dt*rate*(row['pmra']*east+row['pmdec']*north)
    moved /= np.linalg.norm(moved)
    return math.degrees(math.atan2(moved[1], moved[0])) % 360, math.degrees(math.asin(moved[2]))


def separation(a, b):
    # Haversine is stable for both small separations and RA wraparound.
    ra1, de1, ra2, de2 = map(math.radians, (*a, *b))
    h = math.sin((de1-de2)/2)**2+math.cos(de1)*math.cos(de2)*math.sin((ra1-ra2)/2)**2
    return math.degrees(2*math.asin(math.sqrt(min(1.,max(0.,h)))))*3600


def freeze():
    rows = gaia_rows()
    references = [r for r in rows.values() if is_reference(r)]
    chosen = sorted(references, key=lambda r: (digest(('echolens-001b-v1:'+r['source_id']).encode()), int(r['source_id'])))[:100]
    record = {'experiment':'001B', 'version':1, 'gaia_raw_sha256':GAIA_HASH,
              'protocol_sha256':digest(PROTOCOL.read_bytes()), 'selection_salt':'echolens-001b-v1:',
              'search_radius_arcsec':15, 'eligibility_radius_arcsec':3, 'neighbor_radius_arcsec':6,
              'search_epoch_mjd_tt':55400., 'targets':[{'gaia_source_id':r['source_id'],
                'search_center_deg':list(propagate(r,55400.))} for r in chosen]}
    SELECTION.parent.mkdir(parents=True, exist_ok=True)
    if SELECTION.exists() and json.loads(SELECTION.read_text()) != record:
        raise ValueError('Refusing to replace a different frozen selection')
    SELECTION.write_text(json.dumps(record,indent=2)+'\n')
    return record


def selected():
    selection = json.loads(SELECTION.read_text())
    if selection['protocol_sha256'] != digest(PROTOCOL.read_bytes()) or selection['gaia_raw_sha256'] != GAIA_HASH:
        raise ValueError('Frozen protocol/source changed')
    if (selection['search_radius_arcsec'], selection['eligibility_radius_arcsec'],
        selection['neighbor_radius_arcsec'], selection['search_epoch_mjd_tt']) != (15,3,6,55400.):
        raise ValueError('Unregistered policy')
    if len(selection['targets']) != 100 or len({r['gaia_source_id'] for r in selection['targets']}) != 100:
        raise ValueError('Invalid target selection')
    return selection


def query_for(targets):
    if len(targets) != 1:
        raise ValueError('IRSA supports one geometric constraint per request')
    cones = []
    for r in targets:
        ra, dec = r['search_center_deg']
        cones.append(f"1=CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{ra:.12f},{dec:.12f},{15/3600:.12f}))")
    return 'SELECT * FROM allwise_p3as_psd WHERE ('+' OR '.join(cones)+')'


def request(query, fmt):
    parameters = {'REQUEST':'doQuery','LANG':'ADQL','FORMAT':fmt,'QUERY':query,'MAXREC':'10001'}
    url = ENDPOINT+'?'+urllib.parse.urlencode(parameters)
    with urllib.request.urlopen(url, timeout=180) as response:
        payload = response.read()
        headers = {k:response.headers.get(k) for k in ('Content-Type','Date','ETag','Last-Modified')}
    return payload, {'endpoint':ENDPOINT,'request_url':url,'query':query,'parameters':parameters,
                     'retrieved_at':datetime.now(timezone.utc).isoformat(),'response_metadata':headers}


def fetch():
    selection = selected()
    DIRECTORY.mkdir(parents=True,exist_ok=True)
    metadata_path = DIRECTORY/'fields.vot.xml.gz'
    metadata_record = DIRECTORY/'metadata_request.json'
    if metadata_path.exists() and metadata_record.exists():
        metadata = gzip.decompress(metadata_path.read_bytes())
        meta_request = json.loads(metadata_record.read_text())
        if digest(metadata) != meta_request['raw_sha256']:
            raise ValueError('Cached metadata checksum mismatch')
    else:
        metadata, meta_request = request('SELECT TOP 1 * FROM allwise_p3as_psd','votable')
        meta_request['raw_sha256'] = digest(metadata)
    fields, _ = parse_votable(metadata)
    needed = {'source_id','cntr','ra','dec','ra_pm','dec_pm','ph_qual','cc_flags','w1mjdmean'}
    if not needed <= fields.keys():
        raise ValueError('Unexpected AllWISE source columns')
    metadata_path.write_bytes(gzip.compress(metadata,mtime=0))
    metadata_record.write_text(json.dumps(meta_request,indent=2)+'\n')
    # Each independently validated batch is checkpointed and can be resumed.
    def batch(index):
        query = query_for(selection['targets'][index:index+1])
        raw_path, record_path = DIRECTORY/f'batch_{index:02d}.fits.gz', DIRECTORY/f'batch_{index:02d}.json'
        if raw_path.exists() and record_path.exists():
            record = json.loads(record_path.read_text())
            if (record['query'] != query or record['metadata_sha256'] != digest(metadata)
                    or record['selection_sha256'] != digest(SELECTION.read_bytes())):
                raise ValueError('Cached batch query or field metadata changed')
            payload = gzip.decompress(raw_path.read_bytes())
            if digest(payload) != record['raw_sha256']:
                raise ValueError('Cached batch checksum mismatch')
        else:
            payload, record = request(query,'fits')
            record.update({'format':'FITS','metadata_file':'fields.vot.xml.gz','metadata_sha256':digest(metadata),
                           'raw_sha256':digest(payload),'catalog':'AllWISE','table':'allwise_p3as_psd',
                           'selection_sha256':digest(SELECTION.read_bytes())})
        with tempfile.TemporaryDirectory() as staging:
            Path(staging,'fields.vot.xml.gz').write_bytes(gzip.compress(metadata,mtime=0))
            _, rows = parse_snapshot(payload,record,staging)
        validate_wise(rows)
        record['rows'] = len(rows)
        raw_path.write_bytes(gzip.compress(payload,mtime=0))
        record_path.write_text(json.dumps(record,indent=2)+'\n')
        print(f'AllWISE cone {index+1}/100: {len(rows)} records',flush=True)
        return record
    with ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(batch,range(100)))
    (DIRECTORY/'fields.vot.xml.gz').write_bytes(gzip.compress(metadata,mtime=0))
    (DIRECTORY/'manifest.json').write_text(json.dumps({'experiment':'001B','catalog':'AllWISE',
        'selection_sha256':digest(SELECTION.read_bytes()),'transport_amendment_sha256':digest(AMENDMENT.read_bytes()),'metadata_request':meta_request,
        'metadata_sha256':digest(metadata),'batches':records,
        'documentation_url':'https://irsa.ipac.caltech.edu/data/WISE/docs/release/AllWISE/expsup/sec2_1a.html',
        'attribution':'NASA/IPAC IRSA; AllWISE, WISE (UCLA/JPL-Caltech) and NEOWISE (JPL-Caltech), funded by NASA'},indent=2)+'\n')


def validate_wise(rows):
    if len(rows) >= 10000:
        raise ValueError('Possible truncated or unexpectedly large cone result')
    ids = set()
    for r in rows:
        if not r.get('source_id') or r['source_id'] in ids:
            raise ValueError('Missing or duplicate AllWISE source')
        ids.add(r['source_id'])
        for flag in ('ph_qual','cc_flags','moon_lev'):
            if r.get(flag) is not None and len(r[flag]) != 4:
                raise ValueError('Malformed per-band quality flag')
        if not (0<=r['ra']<360 and -90<=r['dec']<=90):
            raise ValueError('Invalid AllWISE coordinates')
        for band in range(1,5):
            for suffix in ('sigmpro','sigflux'):
                value = r.get(f'w{band}{suffix}')
                if value is not None and value < 0:
                    raise ValueError('Negative infrared uncertainty')


def candidate_epoch(row):
    if row.get('ra_pm') is not None and row.get('dec_pm') is not None:
        return (row['ra_pm'],row['dec_pm']), 55400., 'motion_fit_epoch'
    for band in (1,2):
        if row.get(f'w{band}mjdmean') is not None:
            return (row['ra'],row['dec']), row[f'w{band}mjdmean'], f'stationary_approximate_w{band}_mean_epoch'
    return (row['ra'],row['dec']), 55400., 'stationary_assumed_epoch'


def photometry(row):
    result = {}
    for index in range(4):
        band = f'w{index+1}'
        ph = (row.get('ph_qual') or '????')[index]
        cc = (row.get('cc_flags') or '????')[index]
        moon = (row.get('moon_lev') or '????')[index]
        mag, error, flux_error, snr = [row.get(band+k) for k in ('mpro','sigmpro','sigflux','snr')]
        kind = 'upper_limit_95pct_flux' if ph=='U' else 'uncertain_measurement' if ph=='Z' else 'missing' if mag is None or ph=='X' else 'measurement'
        failures = []
        checks = {'photometric_quality':ph=='A','snr':snr is not None and snr>=10,
                  'magnitude_and_errors':mag is not None and error is not None and error>0 and flux_error is not None and flux_error>0,
                  'contamination':cc=='0','moon_contamination':moon=='0',
                  'saturation':row.get(band+'sat')==0,
                  'fit_chi_square':row.get(band+'rchi2') is not None and row[band+'rchi2']<=2,
                  'extendedness':row.get('ext_flg')==0,'blend_count':row.get('nb')==1,'active_deblending':row.get('na')==0}
        failures = [name for name, passed in checks.items() if not passed]
        result[band] = {'kind':kind,'magnitude':mag,'magnitude_error':error,'flux':row.get(band+'flux'),
                        'flux_error':flux_error,'snr':snr,'ph_qual':ph,'cc_flag':cc,'moon_level':moon,
                        'quality_pass':not failures,'quality_failures':failures}
    return result


def replay(output):
    if (DIRECTORY/'manifest.json').exists():
        return replay_snapshot(output,DIRECTORY)
    with tempfile.TemporaryDirectory() as staging:
        with tarfile.open(ROOT/'data/wise_001b.tar.gz','r:gz') as archive:
            archive.extractall(staging,filter='data')
        return replay_snapshot(output,Path(staging)/'wise_001b')


def replay_snapshot(output, directory):
    selection = selected()
    gaia = gaia_rows()
    expected = sorted((r for r in gaia.values() if is_reference(r)),
        key=lambda r:(digest(('echolens-001b-v1:'+r['source_id']).encode()),int(r['source_id'])))[:100]
    if [r['source_id'] for r in expected] != [t['gaia_source_id'] for t in selection['targets']]:
        raise ValueError('Frozen target order differs from registered hash selection')
    manifest = json.loads((directory/'manifest.json').read_text())
    if (manifest['selection_sha256'] != digest(SELECTION.read_bytes()) or len(manifest['batches']) != 100
            or manifest['transport_amendment_sha256'] != digest(AMENDMENT.read_bytes())):
        raise ValueError('Manifest/selection mismatch')
    allwise, fields = {}, None
    for index, record in enumerate(manifest['batches']):
        if record['query'] != query_for(selection['targets'][index:index+1]):
            raise ValueError('Batch query mismatch')
        payload = gzip.decompress((directory/f'batch_{index:02d}.fits.gz').read_bytes())
        if digest(payload) != record['raw_sha256']:
            raise ValueError('AllWISE snapshot checksum mismatch')
        fields, rows = parse_snapshot(payload, record, directory)
        validate_wise(rows)
        if len(rows) != record['rows']:
            raise ValueError('Batch row count changed')
        for row in rows:
            row['cntr'] = str(row['cntr'])
            sid = row['source_id']
            if sid in allwise and allwise[sid] != row:
                raise ValueError('Different measurements for duplicate AllWISE ID')
            allwise[sid] = row
    targets = []
    for target in selection['targets']:
        sid = target['gaia_source_id']
        r = gaia[sid]
        if not is_reference(r) or separation(propagate(r,55400.),target['search_center_deg'])>1e-6:
            raise ValueError('Frozen target/reference selection changed')
        candidates = []
        for infrared in allwise.values():
            position, epoch, method = candidate_epoch(infrared)
            sep = separation(propagate(r,epoch),position)
            if sep<=15:
                # Normalize derived display values at 10 microarcsec across numerical-library builds.
                # Eligibility uses the unrounded separation; observations are untouched.
                candidates.append({'allwise_source_id':infrared['source_id'],'separation_arcsec':round(sep,5),
                    'comparison_epoch_mjd_tt':epoch,'epoch_method':method,'eligible':sep<=3,
                    'photometry':photometry(infrared),'motion_blend_swap':len(infrared.get('pmcode') or '')>=2 and infrared['pmcode'][1]=='Y'})
        candidates.sort(key=lambda c:(c['separation_arcsec'],c['allwise_source_id']))
        eligible = [c for c in candidates if c['eligible']]
        record = {'gaia_source_id':sid,'candidate_count':len(candidates),'eligible_count':len(eligible),
                  'association_status':'no_eligible_candidate' if not eligible else 'ambiguous' if len(eligible)>1 else 'provisional_unique',
                  'candidates':candidates,'review_flags':[]}
        if len(eligible)==1:
            chosen = eligible[0]
            record['provisional_allwise_source_id'] = chosen['allwise_source_id']
            if chosen['epoch_method'] != 'motion_fit_epoch': record['review_flags'].append('approximate_stationary_epoch')
            if chosen['motion_blend_swap']: record['review_flags'].append('motion_fit_blend_swap')
            if any(c['allwise_source_id']!=chosen['allwise_source_id'] and c['separation_arcsec']<=6 for c in candidates):
                record['review_flags'].append('nearby_infrared_neighbor')
        targets.append(record)
    reuse = {}
    for target in targets:
        if 'provisional_allwise_source_id' in target:
            reuse.setdefault(target['provisional_allwise_source_id'],[]).append(target)
    for group in reuse.values():
        if len(group)>1:
            for target in group: target['review_flags'].append('infrared_source_reused')
    for target in targets:
        unique = target['association_status']=='provisional_unique'
        candidate = next((c for c in target['candidates'] if c['eligible']),None) if unique else None
        target['w1_w2_ready_for_image_review'] = bool(unique and not target['review_flags']
            and all(candidate['photometry'][band]['quality_pass'] for band in ('w1','w2')))
    result = {'experiment':'001B','gaia_raw_sha256':GAIA_HASH,'selection_sha256':digest(SELECTION.read_bytes()),
              'wise_manifest_sha256':digest((directory/'manifest.json').read_bytes()),
              'target_count':len(targets),'unique_allwise_rows':len(allwise),'allwise_fields':len(fields),
              'association_counts':{status:sum(t['association_status']==status for t in targets) for status in
                                    ('provisional_unique','ambiguous','no_eligible_candidate')},
              'w1_w2_ready_for_image_review':sum(t['w1_w2_ready_for_image_review'] for t in targets),
              'targets':targets,'interpretation':'Geometry/quality feasibility only; associations provisional; no infrared excess or technology score.'}
    output = Path(output)
    output.mkdir(parents=True,exist_ok=True)
    (output/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    (output/'observations.json').write_text(json.dumps({'catalog':'AllWISE','fields':fields,
        'measurements':list(allwise.values()),'provenance_manifest':'data/wise_001b/manifest.json'},indent=2,allow_nan=False)+'\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['freeze','fetch','replay'])
    p.add_argument('--output',default='reports/experiment_001b')
    args = p.parse_args()
    if args.action=='freeze':
        print('Frozen targets:',len(freeze()['targets']))
    else:
        if args.action=='fetch': fetch()
        result = replay(args.output)
        print(json.dumps({k:result[k] for k in ('target_count','unique_allwise_rows','allwise_fields',
                                             'association_counts','w1_w2_ready_for_image_review')},indent=2))
