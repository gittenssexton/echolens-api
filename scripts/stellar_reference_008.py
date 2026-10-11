"""EchoLens Experiment 008 — frozen real stellar-reference candidate and matching study.

Run against immutable Experiment 003, 003G, 006B and 007 results only.
NO inference of extraterrestrial life, normality or independently certified links.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from statistics import median

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=ROOT/"docs/EXPERIMENT_008.md"
INPUT_SHA={
  "lamost003":"efc4f3eaf5f5e1df8b60aa1897ffd93d44c3b05fe69318b27d3769fddb342e51",
  "gaia003g":"d11e0c62eaa8aa26b2fe92fc30b0ca93891459caf4878d89cf2285fc0527a748",
  "esa006b":"73b2dbf80ff591d42386c4149dcea1e0ca2225569728dd94c8efacb7609b4fa7",
}
N=250
HOLDOUT=40
MIN_POOL=80
MIN_PAIRS=25
SALT="echolens-008-v1:"
FIELDS=("g_mag","bp_rp","teff_K","logg_dex","feh_dex","parallax_snr")
TOLS=(0.75,0.30,350.0,0.50,0.30,3.0)
MISSING_COVERAGE={
 "wise_verified":False,"twomass_verified":False,"extinction_verified":False,
 "spectral_activity_class_verified":False,"full_covariance_crossmatch_verified":False,
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path,expected=None):
    raw=Path(path).read_bytes()
    if expected is not None and sha(raw)!=expected:
        raise ValueError("Archived source checksum changed for "+str(path))
    return json.loads(raw),sha(raw)


def exact(value):
    if value is None or isinstance(value,(float,bool)):
        raise ValueError("Invalid exact decimal source/observation identifier")
    s=str(value)
    if not s.isascii() or not s.isdigit() or not 0<int(s)<2**63:
        raise ValueError("Non-decimal source/observation identifier")
    return s


def finite(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def positive(value):
    return finite(value) and value>0


def geocoord_sep_arcsec(ra1,dec1,ra2,dec2):
    a,d,b,e=map(math.radians,(ra1,dec1,ra2,dec2))
    h=math.sin((e-d)/2)**2+math.cos(d)*math.cos(e)*math.sin((b-a)/2)**2
    return math.degrees(2*math.asin(math.sqrt(max(0,min(1,h)))))*3600


def corrected_target_offset(gaia,esa):
    """Linear PM approximation only, not full parallax/covariance propagation."""
    needed=("ra","dec","ref_epoch","pmra","pmdec","pmra_error","pmdec_error")
    if not all(finite(gaia.get(x)) for x in needed):
        return None
    if not finite(esa.get("mjd")) or not all(finite(esa.get(x)) for x in ("ra","dec")):
        return None
    dec=gaia["dec"]
    cosd=math.cos(math.radians(dec))
    if abs(cosd)<1e-8:
        return None
    years=(esa["mjd"]-(51544.5+(gaia["ref_epoch"]-2000)*365.25))/365.25
    ra=(gaia["ra"]+gaia["pmra"]*years/(3_600_000*cosd))%360
    dec=dec+gaia["pmdec"]*years/3_600_000
    if not -90<=dec<=90:
        return None
    return geocoord_sep_arcsec(ra,dec,esa["ra"],esa["dec"])


def bands_summary(values):
    good=sorted(v for v in values if finite(v))
    return {"available":len(good),"missing":len(values)-len(good),
            "median":median(good) if good else None,
            "minimum":good[0] if good else None,"maximum":good[-1] if good else None}


def validate_inputs(lamost,gaia,esa,conflicts):
    if any(obj.get("experiment")!=key for obj,key in (
      (lamost,"003"),(gaia,"003G"),(esa,"006B"),(conflicts,"007"))):
        raise ValueError("Incorrect historic experiment identity")
    if len(lamost["records"])!=N or len(gaia["sources"])!=N or len(esa["sources"])!=N:
        raise ValueError("Original 250 real spectra cohort changed")
    def byid(items,field):
        o={}
        for row in items:
            sid=exact(row[field])
            if sid in o:raise ValueError("Duplicated "+field)
            o[sid]=row
        return o
    l=byid(lamost["records"],"lamost_obsid")
    g=byid(gaia["sources"],"lamost_obsid")
    e=byid(esa["sources"],"obsid")
    if set(l)!=set(g) or set(l)!=set(e):
        raise ValueError("Cross-experiment 250 source list drift")
    if conflicts.get("exact_gaia_ids_found")!=4 or conflicts.get("dr8_found_among_dr9_missing")!=9:
        raise ValueError("Prior real-data source conflict/DR8 coverage report changed")
    if len(conflicts.get("missing_dr9",[]))!=9 or len(conflicts.get("disagreements",[]))!=2:
        raise ValueError("Previous cross-ID investigation incomplete")
    for rec in conflicts["missing_dr9"]:
        oid=exact(rec["obsid"])
        if e[oid]["status"]!="missing_in_esa_mirror" or not rec["dr8_esa_record_present"]:
            raise ValueError("Prior DR8-only evidence did not match 006B")
    for rec in conflicts["disagreements"]:
        oid=exact(rec["obsid"])
        if e[oid]["status"]!="esa_observation_found" or e[oid]["esa_published_gaia_id_agrees"]:
            raise ValueError("Original competing Gaia associations changed")
    for oid in l:
        sid=exact(l[oid]["gaia_dr3_id_provisional"])
        if sid!=exact(g[oid]["gaia_dr3_source_id"]) or sid!=exact(e[oid]["published_gaia_source_id"]):
            raise ValueError("Original published Gaia DR3 source identifier changed")
        if g[oid]["gaia_record"] is None or sid!=exact(g[oid]["gaia_record"]["source_id"]):
            raise ValueError("Missing exact Gaia DR3 source row")
    return l,g,e


def quality_record(oid,l,g,e):
    spectrum=l[oid]
    gsource=g[oid]["gaia_record"]
    record=e[oid]
    sid=exact(spectrum["gaia_dr3_id_provisional"])
    issues={"provenance":[],"instrument":[],"gaia":[],"spectroscopy":[],"position":[]}
    if record["status"]=="missing_in_esa_mirror":
        tier="DR8_only"
        issues["provenance"].append("ESA_DR9_row_absent")
    elif record.get("esa_published_gaia_id_agrees") is True and record.get("esa_published_gaia_id_raw")==sid:
        tier="DR9_concordant_provisional"
    elif record.get("esa_published_gaia_id_wellformed") is False:
        tier="ESA_missing_Gaia_ID"
        issues["provenance"].append("ESA_DR9_Gaia_ID_missing")
    else:
        tier="competing_Gaia_ID"
        issues["provenance"].append("ESA_and_Huang_Gaia_ID_disagree")
    raw=record.get("esa_record")
    if raw is None:
        issues["instrument"].append("ESA_DR9_observation_metadata_absent")
    else:
        if raw.get("offsets") not in (0,False):
            issues["instrument"].append("fiber_offset_applied_or_unknown")
        if record.get("date_mjd_check")!="consistent_within_2_days":
            issues["instrument"].append("observation_date_MJD_incomplete_or_discrepant")
    if spectrum.get("spectroscopic_label_ready") is not True:
        issues["instrument"].append("LAMOST_spectroscopic_pipeline_quality_not_ready")

    gmag=gsource.get("phot_g_mean_mag")
    color=gsource.get("bp_rp")
    parallax=gsource.get("parallax")
    p_err=gsource.get("parallax_error")
    snr=parallax/p_err if finite(parallax) and positive(p_err) else None
    if not finite(gmag):issues["gaia"].append("Gaia_G_missing")
    if not finite(color):issues["gaia"].append("Gaia_BP_RP_missing")
    if snr is None or snr<10:issues["gaia"].append("Gaia_parallax_SNR_below_10_or_missing")
    ruwe=gsource.get("ruwe")
    if not finite(ruwe) or ruwe>=1.4:issues["gaia"].append("Gaia_RUWE_above_or_missing")
    if gsource.get("duplicated_source") is not False:
        issues["gaia"].append("Gaia_duplicate_flag_or_missing")
    if gsource.get("non_single_star")!=0:
        issues["gaia"].append("Gaia_non_single_star_flag_or_missing")
    if gsource.get("phot_variable_flag")=="VARIABLE":
        issues["gaia"].append("Gaia_catalogued_VARIABLE")
    for key in ("pmra","pmdec","pmra_error","pmdec_error"):
        v=gsource.get(key)
        if not finite(v) or (key.endswith("_error") and v<0):
            issues["gaia"].append("Gaia_"+key+"_missing_or_invalid")

    inferred=spectrum["spectroscopic_inferences"]
    limits={"Teff":(4800,6800),"logg":(3.9,4.7),"FeH":(-0.8,0.45)}
    inf_values={}
    for field,(low,high) in limits.items():
        item=inferred[field]
        val,err=item.get("value"),item.get("published_error")
        inf_values[field]={"value":val,"published_error":err}
        if not finite(val) or not low<=val<=high:
            issues["spectroscopy"].append("LAMOST_"+field+"_outside_registered_range_or_missing")
        if not positive(err):
            issues["spectroscopy"].append("LAMOST_"+field+"_error_missing_or_invalid")

    activity=spectrum["published_raw_row"]
    ca=activity.get("R8542");ca_error=activity.get("e_R8542")
    if not finite(ca) or not positive(ca_error):
        issues["spectroscopy"].append("LAMOST_Ca_II_8542_activity_measurement_uncertainty_missing")

    sep=corrected_target_offset(gsource,raw) if raw else None
    if sep is None or sep>1:
        issues["position"].append("Gaia_to_LAMOST_input_target_exceeds_1_arcsec_or_unassessable")

    v={
        "obsid":oid,"published_gaia_dr3_source_id":sid,
        "cross_catalog_provenance_tier":tier,
        "ESA_release":"ESA_ESASky_LAMOST_DR9_LRS" if raw else "DR9_absent__DR8_coverage_only",
        "observation_MJD":raw.get("mjd") if raw else None,
        "published_fiber_offset_flag":raw.get("offsets") if raw else None,
        "published_fiber_offset_arcsec":raw.get("offsets_v") if raw else None,
        "approx_Gaia_pm_to_LAMOST_input_arcsec":round(sep,6) if sep is not None else None,
        "catalogued_Gaia_variable_flag":gsource.get("phot_variable_flag"),
        "Gaia_duplicate_flag":gsource.get("duplicated_source"),
        "Gaia_non_single_star":gsource.get("non_single_star"),
        "Gaia_RUWE":ruwe,
        "Gaia_parallax_SNR":snr,
        "covariates":{"g_mag":gmag,"bp_rp":color,
                      "teff_K":inf_values["Teff"]["value"],
                      "logg_dex":inf_values["logg"]["value"],
                      "feh_dex":inf_values["FeH"]["value"],
                      "parallax_snr":snr},
        "published_LAMOST_parameter_inferences":inf_values,
        "LAMOST_CaII8542_R_index":{"value":ca,"formal_uncertainty":ca_error},
        "quality_failure_reasons":issues,
        "all_gate_failure_reasons":[x for values in issues.values() for x in values],
        "unknown_stellar_nature_and_survey_coverage":dict(MISSING_COVERAGE),
    }
    v["cross_catalog_ID_concordant"]=(tier=="DR9_concordant_provisional")
    v["quality_candidate"]=(not v["all_gate_failure_reasons"])
    return v


def match_vectors(a,b):
    vals=[]
    for index,name in enumerate(FIELDS):
        left,right=a.get(name),b.get(name)
        if not finite(left) or not finite(right):return None
        if name=="parallax_snr":
            if left<=0 or right<=0:return None
            d=max(left,right)/min(left,right)
        else:
            d=abs(left-right)/TOLS[index]
        vals.append(d if name=="parallax_snr" else d)
    if any(vals[i]>1 for i in range(5)) or vals[5]>TOLS[5]:
        return None
    vals[5]=(vals[5]-1)/(TOLS[5]-1)
    return vals


def paired_targets(eligible):
    """Deterministic maximum-cardinality bipartite association, no control re-use."""
    pool=sorted(eligible,key=lambda x:(
        sha((SALT+x["obsid"]).encode("ascii")),int(x["obsid"])))
    if len(pool)<MIN_POOL:
        return {"status":"not_executable_insufficient_candidates",
                "eligible_count":len(pool),"minimum_pool":MIN_POOL,
                "target_count":0,"match_count":0,
                "criterion_met":False,"matches":[],"targets":[]}
    selected=pool[:HOLDOUT]
    controls=pool[HOLDOUT:]
    edges={}
    for target in selected:
        choices=[]
        for control in controls:
            differences=match_vectors(target["covariates"],control["covariates"])
            if differences is not None:
                choices.append((sum(x*x for x in differences),int(control["obsid"]),
                                control["obsid"],differences))
        choices.sort(key=lambda x:(x[0],x[1]))
        edges[target["obsid"]]=[x[2] for x in choices]
    match_control_to_target={}
    def augment(target_id,visited):
        for cid in edges[target_id]:
            if cid in visited:continue
            visited.add(cid)
            previous=match_control_to_target.get(cid)
            if previous is None or augment(previous,visited):
                match_control_to_target[cid]=target_id
                return True
        return False
    for target in selected:
        augment(target["obsid"],set())
    pairs={target:control for control,target in match_control_to_target.items()}
    if len(set(pairs.values()))!=len(pairs):raise ValueError("Reused control")
    lookups={row["obsid"]:row for row in pool}
    results=[]
    for t in selected:
        oid=t["obsid"]
        cid=pairs.get(oid)
        scaled=match_vectors(t["covariates"],lookups[cid]["covariates"]) if cid else None
        results.append({"target_obsid":oid,
                        "matched_control_obsid":cid,
                        "eligible_control_obsids":edges[oid],
                        "tolerance_scaled_differences":scaled,
                        "status":("matched" if cid is not None else
                                  "no_eligible_control" if not edges[oid] else
                                  "control_competition")})
    return {"status":"executed",
            "eligible_count":len(pool),
            "target_count":len(selected),"control_count":len(controls),
            "match_count":len(pairs),"criterion_met":len(pairs)>=MIN_PAIRS,
            "minimum_matching_target_count":MIN_PAIRS,
            "selection_salt":SALT,"matching_fields":FIELDS,"tolerances":TOLS,
            "targets":results,"matches":[{"target_obsid":t,"control_obsid":c}
                   for t,c in sorted(pairs.items(),key=lambda x:int(x[0]))]}


def execute(lamost,gaia,esa,conflicts,source_hashes):
    l,g,e=validate_inputs(lamost,gaia,esa,conflicts)
    audit=[quality_record(oid,l,g,e) for oid in sorted(l,key=int)]
    categories=("provenance","instrument","gaia","spectroscopy","position")
    remaining=audit
    stages=[{"gate":"all_250","retained":N}]
    for category in categories:
        remaining=[row for row in remaining if not row["quality_failure_reasons"][category]]
        stages.append({"gate":category,"retained":len(remaining)})
    eligible=[x for x in audit if x["quality_candidate"]]
    if {x["obsid"] for x in eligible}!={x["obsid"] for x in remaining}:
        raise ValueError("Gate attrition inconsistent with eligibility")
    reasons=Counter(issue for row in audit for issue in row["all_gate_failure_reasons"])
    tiers=Counter(x["cross_catalog_provenance_tier"] for x in audit)
    match=paired_targets(eligible)
    summary={
        "gaia_g_mag":bands_summary([x["covariates"]["g_mag"] for x in audit]),
        "teff_K":bands_summary([x["covariates"]["teff_K"] for x in audit]),
        "logg_dex":bands_summary([x["covariates"]["logg_dex"] for x in audit]),
        "feh_dex":bands_summary([x["covariates"]["feh_dex"] for x in audit]),
        "parallax_snr":bands_summary([x["covariates"]["parallax_snr"] for x in audit]),
        "CaII8542_index":bands_summary([x["LAMOST_CaII8542_R_index"]["value"] for x in audit]),
        "eligible_gaia_G":bands_summary([x["covariates"]["g_mag"] for x in eligible]),
    }
    result={
      "experiment":"008",
      "study_type":"reference_candidate_quality_and_deterministic_matching_feasibility_only",
      "sources_sha256":source_hashes,
      "protocol_sha256":sha(PROTOCOL.read_bytes()),
      "original_spectra":N,
      "catalog_provenance_tiers":dict(sorted(tiers.items())),
      "ordered_gate_attrition":stages,
      "provisional_reference_candidates":len(eligible),
      "failure_reasons":dict(sorted(reasons.items())),
      "matching":match,
      "sample_descriptive_statistics":summary,
      "original_gaia_10000_median_g_mag_from_003_diagnostic":19.58,
      "full_covariance_and_natural_quietness_verified":False,
      "science_ready_certified_ordinary_controls":0,
      "source_rows":audit,
      "interpretation":"Passing any quality/matching gate gives only bright, FGK, LAMOST-based provisional candidates; identities and normality are NOT independently certified. No infrared survey, extinction, spectral activity-class or full covariance coverage has been validated."
    }
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lamost003",required=True)
    p.add_argument("--gaia003g",required=True)
    p.add_argument("--esa006b",required=True)
    p.add_argument("--conflicts007",required=True)
    p.add_argument("--output",default="reports/experiment_008")
    a=p.parse_args()
    a0,h0=load(a.lamost003,INPUT_SHA["lamost003"])
    a1,h1=load(a.gaia003g,INPUT_SHA["gaia003g"])
    a2,h2=load(a.esa006b,INPUT_SHA["esa006b"])
    a3,h3=load(a.conflicts007)
    result=execute(a0,a1,a2,a3,{"003":h0,"003G":h1,"006B":h2,"007":h3})
    path=Path(a.output);path.mkdir(parents=True,exist_ok=True)
    (path/"results.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps({key:result[key] for key in (
        "original_spectra","catalog_provenance_tiers","ordered_gate_attrition",
        "provisional_reference_candidates","failure_reasons","matching",
        "science_ready_certified_ordinary_controls") if key!="matching"},indent=2))
    print(json.dumps({"matching":{k:result["matching"][k] for k in (
        "status","eligible_count","target_count","match_count","criterion_met")}},indent=2))


if __name__=="__main__":
    main()
