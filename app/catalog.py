"""Read-only searchable Gaia DR3 stellar registry.

Measured fields come from Gaia DR3; this module does not compute anomaly scores.
Database path is set with ECHOLENS_DB_PATH (default data/echolens.sqlite).
"""
import os
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS ingestion_runs (
  run_id TEXT PRIMARY KEY,
  catalog TEXT NOT NULL,
  source_url TEXT NOT NULL,
  adql TEXT NOT NULL,
  query_sha256 TEXT NOT NULL,
  csv_sha256 TEXT NOT NULL,
  retrieved_utc TEXT NOT NULL,
  imported_utc TEXT NOT NULL,
  row_count INTEGER NOT NULL,
  selection_note TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS stars (
  source_id TEXT PRIMARY KEY,
  ra REAL NOT NULL,
  dec REAL NOT NULL,
  parallax REAL,
  parallax_error REAL,
  parallax_over_error REAL,
  pmra REAL,
  pmra_error REAL,
  pmdec REAL,
  pmdec_error REAL,
  phot_g_mean_mag REAL,
  phot_g_mean_flux_over_error REAL,
  bp_rp REAL,
  ruwe REAL,
  random_index INTEGER,
  run_id TEXT NOT NULL REFERENCES ingestion_runs(run_id),
  catalog_release TEXT NOT NULL DEFAULT 'Gaia DR3'
);
CREATE INDEX IF NOT EXISTS stars_g_mag_idx ON stars(phot_g_mean_mag);
CREATE INDEX IF NOT EXISTS stars_color_idx ON stars(bp_rp);
CREATE INDEX IF NOT EXISTS stars_parallax_idx ON stars(parallax);
CREATE INDEX IF NOT EXISTS stars_run_idx ON stars(run_id);
"""

def database_path():
    return Path(os.environ.get("ECHOLENS_DB_PATH", "data/echolens.sqlite"))

def connect(path=None, create=False):
    path = Path(path) if path else database_path()
    if not create and not path.is_file():
        return None
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    if create:
        connection.executescript(SCHEMA)
    return connection

def list_stars(limit=50, offset=0, max_g_mag=None, min_parallax=None, path=None):
    db = connect(path)
    if db is None:
        return {"total": 0, "limit": limit, "offset": offset, "stars": [], "database_loaded": False}
    try:
        where, args = [], []
        if max_g_mag is not None:
            where.append("phot_g_mean_mag <= ?")
            args.append(max_g_mag)
        if min_parallax is not None:
            where.append("parallax >= ?")
            args.append(min_parallax)
        predicate = (" WHERE " + " AND ".join(where)) if where else ""
        total = db.execute("SELECT count(*) FROM stars" + predicate, args).fetchone()[0]
        rows = db.execute("SELECT * FROM stars" + predicate + " ORDER BY source_id LIMIT ? OFFSET ?", args + [limit, offset]).fetchall()
        return {"total": total, "limit": limit, "offset": offset, "stars": [dict(row) for row in rows], "database_loaded": True}
    finally:
        db.close()

def get_star(source_id, path=None):
    db = connect(path)
    if db is None:
        return None
    try:
        row = db.execute("""
          SELECT s.*, r.source_url, r.adql, r.query_sha256, r.csv_sha256,
                 r.retrieved_utc, r.selection_note
          FROM stars s JOIN ingestion_runs r ON s.run_id = r.run_id
          WHERE s.source_id = ?
        """, (str(source_id),)).fetchone()
        return dict(row) if row else None
    finally:
        db.close()

def stats(path=None):
    db = connect(path)
    if db is None:
        return {"database_loaded": False, "star_count": 0, "ingestion_runs": 0}
    try:
        return {
            "database_loaded": True,
            "star_count": db.execute("SELECT count(*) FROM stars").fetchone()[0],
            "ingestion_runs": db.execute("SELECT count(*) FROM ingestion_runs").fetchone()[0],
        }
    finally:
        db.close()
