import numpy as np
import pytest
from scripts.xp_covariance import unpack_correlation,merge_independent_bands,matrix_diagnostics,validate_working_covariance

def test_packed_correlations_use_row_order_and_unit_diagonal():
    assert np.allclose(unpack_correlation([.1,.2,.3],3),[[1,.1,.2],[.1,1,.3],[.2,.3,1]])

def test_merge_weights_apply_to_both_covariance_axes():
    bp={'flux':np.array([10.,20.,30.]),'flux_error':np.ones(3),'correlation_matrix':np.ones((3,3))}
    rp={'flux':np.array([40.,50.,60.]),'flux_error':np.full(3,2.),'correlation_matrix':np.ones((3,3))}
    f,c=merge_independent_bands(bp,rp,np.array([1,.5,0]),np.array([0,.5,1]))
    assert np.allclose(f,[10,35,60])
    assert np.allclose(c,[[1,.5,0],[.5,1.25,2],[0,2,4]])
    assert validate_working_covariance(c)['positive_semidefinite_at_relative_tolerance']

def test_missing_out_of_band_values_are_zero_weight_contributions_only():
    bp={'flux':np.array([10.,np.nan]),'flux_error':np.array([1.,np.nan]),'correlation_matrix':np.eye(2)}
    rp={'flux':np.array([np.nan,20.]),'flux_error':np.array([np.nan,2.]),'correlation_matrix':np.eye(2)}
    f,c=merge_independent_bands(bp,rp,np.array([1,0]),np.array([0,1]))
    assert np.allclose(f,[10,20]) and np.allclose(c,np.diag([1,4]))

def test_indefinite_covariance_cannot_be_used_or_silently_repaired():
    c=np.array([[1.,2.],[2.,1.]])
    assert not matrix_diagnostics(c)['positive_semidefinite_at_relative_tolerance']
    with pytest.raises(ValueError):validate_working_covariance(c)
    assert np.array_equal(c,[[1,2],[2,1]])

def test_singular_valid_covariance_is_distinguished_from_invertible_covariance():
    d=validate_working_covariance(np.ones((2,2)))
    assert d['rank_relative_1e_10']==1 and not d['cholesky_suitable_without_regularization']
    assert validate_working_covariance(np.diag([1.,2.]))['cholesky_suitable_without_regularization']

def test_invalid_weights_or_packed_shapes_are_rejected():
    with pytest.raises(ValueError):unpack_correlation([.1,.2],3)
    with pytest.raises(ValueError):merge_independent_bands({}, {},np.array([.2]),np.array([.2]))

def test_asymmetric_covariance_is_rejected():
    with pytest.raises(ValueError):matrix_diagnostics([[1,0],[.1,1]])
