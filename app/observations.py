"""Optional read-only access to separately staged survey observations."""
from contextlib import contextmanager
import json
import os
import sqlite3
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Path, Query
from scripts.stage_lamost_auxiliary import connect, inspect, search

router = APIRouter(prefix='/observations', tags=['Survey observations'])
Product = Literal['wd', 'qso']


@contextmanager
def observations():
    path = os.environ.get('ECHOLENS_OBSERVATIONS_DB_PATH')
    if not path:
        raise HTTPException(503, 'Survey observations unavailable')
    try:
        db = connect(path)
    except (sqlite3.Error, ValueError):
        raise HTTPException(503, 'Survey observations unavailable')
    try:
        yield db
    finally:
        db.close()


@router.get('')
def search_observations(
    product: Product | None = None,
    reported_gaia_source_id: Annotated[str | None, Query(pattern=r'^[0-9]{1,19}$')] = None,
    obsid: Annotated[int | None, Query(ge=1)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
):
    with observations() as db:
        return search(db, product, reported_gaia_source_id, obsid, limit, offset)


@router.get('/catalogs')
def observation_catalogs():
    with observations() as db:
        rows = db.execute('SELECT product,provenance_json,fields_json FROM imports ORDER BY product').fetchall()
    return {'catalogs': [{'product': r['product'], 'provenance': json.loads(r['provenance_json']),
                          'fields': json.loads(r['fields_json'])} for r in rows],
            'physical_counterparts_certified': False}


@router.get('/{product}/{obsid}')
def inspect_observation(product: Product, obsid: Annotated[int, Path(ge=1)]):
    with observations() as db:
        try:
            result = inspect(db, product, obsid)
        except ValueError:
            raise HTTPException(503, 'Observation integrity check failed')
    if result is None:
        raise HTTPException(404, 'Observation not in this snapshot')
    return result
