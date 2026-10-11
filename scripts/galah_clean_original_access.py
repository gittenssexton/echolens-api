"""Confirm clean FGK dwarf native originals inventory and HTTP permissions only."""
import json,urllib.request,urllib.parse,urllib.error,xml.etree.ElementTree as ET,datetime
from pathlib import Path
out=Path("galah_clean_originals_access");out.mkdir(exist_ok=True)
sid="170416001901162"
url="https://datacentral.org.au/vo/slink/links?"+urllib.parse.urlencode({"ID":sid,"DR":"galah_dr4"})
with urllib.request.urlopen(url,timeout=60) as r: raw=r.read(100000)
(out/"original_links.vot.xml").write_bytes(raw)
tree=ET.fromstring(raw);fields=[x.attrib.get("name") for x in tree.iter() if x.tag.split('}')[-1]=='FIELD']
rows=[]
for item in tree.iter():
 if item.tag.split('}')[-1]=='TR':
  vals=[(x.text or "") for x in item if x.tag.split('}')[-1]=='TD']
  if len(vals)==len(fields):rows.append(dict(zip(fields,vals)))
originals=[x for x in rows if 'original' in x.get('description','').lower()]
result={'source_id':3064554891927687296,'sobject_id':sid,'originals_listed':len(originals),
        'URLs':[x['access_url'] for x in originals],'test_access':None,'method':'Data Central original DataLink; one original request, not bulk'}
if originals:
 try:
  with urllib.request.urlopen(originals[0]['access_url'],timeout=75) as r:
   b=r.read(100)
   result['test_access']={'status':r.status,'first_bytes_hex':b.hex()}
 except urllib.error.HTTPError as e:
  result['test_access']={'status':e.code,'error':str(e)}
(out/"clean_fgk_originals_access.json").write_text(json.dumps(result,indent=2))
print(json.dumps({'count':len(originals),'test':result['test_access']}),flush=True)
