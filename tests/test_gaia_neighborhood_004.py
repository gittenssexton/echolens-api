"""Experiment 004 synthetic transport/unit fixtures only, not scientific source claims."""
import copy
import json
import xml.etree.ElementTree as ET
import pytest
from scripts import gaia_neighborhood_004 as ex


def votable(records,status="OK"):
    table_fields={
        "source_id":"long","ra":"double","dec":"double","ref_epoch":"double",
        "pmra":"double","pmdec":"double","ra_error":"double","dec_error":"double",
        "pmra_error":"double","pmdec_error":"double","parallax":"double",
        "parallax_error":"double","phot_g_mean_mag":"double",
        "phot_g_mean_flux_error":"double","ruwe":"double",
        "duplicated_source":"boolean","non_single_star":"int"
    }
    root=ET.Element("VOTABLE",xmlns="http://www.ivoa.net/xml/VOTable/v1.3",version="1.3")
    res=ET.SubElement(root,"RESOURCE",type="results")
    ET.SubElement(res,"INFO",name="QUERY_STATUS",value=status)
    table=ET.SubElement(res,"TABLE")
    for name in ex.COLUMNS:
        ET.SubElement(table,"FIELD",name=name,datatype=table_fields[name])
    data=ET.SubElement(ET.SubElement(table,"DATA"),"TABLEDATA")
    for row in records:
        tr=ET.SubElement(data,"TR")
        for name in ex.COLUMNS:
            v=row.get(name)
            ET.SubElement(tr,"TD").text=None if v is None else (
               "true" if v is True else "false" if v is False else str(v))
    return ET.tostring(root)


def record(source_id="876451818359869824",ra=120.7483759,dec=29.1898351):
    return {"source_id":source_id,"ra":ra,"dec":dec,"ref_epoch":2016.0,
            "pmra":-6.576,"pmdec":-24.698,"ra_error":.1,"dec_error":.2,
            "pmra_error":.1,"pmdec_error":.1,"parallax":2.0,"parallax_error":.1,
            "phot_g_mean_mag":9.45,"phot_g_mean_flux_error":2.0,"ruwe":1.07,
            "duplicated_source":False,"non_single_star":0}


TARGET={"obsid":"655310123","gaia_dr3_source_id":"876451818359869824",
        "catalog_ra_deg":120.7483759,"catalog_dec_deg":29.1898351,
        "catalog_G_mag":9.451}


def test_truncated_or_unexpected_catalog_rejected():
    xml=votable([record()])
    fields,stars=ex.validate_response(xml,TARGET)
    assert len(fields)==len(ex.COLUMNS) and len(stars)==1
    assert stars[0]["source_id"]=="876451818359869824"
    with pytest.raises(ValueError,match="TAP error|truncated"):
        ex.validate_response(votable([record()],status="OVERFLOW"),TARGET)
    with pytest.raises(ValueError,match="Duplicate"):
        ex.validate_response(votable([record(),record()]),TARGET)


def test_extra_out_of_cone_rejected():
    with pytest.raises(ValueError,match="outside cone"):
        ex.validate_response(votable([record(ra=121.2)]),TARGET)


def test_source_ids_never_float_and_query_is_registered():
    with pytest.raises(ValueError):ex.decimal_id("8.76451818359869824e17")
    assert ex.decimal_id(876451818359869824)=="876451818359869824"
    q=ex.query_for(TARGET)
    assert "gaia_dr3_source" in q and "CIRCLE" in q and "TOP 1000" in q


def test_small_angle_wrap_precision():
    assert ex.separation_arcsec(359.999,0,.001,0)==pytest.approx(7.2,rel=1e-6)
    assert ex.separation_arcsec(0,0,0,0)==0


def test_validates_negative_uncertainty():
    src=record()
    src["dec_error"]=-1
    with pytest.raises(ValueError,match="uncertainty"):
        ex.validate_response(votable([src]),TARGET)


def test_select_is_frozen_exact_sample_and_review_source_first(tmp_path,monkeypatch):
    lamost={"experiment":"003","records":[]}
    gaia={"experiment":"003G","sources":[]}
    for i in range(250):
        obsid="655310123" if i==0 else str(9000000+i)
        sid="876451818359869824" if i==0 else str(10000000+i)
        gaia["sources"].append({"lamost_obsid":obsid,"gaia_dr3_source_id":sid,
              "gaia_record":{"source_id":sid,"ref_epoch":2016.0}})
        lamost["records"].append({"lamost_obsid":obsid,
           "gaia_dr3_id_provisional":sid,
           "published_raw_row":{"RAJ2000":120.7,"DEJ2000":29.1,"Gmag":12.5}})
    lpath=tmp_path/"lamost.json";apath=tmp_path/"gaia.json"
    lpath.write_text(json.dumps(lamost));apath.write_text(json.dumps(gaia))
    monkeypatch.setattr(ex,"EXPECTED_LAMOST_SHA",ex.digest(lpath.read_bytes()))
    monkeypatch.setattr(ex,"EXPECTED_GAIA_AUDIT_SHA",ex.digest(apath.read_bytes()))
    sel=ex.frozen_selection(lpath,apath)
    assert sel==ex.frozen_selection(lpath,apath)
    assert sel["target_count"]==25
    assert sel["targets"][0]["obsid"]=="655310123"
    assert len({x["obsid"] for x in sel["targets"]})==25


def test_selection_rejects_changed_source_json(tmp_path):
    p=tmp_path/"bad.json"
    p.write_text("{}")
    with pytest.raises(ValueError,match="checksum"):
        ex.frozen_selection(p,p)
