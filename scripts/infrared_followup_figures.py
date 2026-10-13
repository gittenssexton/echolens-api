"""Model, sampling and image diagnostics; no significance thresholds."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.nir_prediction import ROOT,models
from scripts.model_validation import load_phoenix,BANDS
from scripts.sampling_audit import resample
OUT=ROOT/'reports/infrared_followup_v07_v09'
def main():
 OUT.mkdir(exist_ok=True);s=json.loads((ROOT/'reports/model_validation_v07/summary.json').read_text());imageaudit=json.loads((ROOT/'reports/wise_image_audit_v09/summary.json').read_text());fig,ax=plt.subplots(2,2,figsize=(12,9),layout='constrained')
 for family,color in [('CK04','#d95f02'),('PHOENIX','#1b9e77')]:
  envelope=s['families'][family]['residual_envelopes'];v=np.array([envelope[b] for b in ['W1','W2','W3']])*100;mid=v.mean(1);ax[0,0].errorbar(np.arange(3)+(.04 if family=='PHOENIX' else -.04),mid,yerr=(v[:,1]-v[:,0])/2,fmt='o',capsize=4,color=color,label=family+' (linear flux interpolation)')
 ax[0,0].axhline(0,color='gray',lw=1);ax[0,0].set(xticks=range(3),xticklabels=['W1','W2','W3'],ylabel='Observed/predicted flux − 1 (%)',title='Independent model-family diagnostic');ax[0,0].legend(fontsize=8)
 cw,ck,_=models();pw,ph,_=load_phoenix();cf=ck([[5046,3.16,-.11]])[0];pf=ph([[5046,3.16,-.11]])[0];x=np.geomspace(75000,250000,1500)
 normal=float(np.interp(100000,pw,pf)*100000**4)
 ax[0,1].plot(x/1e4,np.interp(x,pw,pf)*x**4/normal,color='#1b9e77',label='PHOENIX native sampling')
 for method,label,c in [('linear_flux','CK04 linear flux','#d95f02'),('log_flux_log_wave','CK04 log flux/log wavelength','#7570b3')]:ax[0,1].plot(x/1e4,resample(cw,cf,x,method)*x**4/normal,color=c,label=label)
 mask=(cw>75000)&(cw<250000);ax[0,1].plot(cw[mask]/1e4,cf[mask]*cw[mask]**4/normal,'.',color='black',ms=3,label='CK04 native nodes');ax[0,1].set(xlabel='Wavelength (µm)',ylabel='λ⁴ Fλ (arbitrary normalization)',title='Sparse-grid linear interpolation distorts the IR shape');ax[0,1].legend(fontsize=7)
 data=np.load(ROOT/'reports/wise_image_audit_v09/diagnostic_arrays.npz');im=data['image'];center=imageaudit['catalog_position_pixel'];scale=imageaudit['pixel_scale_arcsec'];extent=[(-.5-center[0])*scale,(im.shape[1]-.5-center[0])*scale,(-.5-center[1])*scale,(im.shape[0]-.5-center[1])*scale];shown=ax[1,0].imshow(im,origin='lower',extent=extent,vmin=np.percentile(im,10),vmax=np.percentile(im,99.5),cmap='gray');
 for r in [8.25,50,70]:ax[1,0].add_patch(plt.Circle((0,0),r,fill=False,color='cyan' if r==8.25 else 'orange',lw=1))
 ax[1,0].set(xlabel='Atlas pixel x offset (arcsec)',ylabel='Atlas pixel y offset (arcsec)',title='W3 aperture and catalog-size sky annulus');fig.colorbar(shown,ax=ax[1,0],label='DN (display clipped)')
 cases=imageaudit['annulus_cases'];ax[1,1].plot(range(3),[r['corrected_mag'] for r in cases],'o-',label='Image aperture; catalog correction reused');ax[1,1].axhline(imageaudit['catalog']['w3mag'],color='green',label='Catalog standard aperture');ax[1,1].axhline(imageaudit['catalog']['w3mpro'],color='black',ls='--',label='Catalog profile fit');ax[1,1].set(xticks=range(3),xticklabels=['25–40','40–55','50–70'],xlabel='Sky annulus radii (arcsec)',ylabel='W3 magnitude',title='Background sensitivity: 0.015 mag spread');ax[1,1].invert_yaxis();ax[1,1].legend(fontsize=7)
 fig.suptitle('EchoLens follow-up: the earlier 32% W3 shortfall is a sampling artifact\nDevelopment diagnostics on Gaia DR3 4461930649238469760; no calibrated excess significance',fontsize=12);fig.savefig(OUT/'followup.png',dpi=150);plt.close(fig)
if __name__=='__main__':main()
