"""Synthetic data tests only. Not physical stellar observations."""
import unittest
from scripts.sp01_p2b_identity_lsf import source_check, TARGETS
class TestIDs(unittest.TestCase):
    def test_exact_original_matches(self):
        self.assertTrue(source_check([{'GALAH':v,'GaiaDR3':g} for g,v in TARGETS])['both_match'])
    def test_mismatches_block(self):
        self.assertFalse(source_check([{'GALAH':v,'GaiaDR3':'1234567890123456'} for g,v in TARGETS])['both_match'])
    def test_missing_block(self):
        self.assertFalse(source_check([{'GALAH':TARGETS[0][1],'GaiaDR3':TARGETS[0][0]}])['both_match'])
    def test_extraneous_rejected(self):
        with self.assertRaises(ValueError):source_check([{'GALAH':'170517001801299','GaiaDR3':'6130627011126533760'}])
if __name__=='__main__':unittest.main()
