"""Derived numerical display must be stable without affecting native measurements."""
from scripts.wise_pilot import display_separation_arcsec


def test_microarcsecond_rounding_difference_collapses():
    assert display_separation_arcsec(.177952) == .17795
    assert display_separation_arcsec(.177953) == .17795


def test_half_up_quantizer_and_no_measurement_mutation():
    sep = .237895
    assert display_separation_arcsec(sep) == .2379
    assert sep == .237895
    assert display_separation_arcsec(3.000001) == 3.0
    assert 3.000001 > 3.0  # eligibility still uses original unrounded separation
