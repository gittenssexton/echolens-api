"""Conditional PHOENIX fits on frozen development candidates only; no validation scoring."""
import json,hashlib,itertools,socket,importlib.metadata as md
import numpy as np
from scripts.nir_prediction import ROOT,profile,prediction,write,digest
from scripts.model_validation import load_phoenix,response,BANDS,OUT as MODELS
COHORT=ROOT/'reports/calibration_cohort_v10';OUT=ROOT/'reports/calibration_development_v11'
def eligible(rows):return [r for r in rows if r['analysis_role']=='calibration_development' and r['joint_ready']]
def robust_summary(values):
    v=np.asarray(values,float);median=float(np.median(v));return {'count':len(v),'median':median,'MAD_about_median':float(np.median(np.abs(v-median))),'min':float(v.min()),'max':float(v.max()),'scope':'descriptive only, not calibrated error distribution or confidence interval'}
def main():
    design=json.loads((OUT/'design.json').read_text());selection=json.loads((COHORT/'selection.json').read_text());cohort=json.loads((COHORT/'results.json').read_text())
    if digest(COHORT/'selection.json')!=design['selection_sha256'] or digest(COHORT/'results.json')!=design['readiness_results_sha256']:raise ValueError('Frozen development inputs changed')
    targets=eligible(cohort)
    if [r['source_id'] for r in targets]!=design['development_source_ids']:raise ValueError('Development membership changed')
    for m in json.loads((MODELS/'acquisition_manifest.json').read_text()):
        if digest(MODELS/'raw'/m['file'])!=m['sha256']:raise ValueError('Native model/response hash mismatch')
    # Socket guard covers model assembly, fitting, and comparison; inputs are all archived.
    old=socket.socket.connect;socket.socket.connect=lambda *a,**kw: (_ for _ in ()).throw(RuntimeError('Network forbidden during development replay'))
    try:
        w,ip,metadata=load_phoenix();resp=response([w]);av=np.arange(201)*.005;stars={t['gaia']['source_id']:t for t in selection['targets']};fits=[]
        for r in targets:
            sid=r['source_id'];g=stars[sid]['gaia'];ctx=r['parameter_calibration_context'];tm=r['surveys']['tmass']['chosen']['measurement'];obs=np.array([tm[b+'_m'] for b in 'jhk']);error=np.array([tm[b+'_msigcom'] for b in 'jhk'])
            for params,rv in itertools.product(['raw','generic_calibration_sensitivity'],design['Rv_cases']):
                logg=g['logg_gspspec'] if params=='raw' else ctx['calibrated_logg_sensitivity'];metal=g['mh_gspspec'] if params=='raw' else ctx['calibrated_mh_sensitivity'];f=ip([[g['teff_gspspec'],logg,metal]])[0];synth=prediction(w,f,av,rv,resp);off,chi=profile(synth[:,:3],obs,error);i=int(np.argmin(chi));fits.append({'source_id':sid,'parameter_case':params,'T_K':g['teff_gspspec'],'logg':logg,'MH':metal,'Rv':rv,'Av':float(av[i]),'Av_boundary':i in [0,200],'chi2_JHK':float(chi[i]),'predicted_magnitudes':(synth[i]+off[i]).tolist()})
            print('Fitted development source',sid,flush=True)
        write(OUT/'fit_cases.json',fits)
        byid={r['source_id']:r for r in targets}
        for f in fits:
            wise=byid[f['source_id']]['surveys']['wise']['chosen']['measurement'];f['W3_residual_fraction']=float(10**(.4*(f['predicted_magnitudes'][5]-wise['w3mpro']))-1);f['W3_observed_mag']=wise['w3mpro'];f['W3_observed_mag_error']=wise['w3sigmpro']
            # W1/W2 comparisons require their own readiness gates; flagged bands remain unscored.
            f['other_band_diagnostics']={}
            for i,b in [(1,'W1'),(2,'W2')]:
                reasons=byid[f['source_id']]['surveys']['wise']['band_quality_failures'][str(i)]
                f['other_band_diagnostics'][b]={'quality_failures':reasons,'residual_fraction':None if reasons else float(10**(.4*(f['predicted_magnitudes'][BANDS.index(b)]-wise[f'w{i}mpro']))-1)}
        write(OUT/'comparison_cases.json',fits)
        summary={'run':'calibration-development-v11','status':'exploratory conditional fits of provisional comparison candidates; no calibrated significance, ordinary-control certification, zero-point adjustment or reserved validation scoring','development_stars':len(targets),'conditional_fit_cases':len(fits),'reserved_validation_stars_scored':0,'bands':BANDS,'selection_sha256':design['selection_sha256'],'descriptive_W3':{},'offline_socket_guard_passed':True,'fit_limitations':'six central-parameter cases per star, not a parameter posterior; JHK errors treated independently; model/zero-point/variability/contamination errors uncalibrated','versions':{p:md.version(p) for p in ['numpy','scipy','astropy','dust_extinction']}}
        for params in ['raw','generic_calibration_sensitivity']:
            rr=[f for f in fits if f['parameter_case']==params and f['Rv']==3.1];summary['descriptive_W3'][params]=robust_summary([f['W3_residual_fraction'] for f in rr]);summary['descriptive_W3'][params]['Av_boundary_cases']=sum(f['Av_boundary'] for f in rr)
        write(OUT/'summary.json',summary);print(json.dumps(summary,indent=2),flush=True)
    finally:socket.socket.connect=old
if __name__=='__main__':main()
