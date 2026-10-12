"""Fail-closed quality gate for GALAH DR4 Data Central SSA FITS products.

Reads only the primary 1-D, big-endian 64-bit FITS image class seen in the
bounded audit. An SSA transformation is never equated to a native reduced FITS.
This is wavelength-arm / duplicated-payload validation, not a calibration or
science/anomaly classifier. Zero additional HTTP requests.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

# Deliberately tolerant ranges to allow edge shifts across fibres/exposures.
# A midpoint *outside* the declared camera is a hard block.
ARMS = {'B': (4700, 4920), 'G': (5630, 5900),
        'R': (6460, 6760), 'I': (7570, 7910)}


def read_header(data: bytes) -> tuple[dict, int]:
    """Decode the primary FITS keyword cards without accepting extensions."""
    values = {}
    for offset in range(0, min(len(data), 2880 * 24), 80):
        card = data[offset: offset+80].decode('ascii', 'strict')
        key = card[:8].strip()
        if key == 'END':
            return values, ((offset + 80 + 2879) // 2880) * 2880
        if card[8:10] == '= ':
            literal = card[10:80].split(' / ')[0].strip()
            if literal.startswith("'"):
                values[key] = literal.split("'", 2)[1].strip()
            else:
                values[key] = literal
    raise ValueError('No primary FITS END card within 24 blocks')


def identify_camera(low: float, high: float) -> str | None:
    if not (math.isfinite(low) and math.isfinite(high) and low < high):
        raise ValueError('Invalid wavelength range')
    middle = (low + high) / 2.0
    matches = [camera for camera, (start, end) in ARMS.items()
               if start <= middle <= end]
    return matches[0] if len(matches) == 1 else None


def inspect(path: Path, expected: str) -> dict:
    expected = expected.upper()
    if expected not in ARMS:
        raise ValueError(f'Unknown expected camera: {expected}')
    b = path.read_bytes()
    h, offset = read_header(b)
    if h.get('SIMPLE') != 'T' or h.get('BITPIX') != '-64' or h.get('NAXIS') != '1':
        raise ValueError(f'{path.name}: not a supported one-HDU 1D double-precision SSA image')
    n = int(h.get('NAXIS1', '0'))
    if n < 1000 or n > 100_000 or len(b) < offset + 8 * n:
        raise ValueError(f'{path.name}: invalid pixel dimensions/truncated image')
    payload = b[offset:offset + 8*n]
    cdelt = float(h['CDELT1'])
    pc = float(h.get('PC1_1', 1.0))
    crpix = float(h.get('CRPIX1', 1.0))
    crval = float(h['CRVAL1'])
    low = crval + (1-crpix)*cdelt*pc
    high = crval + (n-crpix)*cdelt*pc
    if low > high:
        low, high = high, low
    if 'WMIN' in h and abs(float(h['WMIN']) - low) > 3:
        raise ValueError(f'{path.name}: WMIN contradicts wavelength WCS')
    if 'WMAX' in h and abs(float(h['WMAX']) - high) > 3:
        raise ValueError(f'{path.name}: WMAX contradicts wavelength WCS')
    observed = identify_camera(low, high)
    declared = str(h.get('BAND', '')).upper()
    filename_ok = path.name.endswith('_SSA_transformed_' + expected + '.fits')
    accepted = observed == expected and declared == expected and filename_ok
    return {'filename': path.name, 'expected_arm': expected,
            'actual_wavelength_arm': observed, 'FITS_BAND': declared,
            'wavelength_min_A': round(low, 5), 'wavelength_max_A': round(high, 5),
            'pixel_count': n, 'file_sha256': hashlib.sha256(b).hexdigest(),
            'payload_sha256': hashlib.sha256(payload).hexdigest(),
            'filename_matches_arm': filename_ok, 'arm_valid': accepted,
            'quarantine': not accepted,
            'product_kind': 'SSA-transformed one-HDU image, NOT native reduction'}


def audit(inputs: dict[str, Path]) -> dict:
    rows = [inspect(path, arm) for arm, path in sorted(inputs.items())]
    collisions = []
    for i, first in enumerate(rows):
        for second in rows[i+1:]:
            if first['payload_sha256'] == second['payload_sha256']:
                first['quarantine'] = second['quarantine'] = True
                first['arm_valid'] = second['arm_valid'] = False
                collisions.append([first['expected_arm'], second['expected_arm']])
    return {'schema': 'echolens-galah-ssa-integrity-v1',
            'rows': rows, 'cross_arm_duplicate_payload_pairs': collisions,
            'passed': bool(rows) and all(not row['quarantine'] for row in rows),
            'wavelength_convention': 'air (GALAH DR4 source manuscript calibration paragraph)',
            'wavelength_rule': 'For comparisons, convert lab vacuum lines to air explicitly; no line IDs inferred',
            'science_ready': False,
            'native_detector_masks_verified': False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ssa', action='append', nargs=2, metavar=('ARM', 'FILE'), required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    inputs = {}
    for arm, filepath in args.ssa:
        if arm.upper() in inputs:
            parser.error('Duplicate expected arm in input')
        inputs[arm.upper()] = Path(filepath)
    result = audit(inputs)
    value = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(value, encoding='utf-8')
    else:
        print(value, end='')
    if not result['passed']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
