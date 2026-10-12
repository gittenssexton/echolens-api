"""Bounded read-only proof of GALAH DR4 original-FITS delivery via Data Central Datalink.

Only two previously exposed CALIBRATION visits. Crucial change: no IDX parameter.
Never use these spectra as clean control until full identity and camera validation.
No holdout sources queried. Native error documents are not spectra.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import struct
import urllib.error
import urllib.parse
import urllib.request

TARGETS = [('39909218369012608','151111003101245'), ('4616578742686592','221003001101138')]
CAMERAS = {'B': (4600,5000), 'G':(5500,6100), 'R':(6300,6900), 'I':(7400,8200)}
BASE = 'https://datacentral.org.au/vo/slink/links'
OUT = Path(os.environ.get('P2B_ORIGINAL_DATALINK_OUTPUT','reports/sp01_p2b_original_datalink'))
LIMIT = 2_200_000


def fits_header(blob, start):
    values={}
    pos=start
    while pos+80<=len(blob) and pos-start<2880*24:
        card=blob[pos:pos+80].decode('ascii', 'strict');pos+=80
        key=card[:8].strip()
        if key=='END':return values,((pos+2879)//2880)*2880
        if card[8:10]=='= ':
            raw=card[10:80].split(' / ',1)[0].strip()
            values[key]=(raw.split("'",2)[1].strip() if raw.startswith("'") else raw)
    raise ValueError('FITS header END not found')


def verify_eight_hdu(blob,visit,band):
    if not blob.startswith(b'SIMPLE  ='):raise ValueError('not a FITS spectrum')
    if len(blob)%2880:raise ValueError('FITS length not multiple of 2880')
    pos=0;hdus=[];profile=None;starts=[]
    for i in range(8):
        if pos>=len(blob):raise ValueError(f'missing HDU {i}')
        h,body=fits_header(blob,pos)
        naxis=int(h.get('NAXIS','0'))
        if naxis<1 or naxis>3:raise ValueError('unexpected NAXIS')
        size=1
        for j in range(1,naxis+1):size*=int(h[f'NAXIS{j}'])
        bits=int(h['BITPIX'])
        if bits not in [-64,-32,8,16,32,64]:raise ValueError('unsupported BITPIX')
        width=abs(bits)//8
        if len(blob)<body+size*width:raise ValueError('truncated FITS data')
        if i==0:
            header_id=str(h.get('GALAH_ID') or h.get('SOBJECT') or '').strip()
            if header_id and header_id!=visit:
                raise ValueError('GALAH_ID mismatches requested observation')
            typ=str(h.get('SPECTID','')).upper()
            if typ and typ not in ({'B':['BL','B'],'G':['GN','G'],'R':['RD','R'],'I':['IR','I']}[band]):
                raise ValueError('SPECTID mismatches requested camera')
            if not all(k in h for k in ('CRVAL1','CDELT1')):raise ValueError('wavelength WCS missing')
            left=float(h['CRVAL1'])+(1-float(h.get('CRPIX1',1)))*float(h['CDELT1'])
            right=float(h['CRVAL1'])+(size-float(h.get('CRPIX1',1)))*float(h['CDELT1'])
            mid=(left+right)/2
            if not CAMERAS[band][0]<=mid<=CAMERAS[band][1]:
                raise ValueError('wavelength arm inconsistent')
            starts=[float(h['CRVAL1']),float(h['CDELT1']),float(h.get('CRPIX1',1))]
        if i==7:
            if bits not in (-32,-64):raise ValueError('unsupported LSF type')
            fmt=('f' if bits==-32 else 'd')
            profile=struct.unpack('>'+str(size)+fmt,blob[body:body+size*width])
            if not all(0<x<10 for x in profile):raise ValueError('invalid FWHM LSF values')
        hdus.append({'index':i,'naxis':naxis,'pixels':size,'bitpix':bits, 'extname':h.get('EXTNAME')})
        pos=body+((size*width+2879)//2880)*2880
    if profile is None:raise ValueError('missing LSF')
    if any(b not in (0,32) for b in blob[pos:]):raise ValueError('trailing nonpadding data')
    import statistics
    crval,cdelt,crpix=starts
    wavelength=[crval+((i+1)-crpix)*cdelt for i in range(len(profile))]
    return {'hdus':hdus,'confirmed_native_eight_hdu':True,
            'lsf_median_FWHM_A':statistics.median(profile),
            'lsf_range_FWHM_A':[min(profile),max(profile)],
            'R_median':statistics.median(a/b for a,b in zip(wavelength,profile))}


def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'EchoLens-SP01-P2B-readonly-archive-audit/1.0','Accept':'application/fits,application/xml,text/xml,*/*'})
    try:
        with urllib.request.urlopen(req,timeout=35) as resp:
            data=resp.read(LIMIT+1)
            return int(resp.status),str(resp.headers.get('Content-Type','')),data,resp.url
    except urllib.error.HTTPError as e:
        return int(e.code),str(e.headers.get('Content-Type','')),e.read(8192),e.url


def one(gaia,visit,band=None):
    params={'ID':visit,'DR':'galah_dr4'}
    kind=('full_original_'+band if band else 'datalink_unfiltered_index')
    if band:
        params['FILT']=band;params['RESPONSEFORMAT']='fits'
    url=BASE+'?'+urllib.parse.urlencode(params)
    record={'gaia_dr3_id':gaia,'sobject_id':visit,'kind':kind,'url':url,'request_omits_IDX':True}
    try:
        status,mime,raw,final=fetch(url)
        record.update({'http_status':status,'content_type':mime,'returned_url':final,'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()})
        if len(raw)>LIMIT:
            raise ValueError('body exceeded bounded size limit')
        if status!=200:raise ValueError(f'HTTP {status}')
        if not band:
            text=raw[:1800].decode('utf8','replace')
            record['response_type']='VOTABLE_or_listing' if '<VOTABLE' in text.upper() else 'other'
            record['response_excerpt']=text[:1000]
            (OUT/(visit+'_datalink_listing.xml')).write_bytes(raw)
        else:
            info=verify_eight_hdu(raw,visit,band)
            dest=visit+'_'+band+'_original_camera.fits'
            (OUT/dest).write_bytes(raw)
            record['saved_file']=dest
            record['validation']=info
    except Exception as e:
        record['status']='not_acquired_or_rejected'
        record['error']=type(e).__name__+': '+str(e)[:400]
    else:
        record['status']='native_8hdu_verified' if band else 'listing_retrieved'
    return record


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    rows=[]
    for gaia,visit in TARGETS:
        for camera in [None,'B','G','R','I']:
            rec=one(gaia,visit,camera)
            rows.append(rec)
            (OUT/'datalink_results.json').write_text(json.dumps({'utc':dt.datetime.now(dt.timezone.utc).isoformat(),
                 'source':'Data Central Datalink docs: omit IDX for original FITS',
                 'calibration_stars_only':True,'holdout_read_count':0,
                 'results':rows,'native_verified_count':sum(r['status']=='native_8hdu_verified' for r in rows)},indent=2)+'\n')
    print(json.dumps({'native_verified_count':sum(r['status']=='native_8hdu_verified' for r in rows),
         'requests':len(rows),'results':[{k:r.get(k) for k in ('sobject_id','kind','http_status','status','error')} for r in rows]},indent=2))

if __name__=='__main__':main()
