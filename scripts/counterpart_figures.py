"""Render real cutouts and diagnostic graphs for counterpart review v03."""
from pathlib import Path
import json,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from astropy.io import fits
from astropy.wcs import WCS
from astropy.time import Time
from astropy.visualization import ImageNormalize,AsinhStretch,PercentileInterval
from scripts.counterpart_review import INPUT,OUT,inputs,image_bytes
from scripts.infrared_feasibility import propagate

def main():
    queue,gaia,results=inputs();review=json.loads((OUT/'review.json').read_text());bands=['W1','W3','J','K']
    fig=plt.figure(figsize=(14,17),layout='constrained')
    for i,t in enumerate(queue):
        sid=t['gaia_source_id'];g=gaia[sid]
        for j,band in enumerate(bands):
            sv='wise' if band.startswith('W') else 'tmass';a=results[sid]['surveys'][sv];m=a['chosen']['measurement']
            with fits.open(__import__('io').BytesIO(image_bytes(OUT/'images'/sid/f'{band}.fits.gz'))) as h:
                data=h[0].data;w=WCS(h[0].header)
            ax=fig.add_subplot(5,4,i*4+j+1,projection=w)
            ax.imshow(data,origin='lower',cmap='gray_r',norm=ImageNormalize(data,interval=PercentileInterval(99),stretch=AsinhStretch()))
            epoch=Time(55400,format='mjd',scale='tt').jyear if sv=='wise' else Time(m['jdate'],format='jd',scale='utc').jyear
            ra,dec,_=propagate(g,epoch);x,y=w.world_to_pixel_values(ra,dec);ax.plot(x,y,'+',color='#00bfc4',markersize=12,markeredgewidth=1.5)
            x,y=w.world_to_pixel_values(m['ra'],m['dec']);ax.plot(x,y,'o',mfc='none',mec='#d73027',ms=12,mew=1)
            for alternative in a['candidates']:
                other=alternative['measurement']
                if other['designation']==m['designation']:continue
                x,y=w.world_to_pixel_values(other['ra'],other['dec']);ax.plot(x,y,'s',mfc='none',mec='#e69f00',ms=6)
            ax.set_title(f'{sid}\n{band if band!="K" else "Ks"} · 90 arcsec',fontsize=8)
            ax.coords[0].set_axislabel('RA',fontsize=7);ax.coords[1].set_axislabel('Dec',fontsize=7)
            ax.coords[0].set_ticklabel(size=6);ax.coords[1].set_ticklabel(size=6)
    fig.suptitle('EchoLens real-survey cutout review — development only\nCyan +: propagated Gaia; red circle: stationary catalog position; orange squares: cone alternatives\nNative image orientation and independent display stretches; not precision centroids or measured fluxes',fontsize=11)
    fig.savefig(OUT/'cutout_montage.png',dpi=160);plt.close(fig)
    rows=review['sources'];x=np.arange(5);labels=['4310…4800','4461…9760','2224…6496','1923…5536','4262…4912\nVARIABLE']
    fig,axes=plt.subplots(1,2,figsize=(12,4.6),layout='constrained')
    for i,(sv,key,label) in enumerate([('wise','RA_coordinate','WISE coordinate convention'),('wise','RA_tangent_sensitivity','WISE tangent sensitivity'),('tmass','ellipse','2MASS ellipse')]):
        values=[r[sv]['conditional_diagnostics'][key]['unmodeled_floor_sensitivity_arcsec']['0']['mahalanobis_radius'] for r in rows]
        axes[0].plot(x,values,'o',label=label)
    axes[0].axhline(3,color='gray',ls='--',label='Draft review radius 3')
    axes[0].set(xticks=x,xticklabels=labels,ylabel='Conditional positional Mahalanobis radius',title='Reported random errors only; no identity acceptance');axes[0].legend(fontsize=7)
    z=[r['hypothetical_exact_20pct_excess_measurement_only_z_ceiling'] for r in rows]
    axes[1].bar(x,z,color=['#3182bd']*4+['#e6550d']);axes[1].axhline(5,color='gray',ls='--',label='Proposed Z floor 5')
    axes[1].set(xticks=x,xticklabels=labels,ylabel='Measurement-only Z ceiling for exactly 20% excess',title='Sensitivity illustration; no excess measured');axes[1].legend(fontsize=8)
    for ax in axes:ax.tick_params(axis='x',labelsize=8)
    fig.savefig(OUT/'diagnostics.png',dpi=160);plt.close(fig)

if __name__=='__main__':main()
