"""Bounded read-only query interface probe for GALAH DR4 at Data Central.

The query is SELECT TOP 1 on a documented public catalog. Creates no private
account actions, no stored user data, no large catalogue download. Writes raw
HTTP response snippets so transport/schema failures can be diagnosed.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

QUERY='SELECT TOP 1 gaiadr3_source_id,sobject_id FROM galah_dr4.main_star WHERE flag_sp=0'
OUT=Path(os.environ.get('SP01_P2B_OUTPUT','reports/sp01_p2b_trial'))
OUT.mkdir(parents=True,exist_ok=True)

def call(url,payload,headers):
    req=urllib.request.Request(url,data=payload,headers=headers,method='POST')
    try:
        with urllib.request.urlopen(req,timeout=50) as r:
            code=r.status
            data=r.read(8192)
            content_type=r.headers.get('Content-Type','')
            returned_url=r.url
    except urllib.error.HTTPError as e:
        code=e.code
        data=e.read(8192)
        content_type=e.headers.get('Content-Type','')
        returned_url=e.url
    except Exception as e:
        return {'status':'request_failed','exception_class':type(e).__name__,
                'error':str(e)[:500], 'query':QUERY}
    return {'http_status':code,'content_type':content_type,'url':returned_url,
            'response_bytes_sampled':len(data), 'sample_sha256':hashlib.sha256(data).hexdigest(),
            'response_excerpt':data.decode('utf8','replace')[:2000], 'query':QUERY}

probes={
    'legacy_tap_small':call('https://datacentral.org.au/vo/tap/sync',
      urllib.parse.urlencode({'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','QUERY':QUERY}).encode(),
      {'Content-Type':'application/x-www-form-urlencoded'}),
    'modern_query_service':call('https://datacentral.org.au/api/services/query/',
      json.dumps({'title':'EchoLens SP01 P2B bounded GALAH DR4 field probe',
                  'notes':'one catalog row only; no spectra or anomaly inference',
                  'sql':QUERY,'run_async':False,'email':''}).encode(),
      {'Content-Type':'application/json','Accept':'application/json'}),
}
report={'type':'datacentral_read_only_schema_probe','utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'probes':probes}
(OUT/'datacentral_rest_probe.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
