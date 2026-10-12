"""Synthetic FITS images here exercise engineering rules, not observations."""
import struct
import tempfile
import unittest
from pathlib import Path
from scripts.galah_ssa_integrity import audit, identify_camera, inspect


def synthetic_ssa(path, band, wmin, wstep=0.05, flux=1.25):
    """Build a minimal test-only image; no astronomical data are implied."""
    cards = [
        ('SIMPLE', 'T'), ('BITPIX', '-64'), ('NAXIS', '1'), ('NAXIS1', '4096'),
        ('CRPIX1', '1.0'), ('CRVAL1', str(wmin)), ('CDELT1', str(wstep)),
        ('PC1_1', '1.0'), ('BAND', "'"+band+"'"),
        ('WMIN', str(wmin)), ('WMAX', str(wmin+4095*wstep))]
    header = b''.join((f'{key:<8}= {val:<70}'[:80]).encode('ascii') for key, val in cards)
    header += b'END'+b' '*77
    header = header.ljust(((len(header)+2879)//2880)*2880,b' ')
    body = struct.pack('>4096d',*[flux]*4096)
    path.write_bytes((header+body).ljust(((len(header+body)+2879)//2880)*2880,b'\0'))


class IntegrityTests(unittest.TestCase):
    def test_real_arm_windows(self):
        self.assertEqual(identify_camera(5647,5872), 'G')
        self.assertEqual(identify_camera(7585,7887), 'I')

    def test_valid_single_green(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder)/'sample_SSA_transformed_G.fits'
            synthetic_ssa(file,'G',5648)
            self.assertTrue(inspect(file,'G')['arm_valid'])

    def test_ir_disguised_as_green(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder)/'sample_SSA_transformed_G.fits'
            synthetic_ssa(file,'I',7585)
            row = inspect(file,'G')
            self.assertTrue(row['quarantine'])
            self.assertEqual(row['actual_wavelength_arm'],'I')

    def test_cross_arm_duplicate_detection(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            g = folder/'sample_SSA_transformed_G.fits'
            i = folder/'sample_SSA_transformed_I.fits'
            synthetic_ssa(g,'G',5648)
            synthetic_ssa(i,'I',7585)
            result = audit({'G':g,'I':i})
            self.assertFalse(result['passed'])
            self.assertEqual(result['cross_arm_duplicate_payload_pairs'],[['G','I']])

    def test_wrong_WCS_vs_WMIN_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'sample_SSA_transformed_G.fits'
            synthetic_ssa(p,'G',5648)
            raw=p.read_bytes().replace(b'5648',b'7585',1)
            p.write_bytes(raw)
            with self.assertRaises(ValueError):inspect(p,'G')

if __name__ == '__main__':
    unittest.main()
