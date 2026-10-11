"""EchoLens Experiment 003 — provenance-preserving external LAMOST DR9 pilot.

Default mode is offline replay, and no operation writes the serving Gaia database.
An explicit --fetch downloads a *preregistered*, immutable 250-spectrum VizieR sample.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
from statistics import median
import urllib.parse
import urllib.request

from scripts.import_gaia import parse_votable, parse_snapshot, validate as validate_gaia

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data" / "lamost_003"
PROTOCOL = ROOT / "docs" / "EXPERIMENT_003.md"
SOURCE = ROOT / "data" / "gaia_dr3.raw.gz"
SOURCE_MANIFEST = ROOT / "data" / "gaia_dr3.manifest.json"
GAIA_SHA = "d193d7e144d5a7fc9f3d877a9323fc3c68ee2baf05b966d997392309a5248fb0"
TABLE = '"J/ApJS/272/6/catalog"'
ENDPOINT = "https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync"
SALT = "echolens-003-v1:"
FRAME = 699348
COUNT = 250
BATCH = 25
CORE = ("recno", "obsid", "GaiaDR3", "SNRi", "SNRz", "RAJ2000", "DEJ2000",
        "Teff", "e_Teff", "logg", "e_logg", "FeH", "e_FeH",
        "R8542", "e_R8542")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def freeze_selection():
    selected = set()
    counter = 0
    while len(selected) < COUNT:
        value = int(digest((SALT + str(counter)).encode("ascii")), 16) % FRAME + 1
        selected.add(value)
        counter += 1
    return sorted(selected)


def selection_manifest():
    ids = freeze_selection()
    return {
        "experiment": "003",
        "source": "LAMOST DR9 Huang et al. 2024 via CDS VizieR",
        "table": TABLE,
        "selection_salt": SALT,
        "sampling_frame": FRAME,
        "spectrum_count": COUNT,
        "batch_size": BATCH,
        "recno": ids,
        "selection_sha256": digest(json.dumps(ids, separators=(",", ":")).encode()),
        "protocol_sha256": digest(PROTOCOL.read_bytes()),
        "gaia_raw_sha256": GAIA_SHA,
        "readme_url": "https://cdsarc.cds.unistra.fr/viz-bin/ReadMe/J/ApJS/272/6?format=html&tex=true",
        "not_a_clean_control_claim": True,
    }


def query_for(ids):
    if not ids or len(ids) > BATCH or ids != sorted(set(ids)) or any(not 1 <= i <= FRAME for i in ids):
        raise ValueError("Invalid frozen recno batch")
    return ('SELECT TOP 1000 * FROM ' + TABLE + ' WHERE "recno" IN (' +
            ",".join(str(i) for i in ids) + ') ORDER BY "recno" ASC')


def blank_to_null(value):
    if value is None or isinstance(value, str) and not value.strip():
        return None
    if isinstance(value, (int, float)) and (not math.isfinite(value) or value == -9999):
        return None
    if isinstance(value, str) and value.strip() == "-9999":
        return None
    return value


def valid_id(value):
    value = blank_to_null(value)
    if value is None:
        return None
    # Preserve original 64-bit Gaia identifier as decimal string, never floating point.
    if isinstance(value, float) or isinstance(value, bool):
        return None
    s = str(value).strip()
    if not s.isascii() or not s.isdigit() or not 0 < int(s) < 2**63:
        return None
    return s


def assess_row(row):
    if set(CORE) - set(row):
        raise ValueError("Missing published required LAMOST columns: " + str(set(CORE)-set(row)))
    reasons = []
    sid = valid_id(row["GaiaDR3"])
    if sid is None: reasons.append("missing_or_invalid_published_gaia_id")
    snri, snrz = (blank_to_null(row["SNRi"]), blank_to_null(row["SNRz"]))
    if any(not isinstance(v, (int, float)) or v < 100 for v in (snri, snrz)):
        reasons.append("insufficient_or_missing_lamost_snr")
    specs = (("Teff", "e_Teff", 4800, 6800),
             ("logg", "e_logg", 3.6, 4.9),
             ("FeH", "e_FeH", -1.01, .51))
    inferences = {}
    for value_name, error_name, low, high in specs:
        value, error = blank_to_null(row[value_name]), blank_to_null(row[error_name])
        if not isinstance(value, (int, float)) or not low <= value <= high:
            reasons.append("missing_or_out_of_catalog_range_" + value_name)
        if not isinstance(error, (int, float)) or error <= 0:
            reasons.append("missing_or_nonpositive_uncertainty_" + error_name)
        inferences[value_name] = {"value": value, "published_error": error}
    for coord, lo, hi in (("RAJ2000", 0, 360), ("DEJ2000", -90, 90)):
        value = blank_to_null(row[coord])
        if not isinstance(value, (float, int)) or not lo <= value <= hi or (coord == "RAJ2000" and value == 360):
            reasons.append("invalid_" + coord)
    return {"gaia_dr3_id_provisional": sid,
            "lamost_obsid": str(row["obsid"]) if row["obsid"] is not None else None,
            "spectroscopic_inferences": inferences,
            "spectroscopic_label_ready": not reasons,
            "quality_failures": reasons,
            "published_raw_row": row}


def validate_batch(payload, requested):
    fields, rows = parse_votable(payload)  # enforces TAP QUERY_STATUS=OK; rejects OVERFLOW
    if set(CORE) - set(fields):
        raise ValueError("VizieR schema missing mandatory columns")
    if len(rows) != len(requested):
        raise ValueError(f"VizieR row count {len(rows)} != preregistered {len(requested)}")
    ids = [row["recno"] for row in rows]
    if any(not isinstance(i, int) for i in ids):
        raise ValueError("VizieR recno must be an exact integer")
    if ids != requested:
        raise ValueError("Missing, duplicated, reordered or substituted recno")
    if len({str(row["obsid"]) for row in rows}) != len(rows):
        raise ValueError("Duplicate spectrum observation IDs in acquisition batch")
    return fields, [assess_row(row) for row in rows]


def fetch_batches(directory):
    """Network action only when --fetch is explicitly supplied."""
    directory.mkdir(parents=True, exist_ok=True)
    frozen = selection_manifest()
    selection = directory / "selection.json"
    if selection.exists() and json.loads(selection.read_text()) != frozen:
        raise ValueError("Selection/protocol changed; refusing to overwrite")
    selection.write_text(json.dumps(frozen, indent=2) + "\n")
    batches = []
    for index in range(0, COUNT, BATCH):
        ids = frozen["recno"][index:index+BATCH]
        query = query_for(ids)
        name = f"batch_{index//BATCH:02d}"
        rawpath, metapath = directory/(name+".xml.gz"), directory/(name+".json")
        params = {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "votable",
                  "QUERY": query, "MAXREC": "1000"}
        if rawpath.exists() and metapath.exists():
            record = json.loads(metapath.read_text())
            data = gzip.decompress(rawpath.read_bytes())
            if record["query"] != query or record["sha256"] != digest(data):
                raise ValueError("Cached acquisition changed")
        else:
            body = urllib.parse.urlencode(params).encode("ascii")
            req = urllib.request.Request(ENDPOINT, data=body, headers={
                "User-Agent": "EchoLens-Research/003 (public science reproducibility)",
                "Content-Type": "application/x-www-form-urlencoded"}, method="POST")
            with urllib.request.urlopen(req, timeout=150) as response:
                data = response.read()
                headers = {x: response.headers.get(x) for x in
                           ("Content-Type", "Date", "ETag", "Last-Modified")}
            record = {"query": query, "parameters": params, "endpoint": ENDPOINT,
                      "request_method": "POST", "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                      "headers": headers, "sha256": digest(data), "requested_recno": ids}
        validate_batch(data, ids)  # Never archive a failed, truncated or substituted batch.
        if not (rawpath.exists() and metapath.exists()):
            rawpath.write_bytes(gzip.compress(data, mtime=0))
            metapath.write_text(json.dumps(record, indent=2) + "\n")
        batches.append(record)
        print(f"Validated LAMOST batch {index//BATCH+1}/{COUNT//BATCH}", flush=True)
    (directory/"manifest.json").write_text(json.dumps({
        "selection": frozen, "batches": batches, "source": "Huang+2024 LAMOST DR9",
        "service": "CDS VizieR TAP", "format": "VOTable",
        "interpretation": "Independent spectroscopic reference candidates; not certified controls"
    }, indent=2) + "\n")


def initial_gaia_ids():
    raw = gzip.decompress(SOURCE.read_bytes())
    if digest(raw) != GAIA_SHA:
        raise ValueError("Original Gaia DR3 catalog checksum mismatch")
    manifest = json.loads(SOURCE_MANIFEST.read_text())
    _, stars = parse_snapshot(raw, manifest, SOURCE.parent)
    validate_gaia(stars, 10000)
    return {row["source_id"] for row in stars}


def replay(directory, output):
    """Works completely offline from immutable response bytes, original manifest and Gaia snapshot."""
    directory, output = Path(directory), Path(output)
    frozen = selection_manifest()
    if json.loads((directory/"selection.json").read_text()) != frozen:
        raise ValueError("Frozen spectrum selection or protocol changed")
    manifest = json.loads((directory/"manifest.json").read_text())
    if manifest["selection"] != frozen or len(manifest["batches"]) != COUNT//BATCH:
        raise ValueError("Acquisition manifest changed")
    fields = None
    records = []
    for i, record in enumerate(manifest["batches"]):
        ids = frozen["recno"][i*BATCH:(i+1)*BATCH]
        if record["query"] != query_for(ids) or record["requested_recno"] != ids:
            raise ValueError("Wrong archived request/selection")
        raw = gzip.decompress((directory/f"batch_{i:02d}.xml.gz").read_bytes())
        if digest(raw) != record["sha256"]:
            raise ValueError("Original VizieR bytes corrupted")
        meta, items = validate_batch(raw, ids)
        if fields is not None and meta != fields:
            raise ValueError("VizieR field definitions changed across batches")
        fields = meta
        records.extend(items)
    if len(records) != COUNT:
        raise ValueError("Incomplete frozen acquisition")
    obsid = [r["lamost_obsid"] for r in records]
    if len(set(obsid)) != len(obsid) or any(s is None for s in obsid):
        raise ValueError("Duplicate/missing LAMOST observation ID")
    by_star = defaultdict(list)
    for entry in records:
        if entry["gaia_dr3_id_provisional"] is not None:
            by_star[entry["gaia_dr3_id_provisional"]].append(entry)
    ready = {sid for sid, spectrum in by_star.items()
             if any(r["spectroscopic_label_ready"] for r in spectrum)}
    gaia_ids = initial_gaia_ids()
    failures = Counter(reason for entry in records for reason in entry["quality_failures"])
    inference_fields = ("Teff", "logg", "FeH")
    def summarize(values):
        return {"available": len(values), "median": median(values) if values else None,
                "min": min(values) if values else None, "max": max(values) if values else None}
    summaries = {name: summarize([
        item["spectroscopic_inferences"][name]["value"] for item in records
        if isinstance(item["spectroscopic_inferences"][name]["value"], (float, int))])
                 for name in inference_fields}
    result = {
        "experiment": "003", "publication": "Huang et al. 2024 ApJS 272 6",
        "sample_selection": frozen, "archive_sha256": [r["sha256"] for r in manifest["batches"]],
        "requested_spectra": COUNT, "retrieved_spectra": len(records),
        "distinct_published_gaia_ids": len(by_star),
        "spectra_with_quality_ready_labels": sum(x["spectroscopic_label_ready"] for x in records),
        "distinct_stars_with_quality_ready_labels": len(ready),
        "gaia_10000_id_overlap": len(set(by_star).intersection(gaia_ids)),
        "gaia_10000_overlap_source_ids": sorted(set(by_star).intersection(gaia_ids), key=int),
        "failure_reason_counts": dict(sorted(failures.items())),
        "spectroscopic_parameter_summary": summaries,
        "repeat_spectrum_count": sum(len(v)-1 for v in by_star.values()),
        "source_fields": fields, "records": records,
        "interpretation": ("Independent LAMOST spectroscopic observations with published provisional Gaia IDs. "
                           "NO certified control classification, anomaly scoring, or artificial-origin claims."),
    }
    output.mkdir(parents=True, exist_ok=True)
    (output/"results.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    print(json.dumps({k: v for k, v in result.items() if k in (
        "requested_spectra", "retrieved_spectra", "distinct_published_gaia_ids",
        "spectra_with_quality_ready_labels", "distinct_stars_with_quality_ready_labels",
        "gaia_10000_id_overlap", "failure_reason_counts")}, indent=2))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fetch", action="store_true", help="Explicit VizieR network acquisition")
    p.add_argument("--directory", default=str(DIR))
    p.add_argument("--output", default="reports/experiment_003")
    a = p.parse_args()
    if a.fetch:
        fetch_batches(Path(a.directory))
    replay(a.directory, a.output)


if __name__ == "__main__":
    main()
