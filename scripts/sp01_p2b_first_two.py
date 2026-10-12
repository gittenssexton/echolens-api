"""Bounded, read-only GALAH DR4 spectrum-access audit of exactly two frozen CALIBRATION stars.

Inputs are a two-line cut from the archived 50-source *detrended* VizieR
feasibility manifest, not the primary GALAH DR4 allstar validation. Never
read/score the held-out star list. DO NOT use outputs for discovery inference.

Save original FITS bytes only when basic FITS structure passes validation; record
HTTP failure and non-FITS bytes' digest and a short diagnostic excerpt otherwise.
No retries. No secrets. Max eight specific small public data requests.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import urllib.error
import urllib.request

ARCHIVED_MANIFEST_SHA256 = 'ef62ec0bd5afd79a8c39613f2796943937dd09d9eb6e6bfabe644522e2beed32'
EXPECTED = [('39909218369012608','151111003101245'),('4616578742686592','221003001101138')]
ENDPOINT = 'https://cloud.datacentral.org.au/teamdata/GALAH/public/GALAH_DR4'
MAX_BYTES = 2_000_000
ARMS = {'B':(4600,5000),'G':(5550,6000),'R':(6300,6800),'I':(7450,8100)}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def targets(csvpath: Path) -> list[dict]:
    with csvpath.open(newline='',encoding='utf-8') as stream:
        rows=list(csv.DictReader(stream))
    if len(rows)!=2: raise ValueError('Exactly two calibration rows required')
    for row,(gaia,visit) in zip(rows, EXPECTED):
        if row['role']!='calibration' or row['gaia_dr3_source_id']!=gaia or row['representative_sobject_id']!=visit:
            raise ValueError('Input source/sobject_id differs from frozen first two calibration entries')
        if not (re.fullmatch('[0-9]{14,19}',gaia) and re.fullmatch('[0-9]{15}',visit)):
            raise ValueError('Source or visit ID not exact decimal text')
    return rows


def paths(sobject_id: str) -> list[tuple[str,str,str|None]]:
    date=sobject_id[:6]
    root=f'{ENDPOINT}'
    return [
      ('official_allspec',f'{root}/analysis_products_single/{date}/{sobject_id}/{sobject_id}_single_fit_spectrum.fits',None),
      ('native_CCD1_B',f'{root}/observations/{date}/spectra/com/{sobject_id}1.fits','B'),
      ('ssa_B',f'https://datacentral.org.au/vo/slink/links?ID={sobject_id}&DR=galah_dr4&IDX=0&FILT=B&RESPONSEFORMAT=fits','B'),
      ('ssa_G',f'https://datacentral.org.au/vo/slink/links?ID={sobject_id}&DR=galah_dr4&IDX=0&FILT=G&RESPONSEFORMAT=fits','G')]


def header(raw: bytes, pos: int) -> tuple[dict,int]:
    values={}
    start=pos
    while pos+80<=len(raw) and pos-start<2880*24:
        card=raw[pos:pos+80].decode('ascii','strict')
        pos+=80
        key=card[:8].strip()
        if key=='END': return values,((pos+2879)//2880)*2880
        if card[8:10]=='= ':
            val=card[10:80].split(' / ',1)[0].strip()
            values[key]=val.split("'",2)[1] if val.startswith("'") else val
    raise ValueError('No FITS END card in bounded header')


def fits_summary(raw: bytes,kind: str,expected_arm: str|None,visit: str)->dict:
    if not raw.startswith(b'SIMPLE  ='):raise ValueError('Response does not begin with FITS SIMPLE')
    h,offset=header(raw,0)
    if h.get('SIMPLE')!='T':raise ValueError('Invalid FITS primary SIMPLE')
    count=int(h.get('NAXIS','0'))
    if count<0 or count>5:raise ValueError('Invalid NAXIS')
    if h.get('BITPIX') not in ('-64','-32','8','16','32','64'):raise ValueError('Unsupported BITPIX')
    hdus=[]
    pos=0
    for ix in range(12):
        if pos>=len(raw):break
        if not raw[pos:].strip(b' \x00'): break
        hd,after=header(raw,pos)
        naxis=int(hd.get('NAXIS','0'))
        if naxis>5 or naxis<0:raise ValueError('Invalid axis count')
        if hd.get('XTENSION')=='BINTABLE':
            byte_count=int(hd['NAXIS1'])*int(hd['NAXIS2'])+int(hd.get('PCOUNT','0'))
        else:
            dims=math.prod(int(hd[f'NAXIS{i}']) for i in range(1,naxis+1)) if naxis else 0
            byte_count=dims*(abs(int(hd['BITPIX']))//8)
        if byte_count<0 or len(raw)<after+byte_count:raise ValueError('FITS truncated image/table')
        info={'hdu':ix,'type':hd.get('XTENSION','PRIMARY'),'naxis':naxis,'shape':[int(hd[f'NAXIS{i}']) for i in range(1,naxis+1)],'bytes':byte_count}
        if ix==0:
            info['relevant_header']={k:hd.get(k) for k in ('GALAH_ID','GAIA_ID','SOBJECT','BAND','SPECTID','CRVAL1','CDELT1','CRPIX1','WMIN','WMAX','NCOMBINE','EXPOSED') if k in hd}
            reported=hd.get('GALAH_ID') or hd.get('SOBJECT')
            if reported is not None and reported!=visit:raise ValueError(f'Visit header mismatch {reported} != {visit}')
            if kind=='native_CCD1_B':
                spec=hd.get('SPECTID','').upper()
                if spec and spec not in ('BL','B'):raise ValueError('Incorrect native CCD1 camera SPECTID')
            if kind.startswith('ssa_'):
                band=hd.get('BAND','').upper()
                if band!=expected_arm:raise ValueError(f'SSA {expected_arm} is mislabeled BAND={band}')
            if expected_arm and 'CRVAL1' in hd and 'CDELT1' in hd and naxis==1:
                n=int(hd['NAXIS1'])
                lo=float(hd['CRVAL1'])+(1-float(hd.get('CRPIX1','1')))*float(hd['CDELT1'])
                hi=float(hd['CRVAL1'])+(n-float(hd.get('CRPIX1','1')))*float(hd['CDELT1'])
                armrange=ARMS[expected_arm]
                midpoint=(lo+hi)/2
                if not(armrange[0]<=midpoint<=armrange[1]):
                    raise ValueError(f'Spectrum wavelength midpoint {midpoint:.2f} Å contradicts requested {expected_arm}')
                info['wavelength_min_A']=min(lo,hi)
                info['wavelength_max_A']=max(lo,hi)
        hdus.append(info)
        pos=after+((byte_count+2879)//2880)*2880
    if not hdus:raise ValueError('Empty FITS')
    if kind=='official_allspec' and not any(x['type']=='BINTABLE' for x in hdus):
        raise ValueError('Expected the GALAH allspec spectrum BINTABLE; got no table')
    if kind=='native_CCD1_B' and len(hdus)!=8:
        raise ValueError('Expected eight reduced-camera FITS HDUs')
    if kind.startswith('ssa_') and len(hdus)!=1:
        raise ValueError('Expected transformed one-HDU SSA FITS')
    return {'hdu_count':len(hdus),'hdus':hdus,'format_accepted':True,
            'status':'basic FITS structure and requested camera validated, not full scientific provenance',
            'native_detector_quality_verified':False}


def fetch(url:str)->tuple[int,bytes,str]:
    req=urllib.request.Request(url,headers={'User-Agent':'EchoLens-SP01-P2B/1.0 public astronomy read-only research','Accept':'application/fits,application/octet-stream,*/*'})
    try:
        with urllib.request.urlopen(req,timeout=18) as resp:
            code=resp.status; data=resp.read(MAX_BYTES+1)
            ctype=resp.headers.get('Content-Type','')
    except urllib.error.HTTPError as exc:
        code=exc.code;data=exc.read(min(MAX_BYTES,8192));ctype=exc.headers.get('Content-Type','')
    if len(data)>MAX_BYTES:raise ValueError('Provider response exceeds strict 2 MB per-file cap')
    return code,data,ctype


def run(inputfile:Path,out:Path)->dict:
    out.mkdir(parents=True,exist_ok=True)
    items=targets(inputfile)
    report={'schema':'echolens-sp01-p2b-first-two-v1','utc':datetime.now(timezone.utc).isoformat(),
      'source_manifest_SHA256':ARCHIVED_MANIFEST_SHA256,'two_row_manifest_SHA256':sha(inputfile.read_bytes()),
      'catalogue_label':'PROVISIONAL Kos+2025 DETRENDED GALAH DR4; NOT independently original-DR4 verified',
      'stars':[{'gaia_dr3_id':r['gaia_dr3_source_id'],'sobject_id':r['representative_sobject_id'],
                'role':'calibration_only','stratum':r['stratum'],'teff_from_detrended_catalog':r['teff'],
                'catalogue_flags':{'flag_sp':r['flag_sp'],'flag_red':r['flag_red']}} for r in items],
      'downloads':[],'untouched_holdout_sources_read':0,'scientific_detection_performed':False,
      'star_level_null_model_available':False}
    for row in items:
        sid=row['representative_sobject_id']
        for kind,url,arm in paths(sid):
            rec={'sobject_id':sid,'kind':kind,'url':url,'expected_arm':arm}
            try:
                status,data,ctype=fetch(url)
                rec.update(http_status=status,content_type=ctype,bytes=len(data),sha256=sha(data))
                if status!=200:raise ValueError(f'HTTP {status}: {data[:140].decode("utf8","replace")}')
                detail=fits_summary(data,kind,arm,sid)
                rec.update(status='accepted_engineering_format',fits=detail)
                filename=f'{sid}_{kind}.fits'
                (out/filename).write_bytes(data)
                rec['saved_file']=filename
            except Exception as exc:
                rec.update(status='unavailable_or_rejected',error_type=type(exc).__name__,error=str(exc)[:400])
            report['downloads'].append(rec)
            (out/'acquisition_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    report['accepted_count']=sum(r['status']=='accepted_engineering_format' for r in report['downloads'])
    report['total_attempted']=len(report['downloads'])
    report['scientific_ready']=False
    (out/'acquisition_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,default=Path('data/sp01_p2b_first_two_calibration.csv'))
    ap.add_argument('--out',type=Path,default=Path('reports/sp01_p2b_first_two'))
    args=ap.parse_args()
    r=run(args.input,args.out)
    print(json.dumps({'attempted':r['total_attempted'],'accepted_engineering_format':r['accepted_count'],
       'errors':[{'star':v['sobject_id'],'kind':v['kind'],'error':v.get('error')} for v in r['downloads'] if v['status']!='accepted_engineering_format']},indent=2))

if __name__=='__main__':main()
