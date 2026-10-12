"""Synthetic rows only. No real stellar observations or candidate claims."""
import csv
import hashlib
from pathlib import Path
import tempfile
import unittest
from scripts.sp01_p2b_select import (
    build,SelectionBlocked,exact_source_id,ordinary_eligible,hash_rank
)
HEADERS=['gaiadr3_source_id','sobject_id','teff','logg','fe_h','snr_px_ccd2',
         'snr_px_ccd3','flag_sp','flag_red','phot_g_mean_mag','bp_rp','ruwe']
POSHEAD=['gaiadr3_source_id','classification','reference_url']

def fabricate():
    # Entirely synthetic fixture identifiers (no actual observed stars).
    rows=[]
    for ix in range(80):
        groups=ix//20
        sid=str(900000000000000000+ix)
        rows.append(dict(zip(HEADERS,[sid,str(100000000000000+ix),
           5000 if groups<2 else 6000,4.45,0.0,61,
           42 if groups%2==0 else 72,0,0,9.5,1.0,1.05])))
    for ix in range(15):
        sid=str(800000000000000000+ix)
        rows.append(dict(zip(HEADERS,[sid,str(200000000000000+ix),
           4100,2.6,.1,20,20,16,1,11.5,1.5,2.])))
    positives=[{'gaiadr3_source_id':str(800000000000000000+ix),
                 'classification':'synthetic-fixture-peculiar',
                 'reference_url':'https://example.org/fixture'} for ix in range(15)]
    return rows,positives

def writecsv(path,cols,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)

class Tests(unittest.TestCase):
    def pair(self,dirname):
        c=Path(dirname)/'catalog.csv';p=Path(dirname)/'positive.csv'
        rows,labels=fabricate();writecsv(c,HEADERS,rows);writecsv(p,POSHEAD,labels)
        return c,p,rows,labels
    def go(self,c,p):
        return build(c,p,raw_source_sha256='a'*64,catalog_source='synthetic-fixture-only')
    def test_id_string_unrounded(self):
        self.assertEqual(exact_source_id('3064554891927687296',field='source'), '3064554891927687296')
        for s in ['3064554891927687000.0','3.064554891927687e18','', '0']:
            with self.assertRaises(ValueError):exact_source_id(s,field='source')
    def test_complete_cohort_and_splits(self):
        with tempfile.TemporaryDirectory() as td:
            c,p,*_=self.pair(td);r=self.go(c,p)
            self.assertEqual(r['cohort_counts'], {'calibration':20,'holdout':20,'natural_positive_only':10})
            self.assertEqual(len({x['gaia_dr3_source_id'] for x in r['selected_sources']}),50)
            for st in ('cool_low','cool_high','warm_low','warm_high'):
                self.assertEqual(sum(x['stratum']==st for x in r['selected_sources']),10)
    def test_deterministic_when_csv_order_is_reversed(self):
        with tempfile.TemporaryDirectory() as td:
            c,p,rows,labels=self.pair(td);r=self.go(c,p)
            writecsv(c,HEADERS,list(reversed(rows)))
            writecsv(p,POSHEAD,list(reversed(labels)))
            r2=self.go(c,p)
            self.assertEqual(r['selected_sources'],r2['selected_sources'])
    def test_shortage_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            c,p,rows,labels=self.pair(td)
            rows=[r for r in rows if str(r['teff'])!='5000' or str(r['snr_px_ccd3'])!='42'][:]
            writecsv(c,HEADERS,rows)
            with self.assertRaisesRegex(SelectionBlocked,'Insufficient'):
                self.go(c,p)
    def test_positive_provenance_is_required(self):
        with tempfile.TemporaryDirectory() as td:
            c,p,rows,labels=self.pair(td)
            labels[0]['reference_url']=''
            writecsv(p,POSHEAD,labels)
            with self.assertRaisesRegex(ValueError,'literature URL'):
                self.go(c,p)
    def test_duplicate_visits_one_star(self):
        with tempfile.TemporaryDirectory() as td:
            c,p,rows,labels=self.pair(td)
            duplicate=dict(rows[0]);duplicate['sobject_id']='999999999999999'
            rows.append(duplicate);writecsv(c,HEADERS,rows)
            r=self.go(c,p)
            same=[x for x in r['selected_sources'] if x['gaia_dr3_source_id']==duplicate['gaiadr3_source_id']]
            self.assertLessEqual(len(same),1)
            if same:self.assertEqual(len(same[0]['all_known_visit_sobject_ids']),2)
    def test_prior_exposure_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            c,p,rows,labels=self.pair(td)
            # Replacing an eligible row with previously exposed source triggers exclude.
            rows[0]['gaiadr3_source_id']='3064554891927687296'
            writecsv(c,HEADERS,rows)
            r=self.go(c,p)
            self.assertTrue(all(x['gaia_dr3_source_id']!='3064554891927687296' for x in r['selected_sources']))
            self.assertEqual(r['preselection_excluded_source_counts']['development_exposed'],1)
    def test_flag_sp_and_reduction_filter(self):
        rows,_=fabricate()
        row=rows[0].copy();row['flag_sp']='16'
        self.assertEqual(ordinary_eligible(row),(False,'flag_not_zero'))
        row=rows[0].copy();row['flag_red']='2'
        self.assertEqual(ordinary_eligible(row),(False,'flag_not_zero'))
    def test_sha_source_provenance_required(self):
        with tempfile.TemporaryDirectory() as td:
            c,p,*_=self.pair(td)
            with self.assertRaisesRegex(ValueError,'SHA-256'):
                build(c,p,raw_source_sha256='',catalog_source='test')
    def test_positive_never_in_null(self):
        with tempfile.TemporaryDirectory() as td:
            c,p,*_=self.pair(td);r=self.go(c,p)
            self.assertTrue(all((x['role']=='natural_positive_only') == bool(x['positive_classification'])
                                for x in r['selected_sources']))

if __name__=='__main__':unittest.main()
