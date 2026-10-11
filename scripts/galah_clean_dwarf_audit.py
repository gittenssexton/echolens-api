"""GALAH DR4 bounded, observation-complete, two-object FITS engineering audit.
No large catalog downloads, scoring or candidate selection.
"""
from __future__ import annotations
import hashlib, json, urllib.parse, urllib.request, urllib.error, io, sys, traceback, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from astropy.io import fits
ROOT=Path("galah_clean_dwarf_audit")
BASE="https://cloud.datacentral.org.au/teamdata/GALAH/public/GALAH_DR4"
TAP="https://datacentral.org.au/vo/tap/sync"
SLINK="https://datacentral.org.au/vo/slink/links"
TARGETS={
 "ordinary_fgk_dwarf_visit_clean":{
  "source_id":3064554891927687296,"visits":["170416001901162"],
  "selection":"GALAH mainstar G=9.001117 Teff=5973.13K logg=4.3824, flag_sp=0, flag_red=0; independent mainspectable visit also flag_sp=0, flag_red=0; Gaia DR3 3064554891927687296"
 }
}
sha=lambda b:hashlib.sha256(b).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
manifest={"started_utc":now(),"released":"GALAH DR4","program":"EchoLens Experiment 002-A one clean FGK dwarf, independent follow-up to two-star preliminary audit",
          "archive":"AAO Data Central", "source_catalog":"galah_dr4.mainspectable",
          "survey_documentation":"https://www.galah-survey.org/dr4/the_spectra/",
          "targets":TARGETS,"files":[],"requests":[],"limitations":[],"no_science_inference":True}
total=[0]
def request_bytes(label,url,limit=6000000,retries=2):
    entry={"label":label,"url":url,"started_utc":now()}
    manifest["requests"].append(entry)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"EchoLens-GALAH-DR4-single-star-audit/1.0"}),timeout=130) as response:
                data=response.read(limit+1)
                entry.update(status=response.status,content_type=response.headers.get("Content-Type"),
                             content_length=response.headers.get("Content-Length"),response_url=response.url,
                             response_date=response.headers.get("Date"))
            if len(data)>limit: raise ValueError("Single-file safety limit exceeded: "+str(limit))
            entry["download_bytes"]=len(data);entry["sha256"]=sha(data);entry["completed_utc"]=now()
            total[0]+=len(data)
            if total[0]>60000000:raise RuntimeError("Aggregate 60 MB target-only cap exceeded")
            return data,entry
        except Exception as e:
            entry["error"]=repr(e)
            entry["attempts"]=attempt+1
            if isinstance(e,urllib.error.HTTPError):
                entry["error_status"]=e.code
                entry["error_excerpt"]=e.read(1000).decode("utf-8","replace")
            if attempt+1<retries:time.sleep(1)
    return None,entry

def record_file(where,name,data,entry):
    where.mkdir(parents=True,exist_ok=True)
    dest=where/name
    dest.write_bytes(data)
    provenance={"path":str(dest),"label":entry["label"],"url":entry["url"],
        "response_url":entry.get("response_url"),"http_status":entry.get("status"),
        "content_type":entry.get("content_type"),"content_length":entry.get("content_length"),
        "retrieval_utc":entry.get("completed_utc"),"bytes":len(data),"sha256":sha(data),
        "hdu_headers":[]}
    try:
        with fits.open(io.BytesIO(data),memmap=False,checksum=False) as hdus:
            for i,h in enumerate(hdus):
                head={
                 "index":i,"name":h.name,"class":type(h).__name__,
                 "header_full_fits_cards":[card.image for card in h.header.cards],
                 "header_keyword_count":len(h.header.cards),
                 "data_shape":list(h.data.shape) if h.data is not None else None,
                 "data_dtype":str(h.data.dtype) if h.data is not None else None,
                 "columns":list(h.columns.names) if isinstance(h,fits.BinTableHDU) else None,
                 "is_mask_or_flag_hdu": any(x in h.name.upper() for x in ("MASK","FLAG","DQ","BADPIX","CRR"))
                }
                provenance["hdu_headers"].append(head)
        provenance["fits_open_success"]=True
    except Exception as e:
        provenance["fits_open_success"]=False
        provenance["fits_open_error"]=repr(e)
    manifest["files"].append(provenance)
    return provenance

try:
    where=ROOT
    where.mkdir(parents=True,exist_ok=True)
    # Verify visit inventory independently, with a tiny, bounded query.
    query="""SELECT TOP 20 sobject_id,gaiadr3_source_id,teff,logg,flag_sp,flag_red
FROM galah_dr4.mainspectable
WHERE gaiadr3_source_id=3064554891927687296
ORDER BY gaiadr3_source_id,sobject_id"""
    u=TAP+"?"+urllib.parse.urlencode({"REQUEST":"doQuery","LANG":"ADQL","FORMAT":"csv","QUERY":query,"MAXREC":"21"})
    csv,ent=request_bytes("two-target all-visits catalogue",u,25000)
    if csv is None: raise RuntimeError("Cannot verify observation completeness against GALAH DR4")
    (ROOT/"galah_dr4_two_target_all_visits_raw.csv").write_bytes(csv)
    manifest["catalog_request_sha256"]=sha(csv)
    manifest["catalog_request_adql"]=query
    import csv as csvmod
    rows=list(csvmod.DictReader(io.StringIO(csv.decode("utf-8-sig"))))
    for name,t in TARGETS.items():
        for r in rows:
            if int(r["gaiadr3_source_id"])==t["source_id"]:
                if int(r["flag_sp"])!=0 or int(r["flag_red"])!=0:
                    raise RuntimeError("Ordinary comparison source has nonzero visit-level flags")
        actual=sorted(str(r["sobject_id"]) for r in rows if int(r["gaiadr3_source_id"])==t["source_id"])
        t["catalogued_visits"]=actual
        if sorted(t["visits"])!=actual:raise RuntimeError("Visit list discrepancy: "+name+" "+str(actual))
    # Science bytes for only 3 released visits, four cameras each.
    for name,t in TARGETS.items():
        for visit in t["visits"]:
            sub=ROOT/name/visit
            single_url=f"{BASE}/analysis_products_single/{visit[:6]}/{visit}/{visit}_single_fit_spectrum.fits"
            b,e=request_bytes(f"{visit} allspec observed+model",single_url,6000000)
            if b is not None:
                info=record_file(sub,visit+"_single_fit_spectrum.fits",b,e)
                print(visit,"allspec",len(b),info["fits_open_success"],flush=True)
            else:
                manifest["limitations"].append("allspec failed for "+visit+": "+repr(e.get("error")))
            for num,letter in enumerate(("B","G","R","I"),start=1):
                slink_url=SLINK+"?"+urllib.parse.urlencode({"ID":visit,"DR":"galah_dr4","IDX":0,
                                                             "FILT":letter,"RESPONSEFORMAT":"fits"})
                b,e=request_bytes(f"{visit} per-exposure reduced camera {num} ({letter})",slink_url,6000000)
                if b is not None:
                    info=record_file(sub,visit+str(num)+"_reduced_"+letter+".fits",b,e)
                    print(visit,"camera",num,len(b),info["fits_open_success"],flush=True)
                else:
                    manifest["limitations"].append("camera "+str(num)+" unavailable for "+visit+": "+repr(e.get("error")))
    # A model allspec is not identical to an upstream reduced camera.
    mask_summary=[]
    for f in manifest["files"]:
        hdus=f["hdu_headers"]
        keys=[y["name"] for y in hdus]
        mask_summary.append({"path":f["path"],"hdu_count":len(hdus),"hdu_names":keys,
          "mask_named_hdu_count":sum(int(y["is_mask_or_flag_hdu"]) for y in hdus),
          "fits_ok":f.get("fits_open_success",False)})
    (ROOT/"mask_hdu_summary.json").write_text(json.dumps(mask_summary,indent=2)+"\n")
    manifest["status"]="completed_with_gaps" if manifest["limitations"] else "completed"
except Exception as e:
    manifest["status"]="failed";manifest["error"]=repr(e);manifest["traceback"]=traceback.format_exc()
    print(manifest["traceback"],file=sys.stderr,flush=True)
finally:
    manifest["completed_utc"]=now()
    manifest["total_stored_bytes"]=total[0]
    (ROOT/"FILE_SHA256_AND_HEADERS.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (ROOT/"SHA256SUMS.txt").write_text("".join(f["sha256"]+"  "+f["path"]+"\n" for f in manifest["files"]))
print("completed",manifest["status"],len(manifest["files"]),"FITS, bytes",total[0],flush=True)
if manifest["status"]=="failed": sys.exit(1)
