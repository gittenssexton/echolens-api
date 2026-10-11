"""Synthetic fixture tests only: no generated values are research observations."""
import xml.etree.ElementTree as ET
import pytest
from scripts import catalog_crossid_007 as exp


def xml(fields, data, status="OK"):
    root=ET.Element("VOTABLE",xmlns="http://www.ivoa.net/xml/VOTable/v1.3",version="1.3")
    res=ET.SubElement(root,"RESOURCE",type="results")
    ET.SubElement(res,"INFO",name="QUERY_STATUS",value=status)
    table=ET.SubElement(res,"TABLE")
    for name,kind in fields:
        opts={"name":name,"datatype":kind}
        if kind=="char":opts["arraysize"]="*"
        ET.SubElement(table,"FIELD",**opts)
    tbody=ET.SubElement(ET.SubElement(table,"DATA"),"TABLEDATA")
    for item in data:
        tr=ET.SubElement(tbody,"TR")
        for name,_ in fields:
            v=item.get(name)
            ET.SubElement(tr,"TD").text=None if v is None else str(v)
    return ET.tostring(root)


GAIA_TYPES={"source_id":"long","ra":"double","dec":"double","ref_epoch":"double",
    "pmra":"double","pmdec":"double","pmra_error":"double","pmdec_error":"double",
    "parallax":"double","parallax_error":"double",
    "phot_g_mean_mag":"double","phot_g_mean_flux_error":"double",
    "bp_rp":"double","ruwe":"double","duplicated_source":"boolean",
    "non_single_star":"int"}
DR8_TYPES={"obsid":"long","obsdate":"char","mjd":"int","ra":"double",
    "dec":"double","ra_obs":"double","dec_obs":"double","offsets":"short",
    "offsets_v":"double","gaia_source_id":"char"}


def gaia_row(source_id=None):
    return {"source_id":int(source_id or exp.PAIRS["235608062"][0]),
        "ra":227.9,"dec":22.1,"ref_epoch":2016.0,
        "pmra":-10.5,"pmdec":5.4,"pmra_error":0.2,"pmdec_error":0.3,
        "parallax":1.5,"parallax_error":0.1,"phot_g_mean_mag":15.1,
        "phot_g_mean_flux_error":2,"bp_rp":1.2,"ruwe":1.03,
        "duplicated_source":False,"non_single_star":0}


def dr8_row(obsid=None):
    return {"obsid":int(obsid or exp.MISSING[0]),"obsdate":"2014-01-01",
            "mjd":56658,"ra":120.1,"dec":24.0,
            "ra_obs":120.1,"dec_obs":24.0,"offsets":0,"offsets_v":0,
            "gaia_source_id":"-9999"}


def make_xml(kind,rows,status="OK"):
    spec=GAIA_TYPES if kind=="gaia" else DR8_TYPES
    fields=exp.GAIA_COLUMNS if kind=="gaia" else exp.DR8_COLUMNS
    return xml([(name,spec[name]) for name in fields],rows,status)


def test_all_frozen_id_pairs_and_9_mirror_missing_cases():
    assert len(exp.PAIRS)==2
    assert len(exp.MISSING)==9
    assert len({sid for pair in exp.PAIRS.values() for sid in pair})==4
    assert len(exp.frozen_selection()["gaia_source_ids"])==4
    assert len(exp.frozen_selection()["lamost_dr8_obsids"])==9


def test_query_uses_all_exact_big_gaia_ids_with_no_cone():
    url,query,ids,col=exp.query_for("gaia")
    assert "WHERE source_id IN (" in query
    assert len(ids)==4 and col=="source_id"
    assert all(i in query for i in ids)
    assert "CIRCLE" not in query
    assert "SELECT TOP 100" in query


def test_real_64_bit_ids_never_float_cast_or_replaced():
    _,recs=exp.check_batch(make_xml("gaia",[gaia_row()]),"gaia")
    assert recs[0]["source_id"]=="1215223960901067520"
    with pytest.raises(ValueError,match="float-cast"):
        exp.exact_id(1215223960901067520.0)


def test_dr8_found_absent_spectra_but_sentinel_preserved():
    _,recs=exp.check_batch(make_xml("dr8",[dr8_row()]),"dr8")
    assert len(recs)==1 and recs[0]["obsid"]==exp.MISSING[0]
    assert recs[0]["gaia_source_id"]=="-9999"


def test_duplicate_extra_and_bad_error_rejected():
    r=gaia_row()
    with pytest.raises(ValueError,match="excess rows|cap"):
        exp.check_batch(make_xml("gaia",[r,r,r,r,r]),"gaia")
    r["pmra_error"]=-1
    with pytest.raises(ValueError,match="uncertainty"):
        exp.check_batch(make_xml("gaia",[r]),"gaia")
    with pytest.raises(ValueError,match="TAP error|truncated"):
        exp.check_batch(make_xml("gaia",[gaia_row()],status="OVERFLOW"),"gaia")


def test_epoch_propagation_is_diagnostic_not_certification():
    r=gaia_row()
    initial=(r["ra"],r["dec"])
    new=exp.approx_propagate(r,58189)
    assert new!=initial
    assert abs(new[0]-initial[0])<.0001
    assert abs(new[1]-initial[1])<.0001
    assert exp.approx_propagate({**r,"pmra":None},58189) is None
    assert exp.sep_arcsec(359.999,0,.001,0)==pytest.approx(7.2,rel=1e-6)
