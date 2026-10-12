"""Small, read-only GALAH DR4 + independent s-rich control-catalog TAP acquisition.

Executed only as a bounded opt-in research workflow. Writes native response bytes,
queries, SHA-256 checksums, metadata and canonical CSV for the preregistered
SP01-P2B selector. Does not fetch spectra or produce anomaly scores.
"""
from __future__ import annotations
import csv
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# The schema and tables are documented at galah-survey.org/dr4/the_catalogues/
GALAH_TAP = 'https://datacentral.org.au/vo/tap/sync'
POSITIVES_TAP = 'https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync'
POS_CITATION = 'https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=J%2FA%2BA%2F712%2FA111'
COLS = ['gaiadr3_source_id','sobject_id','teff','logg','fe_h','snr_px_ccd2',
        'snr_px_ccd3','flag_sp','flag_red','phot_g_mean_mag','bp_rp','ruwe']
MAX_BYTES = 3_000_000
STRATA = [
 ('cool_low',4800,5600,30,60), ('cool_high',4800,5600,60,None),
 ('warm_low',5600,6400,30,60), ('warm_high',5600,6400,60,None)]

class AcquisitionFailed(Exception):
    pass


def sha(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()


def fetch_tap(endpoint,query,*,retries=2):
    params = urllib.parse.urlencode({'REQUEST':'doQuery','LANG':'ADQL',
                                     'FORMAT':'csv','QUERY':query}).encode('ascii')
    hdr={'Content-Type':'application/x-www-form-urlencoded',
         'User-Agent':'EchoLens-P2B-research/0.1 (bounded scientific TAP query)'}
    error=None
    for attempt in range(retries):
        req=urllib.request.Request(endpoint,data=params,headers=hdr,method='POST')
        try:
            with urllib.request.urlopen(req,timeout=50) as response:
                data=response.read(MAX_BYTES+1)
                status=response.status
                final=response.url
                media=response.headers.get('Content-Type','')
            if len(data)>MAX_BYTES: raise AcquisitionFailed('response limit exceeded')
            if status!=200: raise AcquisitionFailed(f'HTTP {status}')
            text=data[:2000].lower()
            if b'<votable' in text or b'<html' in text or b'query_status' in text or b'error' in text[:160]:
                raise AcquisitionFailed('TAP error document received instead of CSV: '+repr(data[:320]))
            return data,{'status':status,'endpoint':endpoint,'returned_url':final,
                         'content_type':media,'retrieved_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
                         'sha256':sha(data),'bytes':len(data),'query':query}
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError) as e:
            error=e
            if isinstance(e,urllib.error.HTTPError) and e.code not in (429,500,502,503,504):
                break
            if attempt<retries-1:time.sleep(2)
    raise AcquisitionFailed(f'TAP failure at {endpoint}: {error}')


def rows_from_csv(data:bytes, required):
    try:
        s=data.decode('utf-8-sig')
    except UnicodeError as e:
        raise AcquisitionFailed('CSV encoding failure') from e
    noncomment=[line for line in s.splitlines() if line.strip() and not line.startswith('#')]
    if not noncomment:raise AcquisitionFailed('empty TAP CSV')
    parser=csv.DictReader(io.StringIO('\n'.join(noncomment)))
    cols=parser.fieldnames or []
    missing=set(required)-set(cols)
    if missing:raise AcquisitionFailed(f'CSV missing columns {sorted(missing)}; got {cols}')
    out=list(parser)
    if any(None in row for row in out):raise AcquisitionFailed('incomplete CSV row')
    if not out:raise AcquisitionFailed('TAP returned zero records')
    return out


def exact_id(v):
    text=str(v or '').strip()
    if not re.fullmatch('[1-9][0-9]{8,18}',text):
        raise AcquisitionFailed(f'invalid/nonexact identifier {text!r}')
    if int(text)>=2**63:raise AcquisitionFailed('Gaia ID outside int64')
    return text


def acquisition(outdir:Path):
    outdir.mkdir(parents=True,exist_ok=True)
    meta={'schema':'echolens-sp01-p2b-acquisition-v1','status':'started',
          'input_selection':'prospective, no previously-inspected residuals',
          'primary_catalog':'GALAH DR4 main_star, one row/star',
          'positive_catalog':'Escorza et al. 2026 s-process enriched subset, VizieR J/A+A/712/A111',
          'sources':[], 'limits':{'maximum_bytes_per_response':MAX_BYTES,
                                  'top_per_stratum':180,'positive_id_query_limit':150}}
    def save_step(name,data,provenance):
        (outdir/name).write_bytes(data)
        meta['sources'].append({'filename':name,**provenance})
        (outdir/'provenance.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf8')

    # Positives are a *separate independent publication*, not selected by GALAH line-residual outcomes.
    q='SELECT TOP 1059 "GaiaDR3" FROM "J/A+A/712/A111/catalog" WHERE "GaiaDR3" IS NOT NULL'
    raw,ref=fetch_tap(POSITIVES_TAP,q)
    save_step('positive_original_tap.csv',raw,ref)
    pos_rows=rows_from_csv(raw,['GaiaDR3'])
    positive_ids=sorted({exact_id(r['GaiaDR3']) for r in pos_rows},
                        key=lambda sid: hashlib.sha256(('echolens-sp01-p2b-v1:'+sid).encode()).hexdigest())
    positive_ids=positive_ids[:150]
    if len(positive_ids)<10:raise AcquisitionFailed('fewer than 10 independent s-rich catalogue IDs')

    pool=[]
    for label,tlo,thi,slo,shi in STRATA:
        clauses=[f'teff>={tlo}',f'teff<{thi}',f'snr_px_ccd3>{slo}',
                 'snr_px_ccd2>30','flag_sp=0','flag_red=0',
                 'logg>=4.0','logg<=4.65','fe_h>=-0.8','fe_h<=0.5',
                 'ruwe<1.4','ruwe>0']
        if shi is not None:clauses.append(f'snr_px_ccd3<{shi}')
        q=('SELECT TOP 180 '+','.join(COLS)+' FROM galah_dr4.main_star WHERE '+
           ' AND '.join(clauses)+' ORDER BY gaiadr3_source_id')
        data,prov=fetch_tap(GALAH_TAP,q)
        save_step(f'normal_{label}_original_tap.csv',data,prov)
        chunk=rows_from_csv(data,COLS)
        # Data only: ensure the returned rows satisfy the requested temperature and SNR stratum.
        for row in chunk:
            exact_id(row['gaiadr3_source_id']);exact_id(row['sobject_id'])
            t=float(row['teff']);snr=float(row['snr_px_ccd3'])
            if not(tlo<=t<thi and snr>slo and (shi is None or snr<shi)):
                raise AcquisitionFailed(f'archive stratum mismatch {label}')
        pool.extend(chunk)

    # Match preselected independent labels by their original decimal Gaia IDs.
    ids=','.join(positive_ids)
    q='SELECT '+','.join(COLS)+' FROM galah_dr4.main_star WHERE gaiadr3_source_id IN ('+ids+')'
    data,prov=fetch_tap(GALAH_TAP,q)
    save_step('positive_matching_original_tap.csv',data,prov)
    positives_matches=rows_from_csv(data,COLS)
    pool.extend(positives_matches)
    # Strip duplicate same source/visit from results of overlapping queries, but retain visit differences.
    seen=set();uniques=[]
    for row in pool:
        key=(row['gaiadr3_source_id'],row['sobject_id'])
        if key not in seen:
            seen.add(key);uniques.append(row)
    with (outdir/'candidate_metadata.csv').open('w',newline='',encoding='utf8') as out:
        writer=csv.DictWriter(out,fieldnames=COLS);writer.writeheader();writer.writerows(uniques)
    observed=set(row['gaiadr3_source_id'] for row in positives_matches)
    labelled=[{'gaiadr3_source_id':sid,'classification':'Escorza+2026 s-process enriched GALAH DR4',
               'reference_url':POS_CITATION} for sid in positive_ids if sid in observed]
    with (outdir/'independent_positive_labels.csv').open('w',newline='',encoding='utf8') as out:
        writer=csv.DictWriter(out,fieldnames=['gaiadr3_source_id','classification','reference_url'])
        writer.writeheader();writer.writerows(labelled)
    meta['status']='catalog_metadata_retrieved'
    meta['counts']={'normal_query_rows':len(pool)-len(positives_matches),
                    'positive_matched_rows':len(positives_matches),
                    'positive_label_rows':len(labelled),
                    'unique_source_visit_rows':len(uniques)}
    meta['candidate_csv_sha256']=sha((outdir/'candidate_metadata.csv').read_bytes())
    meta['positive_labels_sha256']=sha((outdir/'independent_positive_labels.csv').read_bytes())
    (outdir/'provenance.json').write_text(json.dumps(meta,indent=2)+'\n')
    if len(labelled)<10:
        raise AcquisitionFailed(f'Only {len(labelled)} published positive IDs matched; cohort blocked')
    return meta

if __name__=='__main__':
    folder=Path(os.environ.get('SP01_P2B_OUTPUT','reports/sp01_p2b_trial'))
    try:
        outcome=acquisition(folder)
        print(json.dumps({'status':'catalog_rows_acquired','counts':outcome['counts']},indent=2))
    except Exception as exc:
        failure={'status':'blocked','error_type':type(exc).__name__,'message':str(exc),
                 'utc':dt.datetime.now(dt.timezone.utc).isoformat()}
        folder.mkdir(parents=True,exist_ok=True)
        (folder/'failure.json').write_text(json.dumps(failure,indent=2)+'\n')
        print(json.dumps(failure,indent=2),file=sys.stderr)
        sys.exit(2)
