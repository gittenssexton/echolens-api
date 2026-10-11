"""Unit tests for Experiment 003 use synthetic *test fixtures*, never discovery evidence."""
import copy
import hashlib
import xml.etree.ElementTree as ET

import pytest

from scripts import lamost_controls_003 as exp


def row():
    return {"recno": 10, "obsid": 31703101, "GaiaDR3": 5873456790123456789,
            "SNRi": 120.0, "SNRz": 130.0, "RAJ2000": 7.3, "DEJ2000": -12.0,
            "Teff": 5700, "e_Teff": 70, "logg": 4.3, "e_logg": 0.12,
            "FeH": -0.12, "e_FeH": 0.05, "R8542": 1.23, "e_R8542": .04}


def xml_rows(rows, status="OK"):
    fields = [("recno", "long"), ("obsid", "long"), ("GaiaDR3", "long"),
              ("SNRi", "double"), ("SNRz", "double"), ("RAJ2000", "double"),
              ("DEJ2000", "double"), ("Teff", "double"), ("e_Teff", "double"),
              ("logg", "double"), ("e_logg", "double"), ("FeH", "double"),
              ("e_FeH", "double"), ("R8542", "double"), ("e_R8542", "double")]
    # Namespace and TAP status are mandatory to the upstream parser.
    root = ET.Element("VOTABLE", xmlns="http://www.ivoa.net/xml/VOTable/v1.3", version="1.3")
    resource = ET.SubElement(root, "RESOURCE", type="results")
    ET.SubElement(resource, "INFO", name="QUERY_STATUS", value=status)
    table = ET.SubElement(resource, "TABLE")
    for name, datatype in fields:
        ET.SubElement(table, "FIELD", name=name, datatype=datatype)
    data = ET.SubElement(ET.SubElement(table, "DATA"), "TABLEDATA")
    for item in rows:
        tr = ET.SubElement(data, "TR")
        for name, _ in fields:
            ET.SubElement(tr, "TD").text = str(item[name]) if item.get(name) is not None else ""
    return ET.tostring(root)


def test_selection_stable_in_range_and_not_science_based():
    a, b = exp.freeze_selection(), exp.freeze_selection()
    assert a == b and len(a) == 250 and len(set(a)) == 250
    assert all(1 <= n <= 699348 for n in a)
    assert exp.query_for(a[:25]) == exp.query_for(a[:25])
    with pytest.raises(ValueError):
        exp.query_for([1, 1])


def test_quality_ready_exact_id_and_published_errors():
    r = exp.assess_row(row())
    assert r["spectroscopic_label_ready"]
    assert r["gaia_dr3_id_provisional"] == "5873456790123456789"
    assert r["spectroscopic_inferences"]["Teff"]["published_error"] == 70


def test_null_error_sentinel_keeps_raw_and_rejects_quality():
    src = row()
    src["e_Teff"] = -9999
    entry = exp.assess_row(src)
    assert not entry["spectroscopic_label_ready"]
    assert "missing_or_nonpositive_uncertainty_e_Teff" in entry["quality_failures"]
    assert entry["published_raw_row"]["e_Teff"] == -9999
    assert entry["spectroscopic_inferences"]["Teff"]["published_error"] is None


def test_invalid_id_not_cast_through_float():
    assert exp.valid_id(5873456790123456789) == "5873456790123456789"
    assert exp.valid_id(float(5873456790123456789)) is None
    assert exp.valid_id("") is None
    assert exp.valid_id("-9999") is None


def test_validates_transport_status_and_exact_requested_indices():
    payload = xml_rows([row()])
    fields, records = exp.validate_batch(payload, [10])
    assert len(fields) == 15 and len(records) == 1
    assert records[0]["spectroscopic_label_ready"]
    with pytest.raises(ValueError, match="TAP error|truncated"):
        exp.validate_batch(xml_rows([row()], "OVERFLOW"), [10])
    with pytest.raises(ValueError, match="preregistered|Missing, duplicated"):
        exp.validate_batch(payload, [11])


def test_rejects_duplicate_spectrum_rows_even_if_row_indices_distinct():
    a = row()
    b = copy.deepcopy(a)
    b["recno"] = 11
    with pytest.raises(ValueError, match="Duplicate spectrum"):
        exp.validate_batch(xml_rows([a, b]), [10, 11])


def test_zero_error_is_not_zero_uncertainty():
    x = row()
    x["e_FeH"] = 0
    r = exp.assess_row(x)
    assert not r["spectroscopic_label_ready"]
    assert "missing_or_nonpositive_uncertainty_e_FeH" in r["quality_failures"]


def test_fixed_fingerprint_input():
    x = exp.selection_manifest()
    assert x["selection_salt"] == "echolens-003-v1:"
    assert x["gaia_raw_sha256"] == exp.GAIA_SHA
    assert x["selection_sha256"] == hashlib.sha256(
        __import__("json").dumps(x["recno"], separators=(",", ":")).encode()).hexdigest()
