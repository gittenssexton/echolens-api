"""Read-only EchoLens F01 archive acquisition. Output is never an anomaly score."""
from __future__ import annotations
import gzip, hashlib, io, json, math, os, pathlib, sys, traceback, urllib.parse, urllib.request
from datetime import datetime, timezone
import numpy as np
from astropy.io import fits

ROOT = pathlib.Path("f01_output")
ROOT.mkdir(exist_ok=True)
TAP = "https://gea.esac.esa.int/tap-server/tap/sync"
QUERY = """SELECT TOP 20000 *
FROM gaiadr3.gaia_source
WHERE random_index < 1000000
ORDER BY random_index ASC"""
WISE = """SELECT TOP 20000 g.source_id, g.random_index,
w.original_ext_source_id, w.angular_distance, w.xm_flag,
w.allwise_oid, w.number_of_neighbours, w.number_of_mates
FROM gaiadr3.gaia_source AS g
LEFT OUTER JOIN gaiadr3.allwise_best_neighbour AS w
ON g.source_id = w.source_id
WHERE g.random_index < 1000000
ORDER BY g.random_index ASC"""
META = """SELECT column_name, unit, ucd, description, datatype
FROM TAP_SCHEMA.columns
WHERE table_name = 'gaiadr3.gaia_source'"""
manifest = {
    "protocol": "CLAUDE_PROTO_F01_SELECTION_BIAS.md (2026-10-11)",
    "archive": "ESA Gaia DR3 Archive",
    "endpoint": TAP,
    "sample_is_not_population_representative": True,
    "purpose": "unfiltered F01 selection-frame acquisition; no anomaly test performed",
    "started_utc": datetime.now(timezone.utc).isoformat(),
    "requests": [], "status": "running",
    "attribution": "ESA/Gaia/DPAC, Gaia DR3; original pilot served by NASA/IPAC IRSA"
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def acquire(name, query, fmt, filename):
    params = {"REQUEST":"doQuery", "LANG":"ADQL",
              "FORMAT":fmt, "QUERY":query, "MAXREC":"20001"}
    data = urllib.parse.urlencode(params).encode()
    log = {"name":name, "adql":query, "method":"POST",
           "parameter_names":list(params), "format":fmt,
           "started_utc":datetime.now(timezone.utc).isoformat()}
    manifest["requests"].append(log)
    request = urllib.request.Request(
        TAP, data=data, method="POST",
        headers={"User-Agent":"EchoLens-F01/0.1 (academic provenance audit)",
                 "Content-Type":"application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(request, timeout=620) as response:
            raw = response.read()
            log["http_status"] = response.status
            log["response_url"] = response.url
            log["headers"] = {k:v for k,v in response.headers.items()
                              if k.lower() in ("content-type","date","last-modified","etag")}
        out = ROOT / filename
        out.write_bytes(raw)
        log["sha256"] = sha(raw)
        log["bytes"] = len(raw)
        log["retrieved_utc"] = datetime.now(timezone.utc).isoformat()
        log["file"] = filename
        print(name, len(raw), log["sha256"], flush=True)
        return out
    except Exception as exc:
        log["error"] = repr(exc)
        raise

def numeric(data, key):
    col = data[key]
    if np.ma.isMaskedArray(col):
        return np.asarray(col.filled(np.nan), dtype=float)
    return np.asarray(col, dtype=float)

try:
    raw_path = acquire("F01-unfiltered", QUERY, "fits", "gaia_dr3_f01_unfiltered.fits")
    with fits.open(raw_path, memmap=True) as h:
        x = h[1].data
        ids = np.asarray(x["source_id"],dtype=np.int64).copy()
        ix = np.asarray(x["random_index"],dtype=np.int64).copy()
        assert len(ids)>0, "Empty response"
        assert len(ids)<=20000, "TAP returned more than TOP limit"
        assert len(np.unique(ids))==len(ids), "Duplicate Gaia source ID"
        assert np.all(ix < 1000000), "Out-of-frame random_index"
        assert np.all(ix[1:] >= ix[:-1]), "Not ordered by random_index"
        p = numeric(x,"classprob_dsc_combmod_star")
        star = np.isfinite(p)&(p>=.9)
        low = np.isfinite(p)&(p<.9)
        missing = ~np.isfinite(p)
        eligible=(numeric(x,"parallax_over_error")>=5)&(numeric(x,"ruwe")<1.4)
        for key in ("phot_bp_mean_mag","phot_rp_mean_mag","phot_g_mean_mag"):
            eligible &= np.isfinite(numeric(x,key))
        eligible &= numeric(x,"phot_g_mean_mag") < 17.65
        quality={"total":int(len(ids)),
                 "star_prob_ge_0_9":int(star.sum()),
                 "star_prob_lt_0_9":int(low.sum()),
                 "star_prob_null_or_nonfinite":int(missing.sum()),
                 "quality_frame_total":int(eligible.sum()),
                 "quality_frame_ge_0_9":int((eligible&star).sum()),
                 "quality_frame_lt_0_9":int((eligible&low).sum()),
                 "quality_frame_null":int((eligible&missing).sum())}
        validation={"selection":quality,"random_index_max":int(ix.max()),
                    "random_index_min":int(ix.min()),
                    "field_count":len(h[1].columns.names),
                    "field_names":list(h[1].columns.names),
                    "source_ids_unique":True,"sort_order_valid":True,
                    "allwise_photometry_retrieved":False,
                    "p1_p2_p3_hypotheses_tested":False}
        # Main registry frozen pilot is an independent IRSA observation.
        # Compare only source IDs within the TOP 20000 window.
        pilot_path=pathlib.Path("data/gaia_dr3.raw.gz")
        if pilot_path.exists():
            with gzip.open(pilot_path,"rb") as f:
                pilotbytes=f.read()
            with fits.open(io.BytesIO(pilotbytes),memmap=False) as ph:
                pilot=ph[1].data
                eligible_pilot=[r for r in pilot if int(r["random_index"])<=int(ix.max())]
                lookup={int(src):j for j,src in enumerate(ids)}
                overlap=[r for r in eligible_pilot if int(r["source_id"]) in lookup]
                missing_pilot=len(eligible_pilot)-len(overlap)
                mismatches=[]
                fields=["ra","dec","parallax","phot_g_mean_mag","bp_rp",
                        "classprob_dsc_combmod_star","random_index"]
                for r in overlap:
                    n=x[lookup[int(r["source_id"])]]
                    for field in fields:
                        a=float(r[field]); b=float(n[field])
                        if (math.isnan(a) and math.isnan(b)) or math.isclose(a,b,rel_tol=1e-7,abs_tol=1e-6):
                            continue
                        if len(mismatches)<30:
                            mismatches.append({"source_id":int(r["source_id"]),
                                               "field":field,"pilot":a,"f01":b})
                validation["pilot_crosscheck"]={
                    "pilot_sha256":sha(pilotbytes),"eligible_in_sample_window":len(eligible_pilot),
                    "overlap":len(overlap),"missing":missing_pilot,
                    "measurement_mismatches_first_30":mismatches}
                if missing_pilot or mismatches:
                    validation["pilot_crosscheck"]["warning"]="Independent archive discrepancy: review before analysis"
    metadata_path=acquire("Gaia-source-column-metadata",META,"csv","gaia_dr3_f01_column_metadata.csv")
    wise_path=acquire("F01-AllWISE-best-neighbour",WISE,"fits","gaia_dr3_f01_allwise_best_neighbour.fits")
    with fits.open(wise_path,memmap=True) as h:
        y=h[1].data
        y_ids=np.asarray(y["source_id"],dtype=np.int64)
        y_index=np.asarray(y["random_index"],dtype=np.int64)
        if not np.array_equal(ids,y_ids) or not np.array_equal(ix,y_index):
            raise RuntimeError("AllWISE join row IDs/order differ from unfiltered frame")
        wise_id=y["original_ext_source_id"]
        matched=np.count_nonzero([bool(str(z).strip()) for z in wise_id])
        validation["allwise"]={
            "rows":int(len(y)),"matched_source_id_count":int(matched),
            "unmatched_count":int(len(y)-matched),
            "no_W3_W4_photometry_in_best_neighbour":True,
            "note":"External AllWISE photometry/flags require a separate catalog query."
        }
    (ROOT/"F01_validation.json").write_text(json.dumps(validation,indent=2,default=str)+"\n")
    manifest["status"]="acquired_validated"
except Exception as exc:
    manifest["status"]="failed"
    manifest["error"]=repr(exc)
    manifest["traceback"]=traceback.format_exc()
    print(manifest["traceback"],file=sys.stderr,flush=True)
finally:
    manifest["completed_utc"]=datetime.now(timezone.utc).isoformat()
    (ROOT/"F01_acquisition_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
print("F01 status:",manifest["status"],flush=True)
if manifest["status"]!="acquired_validated":
    sys.exit(1)
