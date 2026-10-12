"""Synthetic engineering fixtures only; never treated as real stellar observations."""
import unittest
import struct
import tempfile
from pathlib import Path
from scripts.sp01_p2b_first_two import fits_summary, targets, paths, EXPECTED


def header(**kws):
    cards=[]
    for k,v in kws.items():
        cards.append(f'{k:<8}= {v!s:<70}'[:80].encode('ascii'))
    cards.append(b'END'+b' '*77)
    return b''.join(cards).ljust(2880,b' ')


def fixture(band='B',lo=4713.0):
    h=header(SIMPLE='T',BITPIX='-64',NAXIS='1',NAXIS1='1000',CRPIX1='1',CRVAL1=lo,CDELT1='0.04',BAND=f"'{band}'")
    body=struct.pack('>'+('d'*1000),*([0.0]*1000))
    return h+body.ljust(8640,b'\x00')

class Tests(unittest.TestCase):
    def test_expected_paired_ids(self):
        self.assertEqual(len(EXPECTED),2)
        self.assertEqual(len({a for a,b in EXPECTED}),2)
    def test_manifest_source_roles(self):
        import csv
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/'selected.csv'
            with f.open('w',newline='') as fd:
                w=csv.DictWriter(fd,fieldnames=['gaia_dr3_source_id','representative_sobject_id','role','stratum','teff','flag_sp','flag_red'])
                w.writeheader()
                for a,b in EXPECTED:w.writerow({'gaia_dr3_source_id':a,'representative_sobject_id':b,'role':'calibration'})
            self.assertEqual(len(targets(f)),2)
    def test_holdout_role_rejected(self):
        import csv
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/'selected.csv'
            with f.open('w',newline='') as fd:
                w=csv.DictWriter(fd,fieldnames=['gaia_dr3_source_id','representative_sobject_id','role'])
                w.writeheader()
                for a,b in EXPECTED:w.writerow({'gaia_dr3_source_id':a,'representative_sobject_id':b,'role':'holdout'})
            with self.assertRaisesRegex(ValueError,'Exactly|differs'):targets(f)
    def test_request_names_bounded(self):
        for _,visit in EXPECTED:
            u=paths(visit)
            self.assertEqual(len(u),4)
            self.assertTrue(all(visit in x[1] for x in u))
    def test_ssa_bad_band_blocked(self):
        with self.assertRaisesRegex(ValueError,'mislabeled'):
            fits_summary(fixture('I',7585),'ssa_G','G',EXPECTED[0][1])
    def test_ssa_correct_band(self):
        info=fits_summary(fixture('B',4713),'ssa_B','B',EXPECTED[0][1]);self.assertEqual(info['hdu_count'],1)
    def test_nonfits_rejected(self):
        with self.assertRaisesRegex(ValueError,'SIMPLE'):fits_summary(b'<html>no</html>','ssa_B','B',EXPECTED[0][1])
    def test_truncated_rejected(self):
        with self.assertRaisesRegex(ValueError,'truncated'):fits_summary(fixture()[:3000],'ssa_B','B',EXPECTED[0][1])

if __name__=='__main__':unittest.main()
