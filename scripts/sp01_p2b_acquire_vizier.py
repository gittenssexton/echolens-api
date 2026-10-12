"""Bounded SP01-P2B VizieR *detrended* GALAH DR4 feasibility acquisition.

This is explicitly a source substitution/engineering feasibility run. The
primary GALAH DR4 main_star native release is NOT downloaded by this script.
The VizieR table is Kos et al (2025)'s 917588-row DETRENDED GALAH DR4 copy,
and labels derive from Escorza et al (2026) s-rich published catalog.
Not a confirmatory null population, no new spectroscopic files or scores.
"""
from __future__ import annotations
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from .sp01_p2b_acquire import (fetch_tap,rows_from_csv,exact_id,COLS,
                                POSITIVES_TAP,POS_CITATION,STRATA,AcquisitionFailed,sha)

OUT=Path(os.environ.get('SP01_P2B_OUTPUT','reports/sp01_p2b_mirror_trial'))
GALAH_MIRROR_TABLE='"J/A+A/703/A104/catalog"'
MIRROR_URL='https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=J%2FA%2BA%2F703%2FA104'
FIELDS={'gaiadr3_source_id':'GaiaDR3','sobject_id':'GALAH',
 'teff':'Teff','logg':'logg','fe_h':'[Fe/H]',
 'snr_px_ccd2':'snrpxccd2','snr_px_ccd3':'snrpxccd3',
 'flag_sp':'flagsp','flag_red':'flagred','phot_g_mean_mag':'Gmag',
 'bp_rp':'BP-RP','ruwe':'RUWE'}


def acquisition():
    OUT.mkdir(parents=True,exist_ok=True)
    meta={'schema':'echolens-sp01-p2b-vizier-feasibility-v1',
          'status':'started','not_original_galah_dr4_catalog':True,
          'provider':'VizieR TAP','catalogue':'Kos et al 2025 DETRENDED GALAH DR4, J/A+A/703/A104/catalog',
          'positive_catalogue':'Escorza et al 2026 J/A+A/712/A111/catalog',
          'mirror_url':MIRROR_URL,'sources':[],
          'governance':'Source-substitution engineering trial: do not call a confirmatory 50-star manifest or measured instrument-level baseline'}
    def save(name,data,p):
        (OUT/name).write_bytes(data)
        meta['sources'].append({'filename':name,**p})
        (OUT/'provenance.json').write_text(json.dumps(meta,indent=2)+'\n')
    posquery='SELECT TOP 1059 "GaiaDR3" FROM "J/A+A/712/A111/catalog" WHERE "GaiaDR3" IS NOT NULL'
    pdata,pp=fetch_tap(POSITIVES_TAP,posquery)
    save('positive_original_vizier.csv',pdata,pp)
    published=rows_from_csv(pdata,['GaiaDR3'])
    ids=sorted({exact_id(x['GaiaDR3']) for x in published},
      key=lambda sid:hashlib.sha256(('echolens-sp01-p2b-v1:'+sid).encode()).hexdigest())[:150]
    if len(ids)<10:raise AcquisitionFailed('Positive literature catalogue has fewer than 10 valid IDs')
    fields=','.join(f'"{v}" AS {k}' for k,v in FIELDS.items())
    pool=[]
    for name,tlo,thi,slo,shi in STRATA:
        clauses=[f'"Teff">={tlo}',f'"Teff"<{thi}',f'"snrpxccd3">{slo}',
           '"snrpxccd2">30','"flagsp"=0','"flagred"=0',
           '"logg">=4.0','"logg"<=4.65','"[Fe/H]">=-0.8',
           '"[Fe/H]"<=0.5','"RUWE"<1.4','"RUWE">0']
        if shi is not None:clauses.append(f'"snrpxccd3"<{shi}')
        q=('SELECT TOP 180 '+fields+' FROM '+GALAH_MIRROR_TABLE+
            ' WHERE '+' AND '.join(clauses)+' ORDER BY "GaiaDR3"')
        data,p=fetch_tap(POSITIVES_TAP,q)
        save(f'normal_{name}_detrended_source.csv',data,p)
        rows=rows_from_csv(data,COLS)
        for row in rows:
            exact_id(row['gaiadr3_source_id']);exact_id(row['sobject_id'])
        pool.extend(rows)
    # Positive IDs independently preordered by source hash, not spectral quality.
    q=('SELECT '+fields+' FROM '+GALAH_MIRROR_TABLE+
       ' WHERE "GaiaDR3" IN ('+','.join(ids)+')')
    data,p=fetch_tap(POSITIVES_TAP,q)
    save('positive_matches_detrended_source.csv',data,p)
    matches=rows_from_csv(data,COLS)
    pool.extend(matches)
    seen=set();unique=[]
    for row in pool:
        key=(row['gaiadr3_source_id'],row['sobject_id'])
        if key not in seen:seen.add(key);unique.append(row)
    with (OUT/'candidate_metadata.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=COLS);w.writeheader();w.writerows(unique)
    observed=set(x['gaiadr3_source_id'] for x in matches)
    labels=[{'gaiadr3_source_id':sid,'classification':'Escorza+2026 published s-process enriched GALAH source',
             'reference_url':POS_CITATION} for sid in ids if sid in observed]
    with (OUT/'independent_positive_labels.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['gaiadr3_source_id','classification','reference_url'])
        w.writeheader();w.writerows(labels)
    meta['status']='source_rows_acquired_pending_source_specific_review'
    meta['counts']={'unique_source_visits':len(unique),'positive_matched_rows':len(matches),'independent_labels':len(labels),
                    'ordinary_rows_by_query':{k:sum(1 for s in meta['sources'] if s['filename']==f'normal_{k}_detrended_source.csv') for k,_,_,_,_ in STRATA}}
    # Provenance bundle hashes original provider responses, not entire original 723 MB GALAH table.
    sourcefiles=sorted(OUT.glob('*source.csv'))+sorted(OUT.glob('*vizier.csv'))
    with (OUT/'native_response_bundle.bin').open('wb') as f:
        for p in sorted(sourcefiles):
            raw=p.read_bytes();name=p.name.encode()
            f.write(len(name).to_bytes(4,'big')+name+len(raw).to_bytes(8,'big')+raw)
    meta['native_response_bundle_sha256']=sha((OUT/'native_response_bundle.bin').read_bytes())
    (OUT/'provenance.json').write_text(json.dumps(meta,indent=2)+'\n')
    if len(labels)<10:raise AcquisitionFailed('Too few independently positive IDs matched: '+str(len(labels)))
    return meta

if __name__=='__main__':
    try:
        result=acquisition();print(json.dumps({'status':result['status'],'counts':result['counts']},indent=2))
    except Exception as exc:
        OUT.mkdir(parents=True,exist_ok=True)
        err={'status':'blocked','error_type':type(exc).__name__,'message':str(exc),
             'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'source':'detrended_VizieR_feasibility'}
        (OUT/'failure.json').write_text(json.dumps(err,indent=2)+'\n')
        print(json.dumps(err,indent=2),file=sys.stderr)
        sys.exit(2)
