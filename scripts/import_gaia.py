"""Reproducible Gaia DR3 pilot importer. Standard library only.

Fetch: python -m scripts.import_gaia --fetch --db data/echolens.sqlite
Offline: python -m scripts.import_gaia --csv path/to/gaia.csv --db data/echolens.sqlite

The 10,000 Gaia DR3 sources are a QUALITY-SELECTED PILOT, not a representative
population and not pre-certified as lifeless controls.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from app.catalog import connect

ARCHIVE = "https://gea.esac.esa.int/tap-server/tap/sync"
COLUMNS = (
    "source_id", "ra", "dec", "parallax", "parallax_error",
    "parallax_over_error", "pmra", "pmra_error", "pmdec", "pmdec_error",
    "phot_g_mean_mag", "phot_g_mean_flux_over_error", "bp_rp", "ruwe",
    "random_index",
)
# Gaia random_index is assigned randomly; fixed interval + ordering
# makes this pilot repeatable. Cuts favor well-measured astrometry.
ADQL = """SELECT TOP 10000
    source_id, ra, dec, parallax, parallax_error, parallax_over_error,
    pmra, pmra_error, pmdec, pmdec_error, phot_g_mean_mag,
    phot_g_mean_flux_over_error, bp_rp, ruwe, random_index
FROM gaiadr3.gaia_source
WHERE random_index >= 500000000 AND random_index < 600000000
  AND parallax IS NOT NULL AND parallax_over_error >= 5
  AND phot_g_mean_mag IS NOT NULL AND bp_rp IS NOT NULL
  AND ruwe < 1.4
ORDER BY random_index ASC"""
SELECTION = (
    "Deterministic random_index interval; parallax SNR>=5; G and BP-RP "
    "present; RUWE<1.4. This is a quality-selected, nonrepresentative "
    "Gaia DR3 pilot; group labels require later matching and review."
)

def utcnow():
    return datetime.now(timezone.utc).isoformat()

def fetch_csv():
    payload = urllib.parse.urlencode({
        "REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
        "QUERY": ADQL, "MAXREC": "10000",
    }).encode("utf-8")
    request = urllib.request.Request(
        ARCHIVE, data=payload,
        headers={"User-Agent": "EchoLens/0.1 research Gaia DR3 importer"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=240) as response:
        if response.status != 200:
            raise RuntimeError(f"Gaia TAP HTTP {response.status}")
        raw = response.read(16_000_001)
    if len(raw) > 16_000_000:
        raise ValueError("Unexpectedly large TAP response")
    if not raw.lstrip().startswith(b"source_id,"):
        # Avoid accidentally importing an HTML/XML error page.
        raise ValueError("Gaia TAP response is not the expected CSV")
    return raw

def number(row, key):
    value = (row.get(key) or "").strip()
    if not value:
        return None
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"Non-finite {key}")
    return result

def parse(raw):
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or not set(COLUMNS).issubset(reader.fieldnames):
        raise ValueError(f"Unexpected CSV fields: {reader.fieldnames}")
    records, seen = [], set()
    for row in reader:
        sid = (row.get("source_id") or "").strip()
        if not sid.isdigit() or sid in seen:
            raise ValueError(f"Invalid or duplicate Gaia source_id: {sid!r}")
        seen.add(sid)
        ra, dec = number(row, "ra"), number(row, "dec")
        if ra is None or dec is None or not 0 <= ra < 360 or not -90 <= dec <= 90:
            raise ValueError(f"Invalid coordinates for source_id {sid}")
        record = [sid]
        for key in COLUMNS[1:]:
            if key == "random_index":
                value = (row.get(key) or "").strip()
                record.append(int(value) if value else None)
            else:
                record.append(number(row, key))
        records.append(tuple(record))
    if len(records) != 10000:
        raise ValueError(f"Expected exactly 10000 real rows, got {len(records)}")
    return records

def import_csv(raw, db_path, retrieved_utc=None):
    records = parse(raw)
    query_hash = hashlib.sha256(ADQL.encode()).hexdigest()
    csv_hash = hashlib.sha256(raw).hexdigest()
    run_id = "gaia-dr3-" + csv_hash[:20]
    db = connect(db_path, create=True)
    try:
        with db:
            exists = db.execute("SELECT count(*) FROM ingestion_runs WHERE run_id = ?", (run_id,)).fetchone()[0]
            if exists:
                raise ValueError("Identical Gaia CSV already imported")
            db.execute(
                """INSERT INTO ingestion_runs
                   (run_id, catalog, source_url, adql, query_sha256, csv_sha256,
                    retrieved_utc, imported_utc, row_count, selection_note)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (run_id, "Gaia DR3", ARCHIVE, ADQL, query_hash, csv_hash,
                 retrieved_utc or utcnow(), utcnow(), len(records), SELECTION),
            )
            sql = ("INSERT INTO stars (" + ", ".join(COLUMNS) + ", run_id) VALUES ("
                   + ", ".join(["?"] * (len(COLUMNS) + 1)) + ")")
            db.executemany(sql, [row + (run_id,) for row in records])
    finally:
        db.close()
    return {
        "run_id": run_id, "source": "Gaia DR3", "source_url": ARCHIVE,
        "row_count": len(records), "csv_sha256": csv_hash,
        "query_sha256": query_hash, "adql": ADQL,
        "selection_note": SELECTION, "imported_utc": utcnow(),
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--fetch", action="store_true", help="Fetch Gaia TAP CSV")
    source.add_argument("--csv", type=Path, help="Import saved Gaia TAP CSV")
    parser.add_argument("--db", type=Path, default=Path("data/echolens.sqlite"))
    parser.add_argument("--raw-out", type=Path, default=Path("data/raw/gaia_dr3_pilot_10000.csv"))
    parser.add_argument("--manifest", type=Path, default=Path("data/gaia_dr3_pilot_manifest.json"))
    args = parser.parse_args()
    raw = fetch_csv() if args.fetch else args.csv.read_bytes()
    retrieved = utcnow()
    # Validate before saving or touching the database.
    parse(raw)
    if args.fetch:
        args.raw_out.parent.mkdir(parents=True, exist_ok=True)
        args.raw_out.write_bytes(raw)
    manifest = import_csv(raw, args.db, retrieved_utc=retrieved)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "db": str(args.db), **manifest}, indent=2))

if __name__ == "__main__":
    main()
