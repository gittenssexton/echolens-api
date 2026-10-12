"""Fetch each original native GALAH DR4 camera by EXACT Datalink-listed filename.

Two already-exposed P2B CALIBRATION visits, no holdout, no anomaly scan. Do not
follow arbitrary VOTABLE URLs: require HTTPS Data Central host/path and filename.
Data Central's unfiltered links include four combined native camera files and
12 individual exposures; this retrieves only four combined files per star.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from .sp01_p2b_original_datalink_probe import TARGETS,BASE,fetch,verify_eight_hdu,LIMIT

OUT=Path(os.environ.get('P2B_EXACT_ORIGINAL_OUTPUT','reports/sp01_p2b_exact_original'))
NS={'v':'http://www.ivoa.net/xml/VOTable/v1.3'}
CAMERAS={'B':1,'G':2,'R':3,'I':4}


def exact_original_links(xml_bytes:bytes,visit:str)->dict:
    root=ET.fromstring(xml_bytes)
    if root.tag!='{http://www.ivoa.net/xml/VOTable/v1.3}VOTABLE':
        raise ValueError('Expected VOTABLE metadata')
    status=[x.get('value') for x in root.findall('.//v:INFO',NS) if x.get('name')=='QUERY_STATUS']
    if status!=['OK']:raise ValueError('VOTABLE status not OK')
    fields=[x.get('name') for x in root.findall('.//v:FIELD',NS)]
    if not {'access_url','description','ID','content_type'}.issubset(fields):raise ValueError('Missing Datalink fields')
    links={}
    for tr in root.findall('.//v:TABLEDATA/v:TR',NS):
        td=[x.text or '' for x in tr.findall('v:TD',NS)]
        r=dict(zip(fields,td))
        if r['ID']!=visit or r['content_type']!='application/fits' or r['description']!='FITS spectrum (original)':continue
        for band,num in CAMERAS.items():
            expected=f'{visit}{num}.fits'
            u=urlparse(r['access_url'])
            if u.scheme!='https' or u.netloc!='datacentral.org.au' or not u.path.startswith('/services/sov/') or not u.path.endswith('/'+expected):continue
            if band in links:raise ValueError('Multiple URLs for exact combined camera '+band)
            links[band]=r['access_url']
    if set(links)!=set(CAMERAS):raise ValueError('Not exactly 4 original combined cameras')
    return links


def acquire():
    OUT.mkdir(parents=True,exist_ok=True)
    results=[]
    for gaia,visit in TARGETS:
        listing_url=BASE+'?ID='+visit+'&DR=galah_dr4'
        status,mime,raw,final=fetch(listing_url)
        record={'gaia_dr3_id':gaia,'sobject_id':visit,'kind':'original_datalink_manifest',
                'listing_url':listing_url,'http_status':status,'bytes':len(raw),
                'sha256':hashlib.sha256(raw).hexdigest()}
        if status!=200 or len(raw)>LIMIT:raise ValueError('Cannot download bounded Datalink listing '+visit)
        (OUT/(visit+'_original_links.xml')).write_bytes(raw)
        links=exact_original_links(raw,visit)
        record['exact_camera_links']=links
        results.append(record)
        for band,url in links.items():
            rec={'gaia_dr3_id':gaia,'sobject_id':visit,'camera':band,
                 'url_from_Datalink_original_listing':url,'synthetic':False}
            try:
                status,mime,raw,final=fetch(url)
                rec.update(http_status=status,returned_url=final,content_type=mime,
                           bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
                if status!=200 or len(raw)>LIMIT:raise ValueError('HTTP '+str(status)+' or response too large')
                fmt=verify_eight_hdu(raw,visit,band)
                fn=visit+'_'+band+'_exact_original_8hdu.fits'
                (OUT/fn).write_bytes(raw)
                rec['status']='verified_native_camera_LSF'
                rec['validation']=fmt;rec['saved_file']=fn
            except Exception as exc:
                rec['status']='blocked';rec['error']=type(exc).__name__+': '+str(exc)[:400]
            results.append(rec)
            (OUT/'exact_original_results.json').write_text(json.dumps({'utc':dt.datetime.now(dt.timezone.utc).isoformat(),
              'research_scope':'two previously exposed calibration stars only',
              'method':'unfiltered GALAH DR4 Datalink original listing + exact filename URL',
              'holdout_stars_read':0,'science_ready':False,
              'verified_native_camera_count':sum(x.get('status')=='verified_native_camera_LSF' for x in results),
              'results':results},indent=2)+'\n')
    print(json.dumps({'verified_native_camera_count':sum(x.get('status')=='verified_native_camera_LSF' for x in results),
     'all_recovered':all(x.get('status')=='verified_native_camera_LSF' for x in results if 'camera' in x),
     'cameras':[{k:r.get(k) for k in ('sobject_id','camera','status','sha256','error')} for r in results if 'camera' in r]},indent=2))

if __name__=='__main__':acquire()
