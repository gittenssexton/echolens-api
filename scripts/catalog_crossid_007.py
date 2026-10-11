"""Experiment 007: frozen Gaia DR3 source-ID conflicts and ESA DR8 coverage.

Only --fetch uses public, documented TAP endpoints. Original observations and
uncertainties are never overwritten. No ordinary-star or anomaly labels.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import urllib.parse
import urllib.request

from scripts.import_gaia import parse_votable

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=ROOT/"docs/EXPERIMENT_007.md"
SOURCE_006B_SHA="73b2dbf80ff591d42386c4149dcea1e0ca2225569728dd94c8efacb7609b4fa7"
SOURCE_003G_SHA="d11e0c62eaa8aa26b2fe92fc30b0ca93891459caf4878d89cf2285fc0527a748"
ESO="https://sky.esa.int/esasky-tap/tap/sync"
IRSA="https://irsa.ipac.caltech.edu/TAP/sync"
ESO_TABLE="catalogues.mv_lamost_dr8_lrs_fdw"
GAIA_TABLE="gaia_dr3_source"
PAIRS={
 "235608062":("1215223960901067520","1215223960901067648"),
 "844313076":("2682701860879616256","2682701860880020992")}
MISSING=(
 "52606232","257813193","318809041","447016213","458106245",
 "459815059","475114198","570209101","574314070")
GAIA_COLUMNS=("source_id","ra","dec","ref_epoch","pmra","pmdec",
    "pmra_error","pmdec_error","parallax","parallax_error",
    "phot_g_mean_mag","phot_g_mean_flux_error","bp_rp","ruwe",
    "duplicated_source","non_single_star")
DR8_COLUMNS=("obsid","obsdate","mjd","ra","dec","ra_obs","dec_obs",
             "offsets","offsets_v","gaia_source_id")
QUERY_FIELDS={"gaia":GAIA_COLUMNS,"dr8":DR8_COLUMNS}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def exact_id(value):
    if value is None or isinstance(value,(float,bool)):
        raise ValueError("Missing or float-cast 64-bit source/obsid identifier")
    s=str(value).strip()
    if not s.isascii() or not s.isdigit() or not 0<int(s)<2**63:
        raise ValueError("Invalid decimal exact identifier")
    return s


def original_inputs(esa_path, gaia_path):
    ebytes=Path(esa_path).read_bytes()
    gbytes=Path(gaia_path).read_bytes()
    if sha(ebytes)!=SOURCE_006B_SHA or sha(gbytes)!=SOURCE_003G_SHA:
        raise ValueError("Frozen observation result snapshot SHA-256 mismatch")
    esa=json.loads(ebytes);gaia=json.loads(gbytes)
    if esa["experiment"]!="006B" or gaia["experiment"]!="003G":
        raise ValueError("Wrong original experiment")
    erows={exact_id(s["obsid"]):s for s in esa["sources"]}
    grows={exact_id(s["lamost_obsid"]):s for s in gaia["sources"]}
    if len(erows)!=250 or len(grows)!=250 or len(esa["sources"])!=250:
        raise ValueError("Original 250-source cohort changed")
    for obsid,(native_id,alt_id) in PAIRS.items():
        a,b=erows[obsid],grows[obsid]
        if a["status"]!="esa_observation_found" or a["published_gaia_source_id"]!=native_id:
            raise ValueError("Changed original ESA source discrepancy")
        if a["esa_published_gaia_id_raw"]!=alt_id or b["gaia_dr3_source_id"]!=native_id:
            raise ValueError("Changed original published Gaia ID pair")
    actually_missing=sorted(k for k,v in erows.items() if v["status"]=="missing_in_esa_mirror")
    if actually_missing!=sorted(MISSING):
        raise ValueError("Changed nine absent ESA DR9 observations")
    if erows["655310123"]["esa_published_gaia_id_raw"]!="-9999":
        raise ValueError("Flagged sentinel no longer present in original archive")
    return erows,grows


def frozen_selection():
    return {"experiment":"007","protocol_sha256":sha(PROTOCOL.read_bytes()),
      "input_esa_006b_results_sha256":SOURCE_006B_SHA,
      "input_gaia_003g_results_sha256":SOURCE_003G_SHA,
      "gaia_source_ids":sorted({sid for pair in PAIRS.values() for sid in pair},key=int),
      "lamost_dr8_obsids":sorted(MISSING,key=int),
      "gaia_table":GAIA_TABLE,"dr8_table":ESO_TABLE,
      "reason":"Exact catalog-ID conflict and historical DR8 mirror coverage only"}


def query_for(kind):
    frozen=frozen_selection()
    if kind=="gaia":
        sql=(f"SELECT TOP 100 {', '.join(GAIA_COLUMNS)} FROM {GAIA_TABLE} "
             "WHERE source_id IN ("+",".join(frozen["gaia_source_ids"])+") "
             "ORDER BY source_id ASC")
        return IRSA,sql,frozen["gaia_source_ids"],"source_id"
    if kind=="dr8":
        sql=(f"SELECT TOP 100 {', '.join(DR8_COLUMNS)} FROM {ESO_TABLE} "
             "WHERE obsid IN ("+",".join(frozen["lamost_dr8_obsids"])+") "
             "ORDER BY obsid ASC")
        return ESO,sql,frozen["lamost_dr8_obsids"],"obsid"
    raise ValueError("Unknown catalog kind")


def check_batch(raw,kind):
    fields,rows=parse_votable(raw)
    if set(fields)!=set(QUERY_FIELDS[kind]):
        raise ValueError("Unexpected survey metadata schema")
    _,_,requested,key=query_for(kind)
    if len(rows)>len(requested) or len(rows)>=100:
        raise ValueError("TAP excess rows or cap")
    got=[]
    for row in rows:
        source=exact_id(row[key])
        if source not in requested or source in got:
            raise ValueError("Unexpected or duplicate source identity")
        got.append(source)
        row[key]=source
        for name in (("ra","dec") if kind=="gaia" else
                     ("ra","dec","ra_obs","dec_obs")):
            v=row.get(name)
            if v is not None and (not isinstance(v,(int,float)) or
                                 not math.isfinite(v) or
                                 not (-90<=v<=90 if "dec" in name else 0<=v<360)):
                raise ValueError("Invalid original survey coordinate")
        if kind=="gaia":
            for name in ("pmra_error","pmdec_error","parallax_error",
                         "phot_g_mean_flux_error"):
                v=row.get(name)
                if v is not None and (not isinstance(v,(int,float)) or
                     not math.isfinite(v) or v<0):
                    raise ValueError("Invalid published uncertainty")
            # Gaia's 64-bit exact IDs must stay decimal strings.
            row["source_id"]=source
        else:
            if row.get("gaia_source_id") is not None:
                row["gaia_source_id"]=str(row["gaia_source_id"]).strip()
            off=row.get("offsets")
            if off is not None and off not in (0,1,False,True):
                raise ValueError("DR8 offset flag unsupported")
    if got!=sorted(got,key=int):
        raise ValueError("Unsorted catalog source IDs")
    return fields,rows


def acquire(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    selection=frozen_selection()
    f=folder/"selection.json"
    if f.exists() and json.loads(f.read_text())!=selection:
        raise ValueError("Protocol/data input changed")
    f.write_text(json.dumps(selection,indent=2)+"\n")
    traces={}
    for kind in ("gaia","dr8"):
        endpoint,adql,requested,_=query_for(kind)
        raw_path=folder/(kind+".xml.gz")
        manifest_path=folder/(kind+".json")
        params={"REQUEST":"doQuery","LANG":"ADQL","FORMAT":"votable",
                "QUERY":adql,"MAXREC":"101"}
        if raw_path.exists() and manifest_path.exists():
            raw=gzip.decompress(raw_path.read_bytes())
            trace=json.loads(manifest_path.read_text())
            if trace["adql"]!=adql or trace["raw_sha256"]!=sha(raw):
                raise ValueError("Archived query/source changed")
        else:
            req=urllib.request.Request(endpoint,
                data=urllib.parse.urlencode(params).encode(),method="POST",
                headers={"User-Agent":"EchoLens-007-catalog-reconciliation",
                         "Content-Type":"application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req,timeout=150) as response:
                raw=response.read(3_000_000)
                response_headers={name:response.headers.get(name) for name in
                    ("Date","Content-Type","ETag","Last-Modified")}
                http_status=response.status
            trace={"kind":kind,"adql":adql,"endpoint":endpoint,
                "request_parameters":params,
                "requested_ids":requested,"retrieved_at_utc":datetime.now(timezone.utc).isoformat(),
                "http_status":http_status,"response_headers":response_headers,
                "raw_sha256":sha(raw)}
        fields,rows=check_batch(raw,kind)
        trace["result_rows"]=len(rows)
        trace["native_field_metadata"]=fields
        if not raw_path.exists():
            raw_path.write_bytes(gzip.compress(raw,mtime=0))
            manifest_path.write_text(json.dumps(trace,indent=2)+"\n")
        traces[kind]=trace
        print(f"Validated {kind} TAP: {len(rows)} real sources for {len(requested)} requested IDs",flush=True)
    (folder/"manifest.json").write_text(json.dumps({
        "selection":selection,"responses":traces,
        "note":"Original Gaia DR3 observations and LAMOST DR8 release coverage, not reclassification"
    },indent=2)+"\n")


def sep_arcsec(a,b,c,d):
    ra1,dec1,ra2,dec2=map(math.radians,(a,b,c,d))
    h=math.sin((dec2-dec1)/2)**2+math.cos(dec1)*math.cos(dec2)*math.sin((ra2-ra1)/2)**2
    return math.degrees(2*math.asin(math.sqrt(min(1,max(0,h)))))*3600


def approx_propagate(row,mjd):
    if any(row.get(v) is None for v in ("ra","dec","pmra","pmdec","ref_epoch")) or mjd is None:
        return None
    dt=(float(mjd)-(51544.5+(float(row["ref_epoch"])-2000)*365.25))/365.25
    lat=math.radians(row["dec"])
    if abs(math.cos(lat))<1e-8: return None
    return ((row["ra"]+row["pmra"]*dt/(3_600_000*math.cos(lat)))%360,
           row["dec"]+row["pmdec"]*dt/3_600_000)


def replay(folder, esa_rows, gaia_rows, out):
    folder,out=Path(folder),Path(out)
    f=frozen_selection()
    if json.loads((folder/"selection.json").read_text())!=f:
        raise ValueError("Selection drift")
    man=json.loads((folder/"manifest.json").read_text())
    if man["selection"]!=f:raise ValueError("Manifest changed")
    results={}
    for kind in ("gaia","dr8"):
        url,adql,req,key=query_for(kind)
        rec=man["responses"][kind]
        if rec["adql"]!=adql or rec["endpoint"]!=url or rec["requested_ids"]!=req:
            raise ValueError("Wrong archived exact query")
        raw=gzip.decompress((folder/(kind+".xml.gz")).read_bytes())
        if sha(raw)!=rec["raw_sha256"]:raise ValueError("Raw TAP observations changed")
        fields,rows=check_batch(raw,kind)
        if rec["native_field_metadata"]!=fields or rec["result_rows"]!=len(rows):
            raise ValueError("Native metadata drift")
        results[kind]={r[key]:r for r in rows}
    pairs=[]
    for obsid,(published,alternative) in PAIRS.items():
        esa=esa_rows[obsid]
        gbase=gaia_rows[obsid]["gaia_record"]
        record=esa["esa_record"]
        mjd=record.get("mjd")
        candidates=[]
        for sid in (published,alternative):
            row=results["gaia"].get(sid)
            if row is None:
                candidates.append({"gaia_dr3_source_id":sid,
                    "catalog_role":"VizieR+003G" if sid==published else "ESA DR9 LRS",
                    "gaia_dr3_source_exists":False})
                continue
            coords=((record["ra"],record["dec"]),(record["ra_obs"],record["dec_obs"]))
            propagated=approx_propagate(row,mjd)
            candidates.append({
                "gaia_dr3_source_id":sid,
                "catalog_role":"VizieR+003G" if sid==published else "ESA DR9 LRS",
                "gaia_dr3_source_exists":True,
                "gaia_ref_epoch":row.get("ref_epoch"),
                "input_target_sep_from_gaia_2016_arcsec":round(sep_arcsec(
                    row["ra"],row["dec"],*coords[0]),5),
                "observed_fiber_sep_from_gaia_2016_arcsec":round(sep_arcsec(
                    row["ra"],row["dec"],*coords[1]),5),
                "input_target_sep_after_linear_pm_arcsec":round(sep_arcsec(
                    *propagated,*coords[0]),5) if propagated else None,
                "observed_fiber_sep_after_linear_pm_arcsec":round(sep_arcsec(
                    *propagated,*coords[1]),5) if propagated else None,
                "gaia_G_mag":row.get("phot_g_mean_mag"),
                "gaia_RUWE":row.get("ruwe"),"gaia_pmra":row.get("pmra"),
                "gaia_pmdec":row.get("pmdec"),
                "gaia_original_fields":row,
            })
        pairs.append({"obsid":obsid,"published_gaia_dr3":published,
                      "esa_gaia_dr3":alternative,
                      "esa_obsdate":record.get("obsdate"),"esa_mjd":mjd,
                      "fiber_offset_flag":record.get("offsets"),
                      "fiber_offset_value":record.get("offsets_v"),
                      "candidates":candidates,
                      "status":"requires_independent_source_identity_and_astrometric_review"})
    absent=[{"obsid":sid,"dr9_esa_missing":True,
             "dr8_esa_record_present":sid in results["dr8"],
             "dr8_original_record":results["dr8"].get(sid),
             "interpretation":"DR8 presence is release-coverage evidence, not a DR9 record replacement"}
            for sid in MISSING]
    report={"experiment":"007","experiment_006b_derived_results_sha256":SOURCE_006B_SHA,
        "experiment_003g_derived_results_sha256":SOURCE_003G_SHA,
        "protocol_sha256":f["protocol_sha256"],
        "tap_native_reply_hashes":{k:v["raw_sha256"] for k,v in man["responses"].items()},
        "exact_gaia_ids_requested":len(f["gaia_source_ids"]),
        "exact_gaia_ids_found":len(results["gaia"]),
        "gaia_id_conflicting_obsids":len(PAIRS),
        "dr9_missing_obsids":len(MISSING),
        "dr8_found_among_dr9_missing":len(results["dr8"]),
        "disagreements":pairs,"missing_dr9":absent,
        "gaia_to_lamost_ids_certified":0,
        "interpretation":"Catalog identity and version audit only. Linear PM approximate; no astrophysical normality, anomaly or technosignature claim."
    }
    out.mkdir(parents=True,exist_ok=True)
    (out/"results.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:report[k] for k in ("exact_gaia_ids_requested",
       "exact_gaia_ids_found","gaia_id_conflicting_obsids","dr9_missing_obsids",
       "dr8_found_among_dr9_missing","gaia_to_lamost_ids_certified")},indent=2))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--esa006b-results",required=True)
    p.add_argument("--gaia003g-results",required=True)
    p.add_argument("--directory",default="data/catalog_crossid_007")
    p.add_argument("--output",default="reports/experiment_007")
    p.add_argument("--fetch",action="store_true")
    args=p.parse_args()
    e,g=original_inputs(args.esa006b_results,args.gaia003g_results)
    if args.fetch:acquire(args.directory)
    replay(args.directory,e,g,args.output)


if __name__=="__main__":
    main()
