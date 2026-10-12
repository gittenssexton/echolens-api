"""EchoLens F01: bounded provider health check, NOT science or a Gaia counterpart join.

One real IRSA AllWISE TOP 2 catalogue request, no original Gaia bulk re-query.
Includes immutable response bytes/SHA when status 200, clear provider failure metadata.
"""
from __future__ import annotations
import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
from scripts.tap_reliability import catalog_provider_spec, encode_tap, request_bytes, TAPPermanentError, TAPExhausted

OUT = Path('reports/f01_irsa_live_probe')
Q = "SELECT TOP 2 designation,ra,dec,w1mpro,w1sigmpro,w3mpro,w3sigmpro,cc_flags,ph_qual FROM allwise_p3as_psd WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',42.20887374878,3.19799995422,0.00277777778))=1"


def valid_csv(raw: bytes) -> dict:
    text=raw.decode('utf-8-sig','strict')
    if text.lstrip().startswith('<') or '<VOTABLE' in text[:500]:
        raise ValueError('IRSA returned XML/HTML error, not CSV')
    lines=[line for line in text.splitlines() if line.strip() and not line.startswith('#')]
    rows=list(csv.DictReader(io.StringIO('\n'.join(lines))))
    if len(rows)>2:
        raise ValueError('Unexpected AllWISE bounded rows')
    required={'designation','ra','dec','w1mpro','w3mpro','cc_flags','ph_qual'}
    header=set(lines[0].split(',')) if lines else set()
    if not required.issubset(header):
        raise ValueError('Missing expected AllWISE columns')
    if any(None in row for row in rows):
        raise ValueError('Malformed CSV row')
    return {'row_count':len(rows),'columns':sorted(rows[0].keys()),'schema_check':'passed','counterpart_identifications':0}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    spec=catalog_provider_spec('IRSA_AllWISE')
    url=encode_tap(spec['endpoint'],Q,fmt='csv',maxrec='3')
    log={'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'purpose':'IRSA AllWISE provider API transport check only','source':'NASA/IPAC IRSA', 'table':'allwise_p3as_psd','adql':Q,'url':url,'retry_on': 'transient only, at most 3 attempts','science_ready':False}
    try:
        raw,receipt=request_bytes(url,timeout=20,attempts=3,max_bytes=12000,max_wait=4,headers={'User-Agent':'EchoLens-F01-provider-health/1.0'})
        log['response']=valid_csv(raw)
        log['receipt']=receipt
        log['status']='API_RESPONDED_VALID_TABLE'
        (OUT/'allwise_raw_2_rows.csv').write_bytes(raw)
        log['sha256']=hashlib.sha256(raw).hexdigest()
    except (TAPPermanentError,TAPExhausted,ValueError,TimeoutError,UnicodeError,ConnectionError) as exc:
        log['status']='API_BLOCKED_OR_BAD_SCHEMA'
        log['error_type']=type(exc).__name__
        log['error']=str(exc)[:350]
    finally:
        (OUT/'probe.json').write_text(json.dumps(log,indent=2)+'\n',encoding='utf8')
        print(json.dumps({'status':log['status'],'sha256':log.get('sha256'),'rows':log.get('response',{}).get('row_count'),'error':log.get('error')},indent=2))

if __name__=='__main__':main()
