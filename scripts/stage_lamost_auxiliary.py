"""Build/search an isolated native-observation store; never modify the Gaia registry."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import struct
import tempfile

from scripts.audit_lamost_auxiliary import audit

SCHEMA = '''
CREATE TABLE imports (
 product TEXT PRIMARY KEY, provenance_json TEXT NOT NULL,
 fields_json TEXT NOT NULL, fits_header_bytes BLOB NOT NULL
);
CREATE TABLE observations (
 product TEXT NOT NULL REFERENCES imports(product), obsid INTEGER NOT NULL,
 row_index INTEGER NOT NULL, fits_offset INTEGER NOT NULL,
 reported_gaia_source_id TEXT, values_json TEXT NOT NULL,
 encoding_flags_json TEXT NOT NULL, row_sha256 TEXT NOT NULL,
 native_row_bytes BLOB NOT NULL,
 PRIMARY KEY(product, obsid), UNIQUE(product, row_index)
);
CREATE INDEX observations_gaia ON observations(reported_gaia_source_id);
PRAGMA user_version = 1;
'''


def layout(columns, row_bytes):
    """Only fixed-width native types used by the audited sources are supported."""
    fields = []
    offset = 0
    names = set()
    sizes = {'A': 1, 'I': 2, 'J': 4, 'K': 8, 'E': 4, 'D': 8}
    for col in columns:
        match = re.fullmatch(r'(\d*)([AIJKED])', col['format'])
        if not match or not col['name'] or col['name'] in names:
            raise ValueError('Unsupported or duplicate FITS field')
        count, kind = int(match[1] or 1), match[2]
        if count < 1:
            raise ValueError('Invalid FITS field repeat count')
        size = count * sizes[kind]
        fields.append((col, offset, count, kind, size))
        offset += size
        names.add(col['name'])
    if offset != row_bytes:
        raise ValueError('Field widths do not cover the native FITS row')
    return fields


def decode_row(raw, fields):
    values, flags = {}, {'nonfinite': [], 'fits_null': []}
    formats = {'I': 'h', 'J': 'i', 'K': 'q', 'E': 'f', 'D': 'd'}
    for col, offset, count, kind, size in fields:
        name = col['name']
        if kind == 'A':
            value = raw[offset:offset + size].decode('ascii').rstrip(' \x00')
        else:
            decoded = list(struct.unpack_from('>' + str(count) + formats[kind], raw, offset))
            for i, value in enumerate(decoded):
                if isinstance(value, float) and not math.isfinite(value):
                    flags['nonfinite'].append({'field': name, 'element': i})
                    decoded[i] = None
                elif col.get('null') is not None and value == col['null']:
                    flags['fits_null'].append({'field': name, 'element': i})
            value = decoded[0] if count == 1 else decoded
        values[name] = value
    # Integer sentinels remain literal; flags explain native FITS null encodings.
    # Original row bytes retain all padding, precision and NaN payloads.
    return values, flags


def reported_id(value):
    if isinstance(value, str):
        value = value.strip(' \x00')
        if re.fullmatch(r'[0-9]{1,19}', value) and 0 < int(value) <= 2**63 - 1:
            return value
    return None


def build(sources, output):
    output = Path(output)
    if output.exists():
        raise ValueError('Refusing to replace an existing database')
    if not sources:
        raise ValueError('No sources supplied')
    # Validate all input bytes before creating a candidate database.
    reports = {product: audit(path, product) for product, path in sources.items()}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as staging:
        candidate = Path(staging) / 'candidate.sqlite3'
        with sqlite3.connect(candidate) as db:
            db.execute('PRAGMA foreign_keys=ON')
            db.executescript(SCHEMA)
            for product, path in sources.items():
                report = reports[product]
                table = next(h for h in report['validation']['hdus'] if h['type'] == 'BINTABLE')
                fields = layout(table['columns'], table['row_bytes'])
                with gzip.open(path, 'rb') as src:
                    headers = src.read(table['data_start'])
                    # Scaling changes numerical meaning; reject rather than silently ignoring it.
                    if any(headers[i:i+8].strip().startswith((b'TSCAL', b'TZERO'))
                           for i in range(0, len(headers), 80)):
                        raise ValueError('Scaled FITS fields need a separately reviewed decoder')
                    provenance = dict(report, staged_at=datetime.now(timezone.utc).isoformat(),
                                      source_path=Path(path).name,
                                      encoding='native FITS row plus finite decoded JSON',
                                      implementation_sha256={name: hashlib.sha256(
                                          (Path(__file__).parent / name).read_bytes()).hexdigest()
                                          for name in ['stage_lamost_auxiliary.py',
                                                       'audit_lamost_auxiliary.py', 'repair_lamost_dr9.py']},
                                      survey_sentinels='Preserved literally; no undocumented imputation')
                    db.execute('INSERT INTO imports VALUES (?,?,?,?)',
                               (product, json.dumps(provenance, allow_nan=False),
                                json.dumps(table['columns']), headers))
                    for index in range(table['rows']):
                        raw = src.read(table['row_bytes'])
                        if len(raw) != table['row_bytes']:
                            raise ValueError('Short native row during staging')
                        values, flags = decode_row(raw, fields)
                        db.execute('INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?)',
                                   (product, values['obsid'], index,
                                    table['data_start'] + index * table['row_bytes'],
                                    reported_id(values.get('gaia_source_id')),
                                    json.dumps(values, allow_nan=False), json.dumps(flags),
                                    hashlib.sha256(raw).hexdigest(), raw))
                count = db.execute('SELECT COUNT(*) FROM observations WHERE product=?', (product,)).fetchone()[0]
                if count != table['rows']:
                    raise ValueError('Staging row count mismatch')
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('SQLite integrity failure')
            if db.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('Source provenance reference failure')
        # Atomic publication refuses a target created by another process meanwhile.
        os.link(candidate, output)
    return {'rows': sum(r['validation']['rows'] for r in reports.values()),
            'products': list(reports), 'database_bytes': output.stat().st_size}


def connect(path):
    uri = Path(path).resolve().as_uri() + '?mode=ro'
    db = sqlite3.connect(uri, uri=True)
    db.row_factory = sqlite3.Row
    if db.execute('PRAGMA user_version').fetchone()[0] != 1:
        db.close()
        raise ValueError('Unsupported staging database version')
    return db


def search(db, product=None, gaia_source_id=None, obsid=None, limit=50):
    if not 1 <= limit <= 200:
        raise ValueError('Limit must be between 1 and 200')
    clauses, params = [], []
    for column, value in [('product', product), ('reported_gaia_source_id', gaia_source_id), ('obsid', obsid)]:
        if value is not None:
            clauses.append(column + '=?')
            params.append(value)
    where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
    total = db.execute('SELECT COUNT(*) FROM observations' + where, params).fetchone()[0]
    rows = db.execute('SELECT product,obsid,reported_gaia_source_id,row_index,row_sha256 '
                      'FROM observations' + where + ' ORDER BY product,obsid LIMIT ?', [*params, limit]).fetchall()
    return {'total': total, 'observations': [dict(r) for r in rows],
            'counterpart_identity_certified': False}


def inspect(db, product, obsid):
    row = db.execute('SELECT * FROM observations WHERE product=? AND obsid=?', (product, obsid)).fetchone()
    if row is None:
        return None
    source = db.execute('SELECT provenance_json,fields_json FROM imports WHERE product=?', (product,)).fetchone()
    if hashlib.sha256(row['native_row_bytes']).hexdigest() != row['row_sha256']:
        raise ValueError('Stored native row checksum mismatch')
    return {'product': product, 'obsid': obsid,
            'survey_reported_values': json.loads(row['values_json']),
            'native_encoding_flags': json.loads(row['encoding_flags_json']),
            'fields': json.loads(source['fields_json']),
            'provenance': json.loads(source['provenance_json']),
            'native_row': {'row_index': row['row_index'], 'fits_offset': row['fits_offset'],
                           'bytes': len(row['native_row_bytes']), 'sha256': row['row_sha256']},
            'counterpart_identity_certified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('build')
    create.add_argument('--wd', required=True)
    create.add_argument('--qso', required=True)
    create.add_argument('--output', required=True)
    for name in ('search', 'inspect'):
        cmd = commands.add_parser(name)
        cmd.add_argument('--db', required=True)
        cmd.add_argument('--product', choices=['wd', 'qso'], required=name == 'inspect')
        cmd.add_argument('--obsid', type=int, required=name == 'inspect')
        if name == 'search':
            cmd.add_argument('--gaia-source-id')
            cmd.add_argument('--limit', type=int, default=50)
    args = parser.parse_args()
    if args.command == 'build':
        result = build({'wd': args.wd, 'qso': args.qso}, args.output)
    else:
        db = connect(args.db)
        try:
            result = inspect(db, args.product, args.obsid) if args.command == 'inspect' else search(
                db, args.product, args.gaia_source_id, args.obsid, args.limit)
        finally:
            db.close()
    print(json.dumps(result, indent=2, allow_nan=False))
