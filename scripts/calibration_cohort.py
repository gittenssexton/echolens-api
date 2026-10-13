"""Frozen Gaia-only comparison selection and native infrared readiness; no excess scoring."""
import json,gzip,hashlib,urllib.request,urllib.parse,math,xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,timezone
from scripts import infrared_catalog as infrared
from scripts.native_catalog import parse_votable
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/calibration_cohort_v10';SALT='echolens-calibration-v10:'
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def parse_pool(payload):
    root=ET.fromstring(payload);fields=root.findall('.//{*}FIELD');names=[f.get('name') for f in fields]
    repeated={name for name in names if names.count(name)>1}
    if repeated-{'classprob_dsc_combmod_star'}:raise ValueError('Unexpected duplicate join fields')
    if repeated:
        if names.count('classprob_dsc_combmod_star')!=2:raise ValueError('Unexpected duplicated probability count')
        fields[names.index('classprob_dsc_combmod_star')].set('name','gaia_classprob_dsc_combmod_star')
        payload=ET.tostring(root)
    return parse_votable(payload)
def choose(rows,excluded,n=20):
    if len({str(r['source_id']) for r in rows})!=len(rows):raise ValueError('Duplicate Gaia pool IDs')
    valid=[r for r in rows if str(r['source_id']) not in excluded]
    return sorted(valid,key=lambda r:(sha((SALT+str(r['source_id'])).encode()),int(r['source_id'])))[:n]
def validate_pool_row(r):
    if not 1000000<=r['random_index']<=100000000 or abs(r['b'])<=20 or not 8<=r['phot_g_mean_mag']<=13 or r['ruwe']>=1.2 or r['non_single_star']!=0 or r['phot_variable_flag']=='VARIABLE' or r['astrometric_params_solved']!=31 or r['parallax_over_error']<=10 or r['classprob_dsc_combmod_star']<=.99:raise ValueError('Gaia quality/range query mismatch')
    if r['duplicated_source'] not in [False,0,'false']:raise ValueError('Duplicated Gaia source')
    for key,lower,upper in [('teff_gspspec',4900,5200),('logg_gspspec',2.5,3.5),('mh_gspspec',-.5,0)]:
        if not lower<=r[key+'_lower']<=r[key]<=r[key+'_upper']<=upper:raise ValueError('Gaia parameter box mismatch')
    if not r['flags_gspspec'].startswith('0000000000000'):raise ValueError('GSPspec quality mismatch')
def calibrated_context(g):
    # Published generic field-star corrections: all polynomials use raw logg.
    x=g['logg_gspspec'];m=g['mh_gspspec'];gc=x+.4496-.0036*x-.0224*x*x;mc=m+.274-.1373*x-.005*x*x+.0048*x*x*x
    glo=g['logg_gspspec_lower'];ghi=g['logg_gspspec_upper'];glo=glo+.4496-.0036*glo-.0224*glo*glo;ghi=ghi+.4496-.0036*ghi-.0224*ghi*ghi
    # Rectangular parameter-box envelope includes polynomial extrema; not a confidence interval.
    gravities=[g['logg_gspspec_lower'],g['logg_gspspec_upper']]
    for critical in [(0.01+math.sqrt(.01**2+4*.0144*.1373))/(2*.0144),(0.01-math.sqrt(.01**2+4*.0144*.1373))/(2*.0144)]:
        if g['logg_gspspec_lower']<=critical<=g['logg_gspspec_upper']:gravities.append(critical)
    metals=[z+.274-.1373*y-.005*y*y+.0048*y*y*y for z in [g['mh_gspspec_lower'],g['mh_gspspec_upper']] for y in gravities]
    return {'calibrated_logg_sensitivity':gc,'calibrated_mh_sensitivity':mc,'logg_transformed_endpoints':[glo,ghi],'mh_parameter_box_envelope':[min(metals),max(metals)],'calibrated_central_within_existing_model_box':2.5<=gc<=3.5 and -.5<=mc<=0,'calibrated_endpoint_envelope_within_existing_model_box':glo>=2.5 and ghi<=3.5 and min(metals)>=-.5 and max(metals)<=0,'status':'published correction sensitivity; raw values retained; not a new posterior or imposed calibration'}
def select():
    if (OUT/'selection.json').exists():raise ValueError('Selection already frozen')
    mp=json.loads((OUT/'gaia_pool.manifest.json').read_text());raw=gzip.decompress((OUT/'raw/gaia_pool.xml.gz').read_bytes())
    if sha(raw)!=mp['raw_sha256']:raise ValueError('Gaia pool hash mismatch')
    fields,rows=parse_pool(raw)
    if not rows or len(rows)>100:raise ValueError('Unexpected pool size')
    for r in rows:
        if int(r['gaia_source_id'])!=int(r['source_id']):raise ValueError('Gaia main/AP ID mismatch')
        r['gaia_source_id']=str(r['gaia_source_id'])
        validate_pool_row(r)
        if not r['flags_gspspec'].startswith('0000000000000') or r['random_index']<1000000:raise ValueError('Selection query mismatch')
    previous=json.loads((ROOT/'reports/infrared_feasibility/selection.json').read_text());excluded={r['gaia']['source_id'] for r in previous['targets']};selected=choose(rows,excluded)
    design=json.loads((OUT/'design.json').read_text());selection={'run':design['run'],'selection_inputs':'Gaia main/AP only; W3 and IR data never used for selection','created_utc':datetime.now(timezone.utc).isoformat(),'design_sha256':sha((OUT/'design.json').read_bytes()),'pool_raw_sha256':sha(raw),'salt':SALT,'pool_rows':len(rows),'excluded_exposed_ids':sorted(excluded,key=int),'overlap_with_exposed_v02_pool':len({r['source_id'] for r in rows}&excluded),'targets':[{'group':'comparison_candidate','gaia':r,'parameter_calibration_context':calibrated_context(r),'analysis_role':'calibration_development' if i<12 else 'validation_reserved'} for i,r in enumerate(selected)]}
    write(OUT/'gaia_pool.fields.json',fields);write(OUT/'gaia_pool.json',rows);write(OUT/'selection.json',selection);print('Frozen candidates:',len(selected),'from pool:',len(rows),flush=True)
def fetch_main():
    s=json.loads((OUT/'selection.json').read_text());ids=','.join(t['gaia']['source_id'] for t in s['targets']);q=f'SELECT * FROM gaiadr3.gaia_source WHERE source_id IN ({ids}) ORDER BY source_id';params={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'votable','QUERY':q,'MAXREC':str(len(s['targets'])+1)};url='https://gea.esac.esa.int/tap-server/tap/sync?'+urllib.parse.urlencode(params)
    with urllib.request.urlopen(url,timeout=100) as r:b=r.read()
    fields,rows=parse_votable(b)
    if {r['source_id'] for r in rows}!={t['gaia']['source_id'] for t in s['targets']}:raise ValueError('Full-main response identity mismatch')
    (OUT/'raw/gaia_selected_main.xml.gz').write_bytes(gzip.compress(b,mtime=0));write(OUT/'gaia_selected_main.manifest.json',{'query':q,'parameters':params,'url':url,'raw_sha256':sha(b),'retrieved_utc':datetime.now(timezone.utc).isoformat(),'rows':len(rows),'fields':len(fields)});write(OUT/'gaia_selected_main.json',rows);write(OUT/'gaia_selected_main.fields.json',fields)
def fetch_ir():
    infrared.OUT=OUT;infrared.fetch()
def replay():
    s=json.loads((OUT/'selection.json').read_text());infrared.OUT=OUT;result=[]
    if sha((OUT/'design.json').read_bytes())!=s['design_sha256']:raise ValueError('Frozen design hash mismatch')
    pool=gzip.decompress((OUT/'raw/gaia_pool.xml.gz').read_bytes())
    if sha(pool)!=s['pool_raw_sha256']:raise ValueError('Frozen Gaia pool hash mismatch')
    _,rows=parse_pool(pool)
    for r in rows:r['gaia_source_id']=str(r['gaia_source_id']);validate_pool_row(r)
    selected=choose(rows,set(s['excluded_exposed_ids']))
    if [r['source_id'] for r in selected]!=[t['gaia']['source_id'] for t in s['targets']]:raise ValueError('Selection ranking changed')
    for r,t in zip(selected,s['targets']):
        if r!=t['gaia'] or calibrated_context(r)!=t['parameter_calibration_context']:raise ValueError('Frozen Gaia/context row mismatch')
    main=gzip.decompress((OUT/'raw/gaia_selected_main.xml.gz').read_bytes());mm=json.loads((OUT/'gaia_selected_main.manifest.json').read_text())
    if sha(main)!=mm['raw_sha256']:raise ValueError('Full-main native checksum mismatch')
    fields,mainrows=parse_votable(main)
    if len(fields)!=mm['fields'] or {r['source_id'] for r in mainrows}!={t['gaia']['source_id'] for t in s['targets']}:raise ValueError('Full-main field/identity mismatch')
    for t in s['targets']:
        row={'source_id':t['gaia']['source_id'],'analysis_role':t['analysis_role'],'parameter_calibration_context':t['parameter_calibration_context'],'surveys':{}}
        for survey in infrared.TABLES:
            p=OUT/'raw'/survey/(row['source_id']+'.fits.gz');m=json.loads(p.with_suffix('.manifest.json').read_text());b=gzip.decompress(p.read_bytes())
            if sha(b)!=m['raw_sha256'] or sha((OUT/'selection.json').read_bytes())!=m['selection_sha256']:raise ValueError('Frozen IR response hash mismatch')
            m['metadata_file']=str((OUT/'metadata'/f'{survey}.xml.gz').resolve());fields,observations=infrared.parse_snapshot(b,m,OUT)
            if len(observations)!=m['row_count']:raise ValueError('IR row count mismatch')
            a=infrared.associate(t['gaia'],observations,survey)
            if a['chosen']:a['band_quality_failures']={band:infrared.quality(a['chosen']['measurement'],survey,band) for band in ('1234' if survey=='wise' else 'jhk')}
            row['surveys'][survey]=a
        result.append(row)
    for survey in infrared.TABLES:
        keys={}
        for r in result:
            a=r['surveys'][survey]
            if a['chosen']:
                v=a['chosen']['measurement'];key=str(v.get('cntr') or v.get('designation') or v.get('source_id'));keys.setdefault(key,[]).append(r['source_id'])
        for r in result:
            a=r['surveys'][survey];a['source_reused']=False
            if a['chosen']:
                v=a['chosen']['measurement'];key=str(v.get('cntr') or v.get('designation') or v.get('source_id'));a['source_reused']=len(keys[key])>1
    def ready(r,survey,bands):
        a=r['surveys'][survey];return bool(a.get('chosen') and not a['neighbor_within_6_arcsec'] and not a['source_reused'] and all(not a['band_quality_failures'][b] for b in bands))
    for r in result:r['JHK_ready']=ready(r,'tmass','jhk');r['W3_ready']=ready(r,'wise','3');r['joint_ready']=r['JHK_ready'] and r['W3_ready']
    summary={'run':s['run'],'candidates':len(result),'pool_rows':s['pool_rows'],'selection_sha256':sha((OUT/'selection.json').read_bytes()),'status':'readiness only; no model fits, residual-based rejection, ordinary-star certification, calibrated predictive distribution or excess scoring','counts':{'JHK_ready':sum(r['JHK_ready'] for r in result),'W3_ready':sum(r['W3_ready'] for r in result),'joint_ready':sum(r['joint_ready'] for r in result),'calibration_corrected_central_in_existing_model_box':sum(r['parameter_calibration_context']['calibrated_central_within_existing_model_box'] for r in result),'calibration_corrected_parameter_envelope_in_box':sum(r['parameter_calibration_context']['calibrated_endpoint_envelope_within_existing_model_box'] for r in result)},'surveys':{v:{k:sum(r['surveys'][v]['status']==k for r in result) for k in ['provisional','ambiguous','unmatched']} for v in infrared.TABLES}}
    write(OUT/'results.json',result);write(OUT/'summary.json',summary);print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('step',choices=['select','fetch_main','fetch_ir','replay']);args=p.parse_args();globals()[args.step]()
