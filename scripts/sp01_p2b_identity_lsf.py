"""SP01-P2B: read-only independent original GALAH DR4 ID audit and native-camera LSF probe.

Two previously exposed CALIBRATION objects only. No holdout access, no anomalies.
Archive native, unmodified response bytes + exact queries, UTC, SHA-256, and errors.
Requires the source ids/visits frozen in earlier manifest; never replaces targets.
"""
from __future__ import annotations
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import struct
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(os.environ.get('P2B_IDENTITY_OUTPUT','reports/sp01_p2b_identity_lsf'))
TAP = 'https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync'
CATALOGUE = 'J/other/PASA/42.51/allspec'  # Buder et al. 2025 ORIGINAL DR4, not detrended Kos+2025
GAIA_CATALOGUE = 'I/355/gaiadr3'
DR4 = 'https://cloud.datacentral.org.au/teamdata/GALAH/public/GALAH_DR4'
TARGETS = [('39909218369012608','151111003101245'),('4616578742686592','221003001101138')]
MAX_CATALOGUE_BYTES = 180000
MAX_NATIVE_BYTES = 1900000


def digest(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()


def request(url:str,post:bytes|None=None,maxbytes:int=180000)->dict:
    hdr={'User-Agent':'EchoLens-SP01-P2B-source-integrity/1.0 public astronomical QA',
         'Accept':'text/csv,application/fits,application/octet-stream,*/*'}
    if post is not None:hdr['Content-Type']='application/x-www-form-urlencoded'
    req=urllib.request.Request(url,data=post,headers=hdr,method='POST' if post else 'GET')
    try:
        with urllib.request.urlopen(req, timeout=50) as r:
            status=r.status; raw=r.read(maxbytes+1); mime=r.headers.get('Content-Type',''); final=r.url
    except urllib.error.HTTPError as e:
        status=e.code;raw=e.read(min(maxbytes+1,8192));mime=e.headers.get('Content-Type','');final=e.url
    except Exception as e:
        return {'status':'network_failure','error':type(e).__name__+': '+str(e)[:400], 'url':url,'ok':False}
    return {'status':status,'url':final,'mime':mime,'size':len(raw),'sha256':digest(raw),
            'body':raw,'ok':status==200 and len(raw)<=maxbytes,'over_limit':len(raw)>maxbytes}


def tap(query:str,stem:str)->dict:
    params=urllib.parse.urlencode({'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','QUERY':query}).encode()
    obj=request(TAP,post=params,maxbytes=MAX_CATALOGUE_BYTES)
    obj['query']=query
    save(obj,stem)
    if not obj.get('ok'):return {k:v for k,v in obj.items() if k!='body'}
    body=obj['body'];start=body[:256].lower()
    if b'<votable' in start or b'<html' in start or b'query_status' in start:
        obj['ok']=False;obj['error']='TAP returned error document rather than CSV'
    else:
        try:
            lines=[line for line in body.decode('utf-8-sig').splitlines() if line and not line.startswith('#')]
            rr=list(csv.DictReader(lines));obj['rows']=rr
            if any(None in row for row in rr): raise ValueError('Malformed CSV data')
        except Exception as e:
            obj['ok']=False;obj['error']=type(e).__name__+': '+str(e)
    return {k:v for k,v in obj.items() if k!='body'}


def save(obj:dict,stem:str)->None:
    ROOT.mkdir(parents=True,exist_ok=True)
    if 'body' in obj:
        (ROOT/(stem+'.native')).write_bytes(obj['body'])


def source_check(rows:list[dict]) -> dict:
    expected={v:g for g,v in TARGETS}
    output={'table':'Buder+2025 original DR4 allspec, VizieR CDS mirror',
            'expected_pair_count':2,'returned':[],'both_match':False}
    for r in rows:
        visit=str(r.get('GALAH','')).strip();gaia=str(r.get('GaiaDR3','')).strip()
        if not re.fullmatch(r'[0-9]{15}',visit) or not re.fullmatch(r'[0-9]{12,19}',gaia):
            raise ValueError('Catalog identifiers missing, truncated or non-decimal')
        if visit not in expected:raise ValueError('Unexpected GALAH visit returned')
        output['returned'].append({'GALAH':visit,'GaiaDR3':gaia,'gaia_matches_frozen':gaia==expected[visit],
                                  'quality':{k:r.get(k) for k in ['flagSp','flagSpFit','flagRed','SNRpxCCD2','SNRpxCCD3','Teff','logg','RAJ2000','DEJ2000']}})
    output['both_match']=len(output['returned'])==2 and len({a['GALAH'] for a in output['returned']})==2 and all(a['gaia_matches_frozen'] for a in output['returned'])
    return output


def _fits_hdr(raw:bytes,offset:int) -> tuple[dict,int]:
    out={};pos=offset
    while pos+80<=len(raw) and pos-offset<24*2880:
        card=raw[pos:pos+80].decode('ascii');pos+=80
        key=card[:8].strip()
        if key=='END':return out,((pos+2879)//2880)*2880
        if card[8:10]=='= ':
            val=card[10:80].split(' / ',1)[0].strip()
            out[key]=val.split("'",2)[1].strip() if val.startswith("'") else val
    raise ValueError('Missing FITS END')


def _get_native_lsf(raw:bytes,sobject_id:str,arm:int)->dict:
    if not raw.startswith(b'SIMPLE  ='):raise ValueError('Not FITS')
    off=0;heads=[];pix=None
    for i in range(8):
        h,body=_fits_hdr(raw,off);heads.append(h)
        bits=int(h.get('BITPIX','0'));naxis=int(h.get('NAXIS','0'))
        n=1
        for ax in range(1,naxis+1):n*=int(h['NAXIS'+str(ax)])
        n=0 if naxis==0 else n
        nb=n*(abs(bits)//8)
        if nb<0 or len(raw)<body+nb:raise ValueError('Truncated camera FITS')
        if i==0:
            obs=h.get('GALAH_ID') or h.get('SOBJECT')
            if obs is not None and obs!=sobject_id:raise ValueError('Native GALAH_ID mismatches visit')
            spectid=h.get('SPECTID','')
            expect=['BL','GN','RD','IR'][arm-1]
            if spectid and spectid not in (expect,expect[0]):raise ValueError('Camera SPECTID mismatches requested arm')
        if i==7:
            if bits!=-32 and bits!=-64:raise ValueError('Unknown LSF BITPIX '+str(bits))
            width={-32:4,-64:8}[bits];t='f' if width==4 else 'd'
            if n<1000 or n>30000:raise ValueError('Unexpected LSF shape')
            pix=struct.unpack('>'+str(n)+t,raw[body:body+nb])
        off=body+((nb+2879)//2880)*2880
    if pix is None:raise ValueError('Eighth resolution-profile HDU not available')
    good=[x for x in pix if 0<x<10 and x==x]
    if len(good)!=len(pix):raise ValueError('Invalid LSF profile elements')
    h=heads[0];step=float(h['CDELT1']);start=float(h['CRVAL1']);crpix=float(h.get('CRPIX1',1))
    wavelengths=[start+(j+1-crpix)*step for j in range(len(good))]
    R=[w/res for w,res in zip(wavelengths,good)]
    return {'count':len(good),'lsf_FWHM_A':{'min':min(good),'median':statistics.median(good),'max':max(good)},
            'lambda_over_FWHM':{'min':min(R),'median':statistics.median(R),'max':max(R)},
            'range_A':[min(wavelengths),max(wavelengths)],'HDUs':8,
            'headers_sha256':digest(''.join(str(x) for x in heads).encode()),
            'physical_note':'Native GALAH camera HDU7 resolution_profile is local wavelength-dependent FWHM, not one nominal R'}


def run()->dict:
    ROOT.mkdir(parents=True,exist_ok=True)
    visits=','.join(str(v) for _,v in TARGETS)
    query=(f'SELECT TOP 4 "GALAH","GaiaDR3","flagSp","flagSpFit","flagRed",'
           f'"SNRpxCCD2","SNRpxCCD3","Teff","logg","RAJ2000","DEJ2000" '
           f'FROM "{CATALOGUE}" WHERE "GALAH" IN ({visits})')
    original=tap(query,'original_galah_dr4_allspec_two_rows')
    result={'schema':'echolens-sp01-p2b-independent-verification-v1',
            'utc':dt.datetime.now(dt.timezone.utc).isoformat(),
            'scope':'TWO PRESELECTED CALIBRATION SOURCES ONLY',
            'holdout_sources_read':0,
            'original_DR4_catalogue':{'query':query,'response_status':original.get('status'),
                       'sha256':original.get('sha256'),'error':original.get('error'),
                       'verified':False}, 'native_camera_probes':[],
            'science_ready':False,'technosignature_claim':False}
    if original.get('ok'):
        try:
            match=source_check(original.get('rows',[]))
            result['original_DR4_catalogue']['match']=match
            result['original_DR4_catalogue']['verified']=match['both_match']
        except Exception as e:result['original_DR4_catalogue']['error']=str(e)
    # For each star, bounded CCD1-CCD4 original camera requests. Never use corrupt SSA transformations.
    for gaia,visit in TARGETS:
        for camera in range(1,5):
            date=visit[:6]
            url=f'{DR4}/observations/{date}/spectra/com/{visit}{camera}.fits'
            obj=request(url,maxbytes=MAX_NATIVE_BYTES)
            stem=f'native_{visit}_ccd{camera}'
            row={'visit':visit,'frozen_gaia':gaia,'camera':camera,'url':url,
                 'status':obj.get('status'),'response_sha256':obj.get('sha256'),
                 'bytes':obj.get('size'),'lsf_verified':False}
            if obj.get('ok'):
                try:
                    profile=_get_native_lsf(obj['body'],visit,camera)
                    save(obj,stem+'.fits')
                    row['lsf_verified']=True;row['LSF']=profile
                except Exception as e:row['error']='FITS/LSF rejection: '+str(e)
            else:
                row['error']=obj.get('error') or ('HTTP/byte limit: '+str(obj.get('status')))
                # Error documents are not saved as original spectrum products.
            result['native_camera_probes'].append(row)
            (ROOT/'status.json').write_text(json.dumps(result,indent=2)+'\n')
    result['original_allspec_identity_confirmed']=result['original_DR4_catalogue']['verified']
    result['native_lsf_fits_recovered']=sum(row['lsf_verified'] for row in result['native_camera_probes'])
    (ROOT/'status.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    out=run()
    print(json.dumps({'original_allspec_identity_confirmed':out['original_allspec_identity_confirmed'],
                      'original_catalogue':out['original_DR4_catalogue'],
                      'native_lsf_fits_recovered':out['native_lsf_fits_recovered'],
                      'native_failures':out['native_camera_probes']},indent=2)[:16000])
