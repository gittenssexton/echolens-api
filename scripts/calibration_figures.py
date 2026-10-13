"""Static cohort/readiness and development residual diagnostics; no Z scores."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.calibration_cohort import OUT as COHORT
from scripts.calibration_development import OUT

def main():
    s=json.loads((COHORT/'summary.json').read_text());rows=json.loads((OUT/'comparison_cases.json').read_text());ids=json.loads((OUT/'design.json').read_text())['development_source_ids'];fig,ax=plt.subplots(2,1,figsize=(12,9),layout='constrained',gridspec_kw={'height_ratios':[1,2]})
    count=s['counts'];labels=['Frozen candidates','J/H/Ks ready','W3 ready','Joint ready'];values=[20,count['JHK_ready'],count['W3_ready'],count['joint_ready']];ax[0].barh(labels,values,color=['#555555','#1b9e77','#1b9e77','#7570b3']);ax[0].set(xlim=(0,23),xlabel='Number of candidates',title='Frozen Gaia-only cohort; flagged cases retained');ax[0].invert_yaxis()
    for i,v in enumerate(values):ax[0].text(v+.25,i,str(v),va='center')
    x=np.arange(len(ids));raw=[];cal=[];errors=[];lo=[];hi=[]
    for sid in ids:
        rr=[r for r in rows if r['source_id']==sid];a=next(r for r in rr if r['parameter_case']=='raw' and r['Rv']==3.1);b=next(r for r in rr if r['parameter_case']=='generic_calibration_sensitivity' and r['Rv']==3.1);raw.append(a['W3_residual_fraction']*100);cal.append(b['W3_residual_fraction']*100);errors.append((1+a['W3_residual_fraction'])*.4*np.log(10)*a['W3_observed_mag_error']*100);lo.append(min(r['W3_residual_fraction'] for r in rr)*100);hi.append(max(r['W3_residual_fraction'] for r in rr)*100)
    ax[1].vlines(x,lo,hi,color='#7570b3',lw=5,alpha=.5,label='Six-case sensitivity envelope (not confidence interval)');ax[1].errorbar(x-.08,raw,yerr=errors,fmt='o',color='black',capsize=3,label='Raw Gaia parameters; W3 measurement error only');ax[1].scatter(x+.08,cal,marker='s',s=30,color='#d95f02',label='Generic calibration sensitivity; Rv=3.1');ax[1].axhline(0,color='gray',lw=1);ax[1].set(xticks=x,xticklabels=ids,ylabel='Observed / predicted W3 flux − 1 (%)',xlabel='Exact Gaia DR3 source ID',title='Nine development sources only; no reserved validation predictions');ax[1].tick_params(axis='x',rotation=90,labelsize=8);ax[1].legend(fontsize=8,loc='lower left',bbox_to_anchor=(0,1.07))
    fig.suptitle('EchoLens calibration development v0.10–v0.11\nProvisional stellar comparisons; model, contamination and zero-point uncertainties uncalibrated',fontsize=12);fig.savefig(OUT/'calibration_development.png',dpi=150);plt.close(fig)
if __name__=='__main__':main()
