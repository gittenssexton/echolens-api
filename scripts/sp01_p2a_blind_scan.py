"""SP01-P2A: blind-window engineering audit of real GALAH DR4 allspec spectra.

All data are read from an existing SHA-256-verified EchoLens audit archive.
No network requests. No line IDs, p-values, or technosignature claims.
The output is a diagnostic scan of in-sample observed/model residuals:
the model was fitted to those same observations.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np

STARS = {
    "ordinary_dwarf_2017": {
        "member": "170416001901162_single_fit_spectrum.fits",
        "sha256": "50effaed542d0195a44e591059c08e6bfdb2b77ea823fe35b69fd141a4871ff1",
        "sobject_id": "170416001901162",
        "gaia_dr3_source_id": "3064554891927687296",
        "group": "ordinary_FGK_reference",
        "archive": "clean",
    },
    "barium_giant_2021": {
        "member": "catalogued_ba_star/210420000101363/210420000101363_single_fit_spectrum.fits",
        "sha256": "fb96a57fe13f46974329259b01b5e79f05efbfdc3b4783f36f2fadffb8e13050",
        "sobject_id": "210420000101363",
        "gaia_dr3_source_id": "6053735173729807872",
        "group": "known_peculiar_Ba_giant_NOT_matched_control",
        "archive": "two_star",
    },
    "barium_giant_2023": {
        "member": "catalogued_ba_star/230302001701254/230302001701254_single_fit_spectrum.fits",
        "sha256": "03f2e55c238c6dcf4afa66040c32ef6ebea10c7996e8a35d1a701b6c7f83e53b",
        "sobject_id": "230302001701254",
        "gaia_dr3_source_id": "6053735173729807872",
        "group": "known_peculiar_Ba_giant_NOT_matched_control",
        "archive": "two_star",
    },
}
SEGMENTS = {"B":(4600,5000),"G":(5550,5950),"R":(6400,6800),"I":(7450,8000)}

def _header(raw, offset):
    values = {}
    pos = offset
    while pos + 80 <= len(raw):
        card = raw[pos:pos+80].decode("ascii", "strict")
        pos += 80
        if card[:8].strip() == "END":
            return values, ((pos + 2879)//2880)*2880
        if card[8:10] == "= ":
            literal = card[10:80].split(" / ", 1)[0].strip()
            values[card[:8].strip()] = (
                literal.split("'",2)[1].strip() if literal.startswith("'") else literal
            )
        if pos - offset > 2880*16:
            raise ValueError("unreasonably long FITS header")
    raise ValueError("FITS END card not found")

def read_allspec(raw: bytes) -> dict[str,np.ndarray]:
    first, offset = _header(raw,0)
    table, data_start = _header(raw,offset)
    if first.get("SIMPLE") != "T" or table.get("XTENSION") != "BINTABLE":
        raise ValueError("Expected primary + BINTABLE GALAH analysis FITS")
    if int(table["NAXIS1"]) != 33 or int(table["TFIELDS"]) != 5:
        raise ValueError("Unexpected FITS table schema")
    if [table[f"TTYPE{i}"] for i in range(1,6)] != ["wave","sob","uob","smod","mob"]:
        raise ValueError("Unexpected columns")
    if [table[f"TFORM{i}"] for i in range(1,6)] != ["1D","1D","1D","1D","1L"]:
        # Some providers write compact TFORM as 'D', 'L'.
        if [table[f"TFORM{i}"] for i in range(1,6)] != ["D","D","D","D","L"]:
            raise ValueError("Unexpected field types")
    rows = int(table["NAXIS2"])
    if rows <= 0 or data_start+33*rows > len(raw):
        raise ValueError("Invalid table rows/size")
    dtype = np.dtype([("wave",">f8"),("sob",">f8"),("uob",">f8"),
                      ("smod",">f8"),("mob","S1")])
    arr = np.frombuffer(raw,dtype=dtype,count=rows,offset=data_start)
    result = {k:arr[k].astype(np.float64).copy() for k in ["wave","sob","uob","smod"]}
    result["mob"] = (arr["mob"] == b"T").copy()
    # Original GALAH analysis software saves mob=unmasked_opt.
    return result

def window(data, arm="R"):
    lo,hi = SEGMENTS[arm]
    w = data["wave"]
    idx = (w >= lo) & (w <= hi)
    out = {key:val[idx] for key,val in data.items()}
    if out["wave"].size < 1000 or not np.all(np.diff(out["wave"]) > 0):
        raise ValueError(f"invalid or absent {arm}-arm spectrum")
    return out

def autocorrelation(z:np.ndarray,selected:np.ndarray,lag:int)->float|None:
    if len(z) <= lag: return None
    good=selected[:-lag]&selected[lag:]
    if good.sum()<30: return None
    a=z[:-lag][good];b=z[lag:][good]
    return float(np.corrcoef(a,b)[0,1]) if np.std(a)>0 and np.std(b)>0 else None

def describe(data:dict, arm="R")->dict:
    red=window(data,arm)
    z=(red["sob"]-red["smod"])/red["uob"]
    good=np.isfinite(z)&np.isfinite(red["wave"])&(red["uob"]>0)
    out={"arm":arm,"wavelength_A":[float(red["wave"][0]),float(red["wave"][-1])],
         "pixels":len(z),"fwhm_A_nominal":float(np.median(red["wave"])/28000),
         "pixel_step_A":float(np.median(np.diff(red["wave"]))),
         "model_is_in_sample":True}
    for name,selection in (("fit_included",red["mob"]),("fit_excluded",~red["mob"])):
        valid=selection&good
        q=z[valid]
        out[name]={
          "pixels":int(valid.sum()),
          "fraction_of_arm":round(float(valid.mean()),6),
          "median_z":float(np.median(q)) if q.size else None,
          "median_abs_z":float(np.median(np.abs(q))) if q.size else None,
          "rms_z":float(np.sqrt(np.mean(q**2))) if q.size else None,
          "fraction_abs_z_over_5":float(np.mean(np.abs(q)>5)) if q.size else None,
          "adjacent_z_lag1_correlation":autocorrelation(z,valid,1),
          "adjacent_z_lag3_correlation":autocorrelation(z,valid,3)
        }
    out["max_run_abs_z_gt5_fit_included"]=longest_run((np.abs(z)>5)&red["mob"]&good)
    out["Halpha_6562p8_mask_true_fraction_pm0p7A"] = fraction_around(red, 6562.8, 0.7)
    return out

def fraction_around(data, wavelength, radius):
    near=np.abs(data["wave"]-wavelength)<=radius
    return float(np.mean(data["mob"][near])) if near.any() else None

def longest_run(mask:np.ndarray)->int:
    count=mx=0
    for x in mask:
        count=count+1 if x else 0
        mx=max(mx,count)
    return mx

def blind_diagnostic_features(data:dict, arm="R", top_n=10,
                              fwhm_R=28000., exclusion_A=0.75)->list:
    """Peak locations in full red arm, no labeled lines and no significance values.

    Gaussian residual contrast to a LOCAL baseline is weighted by quoted per-pixel
    errors; in-sample fitting, autocorrelation and masking invalidate interpreting
    returned scores as independent Gaussian sigmas.
    """
    s=window(data,arm)
    w=s["wave"]
    z=(s["sob"]-s["smod"])/s["uob"]
    ok=s["mob"]&np.isfinite(z)&(s["uob"]>0)
    step=float(np.median(np.diff(w)))
    sigma_pix=(float(np.median(w))/fwhm_R)/2.354820045/step
    half=7
    x=np.arange(-half,half+1)
    kernel=np.exp(-0.5*(x/sigma_pix)**2)
    kernel/=np.sqrt(np.sum(kernel**2))
    scored=[]
    for i in range(60,len(z)-60):
        if not ok[i-half:i+half+1].all(): continue
        baseline_indices=np.r_[i-60:i-15,i+16:i+61]
        if ok[baseline_indices].sum()<60: continue
        baseline=float(np.median(z[baseline_indices][ok[baseline_indices]]))
        contrast= -float(np.dot(z[i-half:i+half+1]-baseline,kernel))
        if not np.isfinite(contrast): continue
        scored.append((i,contrast,baseline))
    chosen=[]
    for idx,score,baseline in sorted(scored,key=lambda v:v[1],reverse=True):
        if any(abs(w[idx]-prev["wavelength_A"])<exclusion_A for prev in chosen):
            continue
        chosen.append({"wavelength_A":round(float(w[idx]),4),
                       "absorption_contrast_diagnostic":round(score,4),
                       "local_baseline_z":round(baseline,4),
                       "fit_mask":True})
        if len(chosen)>=top_n:break
    return chosen

def same_star_visit_overlap(early:dict,late:dict)->dict:
    a,b=window(early,"R"),window(late,"R")
    common=a["mob"]&np.isfinite(a["sob"])&np.isfinite(a["uob"])&(a["uob"]>0)
    w=a["wave"]
    valid_b = b["mob"]&np.isfinite(b["sob"])&np.isfinite(b["uob"])&(b["uob"]>0)
    z1=(a["sob"]-a["smod"])/a["uob"]
    z2=(b["sob"]-b["smod"])/b["uob"]
    inter=np.interp(w,b["wave"],z2,left=np.nan,right=np.nan)
    included=np.interp(w,b["wave"],valid_b.astype(float),left=0,right=0)>0.999
    shared=common&included&np.isfinite(inter)&np.isfinite(z1)
    n=int(shared.sum())
    return {"red_pixels_shared_valid_fit_selected":n,
            "red_overlap_correlation_of_fitted_z":
                float(np.corrcoef(z1[shared],inter[shared])[0,1]) if n>50 else None,
            "interpretation":"Descriptive same-star visit residual agreement only; not a calibrated repeatability or independent significance test"}

def read_archive(archive:Path,member:str,expected_sha:str)->dict:
    with zipfile.ZipFile(archive) as z:
        b=z.read(member)
    digest=hashlib.sha256(b).hexdigest()
    if digest!=expected_sha:
        raise ValueError(f"SHA-256 mismatch for {member}")
    return read_allspec(b)

def run(clean_archive:Path, two_archive:Path)->dict:
    inputs={}
    for k,v in STARS.items():
        path=clean_archive if v["archive"]=="clean" else two_archive
        inputs[k]=read_archive(path,v["member"],v["sha256"])
    records=[]
    for k,v in STARS.items():
        s=inputs[k]
        records.append({"label":k,"catalog_identity":v,
                        "full_allspec_pixels":len(s["wave"]),
                        "arms":[describe(s,arm) for arm in ("B","G","R","I") if
                          ((s["wave"]>=SEGMENTS[arm][0])&(s["wave"]<=SEGMENTS[arm][1])).sum()>1000],
                        "top_10_red_arm_diagnostic_locations":blind_diagnostic_features(s)})
    pair=same_star_visit_overlap(inputs["barium_giant_2021"], inputs["barium_giant_2023"])
    return {"schema":"echolens-sp01-p2a-v1",
            "study":"three spectra, two stars; in-sample fitted residual blind-window feasibility",
            "measurement_source":"original bytes of already-archived GALAH DR4 allspec FITS, SHA-256 validated",
            "mask_semantics":"GALAH source code mob=unmasked_opt; True means retained for fit, NOT a detector quality flag",
            "spectral_frame":"GALAH reduction air wavelengths; effective final allspec velocity convention not independently demonstrated for individual line IDs",
            "features_interpretation":"Uncorrected engineering locations, NOT discoveries, line IDs, sigma significance, or technosignatures",
            "family_wise_error_calibrated":False,
            "source_level_holdout":False,
            "actual_LSF_available":False,
            "science_go":False,
            "records":records,"same_star_repeat_visit":pair}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--clean-archive",required=True,type=Path)
    p.add_argument("--two-star-archive",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    x=p.parse_args()
    r=run(x.clean_archive,x.two_star_archive)
    x.output.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"records":len(r["records"]),
                      "same_star_repeat_visit":r["same_star_repeat_visit"],
                      "science_go":r["science_go"]},indent=2))

if __name__=="__main__":
    main()
