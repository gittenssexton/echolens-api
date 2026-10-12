"""Provisional calibration only: original DR4 identity validation then 12 official analysis FITS.
No holdout reads, no native camera requests, no discovery or false alarm claims.
"""
import csv,datetime as dt,hashlib,json,os,re
from pathlib import Path
from scripts import sp01_p2b_calibration_expansion as main
OUT=Path(os.environ.get('P2B_12_OUTPUT','reports/sp01_p2b_remaining_twelve'))
INPUT=Path('data/sp01_p2b_remaining_twelve_calibration.csv')
FIRST8=Path('data/sp01_p2b_eight_calibration.csv')

def select():
 with INPUT.open(newline='') as f:rows=list(csv.DictReader(f))
 with FIRST8.open(newline='') as f:prior=list(csv.DictReader(f))
 if len(rows)!=12 or len({r['gaia_dr3_source_id'] for r in rows})!=12:raise ValueError('Exactly 12 unique remaining calibrators required')
 priorids={r['gaia_dr3_source_id'] for r in prior}
 if priorids.intersection(r['gaia_dr3_source_id'] for r in rows):raise ValueError('Previously acquired calibration reused')
 for stratum in ('cool_low','cool_high','warm_low','warm_high'):
  if sum(r['stratum']==stratum for r in rows)!=3:raise ValueError('Three remaining sources per stratum required')
 for r in rows:
  if r['role']!='calibration' or r['original_manifest_sha256']!=main.FROZEN_SHA:raise ValueError('Holdout or changed cohort not permitted')
  for k in ('gaia_dr3_source_id','sobject_id'):
   if not re.fullmatch('[1-9][0-9]{13,18}',r[k]):raise ValueError('Nonexact ID')
 return rows

def run():
 OUT.mkdir(parents=True,exist_ok=True)
 rows=select();main.OUT=OUT
 result={'schema':'echolens-P2B-remaining-12-calibration-v1','timestamp':dt.datetime.now(dt.timezone.utc).isoformat(),'provisional_manifest_hash':main.FROZEN_SHA,'holdout_read':0,'calibration_stars_selected':12,'target_ids':[r['sobject_id'] for r in rows],'science_ready':False,'retrievals':[]}
 result['original_catalogue']=main.source_check(rows,b'')
 (OUT/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
 if not result['original_catalogue']['matched']:
  print(json.dumps({'blocked':'original GALAH DR4 12-source catalog crosscheck','error':result['original_catalogue'].get('error')},indent=2));return result
 for r in rows:
  entry=main.analysis(r['sobject_id']);result['retrievals'].append(entry)
  (OUT/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'source_ID_match_count':len(result['original_catalogue']['rows']),'original_allspec_downloads_accepted':sum(x['status']=='verified_analysis_FITS' for x in result['retrievals']),'failed_visits':[x['visit'] for x in result['retrievals'] if x['status']!='verified_analysis_FITS']},indent=2));return result
if __name__=='__main__':run()
