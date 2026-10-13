import math
import unittest

from scripts.wd_counterpart_pilot import assess, covariance, propagate, separation


def row(source='123', ra=10):
    return {'source_id': source, 'ra': ra, 'dec': 30, 'ref_epoch': 2016,
            'pmra': 0., 'pmdec': 0.}


class CounterpartTests(unittest.TestCase):
    def test_spherical_wrap_and_polar_motion(self):
        self.assertAlmostEqual(separation(359.999, 0, .001, 0), 7.2, places=7)
        r = dict(row(), ra=359.9999, dec=0, pmra=1000)
        a, d = propagate(r, 2017)
        self.assertTrue(0 < a < .001)
        self.assertAlmostEqual(separation(r['ra'], 0, a, d), 1., places=7)
        r.update(dec=89.999999)
        self.assertTrue(all(math.isfinite(x) for x in propagate(r, 2017)))

    def test_missing_motion_is_not_zero_motion(self):
        with self.assertRaises(ValueError):
            propagate(dict(row(), pmra=None), 2012)

    def test_covariance_uses_native_cosdec_and_cross_terms(self):
        r = dict(row(), ra_error=2., dec_error=3., pmra_error=1., pmdec_error=2.,
                 ra_dec_corr=.1, ra_pmra_corr=.5, ra_pmdec_corr=.2,
                 dec_pmra_corr=.3, dec_pmdec_corr=.4, pmra_pmdec_corr=.25)
        c = covariance(r, 2018)['matrix_mas2']
        self.assertAlmostEqual(c[0][0], 12.)
        self.assertAlmostEqual(c[1][1], 34.6)
        self.assertAlmostEqual(c[0][1], 6.)
        self.assertIsNone(covariance(row(), 2018))

    def test_ambiguity_missing_neighbors_and_absent_id_remain_explicit(self):
        s = {'obsid': 1, 'reported_gaia_source_id': '123',
             'lamost': {'obsdate': '2012-01-01', 'ra': 10., 'dec': 30., 'ra_obs': 10., 'dec_obs': 30.}}
        self.assertEqual(assess(s, {}, {}, 3)['status'], 'REPORTED_ID_NOT_FOUND')
        exact = {'123': row()}
        a = assess(s, exact, {}, 3)
        self.assertEqual(a['status'], 'SINGLE_POSITION_SUPPORT_CONDITIONAL')
        self.assertFalse(a['physical_counterpart_certified'])
        self.assertEqual(assess(s, exact, {'456': row('456', 10.0005)}, 3)['status'], 'MULTIPLE_POSITION_COMPATIBLE')
        self.assertEqual(assess(s, exact, {'456': dict(row('456', 10.0005), pmra=None)}, 3)['status'], 'UNRESOLVED_NEIGHBOR')
        self.assertEqual(assess(s, {'123': row('123', 10.01)}, {}, 3)['status'], 'POSITION_DISAGREEMENT')


if __name__ == '__main__':
    unittest.main()
