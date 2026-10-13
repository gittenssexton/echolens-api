"""Offline replay of the two independently retrieved DR9 auxiliary catalog audits."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from scripts.repair_lamost_dr9 import validate

PRODUCTS = {
    'wd': {'file': 'dr9_v2.0_LRS_wd.fits.gz', 'rows': 14691,
           'sha256': '8ecfa5859c0cd7b7b6fc26677944da00db44872d12b76bd947cf66e54da75068',
           'drive_file_id': '1QTeu_VB9x4DiXEAirwkTDgWUY7Blq58N'},
    'qso': {'file': 'dr9_v2.0_LRS_qso.fits.gz', 'rows': 18142,
            'sha256': '53fe3148e123ee468bd50a901aabb762baa23c427531ae5ac994d250cc46d41c',
            'drive_file_id': '1awc0hYB6Lbmc84_W8Go9-1lsv6BjLhFB'},
}


def audit(path, product):
    reference = PRODUCTS[product]
    sha = hashlib.sha256()
    with Path(path).open('rb') as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b''):
            sha.update(chunk)
    if sha.hexdigest() != reference['sha256']:
        raise ValueError('Bytes differ from the independently verified archive; re-audit required')
    result = validate(path, expected_rows=reference['rows'])
    return {'release': 'LAMOST DR9 v2.0 LRS', 'product': product,
            'reference': reference,
            'count_reference_url': 'https://www.lamost.org/dr9/v2.0/',
            'replayed_at': datetime.now(timezone.utc).isoformat(),
            'scope': 'File integrity and observation-key verification only',
            'main_catalog_recovered': False,
            'counterpart_identity_certified': False,
            'validation': result}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('product', choices=PRODUCTS)
    parser.add_argument('file')
    args = parser.parse_args()
    print(json.dumps(audit(args.file, args.product), indent=2))
