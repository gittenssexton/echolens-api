import unittest
from scripts.sp01_p2b_remaining_twelve import select
class Tests(unittest.TestCase):
 def test_selection(self):
  rows=select();self.assertEqual(len(rows),12);self.assertTrue(all(r['role']=='calibration' for r in rows))
 def test_all_strata(self):
  rows=select();self.assertEqual({x['stratum'] for x in rows},{'cool_low','cool_high','warm_low','warm_high'})
if __name__=='__main__':unittest.main()
