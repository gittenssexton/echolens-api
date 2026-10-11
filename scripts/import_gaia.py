"""Fetch once, validate, then atomically build a replayable Gaia DR3 snapshot."""
import argparse
from io import BytesIO
from astropy.io.votable import parse
from astropy.table import Table
from astropy.io import fits
from astropy.units import UnitsWarning
import warnings
import numpy as np
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import tempfile
import time
from datetime import datetime, timezone
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from app.registry import SCHEMA

ENDPOINT = 'https://gea.esac.esa.int/tap-server/tap/sync'
DOC = 'https://gea.esac.esa.int/archive/documentation/GDR3/Gaia_archive/chap_datamodel/sec_dm_main_source_catalogue/ssec_dm_gaia_source.html'
VERSION = 'gaia-registry-v1'

def query_for(count, provider="esa"):
    table = {"esa":"gaiadr3.gaia_source", "irsa":"gaia_dr3_source"}[provider]
    if not 1 <= count <= 100000:
        raise ValueError('count must be 1..100000')
    return f'''SELECT TOP {count} * FROM {table}
WHERE random_index < 1000000
AND classprob_dsc_combmod_star >= 0.9
ORDER BY random_index ASC'''

def parse_votable(payload):
    root = ET.fromstring(payload)
    ns = {'v': root.tag.split('}')[0].strip('{')}
    statuses = root.findall('.//v:INFO[@name="QUERY_STATUS"]', ns)
    if not statuses or any(s.get('value') != 'OK' for s in statuses):
        raise ValueError('TAP error or truncated result: ' + ' '.join((s.text or s.get('value', '')) for s in statuses))
    table = root.find('.//v:TABLE', ns)
    if table is None:
        raise ValueError('Missing VOTable table')
    fields = {}
    for f in table.findall('v:FIELD', ns):
        name = f.attrib['name']
        if name in fields:
            raise ValueError('Duplicate column')
        fields[name] = {**dict(f.attrib), 'unit': f.get('unit'), 'datatype': f.get('datatype'),
                        'ucd': f.get('ucd'), 'description': f.findtext('v:DESCRIPTION', default='', namespaces=ns)}
    rows = []
    parsed = parse(BytesIO(payload)).get_first_table().to_table(use_names_over_ids=True)
    for record in parsed:
        row = {}
        for name in fields:
            val = record[name]
            if np.ma.is_masked(val):
                value = None
            elif hasattr(val, 'item'):
                value = val.item()
            else:
                value = val
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            if isinstance(value, str) and not value.strip():
                value = None
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f'Nonfinite {name}; explicit nulls required')
            row[name] = value
        for identifier in ('source_id', 'solution_id'):
            if identifier in row and row[identifier] is not None:
                row[identifier] = str(row[identifier])
        rows.append(row)
    return fields, rows

def parse_snapshot(payload, manifest, directory):
    if manifest.get('format') != 'FITS':
        return parse_votable(payload)
    if not payload.startswith(b'SIMPLE'):
        raise ValueError('Expected a native FITS response')
    metadata = gzip.decompress((Path(directory)/manifest['metadata_file']).read_bytes())
    if hashlib.sha256(metadata).hexdigest() != manifest['metadata_sha256']:
        raise ValueError('Field metadata checksum mismatch')
    fields, _ = parse_votable(metadata)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UnitsWarning)
        table = Table.read(BytesIO(payload), format='fits')
    # IRSA's FITS writer can count zero-filled transport padding as table rows.
    # Only trim trailing records whose numeric bytes are zero, text is blank and logical flags are false; never
    # truncate extra astronomical records merely to satisfy the expected count.
    with fits.open(BytesIO(payload), memmap=False) as hdus:
        statuses = [str(v).split('<VOEND>')[-1] for k,v in hdus[1].header.items() if str(k).startswith('VOKW') and 'QUERY_STATUS.<xmlattr>.value<VOEND>' in str(v)]
        if not statuses or any(value != 'OK' for value in statuses):
            raise ValueError('Missing, failed or truncated FITS TAP status')
        records = hdus[1].data.view(np.recarray)
        end = len(records)
        logical_offsets = [records.dtype.fields[c.name][1] for c in hdus[1].columns if c.format == 'L']
        text_ranges = [(records.dtype.fields[c.name][1],records.dtype.fields[c.name][0].itemsize) for c in hdus[1].columns if str(c.format).endswith('A')]
        def empty_transport_record(record):
            raw = bytearray(record.tobytes())
            for start, size in text_ranges:
                for offset in range(start,start+size):
                    if raw[offset] == ord(' '): raw[offset] = 0
            for offset in logical_offsets:
                if raw[offset] == ord('F'): raw[offset] = 0
            return not any(raw)
        while end and empty_transport_record(records[end-1]):
            end -= 1
        padding = len(records) - end
    if 'transport_padding_rows' in manifest and manifest['transport_padding_rows'] != padding:
        raise ValueError('Unexpected FITS padding change')
    manifest['transport_padding_rows'] = padding
    table = table[:end]
    if set(fields) != set(table.colnames):
        raise ValueError('FITS/metadata field mismatch')
    for name, info in fields.items():
        if 'precision' in info: info['display_precision'] = info.pop('precision')
        if 'irsa_format' in info: info['display_format'] = info.pop('irsa_format')
        info['native_dtype'] = str(table[name].dtype)
        info['serialization'] = 'native FITS; display precision does not limit stored values'
    rows = []
    for record in table:
        row = {}
        for name in fields:
            val = record[name]
            if np.ma.is_masked(val):
                val = None
            elif hasattr(val, 'item'):
                val = val.item()
            if isinstance(val, bytes): val = val.decode('utf-8')
            if isinstance(val, str): val = val.rstrip()
            # IEEE NaN is the FITS representation of missing floating values.
            if isinstance(val, float) and math.isnan(val): val = None
            if isinstance(val, float) and not math.isfinite(val):
                raise ValueError(f'Nonfinite {name}')
            if name in ('source_id','solution_id') and val is not None: val = str(val)
            row[name] = val
        rows.append(row)
    return fields, rows

def fetch_irsa(count, snapshot, manifest_path):
    endpoint = 'https://irsa.ipac.caltech.edu/TAP/sync'
    query = query_for(count, 'irsa')
    params = {'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'fits','QUERY':query,'MAXREC':str(count+1)}
    url = endpoint+'?'+urllib.parse.urlencode(params)
    metadata_query = query_for(1, 'irsa')
    metadata_url = endpoint+'?'+urllib.parse.urlencode({**params,'FORMAT':'votable','QUERY':metadata_query})
    with urllib.request.urlopen(metadata_url,timeout=180) as r:
        metadata = r.read()
    parse_votable(metadata)
    with urllib.request.urlopen(url,timeout=300) as r:
        payload = r.read()
        headers = {k:r.headers.get(k) for k in ('Content-Type','Date','ETag','Last-Modified')}
    manifest = {'schema_version':1,'importer_version':VERSION,'catalog':'Gaia','release':'DR3',
        'provider':'irsa','table':'gaia_dr3_source','endpoint':endpoint,
        'request_url':url,'response_url':url,'request_parameters':params,'query':query,
        'format':'FITS','retrieved_at':datetime.now(timezone.utc).isoformat(),
        'expected_rows':count,'raw_sha256':hashlib.sha256(payload).hexdigest(),
        'response_metadata':headers,'metadata_file':'gaia_dr3.fields.vot.xml.gz',
        'metadata_sha256':hashlib.sha256(metadata).hexdigest(),'metadata_request_url':metadata_url,
        'documentation_url':DOC,
        'mirror_documentation_url':'https://irsa.ipac.caltech.edu/data/Gaia/dr3/gaia_dr3_source_colDescriptions.html',
        'selection':'classification-selected pilot; not a volume-complete census or confirmed non-technological controls',
        'attribution':'ESA/Gaia/DPAC; Gaia DR3 (Gaia Collaboration, Vallenari et al. 2023); served by NASA/IPAC IRSA'}
    return save_irsa_snapshot(payload, metadata, manifest, snapshot, manifest_path)

def save_irsa_snapshot(payload, metadata, manifest, snapshot, manifest_path):
    # Stage both artifacts, validate all observations, then publish the snapshot.
    Path(snapshot).parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as staging:
        Path(staging,manifest['metadata_file']).write_bytes(gzip.compress(metadata,mtime=0))
        _, rows = parse_snapshot(payload,manifest,staging)
        validate(rows,manifest['expected_rows'])
    Path(snapshot).with_name(manifest['metadata_file']).write_bytes(gzip.compress(metadata,mtime=0))
    Path(snapshot).write_bytes(gzip.compress(payload,mtime=0))
    Path(manifest_path).write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

def is_reference(r):
    """Provisional screen only: no claim of constant brightness or absence of life."""
    return ((r.get('parallax_over_error') or 0) >= 10
            and r.get('phot_g_mean_mag') is not None and r['phot_g_mean_mag'] < 18
            and r.get('astrometric_params_solved') in (31, 95)
            and r.get('ruwe') is not None and r['ruwe'] < 1.4
            and (r.get('visibility_periods_used') or 0) >= 9
            and r.get('duplicated_source') in (False, 0)
            and r.get('non_single_star') == 0
            and r.get('phot_variable_flag') != 'VARIABLE'
            and all(r.get(name) is not None for name in ('ra_error','dec_error','parallax_error','pmra_error','pmdec_error'))
            and all(r.get(f'phot_{band}_mean_flux_error') is not None for band in ('g','bp','rp'))
            and all((r.get(f'phot_{band}_mean_flux_over_error') or 0) >= 50
                    for band in ('g','bp','rp')))

def validate(rows, expected):
    if len(rows) != expected:
        raise ValueError(f'Expected {expected} sources; received {len(rows)}')
    ids = set()
    previous = None
    random_indices = set()
    for r in rows:
        sid = r['source_id']
        if not sid.isdigit() or not 0 < int(sid) < 2**63 or sid in ids:
            raise ValueError('Invalid or duplicate source ID')
        ids.add(sid)
        for name in ('ra', 'dec', 'ref_epoch', 'random_index', 'classprob_dsc_combmod_star'):
            if r.get(name) is None:
                raise ValueError(f'Missing required {name}')
        if not (0 <= r['ra'] < 360 and -90 <= r['dec'] <= 90):
            raise ValueError('Invalid sky position')
        if not (0 <= r['random_index'] < 1000000 and .9 <= r['classprob_dsc_combmod_star'] <= 1):
            raise ValueError('Selection violation')
        for name, value in r.items():
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f'Nonfinite {name}')
            if name.endswith('_error') and not name.endswith('_over_error') and value is not None and value < 0:
                raise ValueError(f'Negative uncertainty {name}')
            if name.endswith('_corr') and value is not None and not -1 <= value <= 1:
                raise ValueError(f'Invalid correlation {name}')
        if r['random_index'] in random_indices:
            raise ValueError('Gaia random_index must be unique')
        random_indices.add(r['random_index'])
        key = (r['random_index'], int(sid))
        if previous is not None and key <= previous:
            raise ValueError('Unexpected ordering')
        previous = key
    return {'rows': len(rows), 'unique_source_ids': len(ids), 'selection_valid': True,
            'coordinate_ranges_valid': True, 'uncertainties_valid': True,
            'ranges': {k: {'min': min(v), 'max': max(v)} for k in ('ra','dec','b','phot_g_mean_mag','bp_rp','parallax','teff_gspphot','logg_gspphot','distance_gspphot') if (v := [r[k] for r in rows if r.get(k) is not None])},
            'published_variable_count': sum(r.get('phot_variable_flag') == 'VARIABLE' for r in rows),
            'provisional_reference_criteria': 'parallax SNR>=10, G<18, astrometry31/95, RUWE<1.4, visibility>=9, nonduplicated, non_single_star=0, not VARIABLE, three-band SNR>=50, available uncertainties',
            'provisional_reference_count': sum(is_reference(r) for r in rows),
            'null_counts': {k: sum(r[k] is None for r in rows) for k in rows[0]}}

def build(snapshot, manifest_path, db_path):
    payload = gzip.decompress(Path(snapshot).read_bytes())
    manifest = json.loads(Path(manifest_path).read_text())
    digest = hashlib.sha256(payload).hexdigest()
    expected_query = query_for(manifest['expected_rows'], manifest.get('provider', 'esa'))
    if digest != manifest['raw_sha256'] or ' '.join(manifest['query'].split()) != ' '.join(expected_query.split()):
        raise ValueError('Snapshot digest or query mismatch')
    fields, rows = parse_snapshot(payload, manifest, Path(snapshot).parent)
    report = validate(rows, manifest['expected_rows'])
    report['raw_sha256'] = digest
    report['transport_padding_rows'] = manifest.get('transport_padding_rows', 0)
    manifest['validation'] = report
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=db_path.parent, suffix='.sqlite3')
    os.close(fd)
    try:
        with sqlite3.connect(tmp) as c:
            c.executescript(SCHEMA)
            c.execute('INSERT INTO imports VALUES (?,?,?)', (digest, json.dumps(manifest), json.dumps(fields)))
            c.executemany('INSERT INTO stars VALUES (?,?,?,?,?,?,?,?,?)',
                [(r['source_id'], digest, r['ra'], r['dec'], r.get('phot_g_mean_mag'), r.get('bp_rp'), r.get('parallax'), r.get('ruwe'), json.dumps(r, allow_nan=False)) for r in rows])
            if c.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or c.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('Database integrity failed')
        os.replace(tmp, db_path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    return report

def fetch(count, snapshot, manifest_path, resume_job=None, output_format="votable"):
    query = query_for(count)
    params = {'REQUEST':'doQuery', 'LANG':'ADQL', 'FORMAT':output_format, 'QUERY':query, 'MAXREC':str(count), 'PHASE':'RUN'}
    url = ENDPOINT.removesuffix('/sync') + '/async'
    if resume_job:
        if not resume_job.startswith(url + '/') or '?' in resume_job or '#' in resume_job:
            raise ValueError('Resume URL must be a Gaia archive job URL')
        job_url = resume_job.rstrip('/')
        with urllib.request.urlopen(job_url + '?poll=' + str(time.time_ns()), timeout=60) as response:
            job = ET.fromstring(response.read())
        values = {p.get('id'): p.text for p in job.findall('.//{http://www.ivoa.net/xml/UWS/v1.0}parameter')}
        if values.get('query') != query:
            raise ValueError('Resumed job query does not match frozen selection')
    else:
        body = urllib.parse.urlencode(params).encode()
        with urllib.request.urlopen(urllib.request.Request(url, data=body), timeout=60) as response:
            job_url = response.url.rstrip('/')
    print('Gaia job:', job_url, flush=True)
    deadline = time.monotonic() + 900
    previous_phase = None
    while True:
        with urllib.request.urlopen(job_url + '/phase?poll=' + str(time.time_ns()), timeout=60) as response:
            phase = response.read().decode().strip()
        if phase != previous_phase:
            print('Gaia phase:', phase, flush=True)
            previous_phase = phase
        if phase == 'COMPLETED':
            break
        if phase == 'ABORTED':
            raise ValueError(f'TAP job aborted: {job_url}')
        if phase == 'ERROR':
            with urllib.request.urlopen(job_url + '/error', timeout=60) as response:
                detail = response.read().decode()[:2000]
            raise ValueError(f'TAP job {phase}: {detail}')
        if time.monotonic() > deadline:
            raise TimeoutError(f'TAP deadline; job URL: {job_url}')
        time.sleep(3)
    final_url = job_url + '/results/result'
    with urllib.request.urlopen(final_url, timeout=120) as response:
        payload = response.read()
        response_metadata = {k: response.headers.get(k) for k in ('Content-Type','Date','ETag','Last-Modified')}
    _, rows = parse_votable(payload)
    validate(rows, count)
    manifest = {'schema_version':1, 'importer_version':VERSION, 'catalog':'Gaia', 'release':'DR3',
                'table':'gaiadr3.gaia_source', 'endpoint':url, 'request_url':url, 'request_parameters':params, 'job_url':job_url,
                'response_url':final_url, 'response_metadata':response_metadata, 'query':query, 'format':'VOTable (archive serialization preserved)',
                'retrieved_at':datetime.now(timezone.utc).isoformat(), 'expected_rows':count,
                'raw_sha256':hashlib.sha256(payload).hexdigest(), 'documentation_url':DOC,
                'selection':'pilot stellar candidates; not a volume-complete census or confirmed non-technological controls',
                'attribution':'ESA/Gaia/DPAC; Gaia DR3 (Gaia Collaboration, Vallenari et al. 2023)'}
    Path(snapshot).parent.mkdir(parents=True, exist_ok=True)
    Path(snapshot).write_bytes(gzip.compress(payload, mtime=0))
    Path(manifest_path).write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fetch', action='store_true', help='Explicit network access; default is offline replay')
    p.add_argument('--provider', choices=['esa','irsa'], default='esa')
    p.add_argument('--format', choices=['votable','votable_plain'], default='votable')
    p.add_argument('--resume-job', help='Resume an existing Gaia UWS job with verified matching query')
    p.add_argument('--count', type=int, default=10000)
    p.add_argument('--snapshot', default='data/gaia_dr3.raw.gz')
    p.add_argument('--manifest', default='data/gaia_dr3.manifest.json')
    p.add_argument('--database', default='data/registry.sqlite3')
    a = p.parse_args()
    if a.provider == 'irsa' and a.resume_job:
        p.error('IRSA uses synchronous FITS retrieval, not Gaia job resumption')
    if a.fetch and a.provider == 'irsa':
        fetch_irsa(a.count,a.snapshot,a.manifest)
    elif a.fetch or a.resume_job:
        fetch(a.count, a.snapshot, a.manifest, a.resume_job, a.format)
    report = build(a.snapshot, a.manifest, a.database)
    Path(a.database).with_suffix('.validation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'null_counts'}, indent=2))

if __name__ == '__main__': main()
