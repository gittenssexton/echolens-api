from scripts.calibration_development import eligible,robust_summary

def test_reserved_stars_are_never_development_targets_even_if_ready_or_bright():
    rows=[{'source_id':'1','analysis_role':'calibration_development','joint_ready':True}, {'source_id':'2','analysis_role':'validation_reserved','joint_ready':True,'w3mpro':-100}, {'source_id':'3','analysis_role':'calibration_development','joint_ready':False}]
    assert [r['source_id'] for r in eligible(rows)]==['1']

def test_descriptive_dispersion_uses_median_not_zero_reference():
    s=robust_summary([.1,.2,.3]);assert s['median']==.2
    assert abs(s['MAD_about_median']-.1)<1e-14
    assert s['count']==3 and 'descriptive' in s['scope']
