import numpy as np
import pytest
from scripts.sampling_audit import resample
from scripts.wise_image_audit import fractional_circle,aperture

def test_log_interpolation_exact_for_rayleigh_jeans_shape():
    w=np.array([10.,20.]);f=w**-4;x=np.linspace(10,20,100)
    assert np.allclose(resample(w,f,x,'log_flux_log_wave'),x**-4)
    assert np.allclose(resample(w,f,x,'lambda4_scaled'),x**-4)
    assert resample(w,f,np.array([15.]),'linear_flux')[0]>15**-4*2

def test_log_interpolation_rejects_zero_in_supported_range():
    with pytest.raises(ValueError):resample(np.array([10.,20.]),np.array([1.,0.]),np.array([15.]),'log_flux_log_wave')
    with pytest.raises(ValueError):resample(np.array([10.,20.]),np.ones(2),np.array([25.]),'linear_flux')

def test_irrelevant_uv_zero_does_not_prevent_positive_ir_interpolation():
    assert resample(np.array([1.,10.,20.]),np.array([0.,1.,1.]),np.array([15.]),'log_flux_log_wave')[0]==pytest.approx(1)

def test_uniform_background_and_injected_image_flux():
    weights=fractional_circle((41,41),(20,20),5)
    assert weights.sum()==pytest.approx(np.pi*25,rel=.01)
    image=np.full((41,41),100.);image[20,20]+=500
    assert aperture(image,weights,100)==pytest.approx(500)
    assert aperture(image,weights,101)==pytest.approx(500-weights.sum())
