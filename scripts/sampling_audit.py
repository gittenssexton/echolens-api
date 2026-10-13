"""Controlled PHOENIX degradation onto CK04 knots and interpolation sensitivity."""
import json
import numpy as np
from dust_extinction.parameter_averages import G23
from astropy import units as u
from scripts.nir_prediction import ROOT,write,profile,models
from scripts.model_validation import load_phoenix,response,BANDS
OUT=ROOT/'reports/sampling_audit_v08'
def resample(w,f,x,mode):
    if np.any(np.diff(w)<=0) or x.min()<w.min() or x.max()>w.max():raise ValueError('Invalid/unsupported wavelength coverage')
    lo=max(0,np.searchsorted(w,x.min())-1);hi=min(len(w),np.searchsorted(w,x.max(),side='right')+1)
    w=w[lo:hi];f=f[lo:hi]
    if mode=='linear_flux':return np.interp(x,w,f)
    if np.any(f<=0):raise ValueError('Positive flux required for logarithmic interpolation')
    if mode=='log_flux_log_wave':return np.exp(np.interp(np.log(x),np.log(w),np.log(f)))
    if mode=='lambda4_scaled':return np.interp(x,w,f*w**4)/x**4
    raise ValueError('Unknown interpolation')
def synth(w,f,av,resp,mode):
    mags=[]
    for x,r,d,v,_ in resp:
        flux=resample(w,f,x,mode);a=G23(Rv=3.1)(x*u.AA);counts=np.trapezoid(flux[None,:]*10**(-.4*av[:,None]*a)*r*(x if d else 1),x,axis=1);mags.append(-2.5*np.log10(counts/v))
    return np.array(mags).T

def main():
    design={'experiment':'wavelength-sampling-audit-v08','question':'Does sparse CK04 wavelength sampling plus linear FLAM interpolation reproduce the W3 discrepancy?','controlled_input':'same interpolated PHOENIX spectrum before/after degradation onto CK04 wavelength nodes','central_parameters':[5046,3.16,-.11],'Av_range':[0,1],'Av_step':.005,'Rv':3.1,'methods':['linear_flux','log_flux_log_wave','lambda4_scaled'],'scope':'central-case numerical falsification experiment, not global calibration or confirmation'};write(OUT/'design.json',design)
    cw,ck,_=models();pw,ph,_=load_phoenix();resp=response([cw,pw]);cf=ck([[5046,3.16,-.11]])[0];pf=ph([[5046,3.16,-.11]])[0];dw=cw[(cw>=pw.min())&(cw<=pw.max())];df=np.interp(dw,pw,pf)
    prior=json.loads((ROOT/'reports/nir_prediction_v06/summary.json').read_text());obs=np.array(prior['observed_JHK']);err=np.array(prior['combined_mag_errors_JHK']);av=np.arange(201)*.005;cases=[]
    for family,w,f in [('native_PHOENIX',pw,pf),('degraded_PHOENIX_on_CK04_knots',dw,df),('CK04',cw,cf)]:
        for mode in design['methods']:
            if family=='native_PHOENIX' and mode!='linear_flux':continue
            s=synth(w,f,av,resp,mode);off,chi=profile(s[:,:3],obs,err);i=int(np.argmin(chi));mags=s[i]+off[i]
            cases.append({'family':family,'method':mode,'Av':float(av[i]),'chi2_JHK':float(chi[i]),'model_magnitudes':mags.tolist(),'W3_residual_fraction':float(10**(.4*(mags[5]-prior['W3_observed_mag']))-1)})
    write(OUT/'summary.json',{'status':'numerical sampling artifact reproduced; alternative interpolation remains exploratory','bands':BANDS,'cases':cases,'CK04_nodes_10_to_20um_A':cw[(cw>=99000)&(cw<=200000)].tolist(),'native_sampling_reference':'high-resolution PHOENIX, same parameter-interpolated spectrum','source_id':prior['source_id']});print(json.dumps(cases,indent=2))
if __name__=='__main__':main()
