"""EchoLens 003H: traceable LAMOST/Gaia epoch-window crossmatch *triage*.

Never approve a match from a date window, never fabricate a spectrum date,
and never mutate the original 250 LAMOST or Gaia observations.
"""
import argparse
import csv
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
from statistics import median

START = "2011-10-24"
END = "2021-06-30"
SOURCE_COUNT = 250
REVIEW_RADIUS_ARCSEC = 3.0
REQUIRED_OFFICIAL = (
    "obsid", "obsdate", "mjd", "ra_obs", "dec_obs", "offsets", "offsets_v"
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def input_json(path):
    raw = Path(path).read_bytes()
    return json.loads(raw), sha(raw)


def span_years_from_gaia_epoch(epoch):
    """Conservative time-span in Julian years; epoch not rounded to calendar year."""
    # J2016.0 = JD2457389.0 = 2016-01-01 12:00 UTC approximately;
    # 12-hour offset is immaterial for the documented *diagnostic bound*.
    from datetime import timedelta
    zero = datetime(2016, 1, 1, 12)
    nominal = zero + timedelta(days=(epoch - 2016.0) * 365.25)
    left = abs((datetime.fromisoformat(START) - nominal).total_seconds()) / (86400 * 365.25)
    right = abs((datetime.fromisoformat(END) - nominal).total_seconds()) / (86400 * 365.25)
    return max(left, right)


def clean_id(value):
    text = str(value)
    if not text.isascii() or not text.isdigit() or not 0 < int(text) < 2**63:
        raise ValueError("Invalid exact Gaia source ID")
    return text


def strict_records(lamost, gaia):
    if len(lamost.get("records", [])) != SOURCE_COUNT or len(gaia.get("sources", [])) != SOURCE_COUNT:
        raise ValueError("Original sample count changed")
    seen = set()
    spectrum = {}
    for entry in lamost["records"]:
        obsid = str(entry["lamost_obsid"])
        sid = clean_id(entry["gaia_dr3_id_provisional"])
        if obsid in spectrum or sid in seen:
            raise ValueError("Duplicated LAMOST observation or source ID")
        seen.add(sid)
        spectrum[obsid] = (sid, entry)
    if len({s["lamost_obsid"] for s in gaia["sources"]}) != SOURCE_COUNT:
        raise ValueError("Duplicated Gaia audit source")
    for row in gaia["sources"]:
        sid = clean_id(row["gaia_dr3_source_id"])
        obsid = str(row["lamost_obsid"])
        if obsid not in spectrum or spectrum[obsid][0] != sid:
            raise ValueError("LAMOST-Gaia published mapping changed")
        g = row["gaia_record"]
        if g is None or clean_id(g["source_id"]) != sid:
            raise ValueError("Exact archived Gaia observation missing")
        if not (0 <= g["ra"] < 360 and -90 <= g["dec"] <= 90):
            raise ValueError("Invalid archived Gaia coordinates")
    return spectrum


def bound_row(row):
    g = row["gaia_record"]
    observed = row["fiber_to_gaia_position_arcsec_epoch_unqualified"]
    if observed is None or not math.isfinite(observed) or observed < 0:
        raise ValueError("Invalid non-epoch-qualified measured catalog separation")
    mu_ra, mu_dec = g.get("pmra"), g.get("pmdec")
    errs = (g.get("pmra_error"), g.get("pmdec_error"))
    if any(v is None or not isinstance(v, (int, float)) or not math.isfinite(v) for v in
           (mu_ra, mu_dec, *errs)) or any(e < 0 for e in errs):
        return {
            "original_separation_arcsec": observed,
            "proper_motion_mas_per_year": None,
            "max_linear_motion_arcsec": None,
            "minimum_residual_arcsec": None,
            "review_status": "no_gaia_proper_motion_assessment"
        }
    epoch = g.get("ref_epoch")
    if not isinstance(epoch, (int, float)) or not math.isfinite(epoch) or not 1990 <= epoch <= 2025:
        raise ValueError("Invalid Gaia reference epoch")
    years = span_years_from_gaia_epoch(epoch)
    motion = math.hypot(mu_ra, mu_dec)
    limit = motion * years / 1000
    residual = max(0, observed - limit)
    return {
        "original_separation_arcsec": observed,
        "proper_motion_mas_per_year": round(motion, 6),
        "max_linear_motion_arcsec": round(limit, 6),
        "minimum_residual_arcsec": round(residual, 6),
        "review_status": ("exceeds_3_arcsec_after_linear_pm_bound" if residual > REVIEW_RADIUS_ARCSEC
                          else "needs_actual_epoch_and_fiber_pointing")
    }


def official_metadata_csv(path, allowed_obsids, url, release):
    """Read official DR9 v2 CSV export only; no claimed match certification."""
    if not url.startswith("https://") or release != "LAMOST DR9 v2.0 LRS General":
        raise ValueError("Explicit official DR9 v2 catalog provenance is required")
    raw = Path(path).read_bytes()
    content = raw.decode("utf-8-sig")
    import io
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames or set(REQUIRED_OFFICIAL) - set(reader.fieldnames):
        raise ValueError("Official general catalog required fields missing")
    records = {}
    for row in reader:
        oid = str(row["obsid"]).strip()
        if oid not in allowed_obsids:
            continue  # whole catalog may include other real spectra
        if oid in records:
            raise ValueError("Duplicate official LAMOST obsid")
        try:
            mjd = int(row["mjd"])
            ra, dec = float(row["ra_obs"]), float(row["dec_obs"])
            offset = str(row["offsets"]).strip().lower()
            offsetv = str(row["offsets_v"]).strip()
            dv = float(offsetv) if offsetv else None
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid official observation fields for " + oid) from exc
        if not 55000 <= mjd <= 60000 or not 0 <= ra < 360 or not -90 <= dec <= 90:
            raise ValueError("Implausible observing MJD or fiber coordinates")
        if offset not in ("1","0","t","f","true","false","yes","no"):
            raise ValueError("Unrecognized fiber offset flag")
        if dv is not None and (not math.isfinite(dv) or dv < 0):
            raise ValueError("Invalid fiber offset magnitude")
        if not str(row["obsdate"]).strip():
            raise ValueError("Missing official observation date")
        records[oid] = {key: row[key] for key in reader.fieldnames}
    return {
        "source_release": release,
        "source_url": url,
        "sha256": sha(raw),
        "requested_obsid_count": len(allowed_obsids),
        "official_obsid_retrieved_count": len(records),
        "missing_obsids": sorted(set(allowed_obsids)-set(records),key=int),
        "raw_catalog_records": [records[oid] for oid in sorted(records,key=int)],
        "classification": "raw dated fiber-pointing metadata; no crossmatch certification"
    }


def execute(lamost_path, gaia_path, output, metadata_csv=None, metadata_url=None, metadata_release=None):
    lamost, lamost_hash = input_json(lamost_path)
    gaia, gaia_hash = input_json(gaia_path)
    spectrum = strict_records(lamost, gaia)
    records = []
    for item in gaia["sources"]:
        result = bound_row(item)
        oid = str(item["lamost_obsid"])
        if spectrum[oid][0] != clean_id(item["gaia_dr3_source_id"]):
            raise ValueError("Archived source mismatch")
        records.append({"lamost_obsid": oid, "gaia_dr3_source_id": spectrum[oid][0], **result})
    records.sort(key=lambda x:int(x["lamost_obsid"]))
    counts = {
        "total": SOURCE_COUNT,
        "requires_actual_observation_epoch": SOURCE_COUNT,
        "linear_motion_unassessable": sum(x["review_status"] == "no_gaia_proper_motion_assessment" for x in records),
        "possible_over_3_arcsec_even_after_max_pm": sum(x["review_status"] == "exceeds_3_arcsec_after_linear_pm_bound" for x in records),
        "crossmatches_certified": 0,
    }
    result = {
        "experiment": "003H",
        "observing_window": {"first_date": START, "last_date": END},
        "assumption": "linear Gaia proper-motion triangle-inequality upper bound, NOT a dated astrometric crossmatch",
        "lamost_results_sha256": lamost_hash,
        "gaia_results_sha256": gaia_hash,
        "review_radius_arcsec": REVIEW_RADIUS_ARCSEC,
        "counts": counts,
        "priority_review": [r for r in records if r["review_status"] == "exceeds_3_arcsec_after_linear_pm_bound"],
        "sources": records,
        "actual_lamost_observation_metadata": None,
        "interpretation": "Triage only; original VizieR J2000 coordinates are not verified observation-time pointing coordinates."
    }
    if metadata_csv is not None:
        result["actual_lamost_observation_metadata"] = official_metadata_csv(
            metadata_csv, set(spectrum), metadata_url or "", metadata_release or "")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output/"results.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(counts,indent=2))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lamost-results",required=True)
    p.add_argument("--gaia-results",required=True)
    p.add_argument("--output",default="reports/experiment_003h")
    p.add_argument("--official-csv")
    p.add_argument("--official-url")
    p.add_argument("--official-release")
    a=p.parse_args()
    execute(a.lamost_results,a.gaia_results,a.output,
            a.official_csv,a.official_url,a.official_release)


if __name__=="__main__":
    main()
