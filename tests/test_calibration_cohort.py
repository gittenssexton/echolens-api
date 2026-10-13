import pytest
from scripts.calibration_cohort import choose,calibrated_context

def row(sid):return {'source_id':sid}

def test_selection_is_order_invariant_and_excludes_exposed_ids():
    rows=[row(str(1000000000000000000+i)) for i in range(30)]
    a=choose(rows,{rows[0]['source_id']},20)
    assert a==choose(list(reversed(rows)),{rows[0]['source_id']},20)
    assert len(a)==20 and rows[0] not in a

def test_duplicate_ids_are_rejected():
    with pytest.raises(ValueError):choose([row('1'),row('1')],set())

def test_ir_magnitude_does_not_enter_selection():
    rows=[row(str(i)) for i in range(30)];ids=[r['source_id'] for r in choose(rows,set())]
    for r in rows:r['w3mpro']=-100000 if int(r['source_id'])%2 else 100000
    assert ids==[r['source_id'] for r in choose(rows,set())]

def test_generic_calibration_polynomial_uses_raw_logg():
    r={'logg_gspspec':3.,'mh_gspspec':-.1,'logg_gspspec_lower':2.8,'logg_gspspec_upper':3.2,'mh_gspspec_lower':-.2,'mh_gspspec_upper':0.}
    c=calibrated_context(r)
    assert c['calibrated_logg_sensitivity']==pytest.approx(3.2372)
    assert c['calibrated_mh_sensitivity']==pytest.approx(-.1533)
    assert r['logg_gspspec']==3. and r['mh_gspspec']==-.1

def test_native_join_keeps_exact_identifier_and_both_probability_columns():
    import numpy as np
    from io import BytesIO
    import xml.etree.ElementTree as ET
    from astropy.table import Table
    from astropy.io.votable import from_table,writeto
    from scripts.calibration_cohort import parse_pool
    sid=4461930649238469760
    table=Table({'gaia_source_id':np.array([sid],dtype=np.int64),'source_id':np.array([sid],dtype=np.int64),'gaia_probability':[.999],'ap_probability':[.999]})
    stream=BytesIO();writeto(from_table(table),stream,tabledata_format='binary2');root=ET.fromstring(stream.getvalue())
    for f in root.findall('.//{*}FIELD'):
        if f.get('name') in ['gaia_probability','ap_probability']:f.set('name','classprob_dsc_combmod_star')
    resource=root.find('.//{*}RESOURCE');ET.SubElement(resource,'{http://www.ivoa.net/xml/VOTable/v1.3}INFO',{'name':'QUERY_STATUS','value':'OK'})
    _,rows=parse_pool(ET.tostring(root))
    assert rows[0]['source_id']==str(sid) and rows[0]['gaia_source_id']==sid
    assert rows[0]['gaia_classprob_dsc_combmod_star']==.999 and rows[0]['classprob_dsc_combmod_star']==.999

def test_parameter_box_envelope_includes_internal_calibration_extremum():
    import math
    r={'logg_gspspec':3.45,'mh_gspspec':0.,'logg_gspspec_lower':3.4,'logg_gspspec_upper':3.5,'mh_gspspec_lower':0.,'mh_gspspec_upper':0.}
    c=calibrated_context(r);critical=(.01+math.sqrt(.01**2+4*.0144*.1373))/(2*.0144)
    expected=.274-.1373*critical-.005*critical**2+.0048*critical**3
    assert c['mh_parameter_box_envelope'][0]==pytest.approx(expected)
