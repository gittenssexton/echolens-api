"""Entirely synthetic metadata; no astronomical observations or holdouts."""
import hashlib
import json
import unittest
from scripts.sp01_p2b_repair import select, Blocked, STRATA

def fixture():
    rows=[]
    for j,s in enumerate(STRATA):
        for i in range(30):
            sid=str(1000000000+j*100+i)
            rows.append(dict(source_id=sid,stratum=s,ordinary_eligible=True,
                             natural_positive=False,group_metadata_complete=True,
                             group_keys=['synthetic-batch:'+sid]))
    return rows

def run(rows, exposed=(), **changes):
    raw=json.dumps(rows).encode()
    ev=dict(scope='full_declared_eligible_frame',truncated=False,all_pages_complete=True,
            grouping_reviewed=True,source_release='SYNTHETIC',query_record='fixture',
            completeness_record='fixture',grouping_record='fixture',expected_rows=len(rows),
            frame_sha256=hashlib.sha256(raw).hexdigest())
    ev.update(changes)
    if not isinstance(exposed,dict):
        exposed=dict(source_ids=list(exposed),group_keys=[],group_mapping_complete=True,record='synthetic fixture')
    return select(raw,ev,exposed)

class Tests(unittest.TestCase):
    def test_quotas_and_no_group_overlap(self):
        out=run(fixture())['selected']
        self.assertEqual(len(out),60)
        self.assertEqual(len({r['component_sha256'] for r in out}),60)
        for s in STRATA:
            for role in ('template','calibration','holdout'):
                self.assertEqual(sum(r['stratum']==s and r['role']==role for r in out),5)
    def test_permutation_invariant_membership(self):
        rows=fixture()
        self.assertEqual(run(rows)['selected'],run(list(reversed(rows)))['selected'])
    def test_transitive_groups_and_exposure(self):
        rows=fixture()
        rows[0]['group_keys']=['a']
        rows[1]['group_keys']=['a','b']
        rows[2]['group_keys']=['b']
        out=run(rows,[rows[0]['source_id']])
        self.assertEqual(out['excluded']['exposure_connected_sources'],3)
        self.assertFalse({r['source_id'] for r in rows[:3]} & {r['source_id'] for r in out['selected']})
    def test_bounded_or_partial_frame_rejected(self):
        for change in ({'scope':'top180'}, {'truncated':True}, {'all_pages_complete':False}):
            with self.assertRaises(Blocked):run(fixture(),**change)
    def test_tampering_or_count_mismatch(self):
        for change in ({'frame_sha256':'0'*64},{'expected_rows':121}):
            with self.assertRaises(Blocked):run(fixture(),**change)
    def test_missing_group_metadata_rejected(self):
        rows=fixture();rows[0]['group_metadata_complete']=False
        with self.assertRaises(Blocked):run(rows)
    def test_float_duplicate_and_positive_rejected(self):
        for mode in ('float','duplicate','positive'):
            rows=fixture()
            if mode=='float':rows[0]['source_id']=float(rows[0]['source_id'])
            elif mode=='duplicate':rows[1]['source_id']=rows[0]['source_id']
            else:rows[0]['natural_positive']=True
            with self.assertRaises(Blocked):run(rows)
    def test_shortage_stops_without_relaxing(self):
        rows=fixture()[:14]
        with self.assertRaises(Blocked):run(rows)
    def test_exposed_source_outside_frame_blocks_its_batch(self):
        rows=fixture()
        ledger=dict(source_ids=['999999999'],group_keys=rows[0]['group_keys'],
                    group_mapping_complete=True,record='synthetic fixture')
        out=run(rows,ledger)
        self.assertNotIn(rows[0]['source_id'],[r['source_id'] for r in out['selected']])
        self.assertEqual(out['excluded']['exposure_connected_sources'],1)
        ledger['group_mapping_complete']=False
        with self.assertRaises(Blocked):run(rows,ledger)

if __name__=='__main__':unittest.main()
