from scripts.control_matching import covariates, differences, maximum_matching


def test_assignment_rematches_to_maximize_coverage():
    assert maximum_matching({'a':['1','2'], 'b':['1']}, ['a','b']) == {'b':'1','a':'2'}
    assignment = maximum_matching({'a':['1'], 'b':['1'], 'c':[]}, ['a','b','c'])
    assert len(assignment) == 1
    assert len(set(assignment.values())) == len(assignment)


def test_negative_snr_is_unusable_for_positive_snr_controls():
    row = {'phot_g_mean_mag':15, 'bp_rp':1, 'b':-20, 'parallax_over_error':-1, 'ruwe':1}
    vector, invalid = covariates(row)
    assert vector is None and invalid == ['parallax_over_error']
    assert row['parallax_over_error'] == -1  # Original measurement is retained.


def test_matching_wraps_latitude_sign_and_respects_factor_bounds():
    row = {'phot_g_mean_mag':15, 'bp_rp':1, 'b':-20, 'parallax_over_error':10, 'ruwe':1}
    assert covariates(row)[0][2] == 20
    a = [15, 1, 20, 10, 1]
    b = [15.5, 1.25, 30, 20, 2]
    assert differences(a,b) == [1]*5
    assert differences(a,[15,1,20,21,1])[3] > 1
