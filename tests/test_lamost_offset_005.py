"""Synthetic tests verify analysis math; discovery uses only real frozen observations."""
from copy import deepcopy
import pytest
from scripts import lamost_offset_005 as x


def sample(n=250):
    l={"experiment":"003","records":[]}
    g={"experiment":"003G","sources":[]}
    for i in range(n):
        oid="655310123" if i==0 else str(40000000+i)
        sid="876451818359869824" if i==0 else str(12000000+i)
        l["records"].append({"lamost_obsid":oid,"gaia_dr3_id_provisional":sid,
            "published_raw_row":{"RAJ2000":12.5,"DEJ2000":20.1}})
        g["sources"].append({"lamost_obsid":oid,"gaia_dr3_source_id":sid,
            "fiber_to_gaia_position_arcsec_epoch_unqualified":5.12 if i==0 else .2,
            "gaia_record":{"source_id":sid,"phot_g_mean_mag":9.45 if i==0 else 13.2,
            "pmra":0.0,"pmdec":0.0,"pmra_error":0.1,"pmdec_error":0.1}})
    return l,g


def test_post_hoc_analysis_reports_sources_and_missing_actual_offset():
    l,g=sample()
    v=x.analyze(l,g)
    assert v["rows"]==250
    assert v["flagged_source"]["G_brightness_rank_1_is_brightest"]==1
    assert v["flagged_source"]["separation_rank_1_is_largest"]==1
    assert v["brightness_partitions"]["G_below_11"]["stars"]==1
    assert v["brightness_partitions"]["G_at_least_11"]["stars"]==249
    assert v["flagged_source"]["official_fiber_offset_flag"] is None
    assert v["flagged_source"]["official_observation_date"] is None


def test_spearman_tie_behavior_without_claiming_significance():
    assert x.spearman([1,2,3],[3,2,1])==pytest.approx(-1)
    assert x.spearman([1,1,1],[1,2,3]) is None
    assert x.spearman([1,2,2,3],[4,3,3,2])==pytest.approx(-1)


def test_identity_mismatch_rejected():
    l,g=sample()
    g["sources"][7]["gaia_dr3_source_id"]="992992"
    with pytest.raises(ValueError,match="source ID changed"):
        x.analyze(l,g)


def test_catalog_magnitude_missing_is_not_hidden():
    l,g=sample()
    g["sources"][11]["gaia_record"]["phot_g_mean_mag"]=None
    with pytest.raises(ValueError,match="missing"):
        x.analyze(l,g)


def test_rank_partition_no_synthetic_science():
    assert x.describe([{"separation_arcsec":.1},{"separation_arcsec":1.2}])=={
        "stars":2,"median_separation_arcsec":.65,
        "p90_nearest_rank_separation_arcsec":1.2,
        "above_1_arcsec":1,"above_3_arcsec":0
    }
