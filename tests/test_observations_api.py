import hashlib
import json
import sqlite3
import struct

from fastapi.testclient import TestClient
import pytest
from app.main import app
from scripts.stage_lamost_auxiliary import SCHEMA

GAIA_ID = '4461930649238469760'


@pytest.fixture
def observation_db(tmp_path, monkeypatch):
    path = tmp_path/'observations.sqlite3'
    fields = [{'name': 'obsid', 'format': 'J', 'unit': None},
              {'name': 'teff_err', 'format': 'E', 'unit': 'K'}]
    with sqlite3.connect(path) as db:
        db.executescript(SCHEMA)
        for product in ['wd', 'qso']:
            db.execute('INSERT INTO imports VALUES (?,?,?,?)',
                       (product, '{"release":"DR9","counterpart_identity_certified":false}', json.dumps(fields), b''))
            raw = struct.pack('>if', 1, .125)
            db.execute('INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?)',
                       (product, 1, 0, 14400, GAIA_ID, '{"obsid":1,"teff_err":0.125}',
                        '{"nonfinite":[],"fits_null":[]}', hashlib.sha256(raw).hexdigest(), raw))
    monkeypatch.setenv('ECHOLENS_OBSERVATIONS_DB_PATH', str(path))
    return path


def test_unconfigured_or_missing_database_keeps_health_working(tmp_path, monkeypatch):
    monkeypatch.delenv('ECHOLENS_OBSERVATIONS_DB_PATH', raising=False)
    with TestClient(app) as c:
        assert c.get('/health').json() == {'status': 'ok'}
        assert c.get('/observations').status_code == 503
        missing = tmp_path/'missing.sqlite3'
        monkeypatch.setenv('ECHOLENS_OBSERVATIONS_DB_PATH', str(missing))
        assert c.get('/observations/catalogs').status_code == 503
        assert not missing.exists()


def test_exact_identifiers_product_keys_and_pagination(observation_db):
    with TestClient(app) as c:
        r = c.get('/observations', params={'reported_gaia_source_id': GAIA_ID, 'obsid': 1, 'limit': 1, 'offset': 1}).json()
        assert r['total'] == 2 and len(r['observations']) == 1
        assert r['observations'][0]['reported_gaia_source_id'] == GAIA_ID
        assert not r['counterpart_identity_certified']
        assert c.get('/observations', params={'product': 'wd', 'obsid': 1}).json()['total'] == 1


def test_detail_preserves_uncertainty_units_and_provenance(observation_db):
    before = observation_db.read_bytes()
    with TestClient(app) as c:
        r = c.get('/observations/wd/1').json()
        assert r['survey_reported_values']['teff_err'] == .125
        assert r['fields'][1]['unit'] == 'K'
        assert r['provenance']['release'] == 'DR9'
        assert r['native_row']['bytes'] == 8
        assert len(c.get('/observations/catalogs').json()['catalogs']) == 2
        assert c.post('/observations/wd/1', json={}).status_code == 405
    assert observation_db.read_bytes() == before


def test_invalid_queries_and_unknown_observations(observation_db):
    with TestClient(app) as c:
        for parameters in [{'limit': 201}, {'offset': -1}, {'obsid': 0},
                           {'reported_gaia_source_id': '4.461930649238469760e18'}, {'product': 'unknown'}]:
            assert c.get('/observations', params=parameters).status_code == 422
        assert c.get('/observations/wd/99').status_code == 404
        assert c.get('/observations/unknown/1').status_code == 422


def test_tampered_native_row_is_not_served(observation_db):
    with sqlite3.connect(observation_db) as db:
        db.execute("UPDATE observations SET native_row_bytes=? WHERE product='wd'", (b'changed',))
    with TestClient(app) as c:
        assert c.get('/observations/wd/1').status_code == 503
