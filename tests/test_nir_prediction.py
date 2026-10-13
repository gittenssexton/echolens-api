import numpy as np
import pytest
from scripts.nir_prediction import integral,profile

def test_energy_and_photon_response_analytic_integrals():
    w=np.linspace(1,3,10001);f=w;r=np.ones_like(w)
    assert integral(w,f,w,r,0)==pytest.approx(4,rel=1e-8)
    assert integral(w,f,w,r,1)==pytest.approx(26/3,rel=1e-8)

def test_vega_self_zero_and_constant_scaling_magnitude():
    w=np.linspace(1,3,1001);v=w**-2;r=np.ones_like(w)
    base=integral(w,v,w,r,1)
    assert -2.5*np.log10(integral(w,v,w,r,1)/base)==0
    assert -2.5*np.log10(integral(w,100*v,w,r,1)/base)==pytest.approx(-5)

def test_missing_coverage_and_negative_flux_rejected():
    with pytest.raises(ValueError):integral(np.array([1,2]),np.ones(2),np.array([1,3]),np.ones(2),0)
    with pytest.raises(ValueError):integral(np.array([1,2]),-np.ones(2),np.array([1,2]),np.ones(2),0)

def test_normalization_recovery_and_heldout_band_independence():
    model=np.array([1.,2.,3.,4.,5.]);obs=model[:3]+20;error=np.array([.02,.03,.04])
    offset,chi=profile(model[:3],obs,error)
    assert offset==pytest.approx(20) and chi==pytest.approx(0)
    model[3:]+=100
    assert profile(model[:3],obs,error)==(offset,chi)

def test_profile_matches_weighted_stationary_point():
    model=np.array([[1.,2.,3.],[2.,1.,4.]]);obs=np.array([5.,6.,8.]);error=np.array([.1,.2,.3])
    offset,chi=profile(model,obs,error)
    assert np.allclose(np.sum((obs-model-offset[:,None])/error**2,axis=1),0,atol=1e-10)
    assert np.all(chi>=0)
