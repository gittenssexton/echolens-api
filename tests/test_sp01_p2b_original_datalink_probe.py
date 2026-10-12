"""Tests based on synthetic structures only."""
import unittest
from scripts.sp01_p2b_original_datalink_probe import verify_eight_hdu, TARGETS, CAMERAS

class Tests(unittest.TestCase):
    def test_frozen_two_calibration_only(self):
        self.assertEqual(TARGETS,[('39909218369012608','151111003101245'),('4616578742686592','221003001101138')])
    def test_reject_html(self):
        with self.assertRaisesRegex(ValueError,'not a FITS'):
            verify_eight_hdu(b'<html>not found</html>','151111003101245','B')
    def test_reject_truncated_fits(self):
        with self.assertRaises(ValueError):verify_eight_hdu(b'SIMPLE  ='+b' '*2871, '151111003101245','B')
    def test_four_known_arms(self):
        self.assertEqual(set(CAMERAS),{'B','G','R','I'})

if __name__=='__main__':unittest.main()
