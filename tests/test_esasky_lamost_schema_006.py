"""Synthetic TAP fixtures validate read-only ESASky table discovery."""
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest

from scripts import esasky_lamost_schema_006 as q


def votable(fields, rows, status="OK"):
    root=ET.Element("VOTABLE",xmlns="http://www.ivoa.net/xml/VOTable/v1.3",version="1.3")
    resource=ET.SubElement(root,"RESOURCE",type="results")
    ET.SubElement(resource,"INFO",name="QUERY_STATUS",value=status)
    table=ET.SubElement(resource,"TABLE")
    for name in fields:
        ET.SubElement(table,"FIELD",name=name,datatype="char",arraysize="*")
    data=ET.SubElement(ET.SubElement(table,"DATA"),"TABLEDATA")
    for row in rows:
        tr=ET.SubElement(data,"TR")
        for value in row:
            ET.SubElement(tr,"TD").text=value
    return ET.tostring(root)


def test_metadata_tables_preserve_exact_catalog_names():
    values=q.read_metadata(votable(["table_name","description"],
        [["esasky.lamost_dr9_lrs_general","LAMOST DR9 LRS General catalogue"]]),
        ("table_name","description"))
    assert values[0]["table_name"]=="esasky.lamost_dr9_lrs_general"


def test_rejects_tap_overflow_and_missing_columns():
    with pytest.raises(ValueError):
        q.read_metadata(votable(["table_name","description"],[],status="OVERFLOW"),
                        ("table_name","description"))
    with pytest.raises(ValueError,match="missing"):
        q.read_metadata(votable(["table_name"],[["lamost"]]),
                        ("table_name","description"))


def test_rejects_unsafe_table_and_never_requests_stars():
    for value in ("table';DROP TABLE x--","/untrusted","a b"):
        with pytest.raises(ValueError,match="Unsafe"):
            q.query_columns(value)
    sql=q.query_columns("catalogues.lamost_dr9_lrs_general")
    assert sql.startswith("SELECT TOP 800")
    assert "TAP_SCHEMA.columns" in sql
    assert "WHERE table_name =" in sql
    assert "SELECT *" not in sql


def test_immutable_protocol_path():
    assert q.PROTOCOL.name == "EXPERIMENT_006.md"
    assert q.TAP_URL.startswith("https://sky.esa.int/")
