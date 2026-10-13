import numpy as np
import pytest
from scripts.counterpart_review import gaia_covariance,ellipse_covariance,wise_covariance

def test_epoch_covariance_respects_position_motion_correlation():
    g={'ref_epoch':2016,'ra_error':1,'dec_error':2,'pmra_error':3,'pmdec_error':4,
       'ra_dec_corr':0,'ra_pmra_corr':.5,'ra_pmdec_corr':0,'dec_pmra_corr':0,'dec_pmdec_corr':-.25,'pmra_pmdec_corr':0}
    # Ten years before Gaia epoch: Var(x+dt*v)=Var(x)+dt^2 Var(v)+2dt Cov(x,v).
    c=gaia_covariance(g,2006)
    assert np.allclose(c,np.diag([871,1644])*1e-6)

def test_ellipse_angle_is_east_of_north():
    assert np.allclose(ellipse_covariance(2,1,0),np.diag([1,4]))
    assert np.allclose(ellipse_covariance(2,1,90),np.diag([4,1]))
    assert np.allclose(ellipse_covariance(2,1,45),[[2.5,1.5],[1.5,2.5]])

def test_negative_wise_cosigma_preserves_covariance_sign_and_coordinates():
    m={'sigra_pm':2,'sigdec_pm':1,'sigradec_pm':-.5,'dec_pm':60}
    assert np.allclose(wise_covariance(m),[[1,-.125],[-.125,1]])
    assert np.allclose(wise_covariance(m,False),[[4,-.25],[-.25,1]])

def test_invalid_catalog_covariance_is_rejected():
    with pytest.raises(ValueError):wise_covariance({'sigra_pm':1,'sigdec_pm':1,'sigradec_pm':2,'dec_pm':0})
    with pytest.raises(ValueError):ellipse_covariance(1,2,0)
