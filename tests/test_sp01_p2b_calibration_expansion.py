import unittest, tempfile, csv
from pathlib import Path
from scripts.sp01_p2b_calibration_expansion import targets, DATA, PREVIOUS
class ProtocolTests(unittest.TestCase):
 def test_manifest_eight(self):
  rows=targets(DATA)
  self.assertEqual(len(rows),8)
  self.assertEqual(len({r['gaia_dr3_source_id'] for r in rows}),8)
  self.assertEqual(set(r['sobject_id'] for r in rows[:2]),PREVIOUS)
 def test_no_holdouts(self):
  self.assertTrue(all(r['role']=='calibration' for r in targets(DATA)))
 def test_modified_role_rejected(self):
  with tempfile.TemporaryDirectory() as temp:
   f=Path(temp)/'m.csv'; rows=targets(DATA);rows[1]['role']='holdout'
   with f.open('w',newline='') as s:
    w=csv.DictWriter(s,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
   with self.assertRaisesRegex(ValueError,'holdout'):targets(f)
 def test_precision_rejected(self):
  with tempfile.TemporaryDirectory() as temp:
   f=Path(temp)/'m.csv';rows=targets(DATA);rows[2]['gaia_dr3_source_id']='5.286e16'
   with f.open('w',newline='') as s:
    w=csv.DictWriter(s,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
   with self.assertRaisesRegex(ValueError,'exact decimal'):targets(f)
if __name__=='__main__':unittest.main()
