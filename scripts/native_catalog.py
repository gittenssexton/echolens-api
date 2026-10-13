"""Native snapshot parsers extracted unchanged from the archived registry importer; no DB writes."""
"""Fetch once, validate, then atomically build a replayable Gaia DR3 snapshot."""
import argparse
from io import BytesIO
from astropy.io.votable import parse
from astropy.table import Table
from astropy.io import fits
from astropy.units import UnitsWarning
import warnings
import numpy as np
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import tempfile
import time
from datetime import datetime, timezone
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


ENDPOINT = 'https://gea.esac.esa.int/tap-server/tap/sync'
DOC = 'https://gea.esac.esa.int/archive/documentation/GDR3/Gaia_archive/chap_datamodel/sec_dm_main_source_catalogue/ssec_dm_gaia_source.html'
VERSION = 'gaia-registry-v1'

def query_for(count, provider="esa"):
    table = {"esa":"gaiadr3.gaia_source", "irsa":"gaia_dr3_source"}[provider]
    if not 1 <= count <= 100000:
        raise ValueError('count must be 1..100000')
    return f'''SELECT TOP {count} * FROM {table}
WHERE random_index < 1000000
AND classprob_dsc_combmod_star >= 0.9
ORDER BY random_index ASC'''

def parse_votable(payload):
    root = ET.fromstring(payload)
    ns = {'v': root.tag.split('}')[0].strip('{')}
    statuses = root.findall('.//v:INFO[@name="QUERY_STATUS"]', ns)
    if not statuses or any(s.get('value') != 'OK' for s in statuses):
        raise ValueError('TAP error or truncated result: ' + ' '.join((s.text or s.get('value', '')) for s in statuses))
    table = root.find('.//v:TABLE', ns)
    if table is None:
        raise ValueError('Missing VOTable table')
    fields = {}
    for f in table.findall('v:FIELD', ns):
        name = f.attrib['name']
        if name in fields:
            raise ValueError('Duplicate column')
        fields[name] = {**dict(f.attrib), 'unit': f.get('unit'), 'datatype': f.get('datatype'),
                        'ucd': f.get('ucd'), 'description': f.findtext('v:DESCRIPTION', default='', namespaces=ns)}
    rows = []
    parsed = parse(BytesIO(payload)).get_first_table().to_table(use_names_over_ids=True)
    for record in parsed:
        row = {}
        for name in fields:
            val = record[name]
            if np.ma.is_masked(val):
                value = None
            elif hasattr(val, 'item'):
                value = val.item()
            else:
                value = val
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            if isinstance(value, str) and not value.strip():
                value = None
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f'Nonfinite {name}; explicit nulls required')
            row[name] = value
        for identifier in ('source_id', 'solution_id'):
            if identifier in row and row[identifier] is not None:
                row[identifier] = str(row[identifier])
        rows.append(row)
    return fields, rows

def parse_snapshot(payload, manifest, directory):
    if manifest.get('format') != 'FITS':
        return parse_votable(payload)
    if not payload.startswith(b'SIMPLE'):
        raise ValueError('Expected a native FITS response')
    metadata = gzip.decompress((Path(directory)/manifest['metadata_file']).read_bytes())
    if hashlib.sha256(metadata).hexdigest() != manifest['metadata_sha256']:
        raise ValueError('Field metadata checksum mismatch')
    fields, _ = parse_votable(metadata)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UnitsWarning)
        table = Table.read(BytesIO(payload), format='fits')
    # IRSA's FITS writer can count zero-filled transport padding as table rows.
    # Only trim trailing records whose numeric bytes are zero, text is blank and logical flags are false; never
    # truncate extra astronomical records merely to satisfy the expected count.
    with fits.open(BytesIO(payload), memmap=False) as hdus:
        statuses = [str(v).split('<VOEND>')[-1] for k,v in hdus[1].header.items() if str(k).startswith('VOKW') and 'QUERY_STATUS.<xmlattr>.value<VOEND>' in str(v)]
        if not statuses or any(value != 'OK' for value in statuses):
            raise ValueError('Missing, failed or truncated FITS TAP status')
        records = hdus[1].data.view(np.recarray)
        end = len(records)
        logical_offsets = [records.dtype.fields[c.name][1] for c in hdus[1].columns if c.format == 'L']
        text_ranges = [(records.dtype.fields[c.name][1],records.dtype.fields[c.name][0].itemsize) for c in hdus[1].columns if str(c.format).endswith('A')]
        def empty_transport_record(record):
            raw = bytearray(record.tobytes())
            for start, size in text_ranges:
                for offset in range(start,start+size):
                    if raw[offset] == ord(' '): raw[offset] = 0
            for offset in logical_offsets:
                if raw[offset] == ord('F'): raw[offset] = 0
            return not any(raw)
        while end and empty_transport_record(records[end-1]):
            end -= 1
        padding = len(records) - end
    if 'transport_padding_rows' in manifest and manifest['transport_padding_rows'] != padding:
        raise ValueError('Unexpected FITS padding change')
    manifest['transport_padding_rows'] = padding
    table = table[:end]
    if set(fields) != set(table.colnames):
        raise ValueError('FITS/metadata field mismatch')
    for name, info in fields.items():
        if 'precision' in info: info['display_precision'] = info.pop('precision')
        if 'irsa_format' in info: info['display_format'] = info.pop('irsa_format')
        info['native_dtype'] = str(table[name].dtype)
        info['serialization'] = 'native FITS; display precision does not limit stored values'
    rows = []
    for record in table:
        row = {}
        for name in fields:
            val = record[name]
            if np.ma.is_masked(val):
                val = None
            elif hasattr(val, 'item'):
                val = val.item()
            if isinstance(val, bytes): val = val.decode('utf-8')
            if isinstance(val, str): val = val.rstrip()
            # IEEE NaN is the FITS representation of missing floating values.
            if isinstance(val, float) and math.isnan(val): val = None
            if isinstance(val, float) and not math.isfinite(val):
                raise ValueError(f'Nonfinite {name}')
            if name in ('source_id','solution_id') and val is not None: val = str(val)
            row[name] = val
        rows.append(row)
    return fields, rows

