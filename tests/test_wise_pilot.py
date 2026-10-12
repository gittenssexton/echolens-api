import pytest
from astropy.time import Time
from scripts.wise_pilot import candidate_epoch, photometry, propagate, separation, validate_wise


def test_proper_motion_cos_declination_and_ra_wrap():
    epoch = Time(55400., format='mjd', scale='tt').jyear
    row = dict(ra=359.9999, dec=60., ref_epoch=epoch-1, pmra=1000., pmdec=0.)
    moved = propagate(row,55400.)
    assert moved[0] < .001
    assert separation((row['ra'],row['dec']),moved) == pytest.approx(1.,abs=1e-8)


def test_upper_limit_is_never_a_quality_detection():
    row = dict(ph_qual='UZAX',cc_flags='0000',moon_lev='0000',ext_flg=0,nb=1,na=0)
    for band in range(1,5):
        row.update({f'w{band}mpro':12.,f'w{band}sigmpro':.02,f'w{band}sigflux':1.,
                    f'w{band}snr':20.,f'w{band}sat':0.,f'w{band}rchi2':1.})
    bands = photometry(row)
    assert bands['w1']['kind']=='upper_limit_95pct_flux'
    assert not bands['w1']['quality_pass']
    assert bands['w2']['kind']=='uncertain_measurement'
    assert not bands['w2']['quality_pass']
    assert bands['w3']['quality_pass']
    assert bands['w4']['kind']=='missing'
    row['cc_flags']='00d0'
    assert 'contamination' in photometry(row)['w3']['quality_failures']


def test_epoch_fallback_is_explicitly_approximate():
    row = dict(ra=20.,dec=30.,w1mjdmean=55300.)
    assert 'approximate' in candidate_epoch(row)[2]
    row.update(ra_pm=21.,dec_pm=31.)
    assert candidate_epoch(row)==((21.,31.),55400.,'motion_fit_epoch')


def test_rejects_duplicate_sources_and_negative_uncertainties():
    row = dict(source_id='test',ra=20.,dec=30.,w1sigflux=1.)
    with pytest.raises(ValueError,match='duplicate'):
        validate_wise([row,row])
    row['w1sigflux']=-1.
    with pytest.raises(ValueError,match='Negative'):
        validate_wise([row])
