"""Gaia follow-up for one development source; no photosphere/excess fitting.

Preserves complete ESA VOTables, metadata, nulls and native XP products.
Run --fetch once, then --replay offline. Existing responses are never refreshed.
"""
import argparse,gzip,hashlib,json,math,urllib.parse,urllib.request,warnings
from pathlib import Path
from datetime import datetime,timezone
from io import BytesIO
import xml.etree.ElementTree as ET
import numpy as np
from astropy.io.votable import parse
from astropy.units import UnitsWarning
from astropy.coordinates import SkyCoord
from astropy.time import Time
from scripts.infrared_feasibility import propagate

SID='4461930649238469760'
OUT=Path('reports/gaia_readiness_v04')
INPUT=Path('reports/infrared_feasibility')
ENDPOINT='https://gea.esac.esa.int/tap-server/tap/sync'
sha=lambda b:hashlib.sha256(b).hexdigest()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def scalar(value):
    if isinstance(value,np.ndarray) and value.ndim>0:return [scalar(v) for v in value]
    if np.ma.is_masked(value):return None
    if isinstance(value,np.ndarray):value=value.item()
    if isinstance(value,np.generic):value=value.item()
    if isinstance(value,float) and not math.isfinite(value):return None
    if isinstance(value,bytes):return value.decode()
    return value
def decode(raw,tap=False):
    root=ET.fromstring(raw)
    statuses=[x.attrib.get('value') for x in root.iter() if x.tag.split('}')[-1]=='INFO' and x.attrib.get('name')=='QUERY_STATUS']
    if (tap and not statuses) or any(v!='OK' for v in statuses):raise ValueError('Missing, failed or overflow TAP query status')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',UnitsWarning);v=parse(BytesIO(raw))
    output=[]
    for tab in v.iter_tables():
        t=tab.to_table(use_names_over_ids=True)
        rows=[]
        for r in t:
            row={k:scalar(r[k]) for k in t.colnames}
            for k in ['source_id','solution_id']:
                if row.get(k) is not None:row[k]=str(row[k])
            rows.append(row)
        params={p.name:scalar(p.value) for p in tab.params}
        for k in ['source_id','solution_id']:
            if params.get(k) is not None:params[k]=str(params[k])
        output.append({'fields':[{'name':f.name,'datatype':f.datatype,'arraysize':f.arraysize,'unit':str(f.unit) if f.unit else None,'ucd':f.ucd,'description':f.description} for f in tab.fields],'params':params,'rows':rows})
    return output
def one_source(product):
    rows=product[0]['rows']
    if len(rows)!=1 or rows[0].get('source_id')!=SID:raise ValueError('Expected one exact Gaia source ID')
    return rows[0]
def spectrum_id(product):
    ids={str(t['params']['source_id']) for t in product if t['params'].get('source_id') is not None}
    ids.update(str(r['source_id']) for t in product for r in t['rows'] if r.get('source_id') is not None)
    if ids!={SID}:raise ValueError('Spectral source ID missing or mismatched')
def saved(name):
    m=json.loads((OUT/'raw'/f'{name}.manifest.json').read_text());b=gzip.decompress((OUT/m['file']).read_bytes())
    if sha(b)!=m['raw_sha256']:raise ValueError('Response checksum mismatch')
    return b,m
def request(name,url,tap=False):
    if (OUT/'raw'/f'{name}.manifest.json').exists():return saved(name)[0]
    req=urllib.request.Request(url,headers={'User-Agent':'EchoLens/gaia-model-readiness-v04'})
    with urllib.request.urlopen(req,timeout=55) as r:b=r.read(5000001);final=r.url;ctype=r.headers.get('Content-Type');status=r.status
    if len(b)>5000000:raise ValueError('Response exceeds limit')
    product=decode(b,tap)
    path=OUT/'raw'/f'{name}.xml.gz';path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(gzip.compress(b,mtime=0))
    write(OUT/'raw'/f'{name}.manifest.json',{'request_url':url,'response_url':final,'retrieved_utc':datetime.now(timezone.utc).isoformat(),'raw_sha256':sha(b),'content_type':ctype,'http_status':status,'file':str(path.relative_to(OUT)),'rows_per_table':[len(t['rows']) for t in product],'field_counts':[len(t['fields']) for t in product]})
    return b
def tap(name,query):return request(name,ENDPOINT+'?'+urllib.parse.urlencode({'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'votable','MAXREC':10001,'QUERY':query}),True)
def fetch():
    g=one_source(decode(tap('gaia_source',f'SELECT * FROM gaiadr3.gaia_source WHERE source_id = {SID}'),True))
    tap('astrophysical_parameters',f'SELECT * FROM gaiadr3.astrophysical_parameters WHERE source_id = {SID}')
    # A finite epoch-2016 discovery cone, not a completeness guarantee at prior epochs.
    columns='source_id,ra,dec,ref_epoch,pmra,pmdec,parallax,phot_g_mean_mag,phot_bp_mean_mag,phot_rp_mean_mag,ruwe,phot_variable_flag'
    tap('neighbors',f"SELECT {columns} FROM gaiadr3.gaia_source WHERE 1=CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{g['ra']:.12f},{g['dec']:.12f},{60/3600:.12f})) ORDER BY source_id")
    for name,flag in [('xp_sampled','has_xp_sampled'),('xp_continuous','has_xp_continuous')]:
        if g.get(flag):
            url='https://gea.esac.esa.int/data-server/data?'+urllib.parse.urlencode({'RETRIEVAL_TYPE':name.upper(),'RELEASE':'Gaia DR3','ID':SID})
            raw=request(name,url);spectrum_id(decode(raw))
    print('Gaia follow-up responses preserved',flush=True)
def replay():
    source=one_source(decode(saved('gaia_source')[0],True));ap=one_source(decode(saved('astrophysical_parameters')[0],True))
    neighbor_product=decode(saved('neighbors')[0],True);neighbors=neighbor_product[0]['rows']
    ids=[x['source_id'] for x in neighbors]
    if len(ids)!=len(set(ids)) or SID not in ids or len(ids)>=10000:raise ValueError('Invalid neighbor result')
    selected=next(x['gaia'] for x in json.loads((INPUT/'selection.json').read_text())['targets'] if x['gaia']['source_id']==SID)
    consistency={k:{'frozen':selected.get(k),'ESA':source.get(k),'difference':source[k]-selected[k]} for k in ['ra','dec','parallax','pmra','pmdec','phot_g_mean_mag']}
    year=Time(55400,format='mjd',scale='tt').jyear;target=SkyCoord(*propagate(source,year)[:2],unit='deg');near=[]
    for n in neighbors:
        if n['source_id']==SID:continue
        ra,dec,moved=propagate(n,year);sep=target.separation(SkyCoord(ra,dec,unit='deg')).arcsec
        dm=n['phot_g_mean_mag']-source['phot_g_mean_mag'] if n.get('phot_g_mean_mag') is not None else None
        near.append({'source_id':n['source_id'],'separation_at_wise_epoch_arcsec':float(sep),'proper_motion_applied':moved,'G_magnitude_difference':dm,'G_flux_ratio':10**(-.4*dm) if dm is not None else None})
    near.sort(key=lambda x:x['separation_at_wise_epoch_arcsec'])
    flags=ap.get('flags_gspspec');flag_names=['vbroadT','vbroadG','vbroadM','vradT','vradG','vradM','fluxNoise','extrapol','neg_flux','nanFlux','emission','nullFluxErr','KMgiantPar']
    if not flags or len(flags)<13 or not flags.isdigit():raise ValueError('Invalid GSP-Spec flag chain')
    spectra={}
    for name in ['xp_sampled','xp_continuous']:
        if (OUT/'raw'/f'{name}.manifest.json').exists():
            p=decode(saved(name)[0]);spectrum_id(p);write(OUT/f'{name}.json',p)
            spectra[name]={'tables':len(p),'row_counts':[len(t['rows']) for t in p],'field_counts':[len(t['fields']) for t in p]}
    write(OUT/'gaia_source.json',decode(saved('gaia_source')[0],True));write(OUT/'astrophysical_parameters.json',decode(saved('astrophysical_parameters')[0],True));write(OUT/'neighbors.json',neighbor_product)
    out={'run':'gaia-model-readiness-v04','source_id':SID,'input_selection_sha256':sha((INPUT/'selection.json').read_bytes()),'catalog_consistency':consistency,'spectral_availability':{k:source[k] for k in source if k.startswith('has_')},'spectra_downloaded':spectra,'GSP_Spec':{k:ap.get(k) for k in ap if 'gspspec' in k},'GSP_Spec_parameter_flags':dict(zip(flag_names,flags[:13])),'MSC_model':{k:ap.get(k) for k in ap if 'msc' in k},'neighbor_cone_radius_arcsec':60,'neighbor_count_excluding_target':len(near),'neighbors_at_wise_epoch':near,'scientific_status':'development input readiness; no photosphere fit, infrared residual, acceptance probability or discovery claim'}
    write(OUT/'summary.json',out);print(json.dumps(out,indent=2),flush=True)
def main():
    p=argparse.ArgumentParser(description=__doc__);a=p.add_mutually_exclusive_group(required=True);a.add_argument('--fetch',action='store_true');a.add_argument('--replay',action='store_true');args=p.parse_args();fetch() if args.fetch else replay()
if __name__=='__main__':main()
