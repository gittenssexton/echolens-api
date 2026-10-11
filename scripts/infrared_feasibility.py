"""Mixed Gaia/AllWISE/2MASS feasibility pilot; no excess scoring.

Run import_gaia offline first, then --select, then --fetch, then --replay.
Frozen native responses and manifests live under reports/infrared_feasibility.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import gzip, hashlib, json, math, sqlite3, urllib.parse, urllib.request
from pathlib import Path
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.time import Time
import astropy.units as u
from scripts.import_gaia import is_reference, parse_snapshot

OUT=Path('reports/infrared_feasibility')
ENDPOINT='https://irsa.ipac.caltech.edu/TAP/sync'
SALT='echolens-infrared-feasibility-v02:'
TABLES={'wise':'allwise_p3as_psd','tmass':'fp_psc'}
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,obj):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def propagate(g,jyear):
    if g.get('pmra') is None or g.get('pmdec') is None:return g['ra'],g['dec'],False
    # Direction-only great-circle propagation: no distance/radial velocity inferred.
    ra,dec=np.deg2rad([g['ra'],g['dec']]);dt=jyear-g['ref_epoch']
    v=np.array([math.cos(dec)*math.cos(ra),math.cos(dec)*math.sin(ra),math.sin(dec)])
    east=np.array([-math.sin(ra),math.cos(ra),0]);north=np.array([-math.sin(dec)*math.cos(ra),-math.sin(dec)*math.sin(ra),math.cos(dec)])
    motion=(g['pmra']*east+g['pmdec']*north)*dt*np.deg2rad(1/3600000)
    theta=np.linalg.norm(motion)
    if theta:v=math.cos(theta)*v+math.sin(theta)*motion/theta
    return math.degrees(math.atan2(v[1],v[0]))%360,math.degrees(math.asin(float(np.clip(v[2],-1,1)))),True
def separation(a,b):
    return float(SkyCoord(*a,unit='deg').separation(SkyCoord(*b,unit='deg')).arcsec)
def select():
    if (OUT/'selection.json').exists():raise ValueError('Selection already frozen; replay or use a separate run directory')
    with sqlite3.connect('data/registry.sqlite3') as d:rows=[json.loads(r[0]) for r in d.execute('SELECT raw_json FROM stars')]
    pools={'reference':[g for g in rows if is_reference(g)],'other':[g for g in rows if not is_reference(g) and g.get('phot_variable_flag')!='VARIABLE'],'variable':[g for g in rows if g.get('phot_variable_flag')=='VARIABLE']}
    targets=[]
    for group,n in [('reference',40),('other',40),('variable',20)]:
        for g in sorted(pools[group],key=lambda g:(sha((SALT+g['source_id']).encode()),int(g['source_id'])))[:n]:targets.append({'group':group,'gaia':g})
    manifest={'run':'infrared-feasibility-v02','salt':SALT,'selected_utc':datetime.now(timezone.utc).isoformat(),'gaia_source_hash':json.loads(Path('data/gaia_dr3.manifest.json').read_text())['raw_sha256'],'pool_counts':{k:len(v) for k,v in pools.items()},'targets':targets,'rules':{'radius_arcsec':15,'eligibility_arcsec':3,'maxrec':10001,'max_concurrency':3,'wise_epoch_mjd_tt':55400,'tmass_search_jyear':2000,'matching':'geometric-only provisional; no covariance acceptance or photospheric scoring','transport':'native FITS plus paired VOTable metadata; only empty transport rows removed'}}
    write(OUT/'selection.json',manifest);print('Frozen',len(targets),'targets',flush=True)
def request(query,fmt,path):
    params={'REQUEST':'doQuery','LANG':'ADQL','QUERY':query,'FORMAT':fmt,'MAXREC':'10001'}
    url=ENDPOINT+'?'+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={'User-Agent':'EchoLens/infrared-feasibility-v02'})
    with urllib.request.urlopen(req,timeout=55) as r:
        data=r.read(20000001)
        if len(data)>20000000:raise ValueError('Response too large')
        final=r.url;ctype=r.headers.get('Content-Type')
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(gzip.compress(data,mtime=0))
    return {'query':query,'request_parameters':params,'endpoint':ENDPOINT,'response_url':final,'retrieved_utc':datetime.now(timezone.utc).isoformat(),'content_type':ctype,'raw_sha256':sha(data),'file':str(path.relative_to(OUT))}
def acquire_one(target,survey):
    g=target['gaia'];sid=g['source_id'];path=OUT/'raw'/survey/(sid+'.fits.gz');mp=path.with_suffix('.manifest.json')
    if mp.exists():return
    year=Time(55400,format='mjd',scale='tt').jyear if survey=='wise' else 2000
    ra,dec,moved=propagate(g,year)
    query=f'SELECT * FROM {TABLES[survey]} WHERE CONTAINS(POINT(ra,dec),CIRCLE({ra:.12f},{dec:.12f},{15/3600:.12f}))=1'
    m=request(query,'fits',path);m.update({'survey':survey,'gaia_source_id':sid,'search_center_deg':[ra,dec],'proper_motion_applied':moved,'format':'FITS','metadata_file':str((OUT/'metadata'/f'{survey}.xml.gz').resolve()),'metadata_sha256':sha(gzip.decompress((OUT/'metadata'/f'{survey}.xml.gz').read_bytes()))})
    fields,rows=parse_snapshot(gzip.decompress(path.read_bytes()),m,OUT)
    if len(rows)>=10000:raise ValueError('Possible truncated result')
    m['row_count']=len(rows);m['selection_sha256']=sha((OUT/'selection.json').read_bytes());write(mp,m)
def fetch():
    s=json.loads((OUT/'selection.json').read_text())
    for survey,table in TABLES.items():
        path=OUT/'metadata'/f'{survey}.xml.gz'
        if not path.exists():write(path.with_suffix('.manifest.json'),request(f'SELECT TOP 1 * FROM {table}','votable',path))
    done=0;errors=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks={pool.submit(acquire_one,t,survey):(t['gaia']['source_id'],survey) for t in s['targets'] for survey in TABLES}
        for f in as_completed(tasks):
            sid,survey=tasks[f]
            try:f.result()
            except Exception as e:errors.append({'source_id':sid,'survey':survey,'error':str(e)});print('FAILED',survey,sid,str(e),flush=True)
            done+=1
            if done%20==0:print('Acquired',done,'of',len(tasks),'failures',len(errors),flush=True)
    write(OUT/'acquisition_errors.json',errors)
    if errors:raise RuntimeError(f'{len(errors)} requests failed; rerun --fetch to resume')
def quality(row,survey,band):
    if survey=='wise':
        ix=int(band)-1;k='w'+band
        failures=[]
        if (row.get('ph_qual') or '????')[ix] not in 'AB':failures.append('photometric_quality')
        if row.get(k+'snr') is None or row[k+'snr']<5:failures.append('snr')
        if row.get(k+'sigmpro') is None or row[k+'sigmpro']<=0:failures.append('magnitude_error')
        if row.get(k+'sigflux') is None or row[k+'sigflux']<=0:failures.append('flux_error')
        if (row.get('cc_flags') or '????')[ix]!='0':failures.append('artifact')
        if row.get('ext_flg')!=0:failures.append('extended')
        if row.get(k+'sat') is None or row[k+'sat']!=0:failures.append('saturation_unknown_or_present')
        return failures
    ix='jhk'.index(band)
    failures=[]
    if (row.get('ph_qual') or '???')[ix]!='A':failures.append('photometric_quality')
    if (row.get('cc_flg') or '???')[ix]!='0':failures.append('artifact')
    if row.get(band+'_msigcom') is None or row[band+'_msigcom']<=0:failures.append('magnitude_error')
    return failures
def associate(g,rows,survey):
    result=[]
    for row in rows:
        row=dict(row)
        # Catalog identifiers are text in derived JSON to survive browser parsing.
        if row.get('cntr') is not None:row['cntr']=str(row['cntr'])
        if survey=='wise' and row.get('ra_pm') is not None and row.get('dec_pm') is not None:
            year=Time(55400,format='mjd',scale='tt').jyear;coords=(row['ra_pm'],row['dec_pm']);epoch='motion-fit MJD 55400 TT'
        elif survey=='wise':
            mjd=row.get('w1mjdmean') or row.get('w2mjdmean') or 55400
            year=Time(mjd,format='mjd',scale='tt').jyear;coords=(row['ra'],row['dec']);epoch='approximate stationary epoch from W1/W2 mean MJD'
        else:
            jd=row.get('jdate');year=Time(jd,format='jd',scale='utc').jyear if jd else 2000
            coords=(row['ra'],row['dec']);epoch='2MASS jdate' if jd else 'approximate epoch 2000'
        ra,dec,moved=propagate(g,year);sep=separation((ra,dec),coords)
        result.append({'separation_arcsec':sep,'epoch_basis':epoch,'proper_motion_applied':moved,'measurement':row})
    eligible=[r for r in result if r['separation_arcsec']<=3]
    status='unmatched' if not eligible else 'provisional' if len(eligible)==1 else 'ambiguous'
    chosen=eligible[0] if len(eligible)==1 else None
    return {'status':status,'candidates':sorted(result,key=lambda r:r['separation_arcsec']),'eligible_count':len(eligible),'chosen':chosen,'neighbor_within_6_arcsec':sum(r['separation_arcsec']<=6 for r in result)>1}
def replay():
    s=json.loads((OUT/'selection.json').read_text());results=[]
    for t in s['targets']:
        out={'source_id':t['gaia']['source_id'],'group':t['group'],'surveys':{}}
        for survey in TABLES:
            path=OUT/'raw'/survey/(out['source_id']+'.fits.gz');m=json.loads(path.with_suffix('.manifest.json').read_text());raw=gzip.decompress(path.read_bytes())
            if sha(raw)!=m['raw_sha256'] or sha((OUT/'selection.json').read_bytes())!=m['selection_sha256']:raise ValueError('Checksum mismatch')
            # Relocate metadata path on replay; original manifest retains its initial path.
            m['metadata_file']=str((OUT/'metadata'/f'{survey}.xml.gz').resolve())
            fields,rows=parse_snapshot(raw,m,OUT)
            if len(rows)!=m['row_count']:raise ValueError('Row count mismatch')
            a=associate(t['gaia'],rows,survey)
            if a['chosen']:
                row=a['chosen']['measurement'];a['band_quality_failures']={b:quality(row,survey,b) for b in ('1234' if survey=='wise' else 'jhk')}
            out['surveys'][survey]=a
        results.append(out)
    # One infrared extraction reused for multiple Gaia targets is a review flag.
    for survey in TABLES:
        keys={}
        for r in results:
            a=r['surveys'][survey]
            if a['chosen']:
                row=a['chosen']['measurement'];key=str(row.get('cntr') or row.get('designation') or row.get('source_id'));keys.setdefault(key,[]).append(r['source_id'])
        for r in results:
            a=r['surveys'][survey];a['source_reused']=False
            if a['chosen']:
                row=a['chosen']['measurement'];key=str(row.get('cntr') or row.get('designation') or row.get('source_id'));a['source_reused']=len(keys[key])>1
    summary={'run':s['run'],'selection_sha256':sha((OUT/'selection.json').read_bytes()),'targets':len(results),'groups':{},'scientific_status':'feasibility only; geometric associations; no covariance-qualified identities, image review, photosphere predictions, excess scores or discovery claims'}
    for group in ('reference','other','variable'):
        subset=[r for r in results if r['group']==group];v={'targets':len(subset)}
        for survey in TABLES:
            v[survey]={status:sum(r['surveys'][survey]['status']==status for r in subset) for status in ('unmatched','provisional','ambiguous')}
            v[survey]['bands_pass_screen']={b:sum(r['surveys'][survey].get('chosen') is not None and not r['surveys'][survey].get('neighbor_within_6_arcsec') and not r['surveys'][survey]['source_reused'] and not r['surveys'][survey]['band_quality_failures'][b] for r in subset) for b in ('1234' if survey=='wise' else 'jhk')}
        v['joint_W3_JHK_screen']=sum(all(r['surveys'][sv].get('chosen') and not r['surveys'][sv]['neighbor_within_6_arcsec'] and not r['surveys'][sv]['source_reused'] and all(not r['surveys'][sv]['band_quality_failures'][b] for b in bands) for sv,bands in [('wise','3'),('tmass','jhk')]) for r in subset)
        summary['groups'][group]=v
    write(OUT/'results.json',results);write(OUT/'summary.json',summary);print(json.dumps(summary,indent=2),flush=True)
def main():
    p=argparse.ArgumentParser(description=__doc__);a=p.add_mutually_exclusive_group(required=True)
    for x in ('select','fetch','replay'):a.add_argument('--'+x,action='store_true')
    args=p.parse_args();globals()[next(x for x in ('select','fetch','replay') if getattr(args,x))]()
if __name__=='__main__':main()
