"""Acquire/replay a frozen WD positional-support pilot; never certify counterparts."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import urllib.parse
import urllib.request

from astropy.time import Time
from scripts.import_gaia import parse_votable

ENDPOINT = 'https://gea.esac.esa.int/tap-server/tap/sync'
COLUMNS = ['source_id', 'ref_epoch', 'ra', 'dec', 'ra_error', 'dec_error',
           'parallax', 'parallax_error', 'pmra', 'pmdec', 'pmra_error', 'pmdec_error',
           'ra_dec_corr', 'ra_parallax_corr', 'ra_pmra_corr', 'ra_pmdec_corr',
           'dec_parallax_corr', 'dec_pmra_corr', 'dec_pmdec_corr',
           'parallax_pmra_corr', 'parallax_pmdec_corr', 'pmra_pmdec_corr',
           'phot_g_mean_mag', 'ruwe', 'duplicated_source', 'astrometric_params_solved',
           'ipd_frac_multi_peak', 'radial_velocity', 'radial_velocity_error']


def separation(ra1, dec1, ra2, dec2):
    a, b, c, d = map(math.radians, [ra1, dec1, ra2, dec2])
    h = math.sin((d-b)/2)**2 + math.cos(b)*math.cos(d)*math.sin((c-a)/2)**2
    return math.degrees(2*math.asin(math.sqrt(min(1, max(0, h))))) * 3600


def propagate(row, epoch):
    for k in ['ra', 'dec', 'ref_epoch', 'pmra', 'pmdec']:
        if row.get(k) is None or not math.isfinite(row[k]):
            raise ValueError('Missing astrometry: ' + k)
    a, d = math.radians(row['ra']), math.radians(row['dec'])
    n = [math.cos(d)*math.cos(a), math.cos(d)*math.sin(a), math.sin(d)]
    east, north = [-math.sin(a), math.cos(a), 0], [-math.sin(d)*math.cos(a), -math.sin(d)*math.sin(a), math.cos(d)]
    dt = epoch-row['ref_epoch']
    scale = math.pi/(180*3600*1000)
    moved = [n[i] + dt*scale*(row['pmra']*east[i] + row['pmdec']*north[i]) for i in range(3)]
    norm = math.sqrt(sum(x*x for x in moved))
    return math.degrees(math.atan2(moved[1], moved[0])) % 360, math.degrees(math.asin(moved[2]/norm))


def covariance(row, epoch):
    keys = ['ra_error', 'dec_error', 'pmra_error', 'pmdec_error', 'ra_dec_corr',
            'ra_pmra_corr', 'ra_pmdec_corr', 'dec_pmra_corr', 'dec_pmdec_corr', 'pmra_pmdec_corr']
    if any(row.get(k) is None or not math.isfinite(row[k]) for k in keys):
        return None
    a, d, u, v = (row[k] for k in keys[:4])
    if min(a, d, u, v) < 0 or any(abs(row[k]) > 1 for k in keys[4:]):
        raise ValueError('Invalid native astrometric covariance input')
    t = epoch-row['ref_epoch']
    aa = a*a + 2*t*row['ra_pmra_corr']*a*u + t*t*u*u
    dd = d*d + 2*t*row['dec_pmdec_corr']*d*v + t*t*v*v
    ad = row['ra_dec_corr']*a*d + t*(row['ra_pmdec_corr']*a*v + row['dec_pmra_corr']*d*u) + t*t*row['pmra_pmdec_corr']*u*v
    eigen = (aa+dd+math.sqrt((aa-dd)**2+4*ad*ad))/2
    if min(aa, dd, aa*dd-ad*ad, eigen) < -1e-10:
        raise ValueError('Propagated covariance is not positive semidefinite')
    return {'matrix_mas2': [[aa, ad], [ad, dd]],
            'gaia_only_semimajor_arcsec': math.sqrt(max(0, eigen))/1000,
            'scope': 'Linear Gaia tangent covariance; no LAMOST/parallax/perspective error model'}


def queries(design):
    ids = [s['reported_gaia_source_id'] for s in design['sample']]
    if any(not i.isascii() or not i.isdigit() for i in ids):
        raise ValueError('Nondecimal source ID in frozen design')
    select = 'SELECT ' + ','.join(COLUMNS) + ' FROM gaiadr3.gaia_source'
    exact = select + ' WHERE source_id IN (' + ','.join(ids) + ')'
    cones = set()
    radius = design['decision_rules']['candidate_cone_radius_arcsec']/3600
    for sample in design['sample']:
        for ra, dec in [('ra', 'dec'), ('ra_obs', 'dec_obs')]:
            r = sample['lamost']
            cones.add(f"1=CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{r[ra]:.17g},{r[dec]:.17g},{radius:.17g}))")
    return {'exact_ids': exact, 'neighbors': select + ' WHERE ' + ' OR '.join(sorted(cones))}


def acquire(design, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    q = queries(design)
    manifest = {'design_sha256': hashlib.sha256(json.dumps(design, sort_keys=True).encode()).hexdigest(),
                'endpoint': ENDPOINT, 'catalog': 'gaiadr3.gaia_source',
                'method_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'requests': {}}
    try:
        for label, query in q.items():
            parameters = {'REQUEST': 'doQuery', 'LANG': 'ADQL', 'FORMAT': 'votable',
                          'MAXREC': str(design['decision_rules']['maximum_candidates']), 'QUERY': query}
            record = {'query': query, 'parameters': parameters, 'started_at': datetime.now(timezone.utc).isoformat()}
            manifest['requests'][label] = record
            request = urllib.request.Request(ENDPOINT, data=urllib.parse.urlencode(parameters).encode())
            with urllib.request.urlopen(request, timeout=90) as response:
                raw = response.read(10*1024**2+1)
                record.update(http_status=response.status, response_url=response.url,
                              content_type=response.headers.get('Content-Type'))
            (directory/(label+'.vot')).write_bytes(raw)
            record.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            if len(raw) > 10*1024**2:
                raise ValueError('Response byte cap exceeded')
            fields, rows = parse_votable(raw)  # Rejects TAP ERROR and OVERFLOW.
            if len(rows) > design['decision_rules']['maximum_candidates']:
                raise ValueError('Candidate cap exceeded')
            record.update(rows=len(rows), fields=fields, status='validated',
                          finished_at=datetime.now(timezone.utc).isoformat())
            print(label, len(rows), 'Gaia rows preserved', flush=True)
    except Exception as exc:
        manifest['failure'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        (directory/'acquisition.json').write_text(json.dumps(manifest, indent=2, allow_nan=False)+'\n')
    return manifest


def assess(sample, exact, neighbors, tolerance):
    gid, l = sample['reported_gaia_source_id'], sample['lamost']
    epoch = float(Time(l['obsdate'], scale='utc').tcb.jyear)
    result = {'obsid': sample['obsid'], 'reported_gaia_source_id': gid,
              'epoch_tcb_jyear': epoch, 'physical_counterpart_certified': False,
              'input_to_fiber_arcsec': separation(l['ra'], l['dec'], l['ra_obs'], l['dec_obs'])}
    if gid not in exact:
        return dict(result, status='REPORTED_ID_NOT_FOUND')
    row = exact[gid]
    result['gaia_reported_id_measurements'] = row
    result['fiber_separation_at_gaia_ref_epoch_arcsec'] = separation(row['ra'], row['dec'], l['ra_obs'], l['dec_obs'])
    try:
        ra, dec = propagate(row, epoch)
    except ValueError as e:
        return dict(result, status='INSUFFICIENT_ASTROMETRY', reason=str(e))
    result['propagated_reported_position_deg'] = {'ra': ra, 'dec': dec}
    result['reported_fiber_separation_at_obsdate_arcsec'] = separation(ra, dec, l['ra_obs'], l['dec_obs'])
    result['gaia_only_covariance'] = covariance(row, epoch)
    candidates, unresolved = [], []
    for candidate in {**neighbors, gid: row}.values():
        try:
            a, d = propagate(candidate, epoch)
            sep = separation(a, d, l['ra_obs'], l['dec_obs'])
            if sep <= tolerance:
                candidates.append({'source_id': candidate['source_id'], 'separation_arcsec': sep})
        except ValueError:
            # Unknown PM must not disappear from the local ambiguity screen.
            if separation(candidate['ra'], candidate['dec'], l['ra_obs'], l['dec_obs']) <= tolerance:
                unresolved.append(candidate['source_id'])
    result.update(position_compatible_candidates=sorted(candidates, key=lambda c: c['separation_arcsec']),
                  nearby_candidates_missing_motion=unresolved)
    if result['reported_fiber_separation_at_obsdate_arcsec'] > tolerance:
        status = 'POSITION_DISAGREEMENT'
    elif any(c['source_id'] != gid for c in candidates):
        status = 'MULTIPLE_POSITION_COMPATIBLE'
    elif unresolved:
        status = 'UNRESOLVED_NEIGHBOR'
    else:
        status = 'SINGLE_POSITION_SUPPORT_CONDITIONAL'
    result['status'] = status
    return result


def replay(design, directory):
    directory = Path(directory)
    manifest = json.loads((directory/'acquisition.json').read_text())
    if manifest['design_sha256'] != hashlib.sha256(json.dumps(design, sort_keys=True).encode()).hexdigest():
        raise ValueError('Frozen design differs from acquisition')
    parsed = {}
    for label, query in queries(design).items():
        record = manifest['requests'][label]
        raw = (directory/(label+'.vot')).read_bytes()
        if record['status'] != 'validated' or record['query'] != query or hashlib.sha256(raw).hexdigest() != record['sha256']:
            raise ValueError('Acquisition identity/validation mismatch')
        _, rows = parse_votable(raw)
        by_id = {r['source_id']: r for r in rows}
        if len(by_id) != len(rows):
            raise ValueError('Duplicate Gaia IDs in response')
        parsed[label] = by_id
    allowed = {s['reported_gaia_source_id'] for s in design['sample']}
    if set(parsed['exact_ids']) - allowed:
        raise ValueError('Unexpected exact-query source ID')
    results = [assess(s, parsed['exact_ids'], parsed['neighbors'],
                      design['decision_rules']['fiber_sensitivity_radius_arcsec']) for s in design['sample']]
    return {'run_id': design['run_id'], 'design_sha256': manifest['design_sha256'],
            'method_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'source_count': len(results), 'neighbor_rows': len(parsed['neighbors']),
            'physically_certified_counterparts': 0,
            'limitations': design['limitations'], 'results': results}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('design')
    p.add_argument('directory')
    p.add_argument('--acquire', action='store_true')
    args = p.parse_args()
    design = json.loads(Path(args.design).read_text())
    if args.acquire:
        acquire(design, args.directory)
    result = replay(design, args.directory)
    print(json.dumps(result, indent=2, allow_nan=False))
