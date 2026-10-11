"""Experiment 006B: exact-obsid public ESA/LAMOST DR9 dates and fiber offset pilot.

* Real ESA TAP observations, original VOTable preserved with SHA-256.
* Never replace original LAMOST observations / Gaia 2016 data.
* ESA DR9 mirror does not automatically equal original LAMOST DR9 v2.0.
"""
import argparse
from datetime import datetime, timezone, timedelta
import gzip
import hashlib
import json
import math
from pathlib import Path
import urllib.parse
import urllib.request
from scripts.import_gaia import parse_votable

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=ROOT/"docs/EXPERIMENT_006B.md"
ENDPOINT="https://sky.esa.int/esasky-tap/tap/sync"
TABLE="catalogues.mv_lamost_dr9_lrs_fdw"
LAMOST_SHA="efc4f3eaf5f5e1df8b60aa1897ffd93d44c3b05fe69318b27d3769fddb342e51"
GAIA_SHA="d11e0c62eaa8aa26b2fe92fc30b0ca93891459caf4878d89cf2285fc0527a748"
FIELDS=("obsid","obsdate","mjd","ra","dec","ra_obs","dec_obs","offsets",
        "offsets_v","gaia_source_id","gaia_g_mean_mag","designation","snri","snrz")
BATCH=25
PRIORITY="655310123"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def exact_id(value):
    if isinstance(value,float) or isinstance(value,bool) or value is None:
        raise ValueError("Invalid integer ID representation")
    s=str(value).strip()
    if not s.isascii() or not s.isdigit() or not 0<int(s)<2**63:
        raise ValueError("Invalid exact positive source identifier")
    return s


def original_inputs(lamost_file, gaia_file):
    lp, gp=Path(lamost_file).read_bytes(),Path(gaia_file).read_bytes()
    if sha(lp)!=LAMOST_SHA or sha(gp)!=GAIA_SHA:
        raise ValueError("Original archived LAMOST/Gaia checksum changed")
    lamost, gaia=json.loads(lp),json.loads(gp)
    if lamost.get("experiment")!="003" or gaia.get("experiment")!="003G":
        raise ValueError("Unexpected original experiment")
    records=lamost["records"]
    gs=gaia["sources"]
    if len(records)!=250 or len(gs)!=250:
        raise ValueError("Changed original 250 target population")
    lm={}
    for row in records:
        obsid=exact_id(row["lamost_obsid"])
        sid=exact_id(row["gaia_dr3_id_provisional"])
        if obsid in lm:raise ValueError("Duplicate original LAMOST obsid")
        lm[obsid]={"original":row,"gaia_id":sid}
    for source in gs:
        obsid=exact_id(source["lamost_obsid"])
        if obsid not in lm or exact_id(source["gaia_dr3_source_id"])!=lm[obsid]["gaia_id"]:
            raise ValueError("Published Gaia ID mapping changed")
        if source.get("gaia_record") is None: raise ValueError("Missing original Gaia DR3 record")
        lm[obsid]["gaia"]=source["gaia_record"]
    if PRIORITY not in lm:raise ValueError("Flagged reference obsid absent")
    return lm


def selection(inputs):
    return {"experiment":"006B","table":TABLE,"endpoint":ENDPOINT,
        "protocol_sha256":sha(PROTOCOL.read_bytes()),
        "source_lamost_sha256":LAMOST_SHA,"source_gaia_sha256":GAIA_SHA,
        "obsids":sorted(inputs,key=int),"batch_size":BATCH,
        "priority_obsid":PRIORITY,
        "esa_mirror_is_not_confirmed_identical_to_lamost_v2":True}


def query_for(ids):
    if len(ids)>BATCH or not ids or ids!=sorted(set(ids),key=int):
        raise ValueError("Invalid sorted unique request batch")
    for v in ids:exact_id(v)
    return (f"SELECT TOP 100 {', '.join(FIELDS)} FROM {TABLE} "
       "WHERE obsid IN ("+",".join(ids)+") ORDER BY obsid ASC")


def parse_batch(data, expected):
    fields,rows=parse_votable(data)
    if set(fields)!=set(FIELDS):
        raise ValueError("Unexpected ESA LRS General schema")
    if len(rows)>len(expected) or len(rows)>=100:
        raise ValueError("Unexpected ESA TAP row count")
    ids=[]
    for r in rows:
        oid=exact_id(r["obsid"])
        if oid not in expected or oid in ids:
            raise ValueError("Unrequested or duplicate ESA obsid")
        ids.append(oid)
        for col,lo,hi in (("ra",0,360),("ra_obs",0,360),
                          ("dec",-90,90),("dec_obs",-90,90)):
            val=r.get(col)
            if val is not None and (not isinstance(val,(int,float)) or
                not math.isfinite(val) or not lo<=val<=hi):
                raise ValueError("Bad ESA coordinate "+col)
        flag=r.get("offsets")
        if flag is not None and flag not in (0,1,False,True):
            raise ValueError("Unrecognized ESA fiber offset flag")
        magnitude=r.get("offsets_v")
        if flag in (1,True) and (
            magnitude is None or not isinstance(magnitude,(int,float)) or
            not math.isfinite(magnitude) or magnitude<0):
            raise ValueError("Flagged ESA offset has invalid magnitude")
        if r.get("mjd") is not None and (not isinstance(r["mjd"],(int,float)) or
            not 55000 <= r["mjd"] <= 60000):
            raise ValueError("MJD outside observational range")
        r["obsid"]=oid
        # A missing or sentinel Gaia ID is an ESA catalog quality finding,
        # not a reason to discard the genuine spectrum/offset/date record.
        if r.get("gaia_source_id") is not None:
            r["gaia_source_id"]=str(r["gaia_source_id"]).strip()
    if ids!=sorted(ids,key=int):
        raise ValueError("ESASky returned unsorted obsids")
    return fields,rows


def acquire(directory, source):
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    frozen=selection(source)
    sf=directory/"selection.json"
    if sf.exists() and json.loads(sf.read_text())!=frozen:
        raise ValueError("The source/protocol selection changed; refusing overwrite")
    sf.write_text(json.dumps(frozen,indent=2)+"\n")
    batches=[]
    metadata=None
    for i in range(0,len(frozen["obsids"]),BATCH):
        ids=frozen["obsids"][i:i+BATCH]
        query=query_for(ids)
        label=f"batch_{i//BATCH:02d}"
        rawfile=directory/(label+".xml.gz")
        mf=directory/(label+".json")
        params={"REQUEST":"doQuery","LANG":"ADQL","FORMAT":"votable",
                "MAXREC":"101","QUERY":query}
        if rawfile.exists() and mf.exists():
            payload=gzip.decompress(rawfile.read_bytes())
            record=json.loads(mf.read_text())
            if record["query"]!=query or record["raw_sha256"]!=sha(payload):
                raise ValueError("Changed cached source response")
        else:
            request=urllib.request.Request(ENDPOINT,
                data=urllib.parse.urlencode(params).encode(),method="POST",
                headers={"User-Agent":"EchoLens-006B-reproducible-ESA-LAMOST",
                         "Content-Type":"application/x-www-form-urlencoded"})
            with urllib.request.urlopen(request,timeout=180) as resp:
                payload=resp.read(3_000_000)
                headers={k:resp.headers.get(k) for k in
                         ("Date","Content-Type","ETag","Last-Modified")}
                status=resp.status
            record={"query":query,"parameters":params,"endpoint":ENDPOINT,
                    "utc_retrieved":datetime.now(timezone.utc).isoformat(),
                    "http_status":status,"headers":headers,
                    "requested_obsids":ids,"raw_sha256":sha(payload)}
        fields,rows=parse_batch(payload,ids)
        if metadata is None:metadata=fields
        elif fields!=metadata:raise ValueError("ESA source schema drift across batches")
        record["actual_row_count"]=len(rows)
        if not rawfile.exists():
            rawfile.write_bytes(gzip.compress(payload,mtime=0))
            mf.write_text(json.dumps(record,indent=2)+"\n")
        batches.append(record)
        print(f"Verified ESASky DR9 LRS batch {i//BATCH+1}/10: {len(rows)} of {len(ids)} obsids",flush=True)
    (directory/"manifest.json").write_text(json.dumps({
        "selection":frozen,"field_metadata":metadata,"batches":batches,
        "source_type":"ESA ESASky mirror of LAMOST DR9 LRS General, NOT original release-certified v2 catalog"
    },indent=2)+"\n")


def angular_arcsec(ra1,dec1,ra2,dec2):
    r1,d1,r2,d2=map(math.radians,(ra1,dec1,ra2,dec2))
    h=math.sin((d2-d1)/2)**2 + math.cos(d1)*math.cos(d2)*math.sin((r2-r1)/2)**2
    return math.degrees(2*math.asin(math.sqrt(max(0,min(1,h)))))*3600


def rounded_sep(ra1,dec1,ra2,dec2):
    if any(v is None for v in (ra1,dec1,ra2,dec2)):return None
    return round(angular_arcsec(ra1,dec1,ra2,dec2),4)


def check_date(obsdate,mjd):
    if obsdate is None or mjd is None:return "missing_date_or_mjd"
    try:
        start=datetime.fromisoformat(str(obsdate).strip()[:10])
        calc=datetime(1858,11,17)+timedelta(days=float(mjd))
    except (TypeError,ValueError,OverflowError):
        return "invalid_date_or_mjd"
    return ("consistent_within_2_days" if abs((start-calc).total_seconds())<=2*86400
            else "date_mjd_discrepancy_over_2_days")


def replay(directory, original, output):
    directory=Path(directory)
    frozen=selection(original)
    if json.loads((directory/"selection.json").read_text())!=frozen:
        raise ValueError("Original selection/protocol checksum mismatch")
    archive=json.loads((directory/"manifest.json").read_text())
    if archive["selection"]!=frozen or len(archive["batches"])!=10:
        raise ValueError("ESA source manifest mismatch")
    by_id={}
    response_hashes=[]
    for i,rec in enumerate(archive["batches"]):
        expected=frozen["obsids"][i*BATCH:(i+1)*BATCH]
        if rec["query"]!=query_for(expected) or rec["requested_obsids"]!=expected:
            raise ValueError("Unexpected archived query")
        payload=gzip.decompress((directory/f"batch_{i:02d}.xml.gz").read_bytes())
        if sha(payload)!=rec["raw_sha256"]:
            raise ValueError("Changed original ESA TAP response bytes")
        fields,rows=parse_batch(payload,expected)
        if fields!=archive["field_metadata"] or len(rows)!=rec["actual_row_count"]:
            raise ValueError("ESA table field/row drift")
        for row in rows:
            if row["obsid"] in by_id:raise ValueError("Duplicated ESA obsid across batches")
            by_id[row["obsid"]]=row
        response_hashes.append(sha(payload))
    result_rows=[]
    for obsid in frozen["obsids"]:
        base=original[obsid]
        r=by_id.get(obsid)
        gaia=base["gaia"]
        source=base["original"]["published_raw_row"]
        if r is None:
            result_rows.append({"obsid":obsid,"status":"missing_in_esa_mirror",
                                "published_gaia_source_id":base["gaia_id"],"esa_record":None})
            continue
        esa_id=r.get("gaia_source_id")
        try:
            esa_valid_id=exact_id(esa_id)
        except ValueError:
            esa_valid_id=None
        gaia_ok=esa_valid_id==base["gaia_id"]
        start=rounded_sep(r["ra"],r["dec"],r["ra_obs"],r["dec_obs"])
        vie=rounded_sep(source["RAJ2000"],source["DEJ2000"],
                        r["ra_obs"],r["dec_obs"])
        gaia_ref=rounded_sep(gaia["ra"],gaia["dec"],r["ra_obs"],r["dec_obs"])
        date_status=check_date(r.get("obsdate"),r.get("mjd"))
        result_rows.append({
            "obsid":obsid,"status":"esa_observation_found",
            "published_gaia_source_id":base["gaia_id"],
            "esa_published_gaia_id_agrees":gaia_ok,
            "esa_published_gaia_id_wellformed":esa_valid_id is not None,
            "esa_published_gaia_id_raw":esa_id,
            "date_mjd_check":date_status,
            "esa_published_obsdate":r.get("obsdate"),
            "esa_published_mjd":r.get("mjd"),
            "esa_offset_flag":r.get("offsets"),
            "esa_offset_arcsec":r.get("offsets_v"),
            "input_to_fiber_arcsec":start,
            "vizier_fiber_to_esa_fiber_arcsec":vie,
            "gaia_2016_to_esa_fiber_arcsec_epoch_unqualified":gaia_ref,
            "esa_record":r,
            "instrumental_offset_hypothesis":
                "esa_offset_flag_on" if r.get("offsets") in (1,True) else
                "esa_offset_flag_off" if r.get("offsets") in (0,False) else
                "esa_offset_flag_missing",
            "independent_crossmatch_certified":False
        })
    priority=next(row for row in result_rows if row["obsid"]==PRIORITY)
    result={"experiment":"006B","catalog_provider":"ESA ESASky", "catalog_table":TABLE,
        "official_dr9_v2_release_identity_confirmed":False,
        "input_provenance":frozen,"native_esa_response_sha256":response_hashes,
        "expected_obsids":250,"resolved_esa_obsids":len(by_id),
        "missing_esa_obsids":250-len(by_id),
        "published_gaia_id_matches":sum(r.get("esa_published_gaia_id_agrees") is True for r in result_rows),
        "esa_gaia_id_missing_or_invalid":sum(
            r.get("status")=="esa_observation_found" and
            not r.get("esa_published_gaia_id_wellformed",False) for r in result_rows),
        "esa_offset_flag_on":sum(r.get("esa_offset_flag") in (1,True) for r in result_rows),
        "esa_offset_flag_off":sum(r.get("esa_offset_flag") in (0,False) for r in result_rows),
        "date_mjd_inconsistent":sum(r.get("date_mjd_check")=="date_mjd_discrepancy_over_2_days" for r in result_rows),
        "flagged_priority_source":priority,"sources":result_rows,
        "interpretation":"ESA LAMOST DR9 mirror data, distinct from independently certified original v2 release. No astrophysical anomaly inference."}
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    (output/"results.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps({key:result[key] for key in (
        "expected_obsids","resolved_esa_obsids","missing_esa_obsids",
        "published_gaia_id_matches","esa_offset_flag_on","esa_offset_flag_off",
        "date_mjd_inconsistent","flagged_priority_source")},indent=2))
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--lamost-results",required=True)
    p.add_argument("--gaia-results",required=True)
    p.add_argument("--directory",default="data/esasky_lamost_006")
    p.add_argument("--output",default="reports/experiment_006b")
    p.add_argument("--fetch",action="store_true")
    a=p.parse_args()
    originals=original_inputs(a.lamost_results,a.gaia_results)
    if a.fetch:acquire(a.directory,originals)
    replay(a.directory,originals,a.output)


if __name__=="__main__":
    main()
