"""Plot conditional predictions in magnitudes; no significance classification."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.nir_prediction import OUT,BANDS

def main():
 s=json.loads((OUT/'summary.json').read_text());rows=json.loads((OUT/'comparison_cases.json').read_text());r=s['central_case'];x=np.arange(5)
 fig,ax=plt.subplots(1,2,figsize=(11,4.8),layout='constrained')
 values=np.array([a['model_magnitudes'] for a in rows]);ax[0].fill_between(x,values.min(0),values.max(0),alpha=.25,color='steelblue',label='162 sensitivity cases (not confidence interval)');ax[0].plot(x,r['model_magnitudes'],'o-',color='steelblue',label='Central conditional model')
 ax[0].errorbar(x[:3],s['observed_JHK'],yerr=s['combined_mag_errors_JHK'],fmt='o',color='black',label='J/H/Ks used for fit');ax[0].errorbar(3,s['W3_observed_mag'],yerr=s['W3_error_mag'],fmt='s',color='darkorange',label='W3 held out of fitting')
 ax[0].plot(4,s['W4_95percent_upper_limit_mag'],'v',color='purple',label='W4 95% flux upper limit');ax[0].annotate('',xy=(4,9.25),xytext=(4,8.89),arrowprops={'arrowstyle':'->','color':'purple'})
 ax[0].set(xticks=x,xticklabels=BANDS,ylabel='Vega magnitude (fainter downward)',title='NIR fit and infrared prediction');ax[0].invert_yaxis();ax[0].legend(fontsize=7,loc='lower left')
 for upper,marker in [(.3,'o'),(1.,'x')]:
  rr=[a for a in rows if a['Av_max']==upper];ax[1].scatter([a['Av_fit'] for a in rr],[a['W3_excess_fraction']*100 for a in rr],s=18,marker=marker,alpha=.7,label=f'Av allowed 0–{upper} mag')
 ax[1].axhline(0,color='gray',lw=1);ax[1].set(xlabel='Best-fit Av (mag), conditional on model case',ylabel='100 × (observed W3 / predicted W3 − 1)',title='Negative residual across tested cases');ax[1].legend(fontsize=8)
 fig.suptitle('EchoLens NIR-only development pilot — Gaia DR3 4461930649238469760\nCalibration and model discrepancy unresolved; no calibrated detection score',fontsize=11);fig.savefig(OUT/'nir_prediction.png',dpi=160);plt.close(fig)
if __name__=='__main__':main()
