"""Probe Data Central DataLink original science-file retrieval; single sid only."""
import urllib.request,urllib.parse,urllib.error,json,xml.etree.ElementTree as ET
from pathlib import Path
p=Path("galah_original_probe");p.mkdir(exist_ok=True)
sid="170517001801299"
base="https://datacentral.org.au/vo/slink/links"
tests=[("metadata",{"ID":sid,"DR":"galah_dr4"}),
 ("idx0_nofilt",{"ID":sid,"DR":"galah_dr4","IDX":0}),
 ("idx1_B",{"ID":sid,"DR":"galah_dr4","IDX":1,"FILT":"B","RESPONSEFORMAT":"fits"}),
 ("original_B",{"ID":sid,"DR":"galah_dr4","IDX":0,"FILT":"B","RESPONSEFORMAT":"original"}),
 ("native_B",{"ID":sid,"DR":"galah_dr4","IDX":0,"FILT":"B","RESPONSEFORMAT":"raw"}),
 ("download_B",{"ID":sid,"DR":"galah_dr4","IDX":0,"FILT":"B","RESPONSEFORMAT":"fits","ORIGINAL":"1"}),
 ("ssa_query",{"ID":sid,"DR":"galah_dr4","IDX":0,"FILT":"B","RESPONSEFORMAT":"votable"})]
out=[]
for name,qs in tests:
 url=base+"?"+urllib.parse.urlencode(qs)
 e={"name":name,"url":url};out.append(e)
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"EchoLens-GALAH-one-star-HDU-audit"}),timeout=60) as r:
   data=r.read(160000)
   e["status"]=r.status;e["content_type"]=r.headers.get("Content-Type");e["bytes"]=len(data)
   if data.startswith(b"SIMPLE"): e["fits_primary_header"]=data[:2880].decode("ascii","replace")
   else:e["body"]=data[:15000].decode("utf-8","replace")
 except Exception as exc:
  e["error"]=repr(exc)
 print(name,e.get("status"),e.get("content_type"),e.get("error",""),flush=True)
(p/"original_access_probe.json").write_text(json.dumps(out,indent=2)+"\n")
