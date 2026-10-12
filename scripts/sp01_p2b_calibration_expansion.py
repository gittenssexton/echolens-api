"""Read-only GALAH DR4 P2B calibration-only expansion, 2026-10-12.

Six never-scored CALIBRATION stars plus mapping tests on the two existing calibrators.
Zero holdout reads; do not classify astronomical anomalies or score discovery.
Original Buder+2025 allspec IDs must match BEFORE fetching a new source.
"""
from __future__ import annotations
import csv, datetime as dt, hashlib, io, json, os, re, urllib.parse, urllib.request, urllib.error
from pathlib import Path
from scripts.sp01_p2b_original_datalink_probe import (BASE, fits_header, verify_eight_hdu)

OUT=Path(os.environ.get('P2B_CAL_EXPANSION_OUTPUT','reports/sp01_p2b_calibration_expansion'))
DATA=Path('data/sp01_p2b_eight_calibration.csv')
PREVIOUS={'151111003101245','221003001101138'}
FROZEN_SHA='ef62ec0bd5afd79a8c39613f2796943937dd09d9eb6e6bfabe644522e2beed32'
CATALOG='J/other/PASA/42.51/allspec'
TAP='https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync'
ALLSPEC='https://cloud.datacentral.org.au/teamdata/GALAH/public/GALAH_DR4/analysis_products_single'
MAX=2_000_000
RANGE={'B':(4600,5000),'G':(5500,6100),'R':(6300,6900),'I':(7400,8200)}


def targets(path:Path=DATA)->list[dict]:
    with path.open(newline='') as f:rows=list(csv.DictReader(f))
    expected={'cool_low','cool_high','warm_low','warm_high'}
    if len(rows)!=8 or {r['stratum'] for r in rows}!=expected:raise ValueError('Expected exactly 8 calibration rows, all four strata')
    if any(sum(r['stratum']==s for r in rows)!=2 for s in expected):raise ValueError('Expected 2 stars per stratum')
    if len({r['gaia_dr3_source_id'] for r in rows})!=8 or len({r['sobject_id'] for r in rows})!=8:raise ValueError('Duplicate IDs')
    for r in rows:
        if r['role']!='calibration' or r['original_manifest_sha256']!=FROZEN_SHA:raise ValueError('Cannot accept holdout or altered frozen manifest')
        for col in ('gaia_dr3_source_id','sobject_id'):
            v=r[col]
            if not re.fullmatch('[1-9][0-9]{13,18}',v) or int(v)>=2**63:raise ValueError('IDs must be exact decimal strings')
    if {r['sobject_id'] for r in rows[:2]}!=PREVIOUS:raise ValueError('First two calibrated stars changed')
    return rows


def request(url:str,*,data:bytes|None=None, limit:int=MAX)->tuple[int,str,bytes]:
    req=urllib.request.Request(url,method=('POST' if data is not None else 'GET'),data=data,headers={
        'User-Agent':'EchoLens-DR4-P2B-control-validation/1.0 (calibration-only public research)',
        'Content-Type':'application/x-www-form-urlencoded' if data is not None else 'application/octet-stream'})
    try:
        with urllib.request.urlopen(req,timeout=45) as resp:
            return resp.status,str(resp.headers.get('Content-Type','')),resp.read(limit+1)
    except urllib.error.HTTPError as exc:
        return exc.code,str(exc.headers.get('Content-Type','')),exc.read(min(limit,8192))


def source_check(rows:list[dict],catalogue_bytes:bytes)->dict:
    query='SELECT TOP 16 "GALAH","GaiaDR3","flagSp","flagRed" FROM "'+CATALOG+'" WHERE "GALAH" IN ('+','.join(r['sobject_id'] for r in rows)+')'
    encoded=urllib.parse.urlencode({'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','QUERY':query}).encode()
    status,ctype,raw=request(TAP,data=encoded,limit=250000)
    record={'url':TAP,'query':query,'http_status':status,'response_sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'matched':False,'rows':[]}
    (OUT/'original_dr4_8_visits_response.native').write_bytes(raw)
    if status!=200 or b'<VOTABLE' in raw[:400] or len(raw)>250000:
        record['error']='Original GALAH DR4 subset could not be queried';return record
    try:
        lines=[l for l in raw.decode('utf-8-sig').splitlines() if l.strip() and not l.startswith('#')]
        found=list(csv.DictReader(io.StringIO('\n'.join(lines))))
        expected={r['sobject_id']:r['gaia_dr3_source_id'] for r in rows}
        valid={}
        for x in found:
            visit=x['GALAH'].strip();gaia=x['GaiaDR3'].strip()
            if visit not in expected or gaia!=expected[visit] or visit in valid:raise ValueError('Original catalogue pair mismatch or duplicate')
            valid[visit]=x
        if set(valid)!=set(expected):raise ValueError('Original GALAH catalogue missing one or more visits')
        record.update(matched=True,rows=[{'sobject_id':v,'gaia_dr3_source_id':expected[v],'flagSp':x.get('flagSp'),'flagRed':x.get('flagRed')} for v,x in sorted(valid.items())])
    except Exception as e:record['error']=str(e)
    return record


def header_summary(raw:bytes)->dict:
    if not raw.startswith(b'SIMPLE  ='):return {'valid_FITS_header':False}
    try:
        h,_=fits_header(raw,0)
        n=int(h.get('NAXIS1','0'))
        start=float(h['CRVAL1'])+(1-float(h.get('CRPIX1','1')))*float(h['CDELT1'])
        end=float(h['CRVAL1'])+(n-float(h.get('CRPIX1','1')))*float(h['CDELT1'])
        return {'valid_FITS_header':True,'spectrum_id':h.get('GALAH_ID') or h.get('SOBJECT'), 'SPECTID':h.get('SPECTID'), 'BAND':h.get('BAND'), 'wavelength_bounds_A':[round(min(start,end),2),round(max(start,end),2)]}
    except Exception as e:return {'valid_FITS_header':False,'header_error':str(e)[:180]}


def acquire(visit:str,filter_value:str,band_expected:str|None,kind:str)->dict:
    url=BASE+'?'+urllib.parse.urlencode({'ID':visit,'DR':'galah_dr4','FILT':filter_value,'RESPONSEFORMAT':'fits'})
    r={'visit':visit,'filter':filter_value,'expected_band':band_expected,'kind':kind,'url':url,'IDX_omitted':True}
    try:
        status,ctype,raw=request(url)
        r.update(http_status=status,content_type=ctype,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        if status!=200 or len(raw)>MAX:raise ValueError('HTTP '+str(status)+' or response size exceeded')
        r['header']=header_summary(raw)
        if band_expected is None:
            # A diagnostic filter is never promoted to verified merely because its label looked plausible.
            for possible in ('B','G','R','I'):
                try:
                    info=verify_eight_hdu(raw,visit,possible)
                    r['actual_validated_camera']=possible;r['resolution_median_FWHM_A']=info['lsf_median_FWHM_A']
                    if possible not in ('B','R') and filter_value not in ('G','I'):
                        # Save only for external independent review; registry acceptance is separate.
                        fn=f'{visit}_FILT_{filter_value}_verified_{possible}.fits';(OUT/fn).write_bytes(raw);r['saved_file']=fn
                    break
                except ValueError:pass
            r['status']='diagnostic_mapping_only'
        else:
            info=verify_eight_hdu(raw,visit,band_expected)
            fn=f'{visit}_{band_expected}_original_camera.fits';(OUT/fn).write_bytes(raw)
            r.update(status='verified_native_8hdu',file=fn,LSF={'median_FWHM_A':info['lsf_median_FWHM_A'],'FWHM_range_A':info['lsf_range_FWHM_A'],'median_R':info['R_median']})
    except Exception as e:r.update(status='blocked',error=str(e)[:300])
    return r


def analysis(visit:str)->dict:
    date=visit[:6];url=f'{ALLSPEC}/{date}/{visit}/{visit}_single_fit_spectrum.fits'
    r={'visit':visit,'kind':'original_survey_analysis_product','url':url}
    try:
        status,ctype,raw=request(url)
        r.update(http_status=status,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        if status!=200 or len(raw)>MAX or not raw.startswith(b'SIMPLE  ='):raise ValueError('No valid analysis FITS or exceeded limit')
        from scripts.sp01_p2b_first_two import fits_summary
        info=fits_summary(raw,'official_allspec',None,visit)
        fn=f'{visit}_single_fit_spectrum.fits';(OUT/fn).write_bytes(raw)
        r.update(status='verified_analysis_FITS',filename=fn,hdu_count=info['hdu_count'])
    except Exception as e:r.update(status='blocked',error=str(e)[:250])
    return r


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    rows=targets()
    report={'schema':'echolens-p2b-calibration-expansion-v1','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'holdout_sources_read':0,'source_selection':'frozen 50 source provisional detrended manifest SHA256 '+FROZEN_SHA,'number_of_calibration_sources_selected':8,'real_techno_anomaly_scoring':False,'results':[]}
    report['original_catalogue']=source_check(rows,b'')
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    if not report['original_catalogue']['matched']:
        print(json.dumps({'blocked':'original GALAH DR4 identity verification','catalogue':report['original_catalogue']},indent=2));return
    for row in rows:
        visit=row['sobject_id']
        if visit in PREVIOUS:
            # Four alternative filter probes per previously inspected star, no prior valid B/R re-downloads.
            for flag in ('V','G','I','IR'):
                report['results'].append(acquire(visit,flag,None,'filter_camera_diagnostic'))
                (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
        else:
            for flag in ('B','R'):
                report['results'].append(acquire(visit,flag,flag,'new_calibrator_native'))
                (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
            report['results'].append(analysis(visit))
            (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'identity_verified':True,'existing_sources':2,'new_calibrators':6,'verified_native_new':sum(x['status']=='verified_native_8hdu' for x in report['results']),'verified_allspec_new':sum(x['status']=='verified_analysis_FITS' for x in report['results']),'filter_diagnostics':[{'visit':x['visit'],'filter':x['filter'],'status':x['status'],'valid_camera':x.get('actual_validated_camera'),'header':x.get('header')} for x in report['results'] if x['kind']=='filter_camera_diagnostic']},indent=2))

if __name__=='__main__':main()
