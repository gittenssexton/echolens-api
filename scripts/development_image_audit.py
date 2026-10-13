"""Native AllWISE development-only image acquisition and deterministic diagnostics.

These approximate apertures are checks on existing catalog photometry, not
independent measurements, uncertainty estimates, or a contamination clearance.
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import io
import json
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.stats import sigma_clip
from astropy.wcs import WCS
from scripts.wise_image_audit import fractional_circle, aperture

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/development_image_audit_v12'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def context():
    design = json.loads((OUT / 'design.json').read_text())
    source = ROOT / 'reports/calibration_cohort_v10/results.json'
    if digest(source) != design['readiness_results_sha256']:
        raise ValueError('Readiness input changed')
    rows = {s['source_id']: s for s in json.loads(source.read_text())}
    selected = [rows[sid] for sid in design['development_source_ids']]
    if len(selected) != 9 or len({s['source_id'] for s in selected}) != 9:
        raise ValueError('Expected nine distinct development targets')
    if any(s['analysis_role'] != 'calibration_development' or not s['joint_ready'] for s in selected):
        raise ValueError('Reserved or ineligible target')
    return design, selected


def freeze():
    if (OUT / 'design.json').exists():
        raise FileExistsError('Do not overwrite frozen design')
    old = ROOT / 'reports/calibration_development_v11/design.json'
    d = json.loads(old.read_text())
    write(OUT / 'design.json', {
        'experiment': 'development-image-audit-v12',
        'frozen_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'development_design_sha256': digest(old),
        'readiness_results_sha256': digest(ROOT / 'reports/calibration_cohort_v10/results.json'),
        'development_source_ids': d['development_source_ids'],
        'bands': ['W1', 'W3'], 'cutout_size_arcsec': 180,
        'aperture_radius_arcsec': 8.25, 'subpixels': 8,
        'sky_annuli_arcsec': [[25, 40], [40, 55], [50, 70]],
        'sky_estimator': 'median; 3 sigma clipping, five iterations',
        'role': 'exploratory development only; no replacement, reserved scoring, or clearance',
        'limitations': 'same Atlas observations; catalog aperture correction reused; no uncertainty/covariance model; W1 visual only',
    })


def acquire_one(s, band):
    sid = s['source_id']
    m = s['surveys']['wise']['chosen']['measurement']
    tile = m['coadd_id']
    query = urllib.parse.urlencode({'center': f"{m['ra']},{m['dec']}", 'size': '180arcsec', 'gzip': 'false'})
    url = (f'https://irsa.ipac.caltech.edu/ibe/data/wise/allwise/p3am_cdd/'
           f'{tile[:2]}/{tile[:4]}/{tile}/{tile}-{band.lower()}-int-3.fits?{query}')
    p = OUT / 'raw' / sid / f'{band}.fits'
    if p.exists() or p.with_suffix('.manifest.json').exists():
        raise FileExistsError(p)
    request = urllib.request.Request(url, headers={'User-Agent': 'EchoLens-development-image-audit-v12'})
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
        status = response.status
        final_url = response.url
    with fits.open(io.BytesIO(data)) as hdus:
        hdus.verify('exception')
        if hdus[0].data is None or hdus[0].data.ndim != 2:
            raise ValueError('Not a native two dimensional image')
        shape = list(hdus[0].data.shape)
        header = hdus[0].header
        center = WCS(header).all_world2pix([[m['ra'], m['dec']]], 0)[0]
        if not (0 <= center[0] < shape[1] and 0 <= center[1] < shape[0]):
            raise ValueError('Catalog position outside image')
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    write(p.with_suffix('.manifest.json'), {
        'source_id': sid, 'band': band, 'coadd_id': tile, 'url': url,
        'response_url': final_url, 'status': status,
        'retrieved_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'raw_sha256': digest(p), 'bytes': len(data), 'shape': shape,
    })
    return {'source_id': sid, 'band': band, 'bytes': len(data)}


def acquire():
    d, rows = context()
    # Bounded concurrency for independent, immutable native responses.
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        jobs = [pool.submit(acquire_one, s, b) for s in rows for b in d['bands']]
        for job in concurrent.futures.as_completed(jobs):
            print(json.dumps(job.result()), flush=True)


def image_for(sid, band):
    p = OUT / 'raw' / sid / f'{band}.fits'
    meta = json.loads(p.with_suffix('.manifest.json').read_text())
    if meta['source_id'] != sid or meta['band'] != band or digest(p) != meta['raw_sha256']:
        raise ValueError('Native image provenance mismatch')
    with fits.open(p) as h:
        h.verify('exception')
        header = h[0].header.copy()
        if (header.get('BAND') != int(band[1:]) or header.get('COADDID') != meta['coadd_id']
                or header.get('FILETYPE') != 'intensity image' or header.get('BUNIT') != 'DN'):
            raise ValueError('Image band, tile, type, or units mismatch')
        return np.array(h[0].data, float), header


def diagnose(s, d):
    sid = s['source_id']
    m = s['surveys']['wise']['chosen']['measurement']
    image, header = image_for(sid, 'W3')
    wcs = WCS(header)
    center = wcs.all_world2pix([[m['ra'], m['dec']]], 0)[0]
    scale = float(np.sqrt(abs(np.linalg.det(wcs.pixel_scale_matrix))) * 3600)
    weights = fractional_circle(image.shape, center, d['aperture_radius_arcsec']/scale, d['subpixels'])
    yy, xx = np.indices(image.shape)
    radius = np.hypot(xx-center[0], yy-center[1]) * scale
    if min(center[0], center[1], image.shape[1]-1-center[0], image.shape[0]-1-center[1])*scale < 70:
        raise ValueError('Outer sky annulus truncated')
    cases = []
    for low, high in d['sky_annuli_arcsec']:
        mask = (radius >= low) & (radius <= high) & np.isfinite(image)
        clipped = sigma_clip(image[mask], sigma=3, maxiters=5)
        sky = float(np.ma.median(clipped))
        net = aperture(image, weights, sky)
        mag = None if net <= 0 else float(header['MAGZP'] - 2.5*np.log10(net) - m['w3mcor'])
        cases.append({'annulus_arcsec': [low, high], 'pixels': int(mask.sum()),
                      'pixels_retained': int(clipped.count()), 'sky_DN': sky,
                      'sky_scatter_DN': float(clipped.std()), 'net_DN': net,
                      'corrected_mag': mag,
                      'minus_catalog_standard_mag': None if mag is None else mag-m['w3mag'],
                      'minus_profile_mag': None if mag is None else mag-m['w3mpro']})
    mags = [c['corrected_mag'] for c in cases if c['corrected_mag'] is not None]
    return {'source_id': sid, 'shape': list(image.shape), 'scale_arcsec': scale,
            'catalog_pixel': center.tolist(), 'BUNIT': header.get('BUNIT'), 'MAGZP': header['MAGZP'],
            'annulus_cases': cases, 'sky_choice_mag_range': max(mags)-min(mags) if mags else None,
            'catalog': {k: m[k] for k in ['w3mpro','w3sigmpro','w3mag','w3sigm','w3flg','w3mcor','w3rchi2','w1sat','w1rchi2','nb','na','ext_flg','cc_flags']},
            'catalog_larger_aperture_flags': {str(i): m[f'w3flg_{i}'] for i in range(1,9)},
            'no_formal_image_uncertainty': True}


def replay():
    d, rows = context()
    for s in rows:
        for band in d['bands']:
            image_for(s['source_id'], band)
    result = [diagnose(s, d) for s in rows]
    write(OUT/'diagnostics.json', result)
    write(OUT/'summary.json', {'targets': len(result), 'native_images_verified': len(rows)*len(d['bands']),
                             'reserved_predictions': 0,
                             'standard_aperture_confusion_flagged': [s['source_id'] for s in result if s['catalog']['w3flg'] & 1],
                             'status': 'approximate same-data diagnostics; no detection significance or control clearance'})
    print((OUT/'summary.json').read_text())


def figures():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    from astropy.visualization import simple_norm
    d, rows = context()
    for page in range(3):
        fig, axes = plt.subplots(3, 2, figsize=(9, 12))
        for row, s in enumerate(rows[page*3:(page+1)*3]):
            m = s['surveys']['wise']['chosen']['measurement']
            for col, band in enumerate(d['bands']):
                image, header = image_for(s['source_id'], band)
                wcs = WCS(header)
                center = wcs.all_world2pix([[m['ra'],m['dec']]],0)[0]
                scale = float(np.sqrt(abs(np.linalg.det(wcs.pixel_scale_matrix)))*3600)
                ax = axes[row,col]
                ax.imshow(image, origin='lower', cmap='gray_r', norm=simple_norm(image,'asinh',percent=99.5))
                ax.add_patch(Circle(center,8.25/scale,fill=False,color='tab:red',lw=1))
                for radius in [50,70]:
                    ax.add_patch(Circle(center,radius/scale,fill=False,color='tab:blue',lw=.7))
                ax.set_title(f"{s['source_id']} — {band}",fontsize=10)
                ax.set_xlabel('Atlas x pixel');ax.set_ylabel('Atlas y pixel')
        fig.suptitle('Native 180″ AllWISE fields: red 8.25″ aperture; blue 50–70″ sky\nIndependent display stretches; W1 visual only; same catalog observations',fontsize=11)
        fig.tight_layout(rect=[0,0,1,.95])
        fig.savefig(OUT/f'fields_{page+1}.png',dpi=130)
        plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['freeze','acquire','replay','figures'])
    globals()[parser.parse_args().action]()
