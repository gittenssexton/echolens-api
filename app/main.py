from contextlib import contextmanager
import json
import sqlite3
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from app.registry import connect, star_detail
from app.observations import router as observations_router

app = FastAPI(title='EchoLens API', version='0.2.0')
app.include_router(observations_router)

@app.get('/')
def root():
    return {'service': 'EchoLens API', 'status': 'online', 'docs': '/docs'}

@app.get('/health')
def health():
    return {'status': 'ok'}

@contextmanager
def registry():
    try:
        c = connect()
    except sqlite3.OperationalError:
        raise HTTPException(503, 'Stellar registry unavailable; run the offline importer')
    try:
        yield c
    finally:
        c.close()

@app.get('/stars')
def search_stars(
    source_id: Annotated[str | None, Query(pattern=r'^[0-9]{1,19}$')] = None,
    g_min: Annotated[float | None, Query(allow_inf_nan=False)] = None, g_max: Annotated[float | None, Query(allow_inf_nan=False)] = None,
    color_min: Annotated[float | None, Query(allow_inf_nan=False)] = None, color_max: Annotated[float | None, Query(allow_inf_nan=False)] = None,
    parallax_min: Annotated[float | None, Query(allow_inf_nan=False)] = None, parallax_max: Annotated[float | None, Query(allow_inf_nan=False)] = None,
    ra_min: Annotated[float | None, Query(ge=0, lt=360)] = None,
    ra_max: Annotated[float | None, Query(ge=0, lt=360)] = None,
    dec_min: Annotated[float | None, Query(ge=-90, le=90)] = None,
    dec_max: Annotated[float | None, Query(ge=-90, le=90)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
):
    clauses, params = [], []
    if source_id is not None:
        clauses.append('source_id = ?'); params.append(source_id)
    for column, low, high in [('g_mag', g_min, g_max), ('bp_rp', color_min, color_max),
                             ('parallax', parallax_min, parallax_max),
                             ('ra', ra_min, ra_max), ('dec', dec_min, dec_max)]:
        if low is not None and high is not None and low > high:
            raise HTTPException(422, f'{column}: minimum exceeds maximum; split RA wraparound into two searches')
        if low is not None:
            clauses.append(column + ' >= ?'); params.append(low)
        if high is not None:
            clauses.append(column + ' <= ?'); params.append(high)
    where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
    with registry() as c:
        total = c.execute('SELECT COUNT(*) FROM stars' + where, params).fetchone()[0]
        rows = c.execute('SELECT source_id, ra, dec, g_mag, bp_rp, parallax, ruwe, import_id FROM stars' + where + ' ORDER BY source_id LIMIT ? OFFSET ?', [*params, limit, offset]).fetchall()
    return {'total':total, 'limit':limit, 'offset':offset,
            'units':{'ra':'deg','dec':'deg','g_mag':'mag','bp_rp':'mag','parallax':'mas'},
            'stars':[dict(r) for r in rows], 'detail_endpoint':'/stars/{source_id}'}

@app.get('/stars/stats')
def star_stats():
    # Register before the dynamic source-ID route.
    with registry() as c:
        count = c.execute('SELECT COUNT(*) FROM stars').fetchone()[0]
        imports = c.execute('SELECT id, manifest_json FROM imports ORDER BY id').fetchall()
    return {'database_loaded': True, 'star_count': count, 'ingestion_runs': len(imports),
            'catalogs': [{'import_id': r['id'], 'catalog': json.loads(r['manifest_json'])['catalog'],
                         'release': json.loads(r['manifest_json'])['release']} for r in imports]}

@app.get('/stars/{source_id}')
def inspect_star(source_id: str):
    if not source_id.isascii() or not source_id.isdigit() or not 1 <= len(source_id) <= 19:
        raise HTTPException(422, 'Expected exact decimal Gaia source ID')
    with registry() as c:
        result = star_detail(c, source_id)
    if result is None: raise HTTPException(404, 'Star not in this registry snapshot')
    return result

@app.get('/catalogs')
def catalogs():
    with registry() as c:
        rows = c.execute('SELECT manifest_json, fields_json FROM imports ORDER BY id').fetchall()
    return {'catalogs':[{'provenance':json.loads(r['manifest_json']), 'fields':json.loads(r['fields_json'])} for r in rows]}
