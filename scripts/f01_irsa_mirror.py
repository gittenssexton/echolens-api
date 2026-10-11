"""F01 IRSA Gaia DR3 mirror retry; bounded 20k frames, no science comparisons."""
import hashlib,gzip,io,json,math,pathlib,urllib.parse,urllib.request,traceback,sys
from datetime import datetime,timezone
import numpy as np
from astropy.io import fits
from astropy.table import Table
OUT=pathlib.Path("f01_irsa_output");OUT.mkdir(exist_ok=True)
BASE="https://irsa.ipac.caltech.edu/TAP/sync"
Q="""SELECT TOP 20000 * FROM gaia_dr3_source
WHERE random_index < 1000000 ORDER BY random_index ASC"""
params={"REQUEST":"doQuery","LANG":"ADQL","FORMAT":"fits","QUERY":Q,"MAXREC":"20001"}
url=BASE+"?"+urllib.parse.urlencode(params)
sha=lambda b:hashlib.sha256(b).hexdigest()
log={"protocol":"CLAUDE_PROTO_F01_SELECTION_BIAS.md 2026-10-11",
"note":"Alternate provider IRSA to avoid slow ESA TAP; comparison hypotheses NOT tested",
"provider":"NASA/IPAC IRSA Gaia DR3 mirror (original pilot provider)","query":Q,
"request_url":url,"requested_top":20000,
"started_utc":datetime.now(timezone.utc).isoformat(),"status":"pending"}
try:
    req=urllib.request.Request(url,headers={"User-Agent":"EchoLens F01 bounded IRSA retry/0.1"})
    with urllib.request.urlopen(req,timeout=570) as r:
        content=r.read(50_000_001)
        log["http_status"]=r.status
        log["response_headers"]={k:v for k,v in r.headers.items() if k.lower() in ("content-type","date","last-modified","etag")}
    if len(content)>50_000_000: raise ValueError("Safety cap: 50 MB")
    if not (content.startswith(b"SIMPLE") or content.startswith(bytes([31,139]))):raise ValueError("Response not FITS/gzip")
    (OUT/"f01_unfiltered_20000_irsa.fits").write_bytes(content)
    log["raw_sha256"]=sha(content);log["bytes"]=len(content)
    with fits.open(io.BytesIO(content),memmap=False) as h:
        t=h[1].data
        names=h[1].columns.names
        i=np.asarray(t["random_index"],dtype=np.int64)
        ids=np.asarray(t["source_id"],dtype=np.int64)
        assert 0<len(ids)<=20000 and len(set(map(int,ids)))==len(ids)
        assert np.all(i<1000000) and np.all(i[1:]>=i[:-1])
        def nums(k):
            a=t[k]
            return np.asarray(a.filled(np.nan) if np.ma.isMaskedArray(a) else a,dtype=float)
        p=nums("classprob_dsc_combmod_star")
        quality=np.isfinite(nums("parallax_over_error"))&(nums("parallax_over_error")>=5)
        quality &= nums("ruwe")<1.4
        quality &= nums("phot_g_mean_mag")<17.65
        for k in ("phot_bp_mean_mag","phot_rp_mean_mag"):
            quality &= np.isfinite(nums(k))
        status={"rows":len(ids),"columns":len(names),"unique_ids":True,
        "star_prob_gte_0_9":int((np.isfinite(p)&(p>=.9)).sum()),
        "star_prob_lt_0_9":int((np.isfinite(p)&(p<.9)).sum()),
        "star_prob_null_or_nonfinite":int((~np.isfinite(p)).sum()),
        "quality_frame_total":int(quality.sum()),
        "quality_gte_0_9":int((quality&np.isfinite(p)&(p>=.9)).sum()),
        "quality_lt_0_9":int((quality&np.isfinite(p)&(p<.9)).sum()),
        "quality_prob_missing":int((quality&~np.isfinite(p)).sum()),
        "random_index_min":int(i.min()),"random_index_max":int(i.max()),
        "photometric_outlier_metric_frozen":False,
        "WISE_photometry_complete":False}
        # Validate overlap against frozen Gaia DR3 pilot if present.
        raw=(pathlib.Path("data")/"gaia_dr3.raw.gz")
        if raw.exists():
            with gzip.open(raw,"rb") as f:pb=f.read()
            with fits.open(io.BytesIO(pb),memmap=False) as hh:
                r=hh[1].data
                idx={int(z):j for j,z in enumerate(ids)}
                matches=[x for x in r if int(x["source_id"]) in idx]
                eligible=[x for x in r if int(x["random_index"])<=int(i.max())]
                diff=[]
                for z in matches:
                    a=t[idx[int(z["source_id"])]]
                    for key in ("ra","dec","parallax","classprob_dsc_combmod_star","random_index"):
                        old=float(z[key]);new=float(a[key])
                        if (math.isnan(old) and math.isnan(new)) or math.isclose(old,new,rel_tol=1e-7,abs_tol=1e-6):continue
                        if len(diff)<15:diff.append({"id":int(z["source_id"]),"field":key,"pilot":old,"new":new})
                status["frozen_pilot_overlap"]={"pilot_raw_sha256":sha(pb),"within_frame":len(eligible),
                "matched":len(matches),"missing":len(eligible)-len(matches),"value_differences":diff}
    (OUT/"f01_irsa_validation.json").write_text(json.dumps(status,indent=2)+"\n")
    print("F01 IRSA received",status["rows"],"with",status["columns"],"columns",flush=True)
    print(json.dumps(status["frozen_pilot_overlap"]),flush=True)
    # Small, explicitly exploratory AllWISE IRSA photometry query; no bulk download.
    # A positional cone does NOT replace Gaia's official best-neighbour matching.
    subset=[]
    for j in np.flatnonzero(quality)[:8]:
        subset.append({"source_id":int(ids[j]),"ra":float(nums("ra")[j]),"dec":float(nums("dec")[j])})
    wise_results=[]
    for row in subset:
        cone=f"SELECT TOP 8 designation,ra,dec,w1mpro,w1sigmpro,w2mpro,w2sigmpro,w3mpro,w3sigmpro,w4mpro,w4sigmpro,w3snr,w4snr,cc_flags,ext_flg,ph_qual FROM allwise_p3as_psd WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{row['ra']},{row['dec']},0.000556))=1"
        wise_url="https://irsa.ipac.caltech.edu/TAP/sync?"+urllib.parse.urlencode({"REQUEST":"doQuery","LANG":"ADQL","FORMAT":"csv","QUERY":cone,"MAXREC":"9"})
        item={"gaia_source_id":row["source_id"],"adql":cone,"url":wise_url}
        try:
            with urllib.request.urlopen(wise_url,timeout=85) as response:
                data=response.read(30000)
                item["raw_csv"]=data.decode("utf-8","replace")
                item["response_sha256"]=sha(data)
                item["retrieved_utc"]=datetime.now(timezone.utc).isoformat()
                item["http_status"]=response.status
        except Exception as e:item["error"]=repr(e)
        wise_results.append(item)
    (OUT/"allwise_photometry_exploratory_8.json").write_text(json.dumps({
        "method":"2-arcsecond positional cone on first 8 quality-frame Gaia sources; no proper-motion propagation; NOT verified official best neighbours",
        "survey":"AllWISE Source Catalog (NASA/IPAC IRSA)",
        "results":wise_results,"hypotheses_tested":False},indent=2)+"\n")
    log["status"]="gaia_acquired_validated_allwise_exploratory_queried"
except Exception as e:
    log["status"]="failed";log["error"]=repr(e);log["traceback"]=traceback.format_exc()
    print(log["traceback"],file=sys.stderr,flush=True)
finally:
    log["completed_utc"]=datetime.now(timezone.utc).isoformat()
    (OUT/"f01_irsa_manifest.json").write_text(json.dumps(log,indent=2)+"\n")
if log["status"]=="failed":sys.exit(1)
