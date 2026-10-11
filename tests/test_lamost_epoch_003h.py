"""Synthetic-fixture unit tests only; never publish these as stellar observations."""
import csv
import json
import math

import pytest

from scripts import lamost_epoch_003h as m


def row(separation=5.1201, pmra=-6.576, pmdec=-24.698, err=0.2):
    return {
      "lamost_obsid": "655310123",
      "gaia_dr3_source_id": "876451818359869824",
      "fiber_to_gaia_position_arcsec_epoch_unqualified": separation,
      "gaia_record": {
        "source_id": "876451818359869824",
        "ra": 1.5, "dec": -12.0, "ref_epoch": 2016.0,
        "pmra": pmra, "pmdec": pmdec,
        "pmra_error": err, "pmdec_error": err,
      }
    }


def test_post_hoc_mismatch_cannot_be_explained_by_only_dr9_window_pm():
    v = m.bound_row(row())
    assert v["review_status"] == "exceeds_3_arcsec_after_linear_pm_bound"
    assert v["proper_motion_mas_per_year"] == pytest.approx(25.558462, abs=1e-6)
    assert 0.13 < v["max_linear_motion_arcsec"] < 0.15
    assert v["minimum_residual_arcsec"] > 4.9


def test_missing_proper_motion_does_not_fabricate_corrected_separation():
    v = m.bound_row(row(pmra=None))
    assert v["review_status"] == "no_gaia_proper_motion_assessment"
    assert v["minimum_residual_arcsec"] is None


def test_date_window_has_physical_bounds():
    assert 5.4 < m.span_years_from_gaia_epoch(2016.0) < 5.6


def test_readonly_250_observation_check_keeps_exact_ids():
    l = {"records": [{"lamost_obsid": str(i+10), "gaia_dr3_id_provisional": str(i+1000)}
                     for i in range(250)]}
    g = {"sources": [
      {"lamost_obsid": str(i+10), "gaia_dr3_source_id": str(i+1000),
       "gaia_record": {"source_id":str(i+1000),"ra":1.0,"dec":0.0}}
      for i in range(250)]}
    assert len(m.strict_records(l,g)) == 250
    g["sources"][8]["gaia_dr3_source_id"] = "9876543"
    with pytest.raises(ValueError,match="mapping"):
        m.strict_records(l,g)


def test_official_csv_requires_named_provenance_and_never_substitutes(tmp_path):
    path=tmp_path/"official.csv"
    path.write_text("obsid,obsdate,mjd,ra_obs,dec_obs,offsets,offsets_v\n"
                    "655310123,2018-01-01,58119,150.1,-1.4,false,0\n"
                    "199999999,2017-01-01,57800,77.5,5.1,false,0\n")
    with pytest.raises(ValueError,match="provenance"):
        m.official_metadata_csv(path,{"655310123"},"","")
    data=m.official_metadata_csv(path,{"655310123","5"},
          "https://www.lamost.org/dr9/v2.0/catalogue","LAMOST DR9 v2.0 LRS General")
    assert data["official_obsid_retrieved_count"]==1
    assert data["missing_obsids"]==["5"]
    assert data["raw_catalog_records"][0]["obsid"]=="655310123"


def test_duplicate_official_observation_rejected(tmp_path):
    path=tmp_path/"bad.csv"
    header="obsid,obsdate,mjd,ra_obs,dec_obs,offsets,offsets_v\n"
    line="655310123,2018-01-01,58119,150.1,-1.4,false,0\n"
    path.write_text(header+line+line)
    with pytest.raises(ValueError,match="Duplicate"):
        m.official_metadata_csv(path,{"655310123"},
          "https://www.lamost.org/dr9/v2.0/catalogue","LAMOST DR9 v2.0 LRS General")
