"""Offline exploratory JHK-only fit; conditional W3 comparison, no detection score."""
import hashlib,json,itertools,gzip
from pathlib import Path
import numpy as np
from astropy.io import fits
from astropy.io.votable import parse_single_table
from astropy import units as u
from dust_extinction.parameter_averages import G23
from scipy.interpolate import RegularGridInterpolator
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/nir_prediction_v06';SID='4461930649238469760';BANDS=['J','H','Ks','W3','W4']
def write(p,obj):p.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def profile(model,obs,error):
    model=np.asarray(model);obs=np.asarray(obs);error=np.asarray(error)
    if model.shape[-1]!=len(obs) or np.any(error<=0) or not np.isfinite(model).all():raise ValueError('Invalid fit inputs')
    offset=np.sum((obs-model)/error**2,axis=-1)/np.sum(1/error**2)
    chi=np.sum(((obs-model-offset[...,None])/error)**2,axis=-1)
    return offset,chi

def integral(w,f,x,r,d):
    if d not in [0,1] or np.any(np.diff(w)<=0) or np.any(np.diff(x)<=0):raise ValueError('Invalid response/grid')
    if x[0]<w[0] or x[-1]>w[-1]:raise ValueError('Incomplete spectral coverage')
    if not np.isfinite(f).all() or np.any(f<0) or np.any(r<0):raise ValueError('Invalid spectrum/response')
    return np.trapezoid(np.interp(x,w,f)*r*(x if d else 1),x)

def models():
    grid=np.empty((3,3,2,1221));manifest=[]
    for k,m in enumerate(['ckm05','ckp00']):
        for i,t in enumerate([4750,5000,5250]):
            p=ROOT/f'reports/gaia_covariance_v05/model_context/{m}_{t}.fits.gz';raw=gzip.decompress(p.read_bytes());mp=json.loads(p.with_name(p.name.replace('.fits.gz','.manifest.json')).read_text())
            if hashlib.sha256(raw).hexdigest()!=mp['raw_sha256']:raise ValueError('Model hash mismatch')
            with fits.open(p) as h:
                if h[0].header['TEFF']!=t or h[0].header['LOG_Z']!=[-.5,0][k]:raise ValueError('Wrong model')
                wave=np.array(h[1].data['WAVELENGTH'],float)
                for j,g in enumerate(['g25','g30','g35']):grid[i,j,k]=h[1].data[g]
            manifest.append({'path':str(p.relative_to(ROOT)),'sha256':digest(p),'raw_sha256':mp['raw_sha256']})
    interp=RegularGridInterpolator(([4750,5000,5250],[2.5,3,3.5],[-.5,0]),grid,bounds_error=True)
    assert np.array_equal(interp([[5000,3,0]])[0],grid[1,1,1])
    return wave,interp,manifest

def filters(refine=1):
    with fits.open(OUT/'raw/vega.fits') as h:vw=np.array(h[1].data['WAVELENGTH'],float);vf=np.array(h[1].data['FLUX'],float)
    response=[]
    for b in BANDS:
        t=parse_single_table(OUT/f'raw/{b}.xml');p={v.name:v.value for v in t.params}
        if p['WavelengthUnit']!='Angstrom' or p['MagSys']!='Vega':raise ValueError('Wrong units/system')
        w=np.asarray(t.array['Wavelength'],float);r=np.asarray(t.array['Transmission'],float);d=int(p['DetectorType'])
        x=np.unique(np.r_[w,np.geomspace(w[0],w[-1],4000*refine)]);rr=np.interp(x,w,r);v=integral(vw,vf,x,rr,d)
        if v<=0:raise ValueError('Invalid Vega integral')
        response.append((x,rr,d,v,p))
    return response

def prediction(w,f,av,rv,response):
    result=[]
    for x,r,d,v,_ in response:
        if x[0]<w[0] or x[-1]>w[-1]:raise ValueError('Incomplete model coverage')
        a=G23(Rv=rv)(x*u.AA);base=np.interp(x,w,f)*r*(x if d else 1)
        counts=np.trapezoid(base[None,:]*10**(-.4*np.asarray(av)[:,None]*a),x,axis=1)
        result.append(-2.5*np.log10(counts/v))
    return np.array(result).T

def main():
    design=json.loads((OUT/'design.json').read_text())
    for m in json.loads((OUT/'acquisition_manifest.json').read_text()):
        p=OUT/'raw'/(m['name']+('.fits' if m['name']=='vega' else '.xml'))
        if digest(p)!=m['sha256']:raise ValueError('Response hash mismatch')
    sp=ROOT/'reports/infrared_feasibility/results.json';source=next(s for s in json.loads(sp.read_text()) if s['source_id']==SID);tm=source['surveys']['tmass']['chosen']['measurement']
    obs=np.array([tm[x+'_m'] for x in ['j','h','k']]);err=np.array([tm[x+'_msigcom'] for x in ['j','h','k']]);w,interp,mm=models();response=filters();rows=[]
    for t,g,m,rv in itertools.product(design['temperature_cases'],design['gravity_cases'],design['metallicity_cases'],design['Rv_cases']):
        f=interp([[t,g,m]])[0]
        for upper in [.3,1.]:
            av=np.arange(round(upper/.005)+1)*.005;synth=prediction(w,f,av,rv,response);offset,chi=profile(synth[:,:3],obs,err);i=int(np.argmin(chi))
            rows.append({'T_K':t,'logg':g,'MH':m,'Rv':rv,'Av_max':upper,'Av_fit':float(av[i]),'normalization_magnitude':float(offset[i]),'scale_R_over_D_squared':float(10**(-.4*offset[i])),'chi2_JHK':float(chi[i]),'model_magnitudes':(synth[i]+offset[i]).tolist(),'at_extinction_boundary':i in [0,len(av)-1]})
    # Freeze fits before comparing W3 (source already development-exposed).
    write(OUT/'fit_cases.json',rows);wise=source['surveys']['wise']['chosen']['measurement'];w3=wise['w3mpro'];w4=wise['w4mpro']
    for r in rows:r['W3_excess_fraction']=float(10**(.4*(r['model_magnitudes'][3]-w3))-1);r['W3_residual_mag_model_minus_observed']=r['model_magnitudes'][3]-w3
    write(OUT/'comparison_cases.json',rows)
    central=next(r for r in rows if (r['T_K'],r['logg'],r['MH'],r['Rv'],r['Av_max'])==(5046,3.16,-.11,3.1,.3))
    f=interp([[5046,3.16,-.11]])[0];diff=prediction(w,f,[0,.3,1],3.1,filters(2))-prediction(w,f,[0,.3,1],3.1,response)
    summary={'experiment':design['experiment'],'source_id':SID,'status':'exploratory uncalibrated conditional comparison; no detection significance','observed_JHK':obs.tolist(),'combined_mag_errors_JHK':err.tolist(),'W3_observed_mag':w3,'W3_error_mag':wise['w3sigmpro'],'W4_95percent_upper_limit_mag':w4,'central_case':central,'sensitivity':{},'max_quadrature_refinement_mag_change':float(np.max(np.abs(diff))),'reference':'CALSPEC alpha_lyr_stis_011 assigned zero in every band; survey reference offsets unresolved','source_results_sha256':digest(sp),'design_sha256':digest(OUT/'design.json'),'model_manifest':mm}
    for upper in [.3,1.]:
        s=[r for r in rows if r['Av_max']==upper];summary['sensitivity'][str(upper)]={'cases':len(s),'Av_fit_range':[min(r['Av_fit'] for r in s),max(r['Av_fit'] for r in s)],'boundary_cases':sum(r['at_extinction_boundary'] for r in s),'chi2_range':[min(r['chi2_JHK'] for r in s),max(r['chi2_JHK'] for r in s)],'W3_prediction_mag_range':[min(r['model_magnitudes'][3] for r in s),max(r['model_magnitudes'][3] for r in s)],'W3_excess_fraction_range':[min(r['W3_excess_fraction'] for r in s),max(r['W3_excess_fraction'] for r in s)],'W4_predictions_fainter_than_upper_limit':all(r['model_magnitudes'][4]>w4 for r in s)}
    write(OUT/'summary.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
