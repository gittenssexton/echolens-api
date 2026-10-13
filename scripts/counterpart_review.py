"""Development review of the frozen five-source queue, preserving pilot outputs.

--fetch retrieves 90-arcsec W1/W3 and 2MASS J/Ks cutouts with provenance.
--review computes conditional covariance diagnostics, flags, and image panels.
No counterpart acceptance, photospheric prediction or excess score is produced.
"""
import argparse,gzip,hashlib,json,math,urllib.parse,urllib.request
from pathlib import Path
from io import BytesIO
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from astropy.io import fits
from astropy.io.votable import parse_single_table
from astropy.coordinates import SkyCoord
from astropy.time import Time
from astropy.wcs import WCS
import astropy.units as u
from scripts.infrared_feasibility import propagate

INPUT=Path('reports/infrared_feasibility')
OUT=Path('reports/counterpart_review_v03')
sha=lambda b:hashlib.sha256(b).hexdigest()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def inputs():
    queue=json.loads((INPUT/'review_queue.json').read_text())
    gaia={t['gaia']['source_id']:t['gaia'] for t in json.loads((INPUT/'selection.json').read_text())['targets']}
    results={t['source_id']:t for t in json.loads((INPUT/'results.json').read_text())}
    return queue,gaia,results
def retrieve(url,path,kind):
    manifest=path.with_suffix('.manifest.json')
    if manifest.exists():
        m=json.loads(manifest.read_text());raw=gzip.decompress(path.read_bytes())
        if sha(raw)!=m['raw_sha256']:raise ValueError('Saved response checksum mismatch')
        return raw
    req=urllib.request.Request(url,headers={'User-Agent':'EchoLens/counterpart-review-v03'})
    with urllib.request.urlopen(req,timeout=55) as r:
        raw=r.read(5000001);final=r.url;ctype=r.headers.get('Content-Type')
    if len(raw)>5000000:raise ValueError('Response exceeds cutout limit')
    # gzip=false requested; retain exact server response, including any compression.
    decoded=gzip.decompress(raw) if raw.startswith(b'\x1f\x8b') else raw
    if kind=='image':
        with fits.open(BytesIO(decoded)) as hdus:
            assert hdus[0].data.ndim==2 and np.isfinite(hdus[0].data).any()
            assert WCS(hdus[0].header).has_celestial
    else:parse_single_table(BytesIO(decoded))
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(gzip.compress(raw,mtime=0))
    write(manifest,{'requested_url':url,'response_url':final,'retrieved_utc':datetime.now(timezone.utc).isoformat(),'raw_sha256':sha(raw),'file':str(path.relative_to(OUT)),'content_type':ctype,'kind':kind})
    return raw
def image_bytes(path):
    b=gzip.decompress(path.read_bytes());return gzip.decompress(b) if b.startswith(b'\x1f\x8b') else b
def fetch_one(t,gaia,results):
    sid=t['gaia_source_id'];sv=results[sid]['surveys'];wise=sv['wise']['chosen']['measurement'];tmass=sv['tmass']['chosen']['measurement']
    c=wise['coadd_id'];base=f'https://irsa.ipac.caltech.edu/ibe/data/wise/allwise/p3am_cdd/{c[:2]}/{c[:4]}/{c}/{c}'
    for band in ['1','3']:
        url=base+f'-w{band}-int-3.fits?'+urllib.parse.urlencode({'center':f"{wise['ra']},{wise['dec']}",'size':'90arcsec','gzip':'false'})
        retrieve(url,OUT/'images'/sid/f'W{band}.fits.gz','image')
    url='https://irsa.ipac.caltech.edu/ibe/search/twomass/allsky/allsky?'+urllib.parse.urlencode({'POS':f"{tmass['ra']},{tmass['dec']}",'ct':'VOTABLE'})
    raw=retrieve(url,OUT/'image_metadata'/f'{sid}.xml.gz','metadata')
    table=parse_single_table(BytesIO(raw)).to_table(use_names_over_ids=True)
    for band in ['j','k']:
        rows=[r for r in table if str(r['filter'])==band and int(r['coadd_key'])==int(tmass['coadd_key'])]
        if len(rows)!=1:raise ValueError(f'{sid}: expected exact catalog coadd image for {band}; found {len(rows)}')
        row=rows[0];base=f"https://irsa.ipac.caltech.edu/ibe/data/twomass/allsky/allsky/{str(row['ordate']).zfill(6)}{row['hemisphere']}/s{int(row['scanno']):03d}/image/{row['fname']}"
        url=base+'?'+urllib.parse.urlencode({'center':f"{tmass['ra']},{tmass['dec']}",'size':'90arcsec','gzip':'false'})
        retrieve(url,OUT/'images'/sid/f'{band.upper()}.fits.gz','image')
    print('Preserved four cutouts',sid,flush=True)
def fetch():
    q,g,r=inputs()
    with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(lambda t:fetch_one(t,g,r),q))
def gaia_covariance(g,year):
    names=['ra','dec','pmra','pmdec'];errors=np.array([g[n+'_error'] for n in names],float)/1000
    if not np.isfinite(errors).all() or (errors<=0).any():raise ValueError('Missing/invalid Gaia errors')
    corr=np.eye(4)
    for i in range(4):
        for j in range(i+1,4):corr[i,j]=corr[j,i]=g[names[i]+'_'+names[j]+'_corr']
    c=corr*np.outer(errors,errors)
    if np.linalg.eigvalsh(c).min()<=0:raise ValueError('Invalid Gaia covariance')
    dt=year-g['ref_epoch'];a=np.array([[1,0,dt,0],[0,1,0,dt]])
    return a@c@a.T
def ellipse_covariance(major,minor,angle):
    if not(major>=minor>0):raise ValueError('Invalid uncertainty ellipse')
    th=np.deg2rad(angle);v=np.array([np.sin(th),np.cos(th)]);w=np.array([np.cos(th),-np.sin(th)])
    return major**2*np.outer(v,v)+minor**2*np.outer(w,w)
def wise_covariance(m,cosine=True):
    a,b,c=m['sigra_pm'],m['sigdec_pm'],m['sigradec_pm']
    matrix=np.array([[a*a,c*abs(c)],[c*abs(c),b*b]])
    if cosine:
        t=np.diag([np.cos(np.deg2rad(m['dec_pm'])),1]);matrix=t@matrix@t
    if np.linalg.eigvalsh(matrix).min()<=0:raise ValueError('Invalid WISE covariance')
    return matrix
def diagnostic(g,m,survey):
    year=Time(55400,format='mjd',scale='tt').jyear if survey=='wise' else Time(m['jdate'],format='jd',scale='utc').jyear
    ra,dec,_=propagate(g,year);reference=SkyCoord(ra,dec,unit='deg')
    pos=SkyCoord(m['ra_pm'] if survey=='wise' else m['ra'],m['dec_pm'] if survey=='wise' else m['dec'],unit='deg')
    east,north=reference.spherical_offsets_to(pos);offset=np.array([east.arcsec,north.arcsec]);cg=gaia_covariance(g,year)
    options={'RA_coordinate':wise_covariance(m,True),'RA_tangent_sensitivity':wise_covariance(m,False)} if survey=='wise' else {'ellipse':ellipse_covariance(m['err_maj'],m['err_min'],m['err_ang'])}
    out={'epoch_jyear':float(year),'offset_east_north_arcsec':offset.tolist(),'gaia_covariance_arcsec2':cg.tolist(),'conditional_diagnostics':{}}
    for name,cm in options.items():
        vals={}
        for floor in [0,.05,.1]:
            cov=cg+cm+np.eye(2)*floor**2;d2=float(offset@np.linalg.solve(cov,offset));vals[str(floor)]={'mahalanobis_radius':math.sqrt(d2),'chi2_2d_tail':math.exp(-d2/2)}
        out['conditional_diagnostics'][name]={'catalog_covariance_arcsec2':cm.tolist(),'unmodeled_floor_sensitivity_arcsec':vals}
    return out
def review():
    q,g,r=inputs();out=[]
    for t in q:
        sid=t['gaia_source_id'];star=g[sid];sv=r[sid]['surveys'];wm=sv['wise']['chosen']['measurement'];tm=sv['tmass']['chosen']['measurement']
        flags=[]
        if star['phot_variable_flag']=='VARIABLE':flags.append('Gaia_catalog_VARIABLE; noncontemporaneous_SED_requires_variability_model')
        if any(wm.get('w'+b+'sat',0)>0 for b in '12'):flags.append('WISE_W1_or_W2_saturation')
        if wm['cc_flags'][0]!='0':flags.append('WISE_W1_artifact_'+wm['cc_flags'][0])
        if star.get('azero_gspphot') is not None and star['azero_gspphot']>1:flags.append('Gaia_A0_estimate_above_1mag; extinction_model_required')
        if star.get('teff_gspphot') is None:flags.append('Gaia_GSP_Phot_temperature_unavailable')
        neighbors=[{'separation_arcsec':x['separation_arcsec'],'designation':x['measurement']['designation'],'j_mag':x['measurement'].get('j_m'),'k_mag':x['measurement'].get('k_m')} for x in sv['tmass']['candidates'] if x['measurement']['designation']!=tm['designation']]
        if tm.get('prox',99)<10:flags.append('2MASS_neighbor_within_10arcsec')
        out.append({'source_id':sid,'group':t['group'],'gaia_parameters':{k:star.get(k) for k in ['ra','dec','parallax','parallax_error','ruwe','phot_g_mean_mag','bp_rp','teff_gspphot','logg_gspphot','azero_gspphot','phot_variable_flag']},'wise':diagnostic(star,wm,'wise'),'tmass':diagnostic(star,tm,'tmass'),'review_flags':flags,'tmass_other_cone_sources':neighbors,'tmass_catalog_key_matches_wise':str(tm['cntr'])==str(wm['tmass_key']),'w3_snr':wm['w3snr'],'w3_magnitude_error':wm['w3sigmpro'],'w3_fractional_flux_error':wm['w3sigflux']/wm['w3flux'],'tmass_rd_flg':tm['rd_flg'],'status':'development_review; no counterpart_acceptance_or_excess_score'})
    for x in out:
        f=x['w3_fractional_flux_error']
        x['hypothetical_exact_20pct_excess_measurement_only_z_ceiling']=.2/(1.2*f)
        x['hypothetical_exact_20pct_excess_required_snr_for_z5']=30
    write(OUT/'review.json',{'run':'counterpart-review-v03','input_hashes':{f:sha((INPUT/f).read_bytes()) for f in ['selection.json','results.json','review_queue.json']},'assumptions':['Gaia four-parameter tangent-plane covariance propagated linearly; no parallax/perspective model','AllWISE RA-coordinate convention is evaluated with cosine; an alternative tangent convention is retained as unresolved sensitivity','0/50/100mas extra isotropic error floors are illustrative sensitivity assumptions, not measured systematics','chi-square tails are conditional positional residual checks, not counterpart probabilities or discovery significance','2MASS ellipse angle east of north; WISE signed co-sigma converted to covariance','20pct precision ceiling assumes an exact 20pct excess, fixed catalog fractional noise, independent held-out W3 measurement and perfectly known photosphere; it is not a measured residual or an injection recovery test','No immutable pilot output or selection is changed'],'sources':out})
    print(json.dumps(out,indent=2),flush=True)
def main():
    p=argparse.ArgumentParser(description=__doc__);a=p.add_mutually_exclusive_group(required=True);a.add_argument('--fetch',action='store_true');a.add_argument('--review',action='store_true');args=p.parse_args()
    fetch() if args.fetch else review()
if __name__=='__main__':main()
