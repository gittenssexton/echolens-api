import copy
import gzip
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from app.main import app
from scripts.import_gaia import build, parse_votable, query_for, validate, parse_snapshot

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture(scope='session')
def snapshot():
    payload = gzip.decompress((ROOT/'data/gaia_dr3.raw.gz').read_bytes())
    manifest = json.loads((ROOT/'data/gaia_dr3.manifest.json').read_text())
    fields, rows = parse_snapshot(payload,manifest,ROOT/'data')
    return payload, fields, rows

@pytest.fixture(scope='session')
def db(tmp_path_factory):
    path = tmp_path_factory.mktemp('registry')/'stars.sqlite3'
    build(ROOT/'data/gaia_dr3.raw.gz', ROOT/'data/gaia_dr3.manifest.json', path)
    return path

@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setenv('ECHOLENS_DB_PATH', str(db))
    with TestClient(app) as c:
        yield c

def test_real_snapshot_complete(snapshot, db):
    payload, fields, rows = snapshot
    assert validate(rows, 10000)['unique_source_ids'] == 10000
    assert {'parallax_error','ra_dec_corr','phot_g_mean_flux_error'} <= fields.keys()
    assert fields['parallax']['unit'] == 'mas'
    assert fields['phot_g_mean_flux_error']['unit']
    with sqlite3.connect(db) as c:
        assert c.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        actual = dict(c.execute('SELECT source_id, raw_json FROM stars'))
        assert len(actual) == 10000
        # Verify all imported values including nulls, uncertainties and 64-bit IDs.
        assert all(json.loads(actual[r['source_id']]) == r for r in rows)
        assert c.execute('SELECT COUNT(*) FROM interpretations').fetchone()[0] == 0

@pytest.mark.parametrize('mutation', ['duplicate','position','uncertainty','correlation','selection','order'])
def test_reject_invalid_rows(snapshot, mutation):
    rows = copy.deepcopy(snapshot[2][:2])
    if mutation == 'duplicate': rows[1]['source_id'] = rows[0]['source_id']
    if mutation == 'position': rows[0]['ra'] = 361
    if mutation == 'uncertainty': rows[0]['parallax_error'] = -1
    if mutation == 'correlation': rows[0]['ra_dec_corr'] = 2
    if mutation == 'selection': rows[0]['classprob_dsc_combmod_star'] = .1
    if mutation == 'order': rows.reverse()
    with pytest.raises(ValueError): validate(rows, 2)

def test_count_and_tap_failure(snapshot):
    with pytest.raises(ValueError): validate(snapshot[2], 10001)
    with pytest.raises(ValueError): parse_votable(b'<VOTABLE><RESOURCE><INFO name="QUERY_STATUS" value="OVERFLOW"/></RESOURCE></VOTABLE>')
    with pytest.raises(ValueError): query_for(0)

def test_failed_replay_preserves_database(db, tmp_path):
    manifest = json.loads((ROOT/'data/gaia_dr3.manifest.json').read_text())
    manifest['raw_sha256'] = 'bad'
    path = tmp_path/'bad.json'; path.write_text(json.dumps(manifest))
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    with pytest.raises(ValueError): build(ROOT/'data/gaia_dr3.raw.gz', path, db)
    assert hashlib.sha256(db.read_bytes()).hexdigest() == before

def test_api_search_and_exact_detail(client, snapshot):
    r = client.get('/stars', params={'limit':2}).json()
    assert r['total'] == 10000 and len(r['stars']) == 2
    sid = snapshot[2][0]['source_id']
    exact = client.get('/stars', params={'source_id':sid}).json()
    assert exact['total'] == 1 and exact['stars'][0]['source_id'] == sid
    detail = client.get('/stars/'+sid).json()
    assert detail['source_id'] == sid
    assert detail['measurements']['parallax_error']['value'] == snapshot[2][0]['parallax_error']
    assert 'teff_gspphot' in detail['catalog_inferences']
    assert detail['interpretations'] == []
    assert detail['provenance']['raw_sha256'] == hashlib.sha256(snapshot[0]).hexdigest()
    assert client.get('/stars', params={'g_max':0}).json()['total'] == 0
    page2 = client.get('/stars', params={'limit':2,'offset':2}).json()['stars']
    assert set(x['source_id'] for x in r['stars']).isdisjoint(x['source_id'] for x in page2)

@pytest.mark.parametrize('params',[{'source_id':"1' OR 1=1"},{'limit':201},{'offset':-1},{'ra_min':360},{'g_min':20,'g_max':10},{'g_max':'nan'}])
def test_invalid_search(client, params):
    assert client.get('/stars',params=params).status_code == 422

def test_missing_and_invalid_id(client):
    assert client.get('/stars/0').status_code == 404
    assert client.get('/stars/abc').status_code == 422
    assert client.get('/catalogs').json()['catalogs'][0]['provenance']['expected_rows'] == 10000

def test_stats_route_precedes_source_id(client):
    response = client.get('/stars/stats')
    assert response.status_code == 200
    result = response.json()
    assert result['database_loaded'] is True
    assert result['star_count'] == 10000
    assert result['ingestion_runs'] == 1
    assert result['catalogs'][0]['release'] == 'DR3'

def test_health_without_database(monkeypatch, tmp_path):
    monkeypatch.setenv('ECHOLENS_DB_PATH', str(tmp_path/'missing.sqlite3'))
    with TestClient(app) as client:
        assert client.get('/health').json() == {'status':'ok'}
        assert client.get('/').json() == {'service':'EchoLens API','status':'online','docs':'/docs'}
        assert client.get('/stars').status_code == 503
        assert client.get('/stars/stats').status_code == 503
    assert not (tmp_path/'missing.sqlite3').exists()

def test_offline_rebuild_same_logical_data(db, tmp_path):
    second = tmp_path/'second.sqlite3'
    build(ROOT/'data/gaia_dr3.raw.gz', ROOT/'data/gaia_dr3.manifest.json', second)
    with sqlite3.connect(db) as a, sqlite3.connect(second) as b:
        for table in ('stars','imports'):
            assert a.execute(f'SELECT * FROM {table} ORDER BY 1').fetchall() == b.execute(f'SELECT * FROM {table} ORDER BY 1').fetchall()

def test_independent_archive_spotcheck():
    from scripts.spotcheck_gaia import run
    assert run()['all_values_equal'] is True


def test_negative_parallax_is_not_negative_uncertainty(snapshot):
    rows = copy.deepcopy(snapshot[2][:2])
    rows[0]['parallax'] = -1.0
    rows[0]['parallax_over_error'] = -2.0
    assert validate(rows,2)['rows'] == 2

def test_fits_padding_and_tap_status_are_verified(snapshot):
    from io import BytesIO
    from astropy.io import fits
    manifest = json.loads((ROOT/'data/gaia_dr3.manifest.json').read_text())
    assert manifest['transport_padding_rows'] == 9
    assert snapshot[2][0]['parallax_error'] != round(snapshot[2][0]['parallax_error'],4)
    for kind in ('nonempty_padding','overflow'):
        with fits.open(BytesIO(snapshot[0]),memmap=False) as hdus:
            if kind == 'nonempty_padding':
                hdus[1].data['source_id'][-1] = 1
            else:
                hdus[1].header['VOKW1'] = 'VOTABLE.RESOURCE.INFO.QUERY_STATUS.<xmlattr>.value<VOEND>OVERFLOW'
            target = BytesIO(); hdus.writeto(target)
        with pytest.raises(ValueError): parse_snapshot(target.getvalue(),manifest,ROOT/'data')
