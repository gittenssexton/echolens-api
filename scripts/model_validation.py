"""Offline model-family and held-out WISE diagnostics; no significance score."""
import itertools,json
import numpy as np
from astropy.io import fits
from astropy.io.votable import parse_single_table
from scipy.interpolate import RegularGridInterpolator
from scripts.nir_prediction import ROOT,OUT as OLD,write,digest,profile,integral,prediction,models
OUT=ROOT/'reports/model_validation_v07';BANDS=['J','H','Ks','W1','W2','W3','W4'];SID='4461930649238469760'
def load_phoenix():
    rows=[];waves=[];metadata=[]
    for m,metal in [('phoenixm05',-.5),('phoenixm00',0)]:
        for t in [4900,5000,5100,5200]:
            p=OUT/f'raw/{m}_{t}.fits'
            with fits.open(p) as h:
                if float(h[0].header['TEFF'])!=t or float(h[0].header['METAL10'])!=metal:raise ValueError('Wrong model')
                w=np.array(h[1].data['WAVELENGTH'],float);f=np.array([h[1].data[g] for g in ['g25','g30','g35']],float)
                if np.any(np.diff(w)<=0) or not np.isfinite(f).all() or np.any(f<0):raise ValueError('Invalid spectrum')
                if h[1].columns['WAVELENGTH'].unit!='ANGSTROM' or h[1].columns['g30'].unit!='FLAM':raise ValueError('Wrong units')
                metadata.append({'file':p.name,'T':t,'MH':metal,'alpha_header':h[0].header.get('ALPHA'),'rows':len(w),'range_A':[float(w[0]),float(w[-1])],'flux_unit':h[0].header.get('FLUXUNT')});rows.append((t,metal,w,f));waves.append(w)
    common=np.unique(np.concatenate(waves));cube=np.empty((4,3,2,len(common)))
    for t,m,w,f in rows:
        if common[0]<w[0] or common[-1]>w[-1]:raise ValueError('Incomplete common coverage')
        for j in range(3):cube[[4900,5000,5100,5200].index(t),j,[-.5,0].index(m)]=np.interp(common,w,f[j])
    return common,RegularGridInterpolator(([4900,5000,5100,5200],[2.5,3,3.5],[-.5,0]),cube,bounds_error=True),metadata

def response(native_waves=(),refine=1):
    with fits.open(OLD/'raw/vega.fits') as h:vw=np.array(h[1].data['WAVELENGTH'],float);vf=np.array(h[1].data['FLUX'],float)
    out=[]
    for b in BANDS:
        p=(OUT if b in ['W1','W2'] else OLD)/f'raw/{b}.xml';t=parse_single_table(p);meta={a.name:a.value for a in t.params};w=np.array(t.array['Wavelength'],float);r=np.array(t.array['Transmission'],float);d=int(meta['DetectorType'])
        knots=[w,np.geomspace(w[0],w[-1],4000*refine),vw[(vw>=w[0])&(vw<=w[-1])]]
        for a in native_waves:knots.append(a[(a>=w[0])&(a<=w[-1])])
        x=np.unique(np.concatenate(knots));rr=np.interp(x,w,r);v=integral(vw,vf,x,rr,d);out.append((x,rr,d,v,meta))
    return out

def main():
    for m in json.loads((OUT/'acquisition_manifest.json').read_text()):
        if digest(OUT/'raw'/m['file'])!=m['sha256']:raise ValueError('Input hash mismatch')
    cw,ck,_=models();pw,phoenix,metadata=load_phoenix();resp=response([cw,pw]);old=json.loads((OLD/'summary.json').read_text());obs=np.array(old['observed_JHK']);error=np.array(old['combined_mag_errors_JHK']);av=np.arange(201)*.005;design=json.loads((OLD/'design.json').read_text());rows=[]
    for family,w,ip in [('CK04',cw,ck),('PHOENIX',pw,phoenix)]:
        for t,g,m,rv in itertools.product(design['temperature_cases'],design['gravity_cases'],design['metallicity_cases'],design['Rv_cases']):
            f=ip([[t,g,m]])[0];synth=prediction(w,f,av,rv,resp);off,chi=profile(synth[:,:3],obs,error);i=int(np.argmin(chi));rows.append({'family':family,'T':t,'logg':g,'MH':m,'Rv':rv,'Av':float(av[i]),'offset':float(off[i]),'chi2_JHK':float(chi[i]),'predicted_magnitudes':(synth[i]+off[i]).tolist(),'extinction_boundary':i in [0,200]})
        print('Finished fits:',family,flush=True)
    write(OUT/'fit_cases.json',rows)
    source=next(x for x in json.loads((ROOT/'reports/infrared_feasibility/results.json').read_text()) if x['source_id']==SID);wise=source['surveys']['wise']['chosen']['measurement'];measurement={b:{'magnitude':wise[f'w{i}mpro'],'error':wise[f'w{i}sigmpro'],'snr':wise[f'w{i}snr'],'reduced_chi2_profile':wise[f'w{i}rchi2']} for i,b in enumerate(['W1','W2','W3','W4'],1)}
    for r in rows:r['residuals']={b:float(10**(.4*(r['predicted_magnitudes'][BANDS.index(b)]-measurement[b]['magnitude']))-1) for b in ['W1','W2','W3']}
    write(OUT/'comparison_cases.json',rows);s={'source_id':SID,'bands':BANDS,'status':'exploratory conditional comparison; no significance','observations':measurement,'families':{},'phoenix_metadata':metadata}
    for family in ['CK04','PHOENIX']:
        rr=[r for r in rows if r['family']==family];central=next(r for r in rr if (r['T'],r['logg'],r['MH'],r['Rv'])==(5046,3.16,-.11,3.1));s['families'][family]={'central':central,'cases':len(rr),'Av_range':[min(r['Av'] for r in rr),max(r['Av'] for r in rr)],'boundary_count':sum(r['extinction_boundary'] for r in rr),'chi2_range':[min(r['chi2_JHK'] for r in rr),max(r['chi2_JHK'] for r in rr)],'residual_envelopes':{b:[min(r['residuals'][b] for r in rr),max(r['residuals'][b] for r in rr)] for b in ['W1','W2','W3']}}
    # Synthetic Planck shape check; neither realistic atmosphere nor catalog observation.
    x=pw[(pw>=8000)&(pw<=350000)];lam=x*1e-8;planck=(2*6.62607015e-27*(2.99792458e10)**2/lam**5)/np.expm1(6.62607015e-27*2.99792458e10/(lam*1.380649e-16*5046))*np.pi*1e-8
    bb=prediction(x,planck,av,3.1,resp);bo,bc=profile(bb[:,:3],obs,error);j=int(np.argmin(bc));s['blackbody_shape_check']={'T':5046,'Av':float(av[j]),'chi2_JHK':float(bc[j]),'predicted_magnitudes':(bb[j]+bo[j]).tolist(),'classification':'synthetic shape check, not realistic atmosphere'}
    f=phoenix([[5046,3.16,-.11]])[0];s['quadrature_refinement_max_mag_change']=float(np.max(np.abs(prediction(pw,f,[0,.3,1],3.1,response([cw,pw],2))-prediction(pw,f,[0,.3,1],3.1,resp))));s['grid_points']={b:len(r[0]) for b,r in zip(BANDS,resp)}
    write(OUT/'summary.json',s);print(json.dumps(s['families'],indent=2))
if __name__=='__main__':main()
