"""Plot archived observed Gaia spectrum and the finite neighborhood query."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from astropy.coordinates import SkyCoord
from astropy.time import Time
from scripts.gaia_model_readiness import OUT,SID
from scripts.infrared_feasibility import propagate

def main():
    g=json.loads((OUT/'gaia_source.json').read_text())[0]['rows'][0]
    xp=json.loads((OUT/'xp_sampled.json').read_text())[0]['rows']
    neighbors=json.loads((OUT/'neighbors.json').read_text())[0]['rows']
    wave=np.array([r['wavelength'] for r in xp]);flux=np.array([r['flux'] for r in xp]);error=np.array([r['flux_error'] for r in xp])
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    ax=axes[0];ax.plot(wave,flux/1e-16,color='#3182bd',lw=1,label='Archive sampled mean spectrum')
    ax.fill_between(wave,(flux-error)/1e-16,(flux+error)/1e-16,alpha=.3,color='#3182bd',label='Pointwise reported ±1 error')
    ax.set(xlabel='Wavelength (nm)',ylabel='Flux density (10⁻¹⁶ W m⁻² nm⁻¹)',title='Observed BP/RP spectrum; no model fitted');ax.legend(fontsize=8)
    year=Time(55400,format='mjd',scale='tt').jyear;target=SkyCoord(*propagate(g,year)[:2],unit='deg');ax=axes[1]
    east=[];north=[];mag=[];missing=[]
    for n in neighbors:
        if n['source_id']==SID:continue
        ra,dec,moved=propagate(n,year);e,no=target.spherical_offsets_to(SkyCoord(ra,dec,unit='deg'));east.append(e.arcsec);north.append(no.arcsec);mag.append(n['phot_g_mean_mag']);missing.append(not moved)
    points=ax.scatter(east,north,c=mag,cmap='viridis_r',s=35,edgecolor='black',linewidth=.4)
    for e,n,m in zip(east,north,missing):
        if m:ax.plot(e,n,'o',mfc='none',mec='#d73027',ms=12)
    ax.plot(0,0,'+',color='#d73027',ms=12,mew=2,label='Target')
    for radius in [6,15,60]:ax.add_patch(Circle((0,0),radius,fill=False,ls='--',lw=.7,color='gray'))
    ax.set(xlabel='East offset at WISE epoch (arcsec)',ylabel='North offset at WISE epoch (arcsec)',title='Gaia optical neighborhood; 60-arcsec discovery cone',xlim=(-65,65),ylim=(-65,65),aspect='equal');ax.invert_xaxis();ax.legend(fontsize=8)
    fig.colorbar(points,ax=ax,label='Gaia G magnitude')
    fig.suptitle(f'EchoLens Gaia follow-up — {SID}\n343 spectral samples are correlated; red neighbor rings indicate missing proper motion',fontsize=11)
    fig.savefig(OUT/'gaia_spectrum_neighborhood.png',dpi=160);plt.close(fig)
if __name__=='__main__':main()
