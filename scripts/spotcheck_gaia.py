"""Independently re-query five frozen sample IDs; replay the check offline by default."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request
from scripts.import_gaia import ENDPOINT, parse_votable, parse_snapshot

ROOT = Path(__file__).resolve().parents[1]

def run(fetch=False):
    payload = gzip.decompress((ROOT/'data/gaia_dr3.raw.gz').read_bytes())
    manifest = json.loads((ROOT/'data/gaia_dr3.manifest.json').read_text())
    _, rows = parse_snapshot(payload,manifest,ROOT/'data')
    ids = [rows[i]['source_id'] for i in (0,2499,4999,7499,9999)]
    artifact = ROOT/'data/gaia_dr3.spotcheck.vot.xml.gz'
    record = ROOT/'data/gaia_dr3.spotcheck.json'
    if fetch:
        query = 'SELECT TOP 5 * FROM gaiadr3.gaia_source WHERE source_id IN (' + ','.join(ids) + ')'
        url = ENDPOINT+'?'+urllib.parse.urlencode({'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'votable','QUERY':query})
        with urllib.request.urlopen(url, timeout=180) as response:
            check = response.read()
        artifact.write_bytes(gzip.compress(check, mtime=0))
        record.write_text(json.dumps({'query':query,'request_url':url,
            'retrieved_at':datetime.now(timezone.utc).isoformat(),
            'raw_sha256':hashlib.sha256(check).hexdigest(),
            'sample_raw_sha256':hashlib.sha256(payload).hexdigest(),
            'source_ids':ids},indent=2)+'\n')
    check = gzip.decompress(artifact.read_bytes())
    metadata = json.loads(record.read_text())
    if metadata['raw_sha256'] != hashlib.sha256(check).hexdigest() or metadata['sample_raw_sha256'] != hashlib.sha256(payload).hexdigest():
        raise ValueError('Spot-check artifact checksum mismatch')
    _, checked = parse_votable(check)
    sample = {r['source_id']:r for r in rows}
    if len(checked) != 5 or {r['source_id'] for r in checked} != set(ids):
        raise ValueError('Unexpected spot-check identities')
    if not all(all(value == sample[r['source_id']].get(name) for name,value in r.items()) for r in checked):
        raise ValueError('Independent Gaia observations differ from frozen sample')
    return {'sources_verified':5,'columns_per_source':len(checked[0]),'all_values_equal':True}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    print(json.dumps(run(parser.parse_args().fetch),indent=2))
