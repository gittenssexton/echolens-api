"""Bounded GALAH DR4 two-target spectra endpoint/access audit."""
import urllib.parse,urllib.request,urllib.error,json,traceback
from pathlib import Path
from datetime import datetime,timezone
base="https://cloud.datacentral.org.au/teamdata/GALAH/public/GALAH_DR4"
out=Path("galah_access");out.mkdir(exist_ok=True)
items=[]
def hit(name,url,is_binary=False):
    rec={"name":name,"url":url};items.append(rec)
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"EchoLens GALAH DR4 one-target audit/0.1"}),timeout=35) as response:
            b=response.read(1800 if is_binary else 50000)
            rec.update(status=response.status,content_type=response.headers.get("Content-Type"),
                       content_length=response.headers.get("Content-Length"),final_url=response.url,
                       first_bytes_hex=b[:40].hex())
            if not is_binary:rec["body_first_1200"]=b[:1200].decode("utf-8","replace")
    except Exception as e:
        rec["error"]=repr(e)
        if isinstance(e,urllib.error.HTTPError):
            rec["error_body"]=e.read(1500).decode("utf-8","replace")
    print(name,rec.get("status"),rec.get("content_type"),rec.get("content_length"),rec.get("error",""),flush=True)
D="170517001801299"; B="210420000101363"
q="SELECT TOP 20 sobject_id,gaiadr3_source_id,teff,logg,phot_g_mean_mag,flag_sp,flag_red FROM galah_dr4.mainspectable WHERE gaiadr3_source_id IN (6130627011126533760,6053735173729807872) ORDER BY gaiadr3_source_id,sobject_id"
hit("all_visits","https://datacentral.org.au/vo/tap/sync?"+urllib.parse.urlencode({"REQUEST":"doQuery","LANG":"ADQL","FORMAT":"csv","QUERY":q,"MAXREC":21}))
for name,sid in (("FGK",D),("BA",B)):
    hit(name+"_allspec",base+"/analysis_products_single/"+sid[:6]+"/"+sid+"/"+sid+"_single_fit_spectrum.fits",True)
    hit(name+"_results",base+"/analysis_products_single/"+sid[:6]+"/"+sid+"/"+sid+"_single_fit_results.fits",True)
    for dr in ("galah_dr4",):
        for filt in ("B","G","R","I"):
            url="https://datacentral.org.au/vo/slink/links?"+urllib.parse.urlencode({"ID":sid,"DR":dr,"IDX":0,"FILT":filt,"RESPONSEFORMAT":"fits"})
            hit(name+"_slink_"+dr+"_"+filt,url,True)
        hit(name+"_slink_metadata","https://datacentral.org.au/vo/slink/links?"+urllib.parse.urlencode({"ID":sid,"DR":dr}),False)
r={"started_utc":datetime.now(timezone.utc).isoformat(),"results":items}
(out/"single_star_access.json").write_text(json.dumps(r,indent=2)+"\n")
