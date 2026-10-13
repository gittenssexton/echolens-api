import gzip
import struct
import tempfile
import unittest
from pathlib import Path
from scripts.repair_lamost_dr9 import validate


def fits_header(cards):
    data=''.join(c.ljust(80) for c in cards+['END']).encode('ascii')
    return data.ljust((len(data)+2879)//2880*2880,b' ')


def payload(ids):
    primary=fits_header(['SIMPLE  =                    T','BITPIX  =                    8','NAXIS   =                    0'])
    table=fits_header(["XTENSION= 'BINTABLE'",'BITPIX  =                    8','NAXIS   =                    2',
        'NAXIS1  =                    4',f'NAXIS2  = {len(ids):20d}','PCOUNT  =                    0',
        'GCOUNT  =                    1','TFIELDS =                    1',"TTYPE1  = 'obsid'","TFORM1  = 'J'"])
    rows=b''.join(struct.pack('>i',i) for i in ids)
    return primary+table+rows.ljust((len(rows)+2879)//2880*2880,b'\0')


class CatalogIntegrityTests(unittest.TestCase):
    def check(self,data,expected):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'catalog.fits.gz'; path.write_bytes(data)
            return validate(path,expected)

    def test_complete_catalog_and_exact_unique_ids(self):
        r=self.check(gzip.compress(payload([1,2,3])),3)
        self.assertTrue(r['whole_file_valid']); self.assertEqual(r['unique_obsids'],3)

    def test_missing_gzip_footer_is_rejected(self):
        with self.assertRaises(EOFError): self.check(gzip.compress(payload([1,2,3]))[:-8],3)

    def test_corrupt_gzip_crc_is_rejected(self):
        data=bytearray(gzip.compress(payload([1,2,3]))); data[-8]^=1
        with self.assertRaises(gzip.BadGzipFile): self.check(data,3)

    def test_incomplete_fits_and_wrong_release_rows_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'payload'): self.check(gzip.compress(payload([1,2,3])[:-2880]),3)
        with self.assertRaisesRegex(ValueError,'row count'): self.check(gzip.compress(payload([1,2,3])),4)

    def test_duplicate_and_invalid_observation_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'): self.check(gzip.compress(payload([1,1,3])),3)
        with self.assertRaisesRegex(ValueError,'Invalid'): self.check(gzip.compress(payload([1,0,3])),3)


if __name__=='__main__': unittest.main()
