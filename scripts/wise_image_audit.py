"""Exploratory W3 Atlas aperture/background checks; no independent epoch or Z score."""
import json,hashlib
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.stats import sigma_clip
from scripts.nir_prediction import ROOT,write
OUT=ROOT/'reports/wise_image_audit_v09';SID='4461930649238469760'
def fractional_circle(shape,center,radius,subpixels=8):
    yy,xx=np.indices(shape);weights=np.zeros(shape,float)
    for dx in (np.arange(subpixels)+.5)/subpixels-.5:
        for dy in (np.arange(subpixels)+.5)/subpixels-.5:weights+=((xx+dx-center[0])**2+(yy+dy-center[1])**2<=radius**2)
    return weights/subpixels**2

def aperture(image,weights,sky):
    if not np.isfinite(image[weights>0]).all():raise ValueError('Nonfinite aperture pixels')
    net=float(np.sum((image-sky)*weights));return net

def main():
    p=OUT/'raw/W3_180arcsec.fits';mp=json.loads((OUT/'acquisition_manifest.json').read_text())
    if hashlib.sha256(p.read_bytes()).hexdigest()!=mp['raw_sha256']:raise ValueError('Image hash mismatch')
    s=next(s for s in json.loads((ROOT/'reports/infrared_feasibility/results.json').read_text()) if s['source_id']==SID);m=s['surveys']['wise']['chosen']['measurement']
    with fits.open(p) as h:image=np.array(h[0].data,float);header=h[0].header;wcs=WCS(header)
    center=np.array(wcs.all_world2pix([[m['ra'],m['dec']]],0))[0];scale=float(np.sqrt(abs(np.linalg.det(wcs.pixel_scale_matrix)))*3600);weights=fractional_circle(image.shape,center,8.25/scale)
    yy,xx=np.indices(image.shape);radius=np.hypot(xx-center[0],yy-center[1])*scale;cases=[]
    for low,high in [[25,40],[40,55],[50,70]]:
        mask=(radius>=low)&(radius<=high)&np.isfinite(image);clipped=sigma_clip(image[mask],sigma=3,maxiters=5);sky=float(np.ma.median(clipped));net=aperture(image,weights,sky);rawmag=None if net<=0 else float(header['MAGZP']-2.5*np.log10(net));corrected=None if rawmag is None else rawmag-m['w3mcor']
        cases.append({'annulus_arcsec':[low,high],'sky_median_DN':sky,'sky_clipped_std_DN':float(clipped.std()),'pixels_total':int(mask.sum()),'pixels_retained':int(clipped.count()),'net_aperture_DN':net,'uncorrected_mag':rawmag,'catalog_correction_reused_mag':m['w3mcor'],'corrected_mag':corrected})
    result={'source_id':SID,'status':'approximate aperture diagnostic; no image covariance/error model or independent exposure','shape':list(image.shape),'pixel_scale_arcsec':scale,'catalog_position_pixel':center.tolist(),'effective_aperture_pixels':float(weights.sum()),'BUNIT':header.get('BUNIT'),'MAGZP':header['MAGZP'],'annulus_cases':cases,'catalog':{k:m[k] for k in ['w3mpro','w3sigmpro','w3mag','w3sigm','w3flg','w3mag_2','w3mcor','w3magp','w3sigp1','w3sigp2','w3m','w3rchi2','w3mlq','w3mjdmin','w3mjdmax']},'catalog_aperture_minus_profile_mag':m['w3mag']-m['w3mpro'],'catalog_repeatability_mean_minus_profile_mag':m['w3magp']-m['w3mpro'],'catalog_curve_of_growth_arithmetic_error_mag':m['w3mag_2']-m['w3mcor']-m['w3mag'],'larger_catalog_apertures_confusion_flags':{str(i):m[f'w3flg_{i}'] for i in range(1,9)}}
    write(OUT/'summary.json',result);np.savez_compressed(OUT/'diagnostic_arrays.npz',image=image,weights=weights,radius_arcsec=radius);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
