import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import urllib.parse
from scripts.wd_ten_pilots import color, wise_quality, p10, request_catalog


class PilotRulesTests(unittest.TestCase):
    def test_color_retains_correlation_bounds_without_excess_claim(self):
        r=color(15.,.1,14.,.2)
        self.assertEqual(r['color_mag'],1.)
        self.assertAlmostEqual(r['sigma_correlation_bounds_mag'][0],.1)
        self.assertAlmostEqual(r['sigma_correlation_bounds_mag'][1],.3)
        self.assertTrue(r['conservative_three_sigma_zero_reference_flag'])
        self.assertIn('not a fitted photosphere',r['scope'])
        self.assertIsNone(color(15.,None,14.,.2))
        self.assertIsNone(color(15.,0,14.,.2))

    def test_upper_limit_and_contamination_cannot_pass_detection_gate(self):
        r={'ph_qual':'AAAA','cc_flags':'0000','w1mpro':15.,'w1sigmpro':.1,
           'w1snr':10.,'w1rchi2':1.,'w1sat':0.,'ext_flg':0,'nb':1,'na':0}
        self.assertTrue(wise_quality(r,1)['pass'])
        self.assertFalse(wise_quality(dict(r,ph_qual='UAAA',w1sigmpro=None),1)['pass'])
        self.assertFalse(wise_quality(dict(r,cc_flags='D000'),1)['pass'])
        self.assertFalse(wise_quality(dict(r,nb=2),1)['pass'])

    def test_failed_upstream_is_not_a_zero_readiness_result(self):
        with self.assertRaises(ValueError):p10({'samples':[]})

    def test_technical_pass_does_not_authorize_scientific_inference(self):
        ctx={'samples':[{'reported_gaia_source_id':'123'}],'astrometry':{'123':True},
             'tmass_quality':{'123':True},'wise_quality':{'123':{'1':{'pass':True},'2':{'pass':True}}}}
        r=p10(ctx)[0]
        self.assertTrue(r['five_band_technical_pass'])
        self.assertFalse(r['scientific_excess_search_authorized'])

    def test_irsa_requests_use_one_cone_and_deduplicate_overlapping_results(self):
        gaia={'ra':10.,'dec':20.,'ref_epoch':2016.,'pmra':0.,'pmdec':0.}
        urls=[]
        class Response:
            status=200
            headers={}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):return b'fixture-response'
        def opened(url,timeout):
            urls.append(url)
            query=urllib.parse.parse_qs(urllib.parse.urlparse(url).query)['QUERY'][0]
            self.assertEqual(query.count('CONTAINS'),1)
            self.assertNotIn(' OR ',query)
            return Response()
        with tempfile.TemporaryDirectory() as folder:
            ctx={'design':{'acquisition':{'endpoint':'https://example.test/sync','radius_arcsec':15,'maximum_rows':1000}},
                 'samples':[{'reported_gaia_source_id':'1'},{'reported_gaia_source_id':'2'}],
                 'gaia':{'1':gaia,'2':gaia},'out':Path(folder)}
            with patch('scripts.wd_ten_pilots.urllib.request.urlopen',opened),patch(
                'scripts.wd_ten_pilots.parse_votable',return_value=({'designation':{}},[{'designation':'same-object'}])):
                rows=request_catalog(ctx,'fp_psc',2000)
            self.assertEqual(len(urls),2)
            self.assertEqual(len(rows),1)


if __name__=='__main__':unittest.main()
