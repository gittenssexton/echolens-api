"""Execute ten frozen, linked observational pilots strictly in sequence."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import itertools
import json
import math
from pathlib import Path
import sqlite3
import urllib.parse
import urllib.request

from astropy.time import Time
from scripts.import_gaia import parse_votable
from scripts.wd_counterpart_pilot import propagate, separation, replay


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def color(a, sa, b, sb):
    if not all(finite(v) for v in [a, sa, b, sb]) or min(sa, sb) <= 0:
        return None
    delta = a-b
    return {'color_mag': delta, 'sigma_independent_mag': math.hypot(sa, sb),
            'sigma_correlation_bounds_mag': [abs(sa-sb), sa+sb],
            'conservative_three_sigma_zero_reference_flag': abs(delta) > 3*(sa+sb),
            'scope': 'Measurement-only color; zero reference is not a fitted photosphere'}


def wise_quality(row, band):
    i, p = band-1, 'w'+str(band)
    ph, cc = row.get('ph_qual') or '', row.get('cc_flags') or ''
    checks = {'photometric_detection': len(ph)>i and ph[i] in 'AB',
              'not_catalog_upper_limit': len(ph)>i and ph[i] != 'U',
              'clean_artifact_flag': len(cc)>i and cc[i]=='0',
              'finite_magnitude': finite(row.get(p+'mpro')),
              'measured_positive_uncertainty': finite(row.get(p+'sigmpro')) and row[p+'sigmpro']>0,
              'snr_at_least_5': finite(row.get(p+'snr')) and row[p+'snr']>=5,
              'profile_fit': finite(row.get(p+'rchi2')) and row[p+'rchi2']<=2,
              'low_saturation': finite(row.get(p+'sat')) and row[p+'sat']<=.01,
              'not_extended': row.get('ext_flg')==0,
              'single_component': row.get('nb')==1, 'not_actively_deblended': row.get('na')==0}
    return {'pass': all(checks.values()), 'checks': checks,
            'native_ph_qual': ph[i] if len(ph)>i else None,
            'native_cc_flag': cc[i] if len(cc)>i else None}


def coords(row):
    return row['ra'], row.get('dec', row.get('decl'))


def request_catalog(ctx, table, epoch):
    specification=ctx['design']['acquisition']
    out=ctx['out']/'raw';out.mkdir(exist_ok=True)
    record={'table':table,'epoch_center_jyear':epoch,'started_at':stamp(),
            'transport':'One geometric constraint per request, following existing EchoLens IRSA adapter',
            'batches':[]}
    unique={}
    replay_source=Path(ctx['replay_raw']) if ctx.get('replay_raw') else None
    prior=json.loads((replay_source/(table+'_acquisition.json')).read_text()) if replay_source else None
    try:
        for index,sample in enumerate(ctx['samples']):
            a,d=propagate(ctx['gaia'][sample['reported_gaia_source_id']],epoch)
            query=f"SELECT * FROM {table} WHERE CONTAINS(POINT(ra,dec),CIRCLE({a:.12f},{d:.12f},{specification['radius_arcsec']/3600:.12f}))=1"
            params={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'votable',
                    'MAXREC':str(specification['maximum_rows']),'QUERY':query}
            name=f'{table}_{index:02d}.vot'
            batch={'query':query,'parameters':params,'file':name,
                   'reported_gaia_id':sample['reported_gaia_source_id'],'started_at':stamp()}
            record['batches'].append(batch)
            if replay_source:
                old=prior['batches'][index]
                raw=(replay_source/name).read_bytes()
                if old['status']!='validated' or old['query']!=query or hashlib.sha256(raw).hexdigest()!=old['sha256']:
                    raise ValueError('Offline survey identity/validation mismatch')
            else:
                url=specification['endpoint']+'?'+urllib.parse.urlencode(params)
                with urllib.request.urlopen(url,timeout=90) as response:
                    raw=response.read(10*1024**2+1)
                    batch.update(request_url=url,http_status=response.status,content_type=response.headers.get('Content-Type'))
                (out/name).write_bytes(raw)
            batch.update(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
            if len(raw)>10*1024**2:raise ValueError('Response byte cap exceeded')
            fields,rows=parse_votable(raw)
            if len(rows)>specification['maximum_rows']:raise ValueError('Row cap exceeded')
            if index==0:record['fields']=fields
            elif fields!=record['fields']:raise ValueError('Survey schema changed within run')
            for row in rows:
                key=row['designation']
                if key in unique and unique[key]!=row:raise ValueError('Conflicting repeated catalog row')
                unique[key]=row
            if len(unique)>specification['maximum_rows']:raise ValueError('Aggregate row cap exceeded')
            batch.update(rows=len(rows),status='validated',finished_at=stamp())
            print(table,index+1,'of',len(ctx['samples']),len(rows),'rows',flush=True)
        record.update(rows=len(unique),status='validated')
        return list(unique.values())
    except Exception as exc:
        record.update(status='failed',failure=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        record['finished_at']=stamp()
        (out/(table+'_acquisition.json')).write_text(json.dumps(record,indent=2,allow_nan=False)+'\n')


def p01(ctx):
    return [{'gaia_id':r['reported_gaia_source_id'],
             'reference_separation_arcsec':r['fiber_separation_at_gaia_ref_epoch_arcsec'],
             'observation_separation_arcsec':r['reported_fiber_separation_at_obsdate_arcsec'],
             'change_arcsec':r['reported_fiber_separation_at_obsdate_arcsec']-r['fiber_separation_at_gaia_ref_epoch_arcsec'],
             'material_change':abs(r['reported_fiber_separation_at_obsdate_arcsec']-r['fiber_separation_at_gaia_ref_epoch_arcsec'])>=.1}
            for r in ctx['cp']['results']]


def p02(ctx):
    output=[]
    for s in ctx['samples']:
        l=s['lamost']; epoch=float(Time(l['obsdate'],scale='utc').tcb.jyear)
        distances=[]; missing=[]
        for r in ctx['neighbors']:
            try:
                a,d=propagate(r,epoch);distances.append(separation(a,d,l['ra_obs'],l['dec_obs']))
            except ValueError:
                a,d=coords(r)
                if separation(a,d,l['ra_obs'],l['dec_obs'])<=6:missing.append(r['source_id'])
        output.append({'gaia_id':s['reported_gaia_source_id'],
                       'candidate_counts':{str(radius):sum(v<=radius for v in distances) for radius in [1,2,3,6]},
                       'nearby_missing_motion':missing})
    return output


def p03(ctx):
    rows=[]
    for s in ctx['samples']:
        r=ctx['gaia'][s['reported_gaia_source_id']]
        checks={'motion_errors_available':all(finite(r.get(k)) for k in ['pmra','pmdec','ra_error','dec_error','pmra_error','pmdec_error']),
                'ruwe':finite(r.get('ruwe')) and r['ruwe']<=1.4,
                'not_duplicated':r.get('duplicated_source') is False,
                'few_multiple_peaks':finite(r.get('ipd_frac_multi_peak')) and r['ipd_frac_multi_peak']<=2}
        rows.append({'gaia_id':r['source_id'],'pass':all(checks.values()),'checks':checks,
                     'native_ruwe':r.get('ruwe'),'native_ipd_frac_multi_peak':r.get('ipd_frac_multi_peak')})
    ctx['astrometry']={r['gaia_id']:r['pass'] for r in rows}
    return rows


def p04(ctx):
    output=[]
    supplement=ctx['design'].get('repeat_supplement')
    selected=supplement['sample'] if supplement else ctx['samples']
    with sqlite3.connect(Path(ctx['db']).resolve().as_uri()+'?mode=ro',uri=True) as db:
        for s in selected:
            records=[json.loads(r[0]) for r in db.execute("SELECT values_json FROM observations WHERE product='wd' AND reported_gaia_source_id=? ORDER BY obsid",(s['reported_gaia_source_id'],))]
            pairs=[]
            for a,b in itertools.combinations(records,2):
                for parameter,unit in [('teff','K'),('logg','dex')]:
                    vals=[a.get(parameter),a.get(parameter+'_err'),b.get(parameter),b.get(parameter+'_err')]
                    if all(finite(v) and v!=-9999 for v in vals) and min(vals[1],vals[3])>0:
                        pairs.append({'obsids':[a['obsid'],b['obsid']],'parameter':parameter,'unit':unit,
                                      'native_values':vals,'difference':vals[0]-vals[2],
                                      'maximum_error_sigma':vals[1]+vals[3],
                                      'conservative_three_sigma_tension':abs(vals[0]-vals[2])>3*(vals[1]+vals[3])})
            output.append({'gaia_id':s['reported_gaia_source_id'],'cohort':'repeat_supplement' if supplement else 'primary',
                           'observations':len(records),'comparisons':pairs})
    return output


def p05(ctx):
    data=request_catalog(ctx,'allwise_p3as_psd',2010.5);ctx['wise_rows']=data
    output=[];ctx['wise_matches']={}
    for s in ctx['samples']:
        gid=s['reported_gaia_source_id'];counts={};central=[]
        for epoch in [2009.5,2010.5,2011.5]:
            a,d=propagate(ctx['gaia'][gid],epoch)
            candidates=[r for r in data if separation(a,d,*coords(r))<=3]
            counts[str(epoch)]=len(candidates)
            if epoch==2010.5:central=candidates
        if len(central)==1:ctx['wise_matches'][gid]=central[0]
        output.append({'gaia_id':gid,'counts_by_assumed_epoch':counts,
                       'unique_central_candidate':central[0]['designation'] if len(central)==1 else None,
                       'association_status':'provisional' if len(central)==1 else 'unmatched_or_ambiguous'})
    return output


def p06(ctx):
    rows=[];ctx['wise_quality']={}
    for gid,r in ctx['wise_matches'].items():
        q={str(b):wise_quality(r,b) for b in range(1,5)};ctx['wise_quality'][gid]=q
        rows.append({'gaia_id':gid,'designation':r['designation'],'bands':q})
    return rows


def p07(ctx):
    return [{'gaia_id':gid,'measurement':color(r['w1mpro'],r['w1sigmpro'],r['w2mpro'],r['w2sigmpro'])}
            for gid,r in ctx['wise_matches'].items()
            if all(ctx['wise_quality'][gid][b]['pass'] for b in ['1','2'])]


def p08(ctx):
    data=request_catalog(ctx,'fp_psc',2000);ctx['tmass_matches']={};output=[]
    for s in ctx['samples']:
        gid=s['reported_gaia_source_id'];candidates=[];missing=[]
        for r in data:
            if not finite(r.get('jdate')):
                missing.append(r.get('designation'));continue
            epoch=float(Time(r['jdate'],format='jd',scale='utc').tcb.jyear)
            a,d=propagate(ctx['gaia'][gid],epoch);sep=separation(a,d,*coords(r))
            if sep<=3:candidates.append({'row':r,'separation_arcsec':sep,'epoch_tcb_jyear':epoch})
        if len(candidates)==1:ctx['tmass_matches'][gid]=candidates[0]['row']
        output.append({'gaia_id':gid,'candidates':[{'designation':r['row']['designation'],'separation_arcsec':r['separation_arcsec'],'epoch_tcb_jyear':r['epoch_tcb_jyear']} for r in candidates],
                       'missing_epoch_records':missing,'native_jdate_timescale_assumption':'UTC; conditional positional check'})
    return output


def p09(ctx):
    rows=[];ctx['tmass_quality']={}
    for gid,r in ctx['tmass_matches'].items():
        clean=(r.get('ph_qual')=='AAA' and r.get('cc_flg')=='000' and
               all(finite(r.get(k)) and r[k]>0 for k in ['j_msigcom','h_msigcom','k_msigcom']))
        ctx['tmass_quality'][gid]=clean
        rows.append({'gaia_id':gid,'clean_jhk':clean,'native_ph_qual':r.get('ph_qual'),'native_cc_flg':r.get('cc_flg'),
                     'j_h':color(r.get('j_m'),r.get('j_msigcom'),r.get('h_m'),r.get('h_msigcom')) if clean else None,
                     'h_k':color(r.get('h_m'),r.get('h_msigcom'),r.get('k_m'),r.get('k_msigcom')) if clean else None})
    return rows


def p10(ctx):
    if any(k not in ctx for k in ['astrometry','tmass_quality','wise_quality']):
        raise ValueError('Upstream survey/quality step unavailable; no readiness verdict')
    rows=[]
    for s in ctx['samples']:
        gid=s['reported_gaia_source_id']
        technical=ctx['astrometry'].get(gid,False) and ctx['tmass_quality'].get(gid,False) and all(ctx['wise_quality'].get(gid,{}).get(b,{}).get('pass',False) for b in ['1','2'])
        rows.append({'gaia_id':gid,'five_band_technical_pass':technical,'scientific_excess_search_authorized':False,
                     'remaining_gates':['physical association and imaging review','WD atmosphere and predictive calibration','matched controls and false-alarm calibration']})
    return rows


def run(design, cohort, cp_raw, database, out, replay_raw=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    if hashlib.sha256(json.dumps(cohort,sort_keys=True).encode()).hexdigest()!=design['cohort_design_sha256']:
        raise ValueError('Frozen cohort mismatch')
    if digest(database)!=cohort['staging_database_sha256']:
        raise ValueError('Staging database mismatch')
    cp=replay(cohort,cp_raw)
    _,neighbors=parse_votable((Path(cp_raw)/'neighbors.vot').read_bytes())
    ctx={'design':design,'samples':cohort['sample'],'cp':cp,'neighbors':neighbors,
         'gaia':{r['reported_gaia_source_id']:r['gaia_reported_id_measurements'] for r in cp['results']},
         'out':out,'db':database,'replay_raw':replay_raw}
    journal={'run_id':design['run_id'],'started_at':stamp(),'design_sha256':hashlib.sha256(json.dumps(design,sort_keys=True).encode()).hexdigest(),
             'method_sha256':digest(__file__),'experiments':[],'scientific_limits':design['scientific_limits']}
    for specification,method in zip(design['experiments'],[p01,p02,p03,p04,p05,p06,p07,p08,p09,p10],strict=True):
        record=dict(specification,started_at=stamp())
        print('START',record['id'],record['name'],flush=True)
        try:
            record['results']=method(ctx);record['status']='EXECUTED'
            if specification['id']=='P04' and not any(r['comparisons'] for r in record['results']):
                record['status']='NOT_TESTABLE_NO_REPEAT_PAIRS'
            if specification['id'] in ['P07','P09'] and not record['results']:
                record['status']='NOT_TESTABLE_NO_ELIGIBLE_DATA'
        except Exception as e:
            record.update(status='BLOCKED',failure=f'{type(e).__name__}: {e}')
        record['finished_at']=stamp()
        (out/(record['id']+'.json')).write_text(json.dumps(record,indent=2,allow_nan=False)+'\n')
        journal['experiments'].append(record)
        (out/'journal.json').write_text(json.dumps(journal,indent=2,allow_nan=False)+'\n')
        print('FINISH',record['id'],record['status'],len(record.get('results',[])),flush=True)
    journal['finished_at']=stamp()
    (out/'journal.json').write_text(json.dumps(journal,indent=2,allow_nan=False)+'\n')
    return journal


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['design','cohort','cp_raw','database','output']:p.add_argument(name)
    p.add_argument('--replay-raw')
    a=p.parse_args()
    run(json.loads(Path(a.design).read_text()),json.loads(Path(a.cohort).read_text()),a.cp_raw,a.database,a.output,a.replay_raw)
