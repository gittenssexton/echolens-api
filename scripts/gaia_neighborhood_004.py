"""Experiment 004: Gaia DR3 neighborhood candidates near published LAMOST positions.

Only --fetch contacts IRSA; immutable source observations are not modified.
This pilot never asserts an observing-epoch-corrected stellar crossmatch.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import tempfile
import urllib.parse
import urllib.request

from scripts.import_gaia import parse_votable

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs" / "EXPERIMENT_004.md"
WORK = ROOT / "data" / "gaia_neighbors_004"
ENDPOINT = "https://irsa.ipac.caltech.edu/TAP/sync"
FLAGGED_OBSID = "655310123"
SALT = "echolens-004-v1:"
COUNT = 25
RADIUS_ARCSEC = 12.
COLUMNS = (
    "source_id", "ra", "dec", "ref_epoch", "pmra", "pmdec", "ra_error",
    "dec_error", "pmra_error", "pmdec_error", "parallax", "parallax_error",
    "phot_g_mean_mag", "phot_g_mean_flux_error", "ruwe",
    "duplicated_source", "non_single_star"
)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def read_json(path):
    raw = Path(path).read_bytes()
    return json.loads(raw), digest(raw)


def decimal_id(value):
    s = str(value)
    if not s.isascii() or not s.isdigit() or not 0 < int(s) < 2**63:
        raise ValueError("Invalid exact Gaia identifier")
    return s


def separation_arcsec(ra1, dec1, ra2, dec2):
    r1, d1, r2, d2 = map(math.radians,(ra1,dec1,ra2,dec2))
    h = math.sin((d1-d2)/2)**2 + math.cos(d1)*math.cos(d2)*math.sin((r1-r2)/2)**2
    return math.degrees(2*math.asin(math.sqrt(max(0,min(1,h)))))*3600


def frozen_selection(lamost_path, gaia_path):
    lamost, lhash = read_json(lamost_path)
    audit, ahash = read_json(gaia_path)
    if lamost.get("experiment") != "003" or audit.get("experiment") != "003G":
        raise ValueError("Expected frozen LAMOST 003 and Gaia 003G results")
    spectra = lamost.get("records", [])
    matched = audit.get("sources", [])
    if len(spectra) != 250 or len(matched) != 250:
        raise ValueError("Original sample must have 250 observations each")
    lookup = {}
    for item in matched:
        sid = decimal_id(item["gaia_dr3_source_id"])
        obsid = str(item["lamost_obsid"])
        if obsid in lookup:
            raise ValueError("Duplicated original Gaia audit obsid")
        if not item["gaia_record"] or decimal_id(item["gaia_record"]["source_id"]) != sid:
            raise ValueError("Original published Gaia identifier unresolved")
        lookup[obsid] = item
    spectra_by = {}
    for entry in spectra:
        obsid = str(entry["lamost_obsid"])
        sid = decimal_id(entry["gaia_dr3_id_provisional"])
        if obsid in spectra_by or obsid not in lookup or sid != lookup[obsid]["gaia_dr3_source_id"]:
            raise ValueError("LAMOST-to-Gaia snapshot identity mismatch")
        spectra_by[obsid] = entry
    if FLAGGED_OBSID not in spectra_by:
        raise ValueError("Known review target missing")
    other = sorted((x for x in spectra_by if x != FLAGGED_OBSID),
          key=lambda oid:(digest((SALT+oid).encode("ascii")),int(oid)))
    selected = [FLAGGED_OBSID]+other[:COUNT-1]
    items = []
    for oid in selected:
        entry = spectra_by[oid]["published_raw_row"]
        ra, dec = entry["RAJ2000"], entry["DEJ2000"]
        if not (isinstance(ra,(float,int)) and isinstance(dec,(float,int))
                and math.isfinite(ra) and math.isfinite(dec) and 0<=ra<360 and -90<=dec<=90):
            raise ValueError("Invalid published LAMOST coordinate")
        items.append({
            "obsid":oid, "gaia_dr3_source_id":decimal_id(spectra_by[oid]["gaia_dr3_id_provisional"]),
            "catalog_ra_deg":ra, "catalog_dec_deg":dec,
            "catalog_G_mag":entry.get("Gmag"),
            "gaia_ref_epoch":lookup[oid]["gaia_record"]["ref_epoch"],
            "gaia_original_source":lookup[oid]["gaia_record"],
            "review_target_selected":oid==FLAGGED_OBSID,
        })
    return {"experiment":"004", "protocol_sha256":digest(PROTOCOL.read_bytes()),
            "lamost_results_sha256":lhash, "gaia_003g_results_sha256":ahash,
            "selection_salt":SALT,"review_obsid":FLAGGED_OBSID,
            "cone_radius_arcsec":RADIUS_ARCSEC,"target_count":COUNT,"targets":items,
            "caution":"Published J2000 sky position, NOT confirmed fiber position at actual observing date."}


def query_for(t):
    ra,dec=t["catalog_ra_deg"],t["catalog_dec_deg"]
    if not (0<=ra<360 and -90<=dec<=90):
        raise ValueError("Invalid cone")
    radius=RADIUS_ARCSEC/3600
    return ("SELECT TOP 1000 " + ", ".join(COLUMNS) +
        " FROM gaia_dr3_source WHERE 1=CONTAINS(POINT('ICRS',ra,dec),"
        f"CIRCLE('ICRS',{ra!r},{dec!r},{radius!r})) ORDER BY source_id ASC")


def validate_response(xml, t):
    fields,rows=parse_votable(xml)
    if set(fields) != set(COLUMNS) or len(rows)>=1000:
        raise ValueError("Incomplete schema or capped Gaia result")
    seen=set()
    ordered=[]
    for r in rows:
        sid=decimal_id(r["source_id"])
        if sid in seen: raise ValueError("Duplicate Gaia catalog source")
        seen.add(sid)
        if not (0<=r["ra"]<360 and -90<=r["dec"]<=90):
            raise ValueError("Out-of-sky Gaia coordinate")
        for k in ("ra_error","dec_error","pmra_error","pmdec_error","parallax_error","phot_g_mean_flux_error"):
            v=r.get(k)
            if v is not None and (not isinstance(v,(float,int)) or not math.isfinite(v) or v<0):
                raise ValueError("Invalid Gaia uncertainty")
        if separation_arcsec(t["catalog_ra_deg"],t["catalog_dec_deg"],r["ra"],r["dec"])>RADIUS_ARCSEC+0.01:
            raise ValueError("IRSA result outside cone")
        r["source_id"]=sid
        ordered.append(int(sid))
    if ordered != sorted(ordered):
        raise ValueError("Catalog source IDs are not sorted")
    return fields,rows


def fetch(directory, selection):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    f=directory/"selection.json"
    if f.exists() and json.loads(f.read_text())!=selection:
        raise ValueError("Frozen selection mismatch, refuse overwrite")
    f.write_text(json.dumps(selection,indent=2)+"\n")
    entries=[];meta=None
    for idx,t in enumerate(selection["targets"]):
        query=query_for(t)
        params={"REQUEST":"doQuery","LANG":"ADQL","FORMAT":"votable",
                "QUERY":query,"MAXREC":"1001"}
        rawfile=directory/f"cone_{idx:02d}.xml.gz"
        recfile=directory/f"cone_{idx:02d}.json"
        if rawfile.exists() and recfile.exists():
            xml=gzip.decompress(rawfile.read_bytes())
            r=json.loads(recfile.read_text())
            if r["query"]!=query or r["raw_sha256"]!=digest(xml):
                raise ValueError("Corrupt archive/retrieval mismatch")
        else:
            request=urllib.request.Request(ENDPOINT,data=urllib.parse.urlencode(params).encode(),
                headers={"User-Agent":"EchoLens-neighborhood-pilot-004",
                        "Content-Type":"application/x-www-form-urlencoded"},method="POST")
            with urllib.request.urlopen(request,timeout=150) as response:
                xml=response.read()
                headers={key:response.headers.get(key) for key in
                         ("Content-Type","Date","ETag","Last-Modified")}
            r={"obsid":t["obsid"],"gaia_id":t["gaia_dr3_source_id"],
               "query":query,"parameters":params,"endpoint":ENDPOINT,
               "retrieved_utc":datetime.now(timezone.utc).isoformat(),
               "raw_sha256":digest(xml),"response_headers":headers}
        fields,rows=validate_response(xml,t)
        if meta is None:meta=fields
        elif meta!=fields:raise ValueError("Field metadata changed across Gaia cones")
        r["row_count"]=len(rows)
        if not rawfile.exists():
            rawfile.write_bytes(gzip.compress(xml,mtime=0))
            recfile.write_text(json.dumps(r,indent=2)+"\n")
        entries.append(r)
        print(f"Gaia cone {idx+1}/{COUNT}: {len(rows)} real catalog sources",flush=True)
    (directory/"manifest.json").write_text(json.dumps({
        "experiment":"004","selection":selection,"catalog":"Gaia DR3",
        "provider":"NASA/IPAC IRSA","native_format":"VOTable","field_metadata":meta,
        "replies":entries},indent=2)+"\n")


def replay(directory,selection,output):
    directory=Path(directory);output=Path(output)
    if json.loads((directory/"selection.json").read_text())!=selection:
        raise ValueError("Frozen source IDs/protocol have changed")
    manifest=json.loads((directory/"manifest.json").read_text())
    if manifest["selection"]!=selection or len(manifest["replies"])!=COUNT:
        raise ValueError("Acquisition manifest mismatch")
    summary=[];all_ids=set();nearer=0;absent=0
    for idx,(target,rec) in enumerate(zip(selection["targets"],manifest["replies"])):
        if rec["query"]!=query_for(target) or rec["obsid"]!=target["obsid"]:
            raise ValueError("Archive query mismatch")
        xml=gzip.decompress((directory/f"cone_{idx:02d}.xml.gz").read_bytes())
        if digest(xml)!=rec["raw_sha256"]: raise ValueError("Archived Gaia bytes changed")
        fields,rows=validate_response(xml,target)
        if fields!=manifest["field_metadata"] or len(rows)!=rec["row_count"]:
            raise ValueError("Inconsistent Gaia catalog fields/count")
        candidates=[]
        for r in rows:
            sid=r["source_id"]
            all_ids.add(sid)
            sep=separation_arcsec(target["catalog_ra_deg"],target["catalog_dec_deg"],r["ra"],r["dec"])
            dg=None
            if target["catalog_G_mag"] is not None and r.get("phot_g_mean_mag") is not None:
                dg=abs(target["catalog_G_mag"]-r["phot_g_mean_mag"])
            candidates.append({"gaia_source_id":sid, "separation_arcsec":round(sep,4),
                "magnitude_difference":round(dg,4) if dg is not None else None,
                "pm_available":all(r.get(k) is not None for k in
                                     ("pmra","pmdec","pmra_error","pmdec_error")),
                "published_source_id":sid==target["gaia_dr3_source_id"],
                "original_gaia_record":r, "_separation_exact":sep})
        candidates.sort(key=lambda r:(r["_separation_exact"],int(r["gaia_source_id"])))
        published=next((r for r in candidates if r["published_source_id"]),None)
        closer=bool(published and any(c["_separation_exact"]+1e-9 < published["_separation_exact"]
                                          for c in candidates if not c["published_source_id"]))
        if published is None:status="published_id_absent_in_12_arcsec_cone";absent+=1
        elif closer:status="published_id_not_nearest";nearer+=1
        else:status="published_id_nearest"
        neighbor_counts={f"{n}_arcsec":sum(c["_separation_exact"] <= n and not c["published_source_id"]
                           for c in candidates) for n in (1,3,6,12)}
        for c in candidates:del c["_separation_exact"]
        summary.append({"obsid":target["obsid"],"published_gaia_source_id":target["gaia_dr3_source_id"],
            "known_flagged_target":target["review_target_selected"],
            "classification":status,"other_gaia_closer":closer,
            "published_offset_arcsec":published["separation_arcsec"] if published else None,
            "nearest_gaia_id":candidates[0]["gaia_source_id"] if candidates else None,
            "second_nearest_offset_arcsec":candidates[1]["separation_arcsec"] if len(candidates)>1 else None,
            "other_neighbor_counts":neighbor_counts,"all_candidates":candidates})
    result={"experiment":"004", "input_provenance":{k:v for k,v in selection.items()
            if k in ("protocol_sha256","lamost_results_sha256","gaia_003g_results_sha256")},
        "gaia_archive_raw_hashes":[r["raw_sha256"] for r in manifest["replies"]],
        "target_count":COUNT,"unique_gaia_sources_retrieved":len(all_ids),
        "published_id_nearest":COUNT-nearer-absent,
        "published_id_not_nearest":nearer,
        "published_id_absent":absent,"targets":summary,
        "interpretation":"Neighborhood ambiguity triage only: no epoch-corrected fiber match or astrophysical anomaly assertion."}
    output.mkdir(parents=True,exist_ok=True)
    (output/"results.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:result[k] for k in ("target_count","unique_gaia_sources_retrieved",
                        "published_id_nearest","published_id_not_nearest","published_id_absent")},indent=2))
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lamost-results",required=True)
    ap.add_argument("--gaia-results",required=True)
    ap.add_argument("--directory",default=str(WORK))
    ap.add_argument("--output",default="reports/experiment_004")
    ap.add_argument("--fetch",action="store_true",help="Explicit network fetch")
    args=ap.parse_args()
    selected=frozen_selection(args.lamost_results,args.gaia_results)
    if args.fetch:fetch(args.directory,selected)
    replay(args.directory,selected,args.output)


if __name__=="__main__":
    main()
