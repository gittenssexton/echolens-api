import hashlib
import json
from pathlib import Path
import sqlite3
import struct
import tempfile
import unittest

from scripts.stage_lamost_auxiliary import SCHEMA, build, decode_row, inspect, layout, reported_id, search


class NativeStagingTests(unittest.TestCase):
    def test_exact_large_id_uncertainty_and_native_missing_encodings(self):
        columns = [{'name': 'obsid', 'format': 'J'},
                   {'name': 'gaia_source_id', 'format': '25A'},
                   {'name': 'teff_err', 'format': 'E'},
                   {'name': 'logg_err', 'format': 'E'},
                   {'name': 'quality', 'format': 'I', 'null': -9999}]
        gaia = '4461930649238469760'
        raw = struct.pack('>i', 1) + gaia.ljust(25).encode() + struct.pack('>ffh', 0.1234567, float('nan'), -9999)
        values, flags = decode_row(raw, layout(columns, len(raw)))
        self.assertEqual(reported_id(values['gaia_source_id']), gaia)
        nul_padded = raw[:4] + gaia.encode().ljust(25, b'\x00') + raw[29:]
        padded_values, _ = decode_row(nul_padded, layout(columns, len(raw)))
        self.assertEqual(padded_values['gaia_source_id'], gaia)
        self.assertEqual(reported_id(gaia + '\x00' * 6), gaia)
        self.assertEqual(values['teff_err'], struct.unpack('>f', struct.pack('>f', 0.1234567))[0])
        self.assertIsNone(values['logg_err'])
        self.assertEqual(values['quality'], -9999)
        self.assertEqual(flags['nonfinite'], [{'field': 'logg_err', 'element': 0}])
        self.assertEqual(flags['fits_null'], [{'field': 'quality', 'element': 0}])
        json.dumps(values, allow_nan=False)
        self.assertIsNone(reported_id('-9999'))
        self.assertIsNone(reported_id('9.223372036854776e18'))

    def test_unsupported_layout_and_incomplete_width_are_rejected(self):
        for columns, width in [([{'name': 'x', 'format': 'P'}], 8),
                               ([{'name': 'x', 'format': 'E'}], 8),
                               ([{'name': 'x', 'format': 'E'}, {'name': 'x', 'format': 'E'}], 8)]:
            with self.assertRaises(ValueError):
                layout(columns, width)

    def test_product_scoped_observation_keys_and_row_tampering(self):
        db = sqlite3.connect(':memory:')
        db.row_factory = sqlite3.Row
        db.executescript(SCHEMA)
        raw = b'\x00\x00\x00\x01'
        for product in ['wd', 'qso']:
            db.execute('INSERT INTO imports VALUES (?,?,?,?)', (product, '{}', '[]', b''))
            db.execute('INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?)',
                       (product, 1, 0, 2880, None, '{"obsid":1}', '{}', hashlib.sha256(raw).hexdigest(), raw))
        self.assertEqual(search(db, obsid=1)['total'], 2)
        self.assertEqual(search(db, product='wd', obsid=1)['total'], 1)
        self.assertEqual(inspect(db, 'wd', 1)['survey_reported_values'], {'obsid': 1})
        self.assertFalse(inspect(db, 'qso', 1)['counterpart_identity_certified'])
        self.assertIsNone(inspect(db, 'wd', 99))
        db.execute('UPDATE observations SET native_row_bytes=? WHERE product=?', (b'changed', 'wd'))
        with self.assertRaises(ValueError):
            inspect(db, 'wd', 1)
        db.close()

    def test_failed_input_never_publishes_or_replaces_a_database(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder)/'wrong.gz', Path(folder)/'stage.sqlite3'
            source.write_bytes(b'incomplete')
            with self.assertRaises(ValueError):
                build({'wd': source}, output)
            self.assertFalse(output.exists())
            output.write_bytes(b'keep existing bytes')
            with self.assertRaises(ValueError):
                build({'wd': source}, output)
            self.assertEqual(output.read_bytes(), b'keep existing bytes')


if __name__ == '__main__':
    unittest.main()
