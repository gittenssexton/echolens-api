"""Single bounded TAP check: mainstar-clean dwarf candidates also visit-clean."""
import urllib.parse,urllib.request,json
from pathlib import Path
ids=[3064554891927687296,5386330687921176448,5431576416037953792,5025418263842016768,6130627011126533760,5370615127713831680,3312411480281424000,6094691810031844480]
q="SELECT TOP 30 sobject_id,gaiadr3_source_id,flag_sp,flag_red,teff,logg FROM galah_dr4.mainspectable WHERE gaiadr3_source_id IN ("+",".join(str(x) for x in ids)+") ORDER BY gaiadr3_source_id,sobject_id"
url="https://datacentral.org.au/vo/tap/sync?"+urllib.parse.urlencode({"REQUEST":"doQuery","LANG":"ADQL","FORMAT":"csv","QUERY":q,"MAXREC":"31"})
with urllib.request.urlopen(url,timeout=120) as r:data=r.read(20000)
p=Path("galah_candidate_flags");p.mkdir(exist_ok=True);(p/"candidate_visits.csv").write_bytes(data)
(p/"query.json").write_text(json.dumps({"query":q,"url":url},indent=2))
print(data.decode(),flush=True)
