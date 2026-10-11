"""GALAH DR4 bounded target selection: 1 FGK dwarf + 1 published Ba control."""
import json,urllib.parse,urllib.request,traceback
from pathlib import Path
from datetime import datetime,timezone
out=Path("galah_target_selection");out.mkdir(exist_ok=True)
url="https://datacentral.org.au/vo/tap/sync"
cols="sobject_id,gaiadr3_source_id,teff,logg,fe_h,phot_g_mean_mag,snr_px_ccd1,snr_px_ccd2,snr_px_ccd3,snr_px_ccd4,flag_sp,flag_red,ba_fe,la_fe,flag_ba_fe,flag_la_fe,ra,dec"
queries={
"fgk_dwarf":f"""SELECT TOP 8 {cols} FROM galah_dr4.mainstartable
WHERE teff BETWEEN 5500 AND 6200 AND logg BETWEEN 4.20 AND 4.65
AND flag_sp=0 AND snr_px_ccd3>60 AND phot_g_mean_mag BETWEEN 9 AND 12.5
ORDER BY phot_g_mean_mag ASC""",
"ba_known":f"""SELECT TOP 8 {cols} FROM galah_dr4.mainstartable
WHERE gaiadr3_source_id=6053735173729807872""",
"ba_visits":"""SELECT TOP 25 sobject_id,gaiadr3_source_id,teff,logg,phot_g_mean_mag,flag_sp FROM galah_dr4.mainspectable
WHERE gaiadr3_source_id=6053735173729807872 ORDER BY sobject_id ASC"""
}
report={"source":"AAO Data Central GALAH DR4 TAP","endpoint":url,
"external_catalog":"Yang et al. 2026, arXiv:2602.21014 (Ba star Gaia DR3 6053735173729807872)",
"started_utc":datetime.now(timezone.utc).isoformat(),"queries":{}}
for name,adql in queries.items():
    p={"REQUEST":"doQuery","LANG":"ADQL","FORMAT":"csv","QUERY":adql,"MAXREC":"26"}
    qurl=url+"?"+urllib.parse.urlencode(p)
    record={"adql":adql,"request_url":qurl}
    report["queries"][name]=record
    try:
        with urllib.request.urlopen(urllib.request.Request(qurl,headers={"User-Agent":"EchoLens GALAH DR4 single-star selection"}),timeout=100) as resp:
            b=resp.read(50000)
            record["http_status"]=resp.status
            record["retrieved_utc"]=datetime.now(timezone.utc).isoformat()
            record["body"]=b.decode("utf-8","replace")
            record["bytes"]=len(b)
            (out/(name+".csv")).write_bytes(b)
        print(name,record["body"][:4000],flush=True)
    except Exception as exc:
        record["error"]=repr(exc)
        if isinstance(exc,urllib.error.HTTPError):
            record["error_body"]=exc.read(7000).decode("utf-8","replace")
        print(name,record.get("error_body",record["error"]),flush=True)
report["completed_utc"]=datetime.now(timezone.utc).isoformat()
(out/"selection_provenance.json").write_text(json.dumps(report,indent=2)+"\n")
