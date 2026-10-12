"""Unit tests for SP01 P2A scanner: synthetic fixtures only except checksum regression."""
import json
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.sp01_p2a_blind_scan import (
    autocorrelation, blind_diagnostic_features, describe,
    fraction_around, longest_run, read_allspec, same_star_visit_overlap,
    window, read_archive
)

def fake_spectrum(wave=None, center=6610.0, depth=0.0):
    if wave is None:
        wave=np.linspace(6480,6740,4096)
    profile = depth*np.exp(-0.5*((wave-center)/.13)**2)
    return {
       "wave":np.asarray(wave,dtype=float),
       "sob": np.ones(len(wave))-profile,
       "smod":np.ones(len(wave)),
       "uob":np.ones(len(wave))*.01,
       "mob":np.ones(len(wave),dtype=bool)
    }

class BlindAuditTests(unittest.TestCase):
    def test_gaussian_absorption_is_recovered_near_injection(self):
        x=fake_spectrum(depth=.05)
        results=blind_diagnostic_features(x, top_n=5)
        self.assertLess(abs(results[0]["wavelength_A"]-6610), .2)
        self.assertGreater(results[0]["absorption_contrast_diagnostic"], 5)

    def test_trivial_flat_spectrum_does_not_create_absorption(self):
        x=fake_spectrum()
        found=blind_diagnostic_features(x,top_n=3)
        self.assertTrue(all(r["absorption_contrast_diagnostic"] == 0 for r in found))

    def test_masked_injected_line_is_not_reported(self):
        x=fake_spectrum(depth=.05)
        x["mob"][abs(x["wave"]-6610)<2]=False
        found=blind_diagnostic_features(x,top_n=10)
        self.assertTrue(all(abs(r["wavelength_A"]-6610)>2 for r in found))

    def test_excluded_pixel_statistics_differ(self):
        x=fake_spectrum(depth=.05)
        x["mob"][abs(x["wave"]-6610)<2]=False
        stat=describe(x)
        self.assertGreater(stat["fit_excluded"]["median_abs_z"], stat["fit_included"]["median_abs_z"])

    def test_stellar_repeat_same_input_correlates(self):
        w=np.linspace(6480,6740,4096)
        x=fake_spectrum(wave=w,depth=.05)
        y=fake_spectrum(wave=w,depth=.05)
        v=same_star_visit_overlap(x,y)
        self.assertGreater(v["red_overlap_correlation_of_fitted_z"], 0.99)

    def test_run_count(self):
        self.assertEqual(longest_run(np.array([True,True,False,True,True,True,False])),3)

    def test_lag_correlation_needs_data(self):
        self.assertIsNone(autocorrelation(np.array([0.,1.]),np.array([True,True]),1))

    def test_sha_block_before_reading(self):
        # ZIP contains arbitrary non-astronomical test bytes, must fail checksum.
        import tempfile, zipfile
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"test.zip"
            with zipfile.ZipFile(f,"w") as z: z.writestr("fake.fits", b"not astronomy")
            with self.assertRaises(ValueError):
                read_archive(f,"fake.fits","0"*64)

if __name__ == "__main__":
    unittest.main()
