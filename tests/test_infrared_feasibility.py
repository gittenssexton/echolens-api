from scripts.infrared_feasibility import associate,propagate,quality,separation

def star(**extra):return {'ra':359.9999,'dec':60,'ref_epoch':2016,'pmra':1000,'pmdec':0,**extra}

def test_proper_motion_cosdec_and_wrap():
    ra,dec,moved=propagate(star(),2017)
    assert moved and 0<ra<.001
    assert abs(separation((359.9999,60),(ra,dec))-1)<1e-6

def test_pole_propagation_is_finite():
    ra,dec,moved=propagate(star(ra=15,dec=89.99999),2000)
    assert moved and 0<=ra<360 and -90<=dec<=90

def test_missing_motion_is_explicit():
    assert propagate(star(pmra=None),2000)==(359.9999,60,False)

def test_ambiguous_counterparts_are_not_chosen():
    g=star(ra=10,dec=0,pmra=0)
    rows=[{'ra_pm':10,'dec_pm':0},{'ra_pm':10.0001,'dec_pm':0}]
    a=associate(g,rows,'wise')
    assert a['status']=='ambiguous' and a['chosen'] is None

def test_tmass_uses_observation_date():
    g=star(ra=10,dec=0,pmra=1000)
    row={'ra':10,'dec':0,'jdate':2457388.5}
    a=associate(g,[row],'tmass')
    assert a['chosen']['epoch_basis']=='2MASS jdate'
    assert a['chosen']['separation_arcsec']<.01

def test_upper_limit_is_not_valid_photometry():
    row={'ph_qual':'AAUA','w3snr':1,'w3sigmpro':None,'w3sigflux':1,'cc_flags':'0000','ext_flg':0,'w3sat':0}
    failures=quality(row,'wise','3')
    assert 'photometric_quality' in failures and 'magnitude_error' in failures

def test_quality_is_band_specific():
    row={'ph_qual':'AAAA','w3snr':10,'w3sigmpro':.1,'w3sigflux':1,'cc_flags':'d000','ext_flg':0,'w3sat':0}
    assert quality(row,'wise','3')==[]

def test_2mass_confusion_flag_rejects_band():
    row={'ph_qual':'AAA','cc_flg':'0c0','h_msigcom':.1}
    assert quality(row,'tmass','h')==['artifact']
