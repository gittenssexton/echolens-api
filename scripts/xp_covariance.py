"""Audit and propagate Gaia XP covariance without altering archived inputs.

GaiaXPy 2.1.4's combined-band correlation output is retained as a diagnostic.
The working covariance combines separately calibrated bands with weights on
both axes: W_BP C_BP W_BP + W_RP C_RP W_RP, assuming no cross-band covariance.
"""
import argparse,hashlib,json,math,socket,contextlib,importlib.metadata as md
from pathlib import Path
import numpy as np

INPUT=Path('reports/gaia_readiness_v04')
OUT=Path('reports/gaia_covariance_v05')
SID='4461930649238469760'
sha=lambda b:hashlib.sha256(b).hexdigest()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def unpack_correlation(packed,n):
    packed=np.asarray(packed,float)
    if packed.shape!=(n*(n-1)//2,):raise ValueError('Unexpected packed correlation length')
    matrix=np.eye(n);ix=np.tril_indices(n,-1);matrix[ix]=packed;matrix[(ix[1],ix[0])]=packed
    return matrix
def merge_independent_bands(bp,rp,wb,wr):
    wb=np.asarray(wb,float);wr=np.asarray(wr,float);n=len(wb)
    if wr.shape!=(n,) or not np.allclose(wb+wr,1,atol=1e-14) or (wb<0).any() or (wr<0).any():raise ValueError('Invalid band weights')
    flux=np.zeros(n);cov=np.zeros((n,n))
    for band,w in [(bp,wb),(rp,wr)]:
        f,e,corr=band['flux'],band['flux_error'],band['correlation_matrix'];valid=w>0
        if np.shape(f)!=(n,) or np.shape(e)!=(n,) or np.shape(corr)!=(n,n):raise ValueError('Band/grid dimension mismatch')
        if not (np.isfinite(f[valid]).all() and np.isfinite(e[valid]).all() and (e[valid]>0).all()):raise ValueError('Nonfinite required band data')
        c=corr[np.ix_(valid,valid)]*np.outer(e[valid],e[valid])
        if not np.isfinite(c).all():raise ValueError('Nonfinite required covariance')
        flux[valid]+=w[valid]*f[valid]
        cov[np.ix_(valid,valid)]+=np.outer(w[valid],w[valid])*c
    return flux,cov
def matrix_diagnostics(cov,rtol=1e-10):
    c=np.asarray(cov,float)
    if c.ndim!=2 or c.shape[0]!=c.shape[1] or not np.isfinite(c).all():raise ValueError('Invalid covariance')
    scale=float(np.max(np.abs(c)))
    if scale<=0 or np.max(np.abs(c-c.T))>scale*1e-10:raise ValueError('Nonsymmetric/nonpositive-scale covariance')
    eig=np.linalg.eigvalsh(c);maximum=float(eig[-1])
    if maximum<=0:raise ValueError('No positive covariance mode')
    negative=int((eig< -maximum*rtol).sum());rank=int((eig>maximum*rtol).sum())
    return {'dimension':len(eig),'min_to_max_eigenvalue_ratio':float(eig[0]/maximum),'negative_modes_below_tolerance':negative,'rank_relative_1e_10':rank,'rank_sensitivity':{str(t):int((eig>maximum*t).sum()) for t in [1e-6,1e-8,1e-10,1e-12]},'positive_semidefinite_at_relative_tolerance':negative==0,'cholesky_suitable_without_regularization':negative==0 and float(eig[0]/maximum)>rtol}
def validate_working_covariance(cov):
    d=matrix_diagnostics(cov)
    if not d['positive_semidefinite_at_relative_tolerance']:raise ValueError('Indefinite covariance rejected; no clipping/jitter applied')
    return d
def input_frame(band=None):
    import pandas as pd
    row=json.loads((INPUT/'xp_continuous.json').read_text())[0]['rows'][0]
    if row['source_id']!=SID:raise ValueError('Wrong input spectrum')
    for k,v in list(row.items()):
        if isinstance(v,list):row[k]=np.asarray(v,float)
    for k in ['source_id','solution_id']:row[k]=np.int64(row[k])
    if band:
        other='rp' if band=='bp' else 'bp'
        for k in row:
            if k.startswith(other+'_'):row[k]=np.nan
    return pd.DataFrame([row])
def calibrate_band(band,grid,truncated):
    from gaiaxpy import calibrate
    df,wave=calibrate(input_frame(band),sampling=grid,truncation=truncated,with_correlation=True,save_file=False)
    if str(df.iloc[0]['source_id'])!=SID or not np.array_equal(wave,grid):raise ValueError('Calibrated identity/grid mismatch')
    values={k:np.asarray(df.iloc[0][k],float) for k in ['flux','flux_error','correlation']}
    values['correlation_matrix']=unpack_correlation(values['correlation'],len(grid))
    return values
def calibrate_working(grid,truncated=False):
    from gaiaxpy.core.satellite import BP_WL,RP_WL
    wb=np.clip((BP_WL.high-grid)/(BP_WL.high-RP_WL.low),0,1);wr=1-wb
    bp=calibrate_band('bp',grid,truncated);rp=calibrate_band('rp',grid,truncated)
    flux,cov=merge_independent_bands(bp,rp,wb,wr);diagnostics=validate_working_covariance(cov)
    error=np.sqrt(np.diag(cov));correlation=cov/np.outer(error,error)
    return {'wavelength_nm':grid,'flux':flux,'flux_error':error,'covariance':cov,'correlation':correlation,'bp_weight':wb,'rp_weight':wr},diagnostics
@contextlib.contextmanager
def offline_guard():
    old=socket.socket.connect
    def denied(*args,**kwargs):raise RuntimeError('Network access forbidden during covariance replay')
    socket.socket.connect=denied
    try:yield
    finally:socket.socket.connect=old
def run():
    if md.version('gaiaxpy')!='2.1.4':raise ValueError('This audited adapter requires GaiaXPy 2.1.4')
    from gaiaxpy import calibrate
    from gaiaxpy.config.paths import config_path
    grid=np.arange(336.,1022.,2.);OUT.mkdir(parents=True,exist_ok=True)
    versions={n:md.version(n) for n in ['gaiaxpy','astropy','numpy','pandas','scipy','matplotlib']}
    summary={'run':'gaia-covariance-v05','source_id':SID,'input_sha256':sha((INPUT/'xp_continuous.json').read_bytes()),'versions':versions,'method':'separate-band public calibration; covariance multiplied by merge weights on both axes; cross-band covariance assumed zero','no_eigenvalue_clipping_or_jitter':True,'cases':{}}
    with offline_guard():
        native,w=calibrate(input_frame(),sampling=grid,truncation=False,with_correlation=True,save_file=False)
        f=np.asarray(native.iloc[0]['flux']);e=np.asarray(native.iloc[0]['flux_error']);r=unpack_correlation(native.iloc[0]['correlation'],len(grid));c=r*np.outer(e,e)
        summary['rejected_combined_correlation']=matrix_diagnostics(c)
        np.savez_compressed(OUT/'rejected_provider_combined.npz',wavelength_nm=grid,flux=f,flux_error=e,correlation=r,covariance=c)
        old=json.loads((INPUT/'xp_sampled.json').read_text())[0]['rows'];of=np.array([x['flux'] for x in old]);oe=np.array([x['flux_error'] for x in old])
        for name,wave,truncated in [('full_343',grid,False),('recommended_truncated_343',grid,True),('coarse_32',np.arange(380.,1002.,20.),False)]:
            arrays,d=calibrate_working(wave,truncated);np.savez_compressed(OUT/f'{name}.npz',**arrays);summary['cases'][name]=d
            if name=='full_343':
                summary['agreement_with_public_mean_and_errors']={'max_absolute_flux_difference':float(np.max(np.abs(arrays['flux']-f))),'max_relative_error_difference':float(np.max(np.abs(arrays['flux_error']/e-1)))}
                summary['agreement_with_archive_sampled_spectrum']={'max_flux_difference_in_reported_error_units':float(np.max(np.abs(arrays['flux']-of)/oe)),'max_relative_error_difference':float(np.max(np.abs(arrays['flux_error']/oe-1)))}
                full_flux=arrays['flux'];full_cov=arrays['covariance']
            elif name=='recommended_truncated_343':summary['truncation_comparison']={'max_flux_change_in_full_error_units':float(np.max(np.abs(arrays['flux']-full_flux)/np.sqrt(np.diag(full_cov)))),'median_flux_change_in_full_error_units':float(np.median(np.abs(arrays['flux']-full_flux)/np.sqrt(np.diag(full_cov))))}
    # Hash bundled calibration inputs and implementation; do not alter package files.
    files=sorted(p for p in Path(config_path).rglob('*') if p.is_file())
    write(OUT/'calibration_config_manifest.json',{str(p.relative_to(config_path)):sha(p.read_bytes()) for p in files})
    summary['offline_socket_guard_passed']=True;summary['scientific_status']='calibration/covariance engineering validation; no atmosphere fit or infrared residual'
    write(OUT/'summary.json',summary);print(json.dumps(summary,indent=2),flush=True)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.parse_args();run()
if __name__=='__main__':main()
