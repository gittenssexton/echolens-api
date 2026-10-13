"""Scientific diagnostic plots for archived covariance cases; no fit."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.xp_covariance import OUT

def main():
    full=np.load(OUT/'full_343.npz');trunc=np.load(OUT/'recommended_truncated_343.npz');bad=np.load(OUT/'rejected_provider_combined.npz');coarse=np.load(OUT/'coarse_32.npz')
    fig,ax=plt.subplots(2,2,figsize=(12,9),layout='constrained')
    w=full['wavelength_nm'];ax[0,0].plot(w,full['flux']/1e-16,lw=1,label='All coefficients');ax[0,0].plot(w,trunc['flux']/1e-16,lw=.8,label='Recommended 20 BP / 12 RP bases');ax[0,0].set(xlabel='Wavelength (nm)',ylabel='Flux (10⁻¹⁶ W m⁻² nm⁻¹)',title='Calibration/truncation comparison; no atmosphere fit');ax[0,0].legend(fontsize=8)
    im=ax[0,1].imshow(full['correlation'],origin='lower',extent=[w[0],w[-1],w[0],w[-1]],vmin=-1,vmax=1,cmap='RdBu_r',aspect='auto');ax[0,1].set(xlabel='Wavelength (nm)',ylabel='Wavelength (nm)',title='Corrected two-band propagated correlation');fig.colorbar(im,ax=ax[0,1],label='Correlation')
    for p,label,color in [(bad,'Rejected combined correlation','#d73027'),(full,'Correct two-axis merge','#3182bd'),(trunc,'Correct merge, truncated','#31a354')]:
        e=np.linalg.eigvalsh(p['covariance']);ax[1,0].plot(np.arange(len(e)),e/e[-1],label=label,color=color,lw=.9)
    ax[1,0].set(yscale='symlog',xlabel='Sorted eigenmode',ylabel='Eigenvalue / largest eigenvalue',title='Negative modes and dense-grid rank limits');ax[1,0].axhline(0,color='gray',lw=.5);ax[1,0].legend(fontsize=8);ax[1,0].set_yscale('symlog',linthresh=1e-12)
    e=np.linalg.eigvalsh(coarse['covariance']);ax[1,1].semilogy(np.arange(1,len(e)+1),e/e[-1],'o-',ms=3);ax[1,1].set(xlabel='Sorted eigenmode',ylabel='Eigenvalue / largest eigenvalue',title='32-point audit grid: positive definite, no jitter')
    fig.suptitle('EchoLens XP covariance audit — Gaia DR3 4461930649238469760\nNumerical processing diagnostics; no infrared excess or scientific significance computed',fontsize=12)
    fig.savefig(OUT/'covariance_audit.png',dpi=160);plt.close(fig)
if __name__=='__main__':main()
