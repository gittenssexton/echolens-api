"""Synthetic unit fixtures for 006B; not published as stellar measurements."""
import xml.etree.ElementTree as ET
import pytest
from scripts import esasky_lamost_obsids_006 as ex

TYPES={"obsid":"int","obsdate":"char","mjd":"int",
       "ra":"double","dec":"double","ra_obs":"double","dec_obs":"double",
       "offsets":"short","offsets_v":"double","gaia_source_id":"char",
       "gaia_g_mean_mag":"double","designation":"char","snri":"double","snrz":"double"}


def row():
    return {"obsid":655310123,"obsdate":"2018-01-01","mjd":58119,
      "ra":120.748,"dec":29.19,"ra_obs":120.7484,"dec_obs":29.1898,
      "offsets":1,"offsets_v":1.5,"gaia_source_id":"876451818359869824",
      "gaia_g_mean_mag":9.451,"designation":"LAMOST_Test",
      "snri":120.0,"snrz":110.0}


def xml(rows,status="OK"):
    root=ET.Element("VOTABLE",xmlns="http://www.ivoa.net/xml/VOTable/v1.3",version="1.3")
    resource=ET.SubElement(root,"RESOURCE",type="results")
    ET.SubElement(resource,"INFO",name="QUERY_STATUS",value=status)
    table=ET.SubElement(resource,"TABLE")
    for name in ex.FIELDS:
        kw={"name":name,"datatype":TYPES[name]}
        if TYPES[name]=="char":kw["arraysize"]="*"
        ET.SubElement(table,"FIELD",**kw)
    data=ET.SubElement(ET.SubElement(table,"DATA"),"TABLEDATA")
    for r in rows:
        tr=ET.SubElement(data,"TR")
        for name in ex.FIELDS:
            val=r[name]
            ET.SubElement(tr,"TD").text=str(val) if val is not None else None
    return ET.tostring(root)


def test_expected_fields_exact_gaia_id_and_offset_flag():
    fields,records=ex.parse_batch(xml([row()]),["655310123"])
    assert len(fields)==len(ex.FIELDS)
    assert records[0]["obsid"]=="655310123"
    assert records[0]["gaia_source_id"]=="876451818359869824"
    assert records[0]["offsets"]==1
    assert records[0]["offsets_v"]==1.5


def test_preregistered_query_and_reject_duplicate_substitution():
    q=ex.query_for(["11","655310123"])
    assert "FROM catalogues.mv_lamost_dr9_lrs_fdw" in q
    assert "ORDER BY obsid ASC" in q
    assert "TOP 100" in q
    with pytest.raises(ValueError,match="Invalid sorted"):
        ex.query_for(["12","11"])
    with pytest.raises(ValueError,match="Unrequested or duplicate"):
        ex.parse_batch(xml([row(),row()]),["655310123"])
    with pytest.raises(ValueError,match="Unrequested or duplicate"):
        ex.parse_batch(xml([row()]),["655310124"])


def test_missing_record_allowed_and_no_false_fiber_flag():
    fields,records=ex.parse_batch(xml([]),["655310123"])
    assert not records
    r=row();r["offsets"]=0;r["offsets_v"]=None
    assert ex.parse_batch(xml([r]),["655310123"])[1][0]["offsets"]==0


def test_invalid_offset_and_tap_overflow_rejected():
    r=row();r["offsets"]=1;r["offsets_v"]=-1
    with pytest.raises(ValueError,match="invalid magnitude"):
        ex.parse_batch(xml([r]),["655310123"])
    with pytest.raises(ValueError):
        ex.parse_batch(xml([row()],status="OVERFLOW"),["655310123"])


def test_no_float_id_or_source_relabeling():
    with pytest.raises(ValueError):ex.exact_id(876451818359869824.0)
    assert ex.exact_id("876451818359869824")=="876451818359869824"


def test_fiber_geometry_and_date_not_crossmatch_claim():
    assert ex.rounded_sep(0,0,0,0)==0
    assert ex.angular_arcsec(359.999,0,.001,0)==pytest.approx(7.2,rel=1e-6)
    assert ex.check_date("2018-01-01",58119)=="consistent_within_2_days"
    assert ex.check_date(None,58119)=="missing_date_or_mjd"
