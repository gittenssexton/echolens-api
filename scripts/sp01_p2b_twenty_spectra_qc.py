"""Reproducible descriptive QC only, eight P2B calibration allspec spectra.
NO holdouts, no false alarm probability, no technological-inference labels.
"""
from pathlib import Path
import csv,hashlib,json,datetime as dt
import numpy as np
import matplotlib.pyplot as plt

HERE=Path(__file__).parent
NEW=HERE/'spectra'; NEXT=HERE/'spectra'; OLD=HERE/'spectra'
SELECTION=HERE/'data/sp01_p2b_twenty_calibration.csv'
OUTPUT=HERE/'reproduced_analysis';OUTPUT.mkdir(exist_ok=True)

def header(bs,off):
 cards=[]
 for i in range(off,len(bs),80):
  card=bs[i:i+80].decode('ascii','strict');cards.append(card)
  if card.startswith('END '):break
 if not cards[-1].startswith('END '):raise ValueError('Missing FITS header END')
 end=((off+len(cards)*80+2879)//2880)*2880
 vals={}
 for c in cards:
  if c[8:10]=='= ':
   v=c[10:80].split(' / ',1)[0].strip();vals[c[:8].strip()]=v.strip("' ")
 return vals,end

def load(path):
 bs=path.read_bytes();h,o=header(bs,0);th,d=header(bs,o)
 if th.get('XTENSION')!='BINTABLE' or int(th.get('NAXIS1',0))!=33 or [th.get('TTYPE'+str(i)) for i in range(1,6)]!=['wave','sob','uob','smod','mob']:
  raise ValueError('Unexpected allspec BINTABLE format: '+path.name)
 n=int(th['NAXIS2'])
 if len(bs)<d+33*n:raise ValueError('Truncated BINTABLE')
 dtype=np.dtype([('wave','>f8'),('sob','>f8'),('uob','>f8'),('smod','>f8'),('mob','S1')])
 a=np.frombuffer(bs,dtype,count=n,offset=d)
 w=np.array(a['wave'],dtype=float)
 if not np.all(np.isfinite(w)) or not np.all(np.diff(w)>0):raise ValueError('Invalid wavelength array')
 return a,hashlib.sha256(bs).hexdigest(),len(bs)

obs=[]
for row in csv.DictReader(SELECTION.open()):
 visit=row['sobject_id'];p=(OLD if visit in {'151111003101245','221003001101138'} else (NEW if (NEW/f'{visit}_single_fit_spectrum.fits').is_file() else NEXT))/(f"{visit}_{'official_allspec' if visit in {'151111003101245','221003001101138'} else 'single_fit_spectrum'}.fits")
 a,hashval,nbyte=load(p)
 w=np.array(a['wave'],dtype=float);z=np.full(len(a),np.nan)
 v=(np.isfinite(a['sob'])&np.isfinite(a['smod'])&np.isfinite(a['uob'])&(a['uob']>0)&(w>=6400)&(w<=6900))
 z[v]=(a['sob'][v]-a['smod'][v])/a['uob'][v]
 yes=v&(a['mob']==b'T');no=v&(a['mob']==b'F')
 res={'sobject_id':visit,'gaia_dr3_source_id':row['gaia_dr3_source_id'],'role':row['role'],'stratum':row['stratum'], 'source_sha256':hashval,'source_bytes':nbyte,'pixels_total':len(a),'red_valid':int(v.sum()),'red_fit_included':int(yes.sum()),'red_fit_excluded':int(no.sum()),'red_wavelength_A':[float(w[v].min()),float(w[v].max())]}
 for key,mask in [('fit_included',yes),('fit_excluded',no)]:
  zz=np.abs(z[mask]);res[key+'_fraction_abs_z_gt5']=round(float(np.mean(zz>5)),7) if len(zz) else None
  res[key+'_median_abs_z']=round(float(np.median(zz)),5) if len(zz) else None
 obs.append(res)
assert len(obs)==20 and all(r['role']=='calibration' for r in obs)
summary={'schema':'echolens-P2B-twenty-calibrators-descriptive-same-data-residuals-v1', 'date_utc':dt.datetime.now(dt.timezone.utc).isoformat(), 'source_manifest_SHA256':'ef62ec0bd5afd79a8c39613f2796943937dd09d9eb6e6bfabe644522e2beed32','calibrator_source_count':20,'holdout_reads':0,'metrics_type':'IN_SAMPLE_FIT_MASK_CONDITIONED_DIAGNOSTIC_ONLY','star_level_FAP_calibrated':False,'inference':'No star-level significance, no evidence of astrophysical or artificial emission from these fit residuals','results':obs}
(OUTPUT/'p2b_twenty_calibration_residual_qc.json').write_text(json.dumps(summary,indent=2)+'\n')
with (OUTPUT/'p2b_twenty_calibration_residual_qc.csv').open('w',newline='') as f:
 cols=list(obs[0].keys());writer=csv.DictWriter(f,fieldnames=cols);writer.writeheader();writer.writerows(obs)
fig,ax=plt.subplots(figsize=(16,6.3))
x=np.arange(len(obs));a=100*np.array([r['fit_included_fraction_abs_z_gt5'] for r in obs]);b=100*np.array([r['fit_excluded_fraction_abs_z_gt5'] for r in obs]);
ax.bar(x-.2,a,.38,label='Retained in model fit');ax.bar(x+.2,b,.38,label='Excluded from model fit')
ax.set_xticks(x,labels=[r['stratum'].replace('_',' ')+'\n'+r['sobject_id'][-5:] for r in obs],rotation=75,ha='right',fontsize=8);ax.set_ylabel('Red-arm pixels with |(observed - model)/uncertainty| > 5 (%)');ax.set_title('SP01-P2B: Twenty GALAH DR4 calibration analysis spectra — descriptive fit-mask QC');ax.legend();ax.grid(axis='y',alpha=.2)
fig.text(.02,.01,'Original GALAH fits used to compute residuals; this is NOT a calibrated statistical discovery test.',fontsize=8)
fig.tight_layout(rect=(0,.05,1,1));fig.savefig(OUTPUT/'p2b_twenty_calibration_residual_qc.png',dpi=175);plt.close(fig)
print(json.dumps({'count':20,'results':[{'star':x['sobject_id'],'included_rate_percent':round(100*x['fit_included_fraction_abs_z_gt5'],3),'excluded_rate_percent':round(100*x['fit_excluded_fraction_abs_z_gt5'],3),'n':x['red_valid']} for x in obs]},indent=2))
