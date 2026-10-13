"""Exploratory J/H/Ks morphology follow-up of the weakest development fit.

The Atlas images do not independently validate the catalog's R1 H photometry.
No image flux is used to change the fit or score the reserved sample.
"""
import datetime
import io
import json
import urllib.parse
import urllib.request
import numpy as np
from astropy.io import fits
from astropy.io.votable import parse_single_table
from astropy.wcs import WCS
from scripts.development_image_audit import ROOT, OUT, context, digest, write

SID = '2336863054027651456'


def retrieve(url, p):
    if p.exists():
        meta = json.loads(p.with_suffix('.manifest.json').read_text())
        if digest(p) != meta['raw_sha256'] or url != meta['url']:
            raise ValueError('Existing response differs')
        return p.read_bytes()
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'EchoLens-development-NIR-v12'}),timeout=90) as r:
        b = r.read(); final = r.url; status = r.status
    p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(b)
    write(p.with_suffix('.manifest.json'),{'url':url,'response_url':final,'status':status,
          'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'raw_sha256':digest(p),'bytes':len(b)})
    return b


def main():
    d, rows = context()
    s = next(s for s in rows if s['source_id']==SID)
    m = s['surveys']['tmass']['chosen']['measurement']
    p = OUT/'nir_followup_design.json'
    if not p.exists():
        write(p,{'source_id':SID,'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 'reason':'weakest conditional J/H/Ks fit in v11 development; exploratory morphology only',
                 'bands':['J','H','Ks'],'size_arcsec':90,'catalog_read_flags':m['rd_flg'],
                 'no_flux_refit_or_reserved_scoring':True})
    center = f"{m['ra']},{m['dec']}"
    url = 'https://irsa.ipac.caltech.edu/ibe/search/twomass/allsky/allsky?'+urllib.parse.urlencode({'POS':center,'ct':'VOTABLE'})
    raw = retrieve(url,OUT/'raw'/SID/'tmass_metadata.xml')
    table = parse_single_table(io.BytesIO(raw)).to_table(use_names_over_ids=True)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    from astropy.visualization import simple_norm
    fig, axes = plt.subplots(1,3,figsize=(12,4.5))
    images = []
    for ax,band,code in zip(axes,['J','H','Ks'],['j','h','k']):
        candidates = [r for r in table if str(r['filter'])==code and int(r['coadd_key'])==int(m['coadd_key'])]
        if len(candidates)!=1:
            raise ValueError('No unique exact catalog coadd image')
        r=candidates[0]
        base=f"https://irsa.ipac.caltech.edu/ibe/data/twomass/allsky/allsky/{str(r['ordate']).zfill(6)}{r['hemisphere']}/s{int(r['scanno']):03d}/image/{r['fname']}"
        url=base+'?'+urllib.parse.urlencode({'center':center,'size':'90arcsec','gzip':'false'})
        b=retrieve(url,OUT/'raw'/SID/f'{band}.fits')
        with fits.open(io.BytesIO(b)) as h:
            h.verify('exception');im=np.array(h[0].data,float);header=h[0].header.copy()
        wcs=WCS(header);xy=wcs.all_world2pix([[m['ra'],m['dec']]],0)[0]
        scale=float(np.sqrt(abs(np.linalg.det(wcs.pixel_scale_matrix)))*3600)
        ax.imshow(im,origin='lower',cmap='gray_r',norm=simple_norm(im,'asinh',percent=99.5))
        ax.add_patch(Circle(xy,4/scale,fill=False,color='tab:red'))
        ax.set(title=band,xlabel='Atlas x pixel',ylabel='Atlas y pixel')
        images.append({'band':band,'shape':list(im.shape),'catalog_pixel':xy.tolist(),'scale_arcsec':scale,
                       'coadd_key':int(r['coadd_key']),'native_filename':str(r['fname'])})
    fig.suptitle(f'{SID}: native 90″ 2MASS fields; red 4″ locator circle\nMorphology only; Atlas images do not independently validate short-read H catalog photometry',fontsize=11)
    fig.tight_layout(rect=[0,0,1,.87]);fig.savefig(OUT/'weakest_fit_JHK.png',dpi=140);plt.close(fig)
    fit = next(r for r in json.loads((ROOT/'reports/calibration_development_v11/fit_cases.json').read_text())
               if r['source_id']==SID and r['parameter_case']=='raw' and r['Rv']==3.1)
    observed=[m[k] for k in ['j_m','h_m','k_m']]
    write(OUT/'weakest_fit_nir_context.json',{'source_id':SID,'catalog':m,'native_image_metadata':images,
          'raw_Rv3p1_fit':fit,'JHK_observed_minus_model_mag':[float(a-b) for a,b in zip(observed,fit['predicted_magnitudes'][:3])],
          'status':'morphology/provenance context; no alternative fit, validation scoring, or physical classification'})


if __name__=='__main__':main()
