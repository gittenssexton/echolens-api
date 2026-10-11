"""Bounded complete original GALAH DR4 HERMES exposures from DataLink originals.
Two Gaia source IDs only, three allspec visit IDs; never bulk-query survey.
"""
import hashlib, json, urllib.request, urllib.parse, urllib.error, io, sys, time, traceback
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
from astropy.io import fits
ROOT=Path("galah_originals")
TARGETS={
    "ordinary_g_dwarf":["170517001801299"],
    "catalogued_ba_star":["210420000101363","230302001701254"]
}
sha=lambda b:hashlib.sha256(b).hexdigest()
utc=lambda:datetime.now(timezone.utc).isoformat()
manifest={"created_utc":utc(),"project":"EchoLens GALAH DR4 Experiment 002-A",
  "archive":"Data Central GALAH DR4 IVOA DataLink raw original release spectra",
  "mainstar_gaia_ids":{"ordinary_g_dwarf":"6130627011126533760",
                     "catalogued_ba_star":"6053735173729807872"},
  "source_catalogue":"GALAH DR4 mainspectable (3 allspec visits)",
  "targets":TARGETS,"url_inventory":[],"retrievals":[],"files":[],"misses":[],
  "status":"incomplete","no_bulk":True,"no_science_inference":True}
def fetch(url,label,max_bytes=1500000):
 entry={"label":label,"url":url,"requested_utc":utc()}
 manifest["retrievals"].append(entry)
 for attempt in range(2):
  try:
   if not url.startswith("https://datacentral.org.au/"):raise ValueError("Unapproved archive domain")
   req=urllib.request.Request(url,headers={"User-Agent":"EchoLens-GALAH-DR4-2-star-original-FITS-audit"})
   with urllib.request.urlopen(req,timeout=85) as response:
    b=response.read(max_bytes+1)
    entry.update(status=response.status,content_type=response.headers.get("Content-Type"),
      declared_bytes=response.headers.get("Content-Length"),date=response.headers.get("Date"),
      final_url=response.url,received_utc=utc())
   if len(b)>max_bytes:raise ValueError("Exceeded bounded per-file byte cap")
   entry.update(bytes=len(b),sha256=sha(b))
   return b,entry
  except Exception as e:
   entry["error"]=repr(e)
   if isinstance(e,urllib.error.HTTPError):
    entry["http_error"]=e.code
    entry["body_excerpt"]=e.read(1000).decode("utf-8","replace")
   if attempt==0:time.sleep(1.0)
 return None,entry
try:
 files_to_get=[]
 for name, visits in TARGETS.items():
  for sid in visits:
   url="https://datacentral.org.au/vo/slink/links?"+urllib.parse.urlencode({"ID":sid,"DR":"galah_dr4"})
   raw,entry=fetch(url,f"Original GALAH DR4 DataLink for {sid}",180000)
   if raw is None:raise RuntimeError("Could not obtain data inventory for "+sid)
   dn=ROOT/name/sid;dn.mkdir(parents=True,exist_ok=True)
   (dn/"datalink_original_inventory.vot.xml").write_bytes(raw)
   xml=ET.fromstring(raw)
   fields=[x.attrib.get("name","") for x in xml.iter() if x.tag.split("}")[-1]=="FIELD"]
   tabrows=[]
   for row in xml.iter():
    if row.tag.split("}")[-1]!="TR":continue
    vals=[(a.text or "") for a in row if a.tag.split("}")[-1]=="TD"]
    if len(vals)==len(fields):tabrows.append(dict(zip(fields,vals)))
   originals=[x for x in tabrows if "original" in x.get("description","").lower()
               and x.get("access_url","").endswith(".fits")]
   manifest["url_inventory"].append({"target":name,"visit":sid,"datalink_sha256":sha(raw),
        "rows":len(tabrows),"original_fits_links":len(originals),
        "files":[{"url":x.get("access_url"),"description":x.get("description"),
             "content_length":x.get("content_length"),"mjd_beg":x.get("mjd_beg"),
             "mjd_end":x.get("mjd_end")} for x in originals]})
   if not originals:raise RuntimeError("No original DR4 science links for "+sid)
   for x in originals:
    url=x["access_url"]
    if not url.startswith("https://datacentral.org.au/services/sov/"):
     raise RuntimeError("Datalink source outside original-release namespace")
    files_to_get.append((name,sid,url,x))
 if len(files_to_get)>80: raise RuntimeError("Bounded single-target cap: >80 originals")
 manifest["planned_original_count"]=len(files_to_get)
 print("Original requested exposures/cameras",len(files_to_get),flush=True)
 total=0
 for name,sid,url,info in files_to_get:
  filename=url.rsplit("/",1)[-1]
  raw,entry=fetch(url,name+"/"+sid+"/"+filename,1400000)
  if raw is None:
   manifest["misses"].append({"target":name,"visit":sid,"filename":filename,"error":entry.get("error"),"url":url})
   print("MISSING",filename,entry.get("error"),flush=True)
   continue
  total+=len(raw)
  if total>60000000:raise RuntimeError("Aggregate safety cap 60MB")
  if not raw.startswith(b"SIMPLE"):
   manifest["misses"].append({"target":name,"visit":sid,"filename":filename,
       "error":"Server did not return FITS", "content_type":entry.get("content_type")})
   print("INVALID_FITS",filename,flush=True);continue
  dest=ROOT/name/sid/"original_reduced"
  dest.mkdir(parents=True,exist_ok=True)
  (dest/filename).write_bytes(raw)
  record={"path":str((dest/filename).relative_to(ROOT)),"size_bytes":len(raw),
    "sha256":sha(raw),"origin_url":url,"retrieved_utc":entry.get("received_utc"),
    "declared_content_length":entry.get("declared_bytes"),
    "camera":int(filename[-6]) if len(filename)>6 and filename[-6].isdigit() else None,
    "native_original":True,"fits_hdus":[]}
  try:
   with fits.open(io.BytesIO(raw),memmap=False) as hdul:
    for i,hdu in enumerate(hdul):
     record["fits_hdus"].append({
      "index":i,"name":hdu.name,"class":type(hdu).__name__,
      "header_cards_exact":[card.image for card in hdu.header.cards],
      "header_count":len(hdu.header.cards),
      "data_shape":list(hdu.data.shape) if hdu.data is not None else None,
      "data_dtype":str(hdu.data.dtype) if hdu.data is not None else None,
      "columns":list(hdu.columns.names) if isinstance(hdu,fits.BinTableHDU) else None,
      "mask_or_badpixel_named":any(s in hdu.name.upper() for s in ("MASK","FLAG","DQ","BADPIX","CRR"))
     })
   record["fits_parse_ok"]=True
  except Exception as e:
   record["fits_parse_ok"]=False;record["parse_error"]=repr(e)
  manifest["files"].append(record)
  print("NATIVE",filename,len(raw),"HDUs",len(record["fits_hdus"]),"valid",record.get("fits_parse_ok"),flush=True)
 manifest["total_native_bytes"]=total
 manifest["status"]="completed" if not manifest["misses"] else "completed_with_missing_originals"
except Exception as e:
 manifest["status"]="failed";manifest["error"]=repr(e);manifest["traceback"]=traceback.format_exc()
 print(manifest["traceback"],file=sys.stderr,flush=True)
finally:
 manifest["closed_utc"]=utc()
 ROOT.mkdir(exist_ok=True)
 (ROOT/"HDU_HEADERS_AND_SHA256_ORIGINALS.json").write_text(json.dumps(manifest,indent=2)+"\n")
 (ROOT/"SHA256SUMS_ORIGINALS.txt").write_text("".join(x["sha256"]+"  "+x["path"]+"\n" for x in manifest["files"]))
print("Audit status",manifest["status"],"n_original",len(manifest["files"]),"missing",len(manifest["misses"]),flush=True)
if manifest["status"]=="failed":sys.exit(1)
