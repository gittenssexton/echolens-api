"""Development-only crowding and TESS source-availability checkpoint.

No validation residuals, transit search, counterpart certification or p-values.
"""
import argparse, datetime, hashlib, io, json, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from astropy.io.votable import parse_single_table
from astropy.coordinates import SkyCoord
from astropy.time import Time
from astropy import units as u
from astropy.io import fits

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/project_checkpoint_v13'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')

def inputs():
    d=json.loads((OUT/'design.json').read_text())
    for name,h in d['input_sha256'].items():
        if sha(ROOT/name)!=h:raise ValueError('Input changed: '+name)
    rows=json.loads((ROOT/'reports/calibration_cohort_v10/results.json').read_text())
    selected=[next(s for s in rows if s['source_id']==sid) for sid in d['development_source_ids']]
    if len(selected)!=9 or any(s['analysis_role']!='calibration_development' or not s['joint_ready'] for s in selected):
        raise ValueError('Unexpected or reserved source')
    return d,selected

def freeze():
    p=OUT/'design.json'
    if p.exists():raise FileExistsError('Design already frozen')
    old=json.loads((ROOT/'reports/calibration_development_v11/design.json').read_text())
    write(p,{'run':'project-checkpoint-v13','frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'development_source_ids':old['development_source_ids'],
             'input_sha256':{name:sha(ROOT/name) for name in ['reports/calibration_cohort_v10/results.json','reports/calibration_cohort_v10/gaia_selected_main.json']},
             'cone_radius_arcsec':60,'row_limit':200,'crowding_radii_arcsec':[6,8.25,15],
             'epoch':'Gaia neighbors relative to Gaia target at each target W3 mean MJD; missing motions unresolved',
             'TESS_scope':'TIC 4206066 exact target metadata and products inventory only; no lightcurve pixels or future-sector scoring',
             'status':'engineering diagnostics only; no empirical significance or ordinary-control certification'})

def retrieve(url,p,data=None):
    if p.exists():raise FileExistsError(p)
    request=urllib.request.Request(url,data=data,headers={'User-Agent':'EchoLens-project-checkpoint-v13'})
    with urllib.request.urlopen(request,timeout=60) as r:b=r.read();status=r.status;final=r.url
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    write(p.with_suffix('.manifest.json'),{'url':url,'response_url':final,'request_body':data.decode() if data else None,
        'status':status,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sha256':sha(p),'bytes':len(b)})
    return b

def acquire_gaia():
    d,rows=inputs()
    main=json.loads((ROOT/'reports/calibration_cohort_v10/gaia_selected_main.json').read_text())
    main={str(g['source_id']):g for g in main}
    fields='source_id,ra,dec,ref_epoch,ra_error,dec_error,pmra,pmdec,pmra_error,pmdec_error,parallax,parallax_error,phot_g_mean_mag,bp_rp,ruwe,duplicated_source,non_single_star'
    for s in rows:
        g=main[s['source_id']]
        query=f"SELECT TOP {d['row_limit']} {fields} FROM gaiadr3.gaia_source WHERE 1=CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{g['ra']},{g['dec']},{d['cone_radius_arcsec']/3600})) ORDER BY source_id"
        url='https://gea.esac.esa.int/tap-server/tap/sync?'+urllib.parse.urlencode({'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'votable','QUERY':query})
        retrieve(url,OUT/'raw/gaia'/f"{s['source_id']}.xml")
        print('Preserved cone',s['source_id'],flush=True)

def mast(payload,p):
    raw=retrieve('https://mast.stsci.edu/api/v0/invoke',p,urllib.parse.urlencode({'request':json.dumps(payload)}).encode())
    d=json.loads(raw)
    if d.get('status')!='COMPLETE':raise ValueError('MAST did not complete: '+str(d.get('msg')))
    if d.get('paging',{}).get('pagesFiltered',1)>1:raise ValueError('MAST pagination incomplete')
    return d

def acquire_tess():
    inputs()
    payload={'service':'Mast.Caom.Filtered','params':{'columns':'*','filters':[
        {'paramName':'target_name','values':['4206066']},{'paramName':'obs_collection','values':['TESS']},
        {'paramName':'dataproduct_type','values':['timeseries']}]},'format':'json','pagesize':1000,'page':1}
    d=mast(payload,OUT/'raw/tess/observations.json')
    print('TESS observations:',len(d.get('data',[])),flush=True)
    ids=[str(r['obsid']) for r in d.get('data',[]) if r.get('dataRights')=='PUBLIC']
    if ids:
        payload={'service':'Mast.Caom.Products','params':{'obsid':','.join(ids)},'format':'json','pagesize':10000,'page':1}
        p=mast(payload,OUT/'raw/tess/products.json')
        print('Products:',len(p.get('data',[])),flush=True)

def finite(v):return v is not np.ma.masked and v is not None and np.isfinite(v)
def coord(g,year=None):
    ra=float(g['ra']);dec=float(g['dec'])
    if year is not None:
        if not all(finite(g[k]) for k in ['pmra','pmdec','ref_epoch']):return None
        dt=year-float(g['ref_epoch']);cos=np.cos(np.deg2rad(dec))
        if abs(cos)<1e-8:return None
        ra=(ra+float(g['pmra'])*dt/(3600000*cos))%360;dec+=float(g['pmdec'])*dt/3600000
    return SkyCoord(ra*u.deg,dec*u.deg)

def verify(p):
    m=json.loads(p.with_suffix('.manifest.json').read_text())
    if sha(p)!=m['sha256']:raise ValueError('Response changed')

def replay():
    d,rows=inputs();main={str(g['source_id']):g for g in json.loads((ROOT/'reports/calibration_cohort_v10/gaia_selected_main.json').read_text())};results=[]
    for s in rows:
        sid=s['source_id'];p=OUT/'raw/gaia'/f'{sid}.xml';verify(p)
        states=[el.attrib.get('value') for el in ET.fromstring(p.read_bytes()).iter() if el.attrib.get('name')=='QUERY_STATUS']
        if not states or any(value!='OK' for value in states):raise ValueError('Non-OK Gaia query status')
        table=parse_single_table(p).to_table(use_names_over_ids=True)
        if len(table)>=d['row_limit']:raise ValueError('Cone reached truncation limit')
        if len(set(map(str,table['source_id'])))!=len(table):raise ValueError('Duplicate Gaia neighbor')
        if sum(str(r['source_id'])==sid for r in table)!=1:raise ValueError('Target missing from cone')
        target=main[sid];wm=s['surveys']['wise']['chosen']['measurement'];year=Time(wm['w3mjdmean'],format='mjd',scale='utc').jyear
        c=coord(target,year);neighbors=[]
        for r in table:
            if str(r['source_id'])==sid:continue
            c2=coord(r,year)
            neighbors.append({'source_id':str(r['source_id']),'at_Gaia_epoch_arcsec':float(coord(target).separation(coord(r)).arcsec),
                'at_W3_mean_epoch_arcsec':None if c2 is None else float(c.separation(c2).arcsec),
                'missing_motion_unresolved':c2 is None,'G_mag':float(r['phot_g_mean_mag']) if finite(r['phot_g_mean_mag']) else None})
        moving=[r for r in neighbors if r['at_W3_mean_epoch_arcsec'] is not None];moving.sort(key=lambda r:r['at_W3_mean_epoch_arcsec'])
        results.append({'source_id':sid,'gaia_cone_rows':len(table),'W3_mean_epoch_jyear':float(year),
           'nearest_complete_motion_neighbor':moving[0] if moving else None,
           'complete_motion_counts_within_radii':{str(radius):sum(r['at_W3_mean_epoch_arcsec']<=radius for r in moving) for radius in d['crowding_radii_arcsec']},
           'missing_motion_neighbors':sum(r['missing_motion_unresolved'] for r in neighbors),'neighbors':neighbors,
           'catalog_standard_W3_aperture_flag':wm['w3flg'],'status':'finite Gaia-cone geometric diagnostic; no IR flux/color or PSF deblending model'})
    write(OUT/'neighborhood_results.json',results)
    p=OUT/'raw/tess/observations.json';verify(p);obs=json.loads(p.read_text())
    pp=OUT/'raw/tess/products.json';products=[]
    if pp.exists():verify(pp);products=json.loads(pp.read_text()).get('data',[])
    public=[r for r in obs['data'] if r.get('dataRights')=='PUBLIC']
    ffi=OUT/'raw/tess/ffi_sectors.json';ffi_sectors=[]
    if ffi.exists():
        verify(ffi);ffi_sectors=sorted(int(r['sector']) for r in json.loads(ffi.read_text()).get('results',[]))
    write(OUT/'tess_inventory_summary.json',{'TIC':'4206066','observation_count':len(obs['data']),'public_observations':len(public),
        'observations':[{'obsid':str(r['obsid']),'obs_id':r['obs_id'],'target_name':r['target_name'],'provenance_name':r.get('provenance_name'),'sequence_number':r.get('sequence_number'),'dataRights':r.get('dataRights'),'t_min':r.get('t_min'),'t_max':r.get('t_max'),'t_exptime':r.get('t_exptime')} for r in obs['data']],
        'product_count':len(products),'lightcurve_products':[r for r in products if r.get('productSubGroupDescription')=='LC'],
        'target_pixel_products':[r for r in products if r.get('productSubGroupDescription')=='TP'],
        'FFI_available_sector_numbers':ffi_sectors,'inventory_stage_scores_time_series':False,
        'downloaded_native_FITS_products':len(list((OUT/'raw/tess').glob('*.fits'))),
        'status':'source availability; separate native product QA; no transit or future-sector analysis'})
    print('Replayed Gaia fields:',len(results),'TESS observations:',len(obs['data']))

def tess_QA():
    inputs();d=json.loads((OUT/'tess_QA_design.json').read_text());data={};headers={};masks={};units={}
    for product in d['products']:
        p=OUT/'raw/tess'/product['productFilename'];verify(p)
        if p.stat().st_size!=product['size']:raise ValueError('Product byte count differs')
        with fits.open(p) as h:
            h.verify('exception')
            if h[0].header.get('TICID')!=int(d['TIC']) or h[0].header.get('SECTOR')!=d['sector']:raise ValueError('Wrong TIC or sector')
            band=product['productSubGroupDescription'];data[band]=h[1].data.copy();headers[band]=h[1].header.copy();masks[band]=h[2].data.copy()
            units[band]={c.name:c.unit for c in h[1].columns}
    lc,tp=data['LC'],data['TP']
    if len(lc)!=len(tp) or not np.array_equal(lc['CADENCENO'],tp['CADENCENO']):raise ValueError('Cadence mismatch')
    if not np.allclose(lc['TIME'],tp['TIME'],rtol=0,atol=1e-12,equal_nan=True):raise ValueError('Time mismatch')
    if not np.array_equal(masks['LC'],masks['TP']):raise ValueError('Aperture masks differ')
    if any(h.get('TIMESYS')!='TDB' or h.get('BJDREFI')!=2457000 for h in headers.values()):raise ValueError('Unexpected clock convention')
    valid=(lc['QUALITY']==0)&np.isfinite(lc['TIME'])&np.isfinite(lc['PDCSAP_FLUX'])&np.isfinite(lc['PDCSAP_FLUX_ERR'])&(lc['PDCSAP_FLUX_ERR']>0)
    t=np.asarray(lc['TIME'][valid],float);flux=np.asarray(lc['PDCSAP_FLUX'][valid],float);err=np.asarray(lc['PDCSAP_FLUX_ERR'][valid],float)
    values,counts=np.unique(lc['QUALITY'],return_counts=True)
    result={'TIC':d['TIC'],'sector':d['sector'],'rows':len(lc),'cadence_identity_equal':True,'time_arrays_equal_to_1e_minus12_day':True,
       'aperture_masks_identical':True,'clock':'BJD_TDB = TIME + 2457000 + BJDREFF; native reference retained',
       'native_header_time_metadata':{k:{key:headers[k].get(key) for key in ['TIMESYS','TIMEREF','TIMEUNIT','BJDREFI','BJDREFF']} for k in headers},
       'quality_counts':{str(int(k)):int(v) for k,v in zip(values,counts)},'quality_zero_and_finite_flux_error_rows':int(valid.sum()),
       'all_finite_times':int(np.isfinite(lc['TIME']).sum()),'valid_span_days':float(t[-1]-t[0]),'median_valid_spacing_seconds':float(np.median(np.diff(t))*86400),
       'native_TPF_flux_shape':list(tp['FLUX'].shape),'aperture_mask_values':np.unique(masks['LC']).tolist(),'native_column_units':units,
       'formal_median_PDCSAP_fractional_error':float(np.median(err)/np.median(flux)),
       'transit_searches':0,'new_detection_significance':None,'status':'file/time/mask engineering QA; no event selection, detrending, transit recovery or blend veto'}
    write(OUT/'tess_native_QA.json',result)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(1,2,figsize=(11,4))
    ax[0].plot(t,flux/np.median(flux),'.',markersize=.6)
    ax[0].set(xlabel='TIME (BJD_TDB − 2457000)',ylabel='PDCSAP / median',title='Sector 32; QUALITY=0, finite flux/error; no detrending')
    good=(tp['QUALITY']==0)&np.isfinite(tp['TIME'])
    mean=np.nanmedian(tp['FLUX'][good],axis=0)
    ax[1].imshow(mean,origin='lower',cmap='viridis');ax[1].contour((masks['TP']&2)>0,levels=[.5],colors='white')
    ax[1].set(xlabel='Stamp column',ylabel='Stamp row',title='Median TPF flux; white extraction aperture')
    fig.suptitle('Native observational QA only; no planet or technosignature test',fontsize=11)
    fig.tight_layout();fig.savefig(OUT/'tess_native_QA.png',dpi=140);plt.close(fig)
    print(json.dumps({k:v for k,v in result.items() if k!='native_column_units'},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['freeze','acquire_gaia','acquire_tess','replay','tess_QA']);globals()[parser.parse_args().action]()
