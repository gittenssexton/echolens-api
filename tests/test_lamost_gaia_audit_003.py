"""Synthetic fixture checks for Experiment 003G, no fabricated discovery records."""
import xml.etree.ElementTree as ET
import pytest
from scripts import lamost_gaia_audit_003 as a


def votable(items, status="OK"):
    specs=[("source_id","long"),("ra","double"),("dec","double"),
           ("ra_error","double"),("dec_error","double"),("pmra","double"),
           ("pmdec","double"),("pmra_error","double"),("pmdec_error","double"),
           ("ref_epoch","double"),("phot_g_mean_mag","double"),
           ("ruwe","double"),("parallax","double"),("parallax_error","double")]
    root=ET.Element("VOTABLE",xmlns="http://www.ivoa.net/xml/VOTable/v1.3",version="1.3")
    resource=ET.SubElement(root,"RESOURCE",type="results")
    ET.SubElement(resource,"INFO",name="QUERY_STATUS",value=status)
    tab=ET.SubElement(resource,"TABLE")
    for name,t in specs: ET.SubElement(tab,"FIELD",name=name,datatype=t)
    data=ET.SubElement(ET.SubElement(tab,"DATA"),"TABLEDATA")
    for sid in items:
        values={"source_id":sid,"ra":359.999,"dec":0,"ra_error":0.1,"dec_error":0.1,
                "pmra":1,"pmdec":2,"pmra_error":0.5,"pmdec_error":0.5,
                "ref_epoch":2016.0,"phot_g_mean_mag":12.7,
                "ruwe":1.01,"parallax":1.0,"parallax_error":0.1}
        tr=ET.SubElement(data,"TR")
        for name,_ in specs: ET.SubElement(tr,"TD").text=str(values[name])
    return ET.tostring(root)


def test_exact_large_gaia_id_through_votable():
    sid="5873456790123456789"
    fields,rows=a.validate_response(votable([sid]),[sid])
    assert rows[0]["source_id"]==sid
    assert "parallax_error" in fields


def test_extra_id_and_overflow_rejected():
    with pytest.raises(ValueError,match="Extra"):
        a.validate_response(votable(["11"]),["12"])
    with pytest.raises(ValueError,match="TAP error|truncated"):
        a.validate_response(votable(["11"],status="OVERFLOW"),["11"])


def test_exact_numeric_batches_only():
    assert 'IN (11,12)' in a.query_for(["11","12"])
    with pytest.raises(ValueError): a.query_for(["12","11"])
    with pytest.raises(ValueError): a.query_for(["11","11"])
    with pytest.raises(ValueError): a.query_for(["1e9"])


def test_angle_wrapping_and_positive_offsets():
    assert a.separation_arcsec(359.999,0,.001,0)==pytest.approx(7.2,rel=1e-6)
    assert a.separation_arcsec(1,2,1,2)==pytest.approx(0.0)


def test_negative_astrometric_error_rejected():
    s=votable(["11"]).replace(b"<TD>0.1</TD>",b"<TD>-0.1</TD>",1)
    with pytest.raises(ValueError,match="uncertainty"):
        a.validate_response(s,["11"])
