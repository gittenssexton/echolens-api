"""GALAH DR4: bounded endpoint discovery only; NO spectra or bulk catalog downloads."""
from datetime import datetime,timezone
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from pathlib import Path
import json,traceback
root=Path("galah_probe");root.mkdir(exist_ok=True)
urls=[
 ("root","https://cloud.datacentral.org.au/teamdata/GALAH/public/GALAH_DR4/"),
 ("single_root","https://cloud.datacentral.org.au/teamdata/GALAH/public/GALAH_DR4/analysis_products_single/"),
 ("date","https://cloud.datacentral.org.au/teamdata/GALAH/public/GALAH_DR4/analysis_products_single/140116/"),
 ("example_dir","https://cloud.datacentral.org.au/teamdata/GALAH/public/GALAH_DR4/analysis_products_single/140116/140116004301057/"),
 ("example_allspec","https://cloud.datacentral.org.au/teamdata/GALAH/public/GALAH_DR4/analysis_products_single/140116/140116004301057/140116004301057_spectrum.fits"),
 ("reduced_parent","https://cloud.datacentral.org.au/teamdata/GALAH/public/GALAH_DR4/observations/"),
 ("example_reduced","https://cloud.datacentral.org.au/teamdata/GALAH/public/GALAH_DR4/observations/140116/spectra/com/1401160043010571.fits"),
 ("galah_dr3_example","https://cloud.datacentral.org.au/teamdata/GALAH/public/GALAH_DR3/spectra/"),
 ("tap_available","https://datacentral.org.au/vo/tap/availability"),
 ("tap_tables","https://datacentral.org.au/vo/tap/tables"),
 ("query_service","https://datacentral.org.au/services/query/"),
]
adql="SELECT TOP 1 sobject_id,teff,logg,fe_h,phot_g_mean_mag,flag_sp FROM galah_dr4.allstar WHERE teff BETWEEN 5500 AND 6000 AND logg BETWEEN 4.2 AND 4.65 AND flag_sp=0"
for host in ("https://datacentral.org.au/vo/tap/sync","https://data.datacentral.org.au/vo/tap/sync",
             "https://datacentral.org.au/vo/tap/"):
    urls.append(("tiny_adql_"+host.split("//")[1].replace("/","_"),host+"?"+urlencode({"REQUEST":"doQuery","LANG":"ADQL","FORMAT":"csv","QUERY":adql,"MAXREC":2})))
urls.append(("galah_tables", "https://datacentral.org.au/vo/tap/sync?"+urlencode({"REQUEST":"doQuery","LANG":"ADQL","FORMAT":"csv","QUERY":"SELECT TOP 15 table_name FROM TAP_SCHEMA.tables WHERE table_name LIKE '%galah%'","MAXREC":16})))
result={"started_utc":datetime.now(timezone.utc).isoformat(),"requests":[]}
for name,url in urls:
    item={"name":name,"url":url}
    result["requests"].append(item)
    for method in (("HEAD",) if "fits" in name or name=="example_reduced" else ("GET",)):
        try:
            with urlopen(Request(url,method=method,headers={"User-Agent":"EchoLens DR4 one-star audit research"}),timeout=26) as r:
                item["status"]=r.status
                item["final_url"]=r.url
                item["content_type"]=r.headers.get("Content-Type")
                item["content_length"]=r.headers.get("Content-Length")
                if method=="GET":
                    data=r.read(90000)
                    item["sample_first_2000"]=data[:2000].decode("utf-8","replace")
            break
        except Exception as e:
            item["error"]=str(e)
            if isinstance(e,HTTPError):
                item["error_body"]=e.read(5000).decode("utf-8","replace")
    print(name,item.get("status"),item.get("error",""), item.get("error_body","")[:500], flush=True)
result["finished_utc"]=datetime.now(timezone.utc).isoformat()
(root/"network_probes.json").write_text(json.dumps(result,indent=2)+"\n")
