"""Experiment 003G: audit archived LAMOST published Gaia IDs against real Gaia DR3 records.

Exact ID existence is not an epoch-qualified spectroscopic counterpart validation.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import tempfile
from datetime import datetime, timezone
import urllib.parse
import urllib.request

from scripts.lamost_controls_003 import replay as replay_lamost
from scripts.import_gaia import parse_votable

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://irsa.ipac.caltech.edu/TAP/sync"
DIR = ROOT / "data" / "lamost_gaia_003"
LAMOST_DIR = ROOT / "data" / "lamost_003"
PROTOCOL = ROOT / "docs" / "EXPERIMENT_003_GAIA_AUDIT.md"
BATCH_SIZE = 25


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def lamost_records(lamost_dir):
    with tempfile.TemporaryDirectory() as d:
        result = replay_lamost(lamost_dir, d)
    records = result["records"]
    ids = [r["gaia_dr3_id_provisional"] for r in records]
    if len(ids) != 250 or len(set(ids)) != 250 or any(i is None for i in ids):
        raise ValueError("LAMOST experiment 003 frozen 250 ID selection changed")
    return result, sorted(ids, key=int)


def query_for(ids):
    if not ids or len(ids) > BATCH_SIZE or len(ids) != len(set(ids)):
        raise ValueError("Invalid Gaia lookup batch")
    if ids != sorted(ids, key=int) or any(not sid.isascii() or not sid.isdigit() or
                                          not 0 < int(sid) < 2**63 for sid in ids):
        raise ValueError("Invalid exact Gaia source IDs")
    return ("SELECT TOP 100 * FROM gaia_dr3_source WHERE source_id IN (" +
            ",".join(ids) + ") ORDER BY source_id ASC")


def validate_response(raw, ids):
    fields, rows = parse_votable(raw)
    required = {"source_id", "ra", "dec", "ra_error", "dec_error", "pmra", "pmdec",
                "pmra_error", "pmdec_error", "ref_epoch", "phot_g_mean_mag",
                "ruwe", "parallax", "parallax_error"}
    if required - set(fields):
        raise ValueError("Missing Gaia astrometry/uncertainties in TAP response")
    got = [str(row["source_id"]) for row in rows]
    if any(v not in ids for v in got) or len(set(got)) != len(got) or got != sorted(got, key=int):
        raise ValueError("Extra/duplicate/misordered Gaia identities")
    if len(rows) > len(ids):
        raise ValueError("Unexpected Gaia query result count")
    for row in rows:
        if not (0 <= row["ra"] < 360 and -90 <= row["dec"] <= 90):
            raise ValueError("Invalid Gaia coordinate")
        for name in ("ra_error","dec_error","pmra_error","pmdec_error","parallax_error"):
            if row.get(name) is not None and (not math.isfinite(row[name]) or row[name] < 0):
                raise ValueError("Invalid published Gaia uncertainty")
        row["source_id"] = str(row["source_id"])
    return fields, rows


def _selection(lamost):
    ids = sorted([r["gaia_dr3_id_provisional"] for r in lamost["records"]], key=int)
    return {"protocol_sha256": digest(PROTOCOL.read_bytes()),
            "source_selection_sha256": lamost["sample_selection"]["selection_sha256"],
            "lamost_response_sha256": lamost["archive_sha256"],
            "gaia_source_ids": ids,
            "source_release": "Gaia DR3", "archive": "IRSA"}


def fetch_gaia(directory, lamost_dir):
    lamost, ids = lamost_records(lamost_dir)
    selector = _selection(lamost)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    sf = directory/"selection.json"
    if sf.exists() and json.loads(sf.read_text()) != selector:
        raise ValueError("Gaia lookup frozen selection changed")
    sf.write_text(json.dumps(selector, indent=2)+"\n")
    batches = []
    for batch in range(0, 250, BATCH_SIZE):
        chosen = ids[batch:batch+BATCH_SIZE]
        query = query_for(chosen)
        tag = f"batch_{batch//BATCH_SIZE:02d}"
        payload_file, record_file = directory/(tag+".xml.gz"), directory/(tag+".json")
        params = {"REQUEST":"doQuery","LANG":"ADQL","FORMAT":"votable",
                  "QUERY":query,"MAXREC":"100"}
        if payload_file.exists() and record_file.exists():
            record = json.loads(record_file.read_text())
            data = gzip.decompress(payload_file.read_bytes())
            if record["query"] != query or record["sha256"] != digest(data):
                raise ValueError("Changed Gaia cache or query")
        else:
            req = urllib.request.Request(ENDPOINT, data=urllib.parse.urlencode(params).encode(),
                  headers={"User-Agent":"EchoLens-Research/003G","Content-Type":"application/x-www-form-urlencoded"},
                  method="POST")
            with urllib.request.urlopen(req,timeout=180) as response:
                data=response.read()
                headers={key:response.headers.get(key) for key in
                         ("Content-Type","Date","ETag","Last-Modified")}
            record={"query":query,"parameters":params,"request_method":"POST","endpoint":ENDPOINT,
                    "retrieved_utc":datetime.now(timezone.utc).isoformat(),
                    "sha256":digest(data),"requested_ids":chosen,"headers":headers}
        validate_response(data, chosen)
        if not payload_file.exists():
            payload_file.write_bytes(gzip.compress(data,mtime=0))
            record_file.write_text(json.dumps(record,indent=2)+"\n")
        batches.append(record)
        print(f"Verified Gaia DR3 exact ID batch {batch//BATCH_SIZE+1}/10", flush=True)
    (directory/"manifest.json").write_text(json.dumps({
        "experiment":"003G","selection":selector,"batches":batches,
        "data_note":"Gaia source ID existence is not an independent position/counterpart confirmation"
    },indent=2)+"\n")


def separation_arcsec(ra1, dec1, ra2, dec2):
    ra1, dec1, ra2, dec2 = map(math.radians, (ra1, dec1, ra2, dec2))
    h = math.sin((dec1-dec2)/2)**2 + math.cos(dec1)*math.cos(dec2)*math.sin((ra1-ra2)/2)**2
    return math.degrees(2*math.asin(math.sqrt(min(1.0,max(0.0,h)))))*3600


def replay(directory, lamost_dir, output):
    directory, output = Path(directory),Path(output)
    lamost, ids = lamost_records(lamost_dir)
    selection = _selection(lamost)
    if json.loads((directory/"selection.json").read_text()) != selection:
        raise ValueError("Frozen Gaia requery selection changed")
    manifest = json.loads((directory/"manifest.json").read_text())
    if manifest["selection"] != selection or len(manifest["batches"]) != 10:
        raise ValueError("Gaia response manifest changed")
    by_id = {}
    field_metadata = None
    for batch, rec in enumerate(manifest["batches"]):
        chosen = ids[batch*BATCH_SIZE:(batch+1)*BATCH_SIZE]
        if rec["query"] != query_for(chosen) or rec["requested_ids"] != chosen:
            raise ValueError("Gaia query/identity drift")
        payload = gzip.decompress((directory/f"batch_{batch:02d}.xml.gz").read_bytes())
        if digest(payload) != rec["sha256"]:
            raise ValueError("Gaia response content changed")
        fields, rows = validate_response(payload, chosen)
        if field_metadata is None: field_metadata = fields
        elif fields != field_metadata: raise ValueError("Gaia batch metadata inconsistent")
        for row in rows:
            if row["source_id"] in by_id: raise ValueError("Duplicate Gaia ID across batches")
            by_id[row["source_id"]] = row
    outcome = []
    for item in lamost["records"]:
        sid = item["gaia_dr3_id_provisional"]
        gaia = by_id.get(sid)
        flags=[]
        sep = None
        gdiff = None
        if gaia is None:
            flags.append("gaia_source_id_unresolved")
        else:
            src = item["published_raw_row"]
            sep = separation_arcsec(gaia["ra"],gaia["dec"],src["RAJ2000"],src["DEJ2000"])
            # Reporting deliberately rounds a *derived* angle, never native measurements.
            sep = round(sep,4)
            if sep > 3: flags.append("different_epoch_position_offset_over_3_arcsec")
            if any(gaia.get(field) is None for field in
                   ("pmra","pmdec","pmra_error","pmdec_error")):
                flags.append("gaia_proper_motion_incomplete")
            if gaia.get("phot_g_mean_mag") is not None and src.get("Gmag") is not None:
                gdiff = round(abs(gaia["phot_g_mean_mag"]-src["Gmag"]),5)
                if gdiff > .5: flags.append("published_g_magnitude_difference_over_0_5")
        outcome.append({
            "lamost_obsid":item["lamost_obsid"],"gaia_dr3_source_id":sid,
            "gaia_identifier_exists":gaia is not None,
            "gaia_reference_epoch":gaia["ref_epoch"] if gaia else None,
            "fiber_to_gaia_position_arcsec_epoch_unqualified":sep,
            "published_g_difference_mag":gdiff,
            "review_flags":flags,
            "gaia_record":gaia,
        })
    counts={"resolved_gaia_ids":len(by_id),
            "unresolved_gaia_ids":250-len(by_id),
            "complete_gaia_proper_motion":sum(o["gaia_identifier_exists"] and
                "gaia_proper_motion_incomplete" not in o["review_flags"] for o in outcome),
            "position_offset_gt_3_arcsec_epoch_unqualified":sum(
                "different_epoch_position_offset_over_3_arcsec" in o["review_flags"] for o in outcome),
            "published_gaia_G_difference_gt_0_5mag":sum(
                "published_g_magnitude_difference_over_0_5" in o["review_flags"] for o in outcome)}
    result={"experiment":"003G","selection":selection,
            "archive_sha256":[b["sha256"] for b in manifest["batches"]],
            "source_fields":field_metadata, "counts":counts,"sources":outcome,
            "interpretation":"Exact Gaia DR3 ID existence only; no observing-epoch qualified crossmatch or clean-control claim"}
    output.mkdir(parents=True,exist_ok=True)
    (output/"results.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(counts,indent=2))
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--fetch", action="store_true")
    p.add_argument("--directory",default=str(DIR))
    p.add_argument("--lamost-directory",default=str(LAMOST_DIR))
    p.add_argument("--output",default="reports/experiment_003/gaia_audit")
    a=p.parse_args()
    if a.fetch: fetch_gaia(a.directory,a.lamost_directory)
    replay(a.directory,a.lamost_directory,a.output)


if __name__ == "__main__":
    main()
