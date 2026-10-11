"""Synthetic test fixtures are NOT real astronomical measurements."""
import copy
import hashlib
import pytest

from scripts import stellar_reference_008 as ex


def fixture(obsid="123",sid="98765"):
    source={"source_id":sid,"ra":34.0,"dec":22.0,"ref_epoch":2016.0,
       "pmra":3.0,"pmdec":-2.0,"pmra_error":0.1,"pmdec_error":0.2,
       "parallax":5.0,"parallax_error":0.1,"phot_g_mean_mag":13.0,
       "bp_rp":1.0,"ruwe":1.05,"duplicated_source":False,
       "non_single_star":0,"phot_variable_flag":"NOT_AVAILABLE"}
    inference={field:{"value":value,"published_error":error}
               for field,value,error in (("Teff",5700,30),("logg",4.25,.04),
                                        ("FeH",-.13,.02))}
    l={obsid:{"lamost_obsid":obsid,"gaia_dr3_id_provisional":sid,
         "spectroscopic_label_ready":True,
         "published_raw_row":{"R8542":.4,"e_R8542":.01},
         "spectroscopic_inferences":inference}}
    g={obsid:{"gaia_dr3_source_id":sid,"gaia_record":source}}
    e={obsid:{"status":"esa_observation_found","published_gaia_source_id":sid,
         "esa_published_gaia_id_agrees":True,
         "esa_published_gaia_id_raw":sid,
         "date_mjd_check":"consistent_within_2_days",
         "esa_record":{"mjd":58189,"ra":34.0,"dec":22.0,
                       "offsets":0,"offsets_v":0}}}
    return l,g,e


def test_quality_reference_candidate_is_not_science_certified():
    l,g,e=fixture()
    row=ex.quality_record("123",l,g,e)
    assert row["quality_candidate"]
    assert row["cross_catalog_ID_concordant"]
    assert row["approx_Gaia_pm_to_LAMOST_input_arcsec"]<.03
    assert row["unknown_stellar_nature_and_survey_coverage"]["wise_verified"] is False
    assert row["catalogued_Gaia_variable_flag"]=="NOT_AVAILABLE"


def test_esa_alternative_gaia_id_and_offset_exclude_without_auto_correction():
    l,g,e=fixture()
    e["123"]["esa_published_gaia_id_agrees"]=False
    e["123"]["esa_published_gaia_id_wellformed"]=True
    e["123"]["esa_published_gaia_id_raw"]="98766"
    e["123"]["esa_record"]["offsets"]=1
    row=ex.quality_record("123",l,g,e)
    assert not row["quality_candidate"]
    assert row["cross_catalog_provenance_tier"]=="competing_Gaia_ID"
    assert "fiber_offset_applied_or_unknown" in row["all_gate_failure_reasons"]
    assert row["published_gaia_dr3_source_id"]=="98765"


def test_missing_or_out_of_range_catalog_measurements_are_not_imputed():
    l,g,e=fixture()
    g["123"]["gaia_record"]["parallax_error"]=0
    g["123"]["gaia_record"]["duplicated_source"]=None
    g["123"]["gaia_record"]["phot_variable_flag"]="VARIABLE"
    l["123"]["spectroscopic_inferences"]["logg"]["value"]=3.8
    l["123"]["published_raw_row"]["e_R8542"]=None
    row=ex.quality_record("123",l,g,e)
    assert not row["quality_candidate"]
    assert "Gaia_parallax_SNR_below_10_or_missing" in row["all_gate_failure_reasons"]
    assert "Gaia_duplicate_flag_or_missing" in row["all_gate_failure_reasons"]
    assert "Gaia_catalogued_VARIABLE" in row["all_gate_failure_reasons"]
    assert "LAMOST_logg_outside_registered_range_or_missing" in row["all_gate_failure_reasons"]
    assert "LAMOST_Ca_II_8542_activity_measurement_uncertainty_missing" in row["all_gate_failure_reasons"]


def candidate(oid, g=13.0, color=1.0):
    return {"obsid":str(oid),"quality_candidate":True,
            "covariates":{"g_mag":g,"bp_rp":color,"teff_K":5650,
                          "logg_dex":4.2,"feh_dex":-.1,"parallax_snr":22}}


def test_tolerances_fixed_and_match_distance_symmetric():
    a=candidate(1)["covariates"]
    b=candidate(2,g=13.7)["covariates"]
    left=ex.match_vectors(a,b)
    assert left and left==ex.match_vectors(b,a)
    assert left[0]==pytest.approx(.7/.75)
    assert ex.match_vectors(a,candidate(3,g=14.0)["covariates"]) is None
    assert ex.match_vectors(a,{**a,"parallax_snr":66.001}) is None


def test_frozen_deterministic_holdout_max_cardinality_and_no_reuse():
    pool=[candidate(1000+i) for i in range(90)]
    one=ex.paired_targets(pool)
    two=ex.paired_targets(list(reversed(pool)))
    assert one==two
    assert one["target_count"]==40
    assert one["control_count"]==50
    assert one["match_count"]==40
    assert one["criterion_met"]
    assert len({m["control_obsid"] for m in one["matches"]})==40
    assert one["targets"][0]["target_obsid"]==sorted(
        pool,key=lambda x:(hashlib.sha256((ex.SALT+x["obsid"]).encode()).hexdigest(),
                           int(x["obsid"])))[0]["obsid"]


def test_insufficient_candidate_count_cannot_invent_controls():
    result=ex.paired_targets([candidate(i) for i in range(79)])
    assert result["status"]=="not_executable_insufficient_candidates"
    assert result["match_count"]==0 and not result["criterion_met"]


def test_published_gaia_ids_must_be_exact_decimal_strings():
    for invalid in (999999.0,None,True,"1e19","-9999"):
        with pytest.raises(ValueError):
            ex.exact(invalid)
    assert ex.exact("876451818359869824")=="876451818359869824"


def test_missing_original_stellar_coordinates_cannot_pass_position():
    l,g,e=fixture()
    g["123"]["gaia_record"]["pmra"]=None
    result=ex.quality_record("123",l,g,e)
    assert not result["quality_candidate"]
    assert result["approx_Gaia_pm_to_LAMOST_input_arcsec"] is None
    assert "Gaia_to_LAMOST_input_target_exceeds_1_arcsec_or_unassessable" in result["all_gate_failure_reasons"]


def test_spherical_separation_handles_ra_wrapping():
    assert ex.geocoord_sep_arcsec(359.999,0,.001,0)==pytest.approx(7.2,rel=1e-6)
    assert ex.geocoord_sep_arcsec(34,22,34,22)==0.0
