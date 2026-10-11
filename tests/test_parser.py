import pytest
from scripts.import_gaia import parse_votable

BASE = '''<VOTABLE xmlns="http://www.ivoa.net/xml/VOTable/v1.3" version="1.3"><RESOURCE type="results"><INFO name="QUERY_STATUS" value="OK"/><TABLE><FIELD name="source_id" datatype="long"/><FIELD name="parallax_error" datatype="double" unit="mas"/><DATA><TABLEDATA><TR><TD>5873456790123456789</TD><TD>{value}</TD></TR></TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>'''

def test_exact_identifier_and_null():
    fields, rows = parse_votable(BASE.format(value='').encode())
    assert rows[0]['source_id'] == '5873456790123456789'
    assert rows[0]['parallax_error'] is None
    assert fields['parallax_error']['unit'] == 'mas'

def test_nonfinite_rejected():
    with pytest.raises(ValueError): parse_votable(BASE.format(value='inf').encode())

def test_trailing_overflow_rejected():
    xml = BASE.format(value='1').replace('</RESOURCE>', '<INFO name="QUERY_STATUS" value="OVERFLOW"/></RESOURCE>')
    with pytest.raises(ValueError): parse_votable(xml.encode())
