"""Acquire and validate the official DR9 v2 LRS catalog without replacing old copies."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import struct
import tempfile
import time
import urllib.request

URL = 'https://www.lamost.org/dr9/v2.0/catdl?name=dr9_v2.0_LRS_catalogue.fits.gz'
ROWS = 10809336
BLOCK = 2880


def value(cards, name, default=None):
    for c in cards:
        if c[:8].strip()==name and c[8:10]=='= ':
            text=c[10:].strip()
            if text.startswith("'"):
                return text[1:].split("'")[0].strip()
            text=text.split('/')[0].strip()
            if text in ('T','F'): return text=='T'
            return int(text)
    return default


def header(stream):
    cards=[]
    for _ in range(200):
        block=stream.read(BLOCK)
        if len(block)!=BLOCK: raise ValueError('Incomplete FITS header')
        for n in range(0,BLOCK,80):
            c=block[n:n+80].decode('ascii')
            if c[:8]=='END     ': return cards
            cards.append(c)
    raise ValueError('Unexpectedly large FITS header')


def validate(path, expected_rows=ROWS):
    """Stream gzip CRC/footer validation, inspect all HDUs, check exact observation IDs."""
    path=Path(path)
    sha,md5=hashlib.sha256(),hashlib.md5()
    with path.open('rb') as src:
        for chunk in iter(lambda:src.read(1024*1024),b''):
            sha.update(chunk); md5.update(chunk)
    report={'compressed_bytes':path.stat().st_size,'sha256':sha.hexdigest(),'md5':md5.hexdigest()}
    with tempfile.TemporaryDirectory(dir=path.parent) as staging:
        raw=Path(staging)/'catalog.fits'
        size=0
        with gzip.open(path,'rb') as src,raw.open('wb') as dst:
            for chunk in iter(lambda:src.read(1024*1024),b''):
                size+=len(chunk)
                if size>4*1024**3: raise ValueError('Uncompressed size cap exceeded')
                dst.write(chunk)
        if size%BLOCK: raise ValueError('FITS file is not block aligned')
        report['uncompressed_bytes']=size
        hdus=[]
        with raw.open('rb') as f:
            while f.tell()<size:
                start=f.tell(); cards=header(f); data=f.tell()
                kind=value(cards,'XTENSION','PRIMARY')
                if not hdus and value(cards,'SIMPLE') is not True:
                    raise ValueError('Not a primary FITS header')
                if kind=='BINTABLE':
                    width,rows=value(cards,'NAXIS1'),value(cards,'NAXIS2')
                    count=width*rows+value(cards,'PCOUNT',0)
                    columns=[{'name':value(cards,f'TTYPE{i}'),'format':value(cards,f'TFORM{i}'),
                        'unit':value(cards,f'TUNIT{i}'),'null':value(cards,f'TNULL{i}')}
                        for i in range(1,value(cards,'TFIELDS',0)+1)]
                else:
                    axes=value(cards,'NAXIS',0); count=0 if axes==0 else abs(value(cards,'BITPIX'))//8
                    for i in range(1,axes+1): count*=value(cards,f'NAXIS{i}')
                    width=rows=0; columns=[]
                end=data+((count+BLOCK-1)//BLOCK)*BLOCK
                if end>size: raise ValueError('FITS table payload is incomplete')
                h={'type':kind,'header_start':start,'data_start':data,'data_bytes':count,
                   'row_bytes':width,'rows':rows,'columns':columns}
                hdus.append(h); f.seek(end)
        tables=[h for h in hdus if h['type']=='BINTABLE']
        if len(tables)!=1 or tables[0]['rows']!=expected_rows:
            raise ValueError('Catalog table or release row count mismatch')
        table=tables[0]
        if (not table['columns'] or table['columns'][0]['name'] != 'obsid'
                or table['columns'][0]['format'] not in ('J','1J')):
            raise ValueError('Expected scalar 32-bit obsid as first column')
        db=sqlite3.connect(Path(staging)/'ids.sqlite')
        db.execute('PRAGMA journal_mode=OFF'); db.execute('PRAGMA synchronous=OFF')
        db.execute('CREATE TABLE ids(obsid INTEGER PRIMARY KEY)')
        with raw.open('rb') as f:
            f.seek(table['data_start']); remaining=expected_rows
            while remaining:
                n=min(10000,remaining); payload=f.read(n*table['row_bytes'])
                ids=[(struct.unpack_from('>i',payload,k*table['row_bytes'])[0],) for k in range(n)]
                if any(i[0]<=0 for i in ids): raise ValueError('Invalid observation ID')
                db.executemany('INSERT OR IGNORE INTO ids VALUES (?)',ids); remaining-=n
        unique=db.execute('SELECT COUNT(*) FROM ids').fetchone()[0]; db.close()
        if unique!=expected_rows: raise ValueError('Duplicate observation IDs')
        report.update({'gzip_integrity':'complete','hdus':hdus,'rows':expected_rows,
                       'unique_obsids':unique,'whole_file_valid':True})
    return report


def acquire(directory):
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
    partial=directory/'dr9_v2.0_LRS_catalogue.fits.gz.part'
    final=directory/'dr9_v2.0_LRS_catalogue.complete.fits.gz'
    if partial.exists() or final.exists(): raise ValueError('Refusing to overwrite an acquisition')
    record={'source_url':URL,'source_page':'https://www.lamost.org/dr9/v2.0/catalogue',
            'release':'LAMOST DR9 v2.0 LRS','started_at':datetime.now(timezone.utc).isoformat(),
            'expected_rows':ROWS,'state':'acquiring','range_resume_supported':False}
    metadata=directory/'acquisition.json'
    metadata.write_text(json.dumps(record,indent=2)+'\n')
    start=time.monotonic(); total=0; last=start
    try:
        with urllib.request.urlopen(URL,timeout=90) as response,partial.open('wb') as dst:
            record.update({'http_status':response.status,'response_url':response.geturl(),
                'headers':{k:response.headers.get(k) for k in ('Content-Length','Content-Type','ETag','Last-Modified')}})
            for chunk in iter(lambda:response.read(1024*1024),b''):
                if total==0 and not chunk.startswith(b'\x1f\x8b'): raise ValueError('Response is not gzip data')
                total+=len(chunk)
                if total>4*1024**3 or time.monotonic()-start>1800:
                    raise ValueError('Acquisition cap exceeded')
                dst.write(chunk)
                if time.monotonic()-last>20:
                    print(f'Received {total/1e6:.1f} MB',flush=True); last=time.monotonic()
        print(f'Received {total/1e6:.1f} MB; checking gzip and FITS',flush=True)
        record['validation']=validate(partial)
        partial.rename(final); record['state']='validated'; record['file']=final.name
    except Exception as exc:
        record.update({'state':'failed','failure':f'{type(exc).__name__}: {exc}',
                       'received_bytes':partial.stat().st_size if partial.exists() else 0})
        if partial.exists():
            sha=hashlib.sha256()
            with partial.open('rb') as src:
                for chunk in iter(lambda:src.read(1024*1024),b''): sha.update(chunk)
            record['partial_sha256']=sha.hexdigest()
        raise
    finally:
        record['finished_at']=datetime.now(timezone.utc).isoformat()
        metadata.write_text(json.dumps(record,indent=2)+'\n')
    return record


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('directory',nargs='?')
    p.add_argument('--validate-file')
    args=p.parse_args()
    if args.validate_file:
        print(json.dumps(validate(args.validate_file),indent=2))
    elif args.directory:
        result=acquire(args.directory)
        print(json.dumps({'state':result['state'],'validation':result['validation']},indent=2))
    else: p.error('Provide a new acquisition directory or --validate-file')
