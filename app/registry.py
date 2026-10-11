"""Immutable catalog snapshots; observations and interpretations remain separate."""
import json
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / 'data' / 'registry.sqlite3'

def database_path():
    return Path(os.environ.get('ECHOLENS_DB_PATH', DEFAULT_DB))

def connect(path=None):
    path = Path(path or database_path())
    # Never create an empty database during a request.
    conn = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    return conn

SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE imports (
 id TEXT PRIMARY KEY, manifest_json TEXT NOT NULL, fields_json TEXT NOT NULL
);
CREATE TABLE stars (
 source_id TEXT PRIMARY KEY, import_id TEXT NOT NULL REFERENCES imports(id),
 ra REAL NOT NULL, dec REAL NOT NULL, g_mag REAL, bp_rp REAL,
 parallax REAL, ruwe REAL, raw_json TEXT NOT NULL
);
CREATE INDEX stars_g ON stars(g_mag, source_id);
CREATE INDEX stars_position ON stars(dec, ra);
CREATE INDEX stars_color ON stars(bp_rp, source_id);
CREATE TABLE observations (
 id INTEGER PRIMARY KEY, source_id TEXT NOT NULL REFERENCES stars(source_id),
 survey TEXT NOT NULL, release TEXT NOT NULL, external_id TEXT NOT NULL,
 epoch REAL, payload_json TEXT NOT NULL, provenance_json TEXT NOT NULL,
 UNIQUE(source_id, survey, release, external_id)
);
CREATE TABLE crossmatches (
 id INTEGER PRIMARY KEY, source_id TEXT NOT NULL REFERENCES stars(source_id),
 survey TEXT NOT NULL, release TEXT NOT NULL, external_id TEXT NOT NULL,
 separation_arcsec REAL CHECK(separation_arcsec>=0), match_epoch REAL,
 method TEXT NOT NULL, alternatives_json TEXT NOT NULL,
 provenance_json TEXT NOT NULL
);
CREATE TABLE interpretations (
 id INTEGER PRIMARY KEY, source_id TEXT NOT NULL REFERENCES stars(source_id),
 method TEXT NOT NULL, version TEXT NOT NULL, created_at TEXT NOT NULL,
 inputs_json TEXT NOT NULL, result_json TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('derived','ai_interpretation'))
);
'''

def star_detail(conn, source_id):
    row = conn.execute('SELECT * FROM stars WHERE source_id=?', (source_id,)).fetchone()
    if row is None:
        return None
    imp = conn.execute('SELECT * FROM imports WHERE id=?', (row['import_id'],)).fetchone()
    fields = json.loads(imp['fields_json'])
    raw = json.loads(row['raw_json'])
    measurements, catalog_inferences = {}, {}
    for name, value in raw.items():
        # These are Gaia pipeline estimates, not direct measurements or EchoLens AI.
        target = catalog_inferences if ('gspphot' in name or name.startswith(('classprob_', 'rv_template_'))) else measurements
        target[name] = {'value': value, **fields[name]}
    related = {}
    for table in ('observations', 'crossmatches', 'interpretations'):
        related[table] = [dict(r) for r in conn.execute(f'SELECT * FROM {table} WHERE source_id=? ORDER BY id', (source_id,))]
    return {'source_id': source_id, 'catalog': 'Gaia DR3',
            'measurements': measurements, 'catalog_inferences': catalog_inferences,
            'provenance': json.loads(imp['manifest_json']), **related}
