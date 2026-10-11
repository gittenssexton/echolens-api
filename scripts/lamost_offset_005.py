"""Post-hoc LAMOST bright-source fiber-coordinate offset analysis.

Uses only frozen 003 and 003G real catalog observations; results cannot
certify fiber offset or a crossmatch without official LAMOST OFFSET metadata.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import median

SOURCE_003_SHA = "efc4f3eaf5f5e1df8b60aa1897ffd93d44c3b05fe69318b27d3769fddb342e51"
SOURCE_003G_SHA = "d11e0c62eaa8aa26b2fe92fc30b0ca93891459caf4878d89cf2285fc0527a748"
PROTOCOL = Path(__file__).resolve().parents[1] / "docs/EXPERIMENT_005.md"
FLAGGED = "655310123"


def checksum(payload):
    return hashlib.sha256(payload).hexdigest()


def load_exact(path, expected):
    raw = Path(path).read_bytes()
    if checksum(raw) != expected:
        raise ValueError("Immutable original source SHA-256 differs")
    return json.loads(raw)


def mean_rank(values):
    indexed = sorted(enumerate(values), key=lambda t:t[1])
    ranks = [None]*len(values)
    k = 0
    while k < len(values):
        j = k+1
        while j < len(values) and indexed[j][1] == indexed[k][1]:
            j += 1
        rank = (k+1+j)/2
        for i in range(k,j):
            ranks[indexed[i][0]] = rank
        k=j
    return ranks


def spearman(values_a, values_b):
    """Descriptive Spearman rho with average ranks for ties; no p-value."""
    if len(values_a) != len(values_b) or len(values_a) < 3:
        return None
    a,b = mean_rank(values_a),mean_rank(values_b)
    avg_a,avg_b = sum(a)/len(a),sum(b)/len(b)
    cov = sum((x-avg_a)*(y-avg_b) for x,y in zip(a,b))
    sa = sum((x-avg_a)**2 for x in a)
    sb = sum((y-avg_b)**2 for y in b)
    return cov/math.sqrt(sa*sb) if sa>0 and sb>0 else None


def describe(group):
    offsets=sorted(r["separation_arcsec"] for r in group)
    n=len(offsets)
    return {
        "stars":n,
        "median_separation_arcsec":median(offsets) if n else None,
        "p90_nearest_rank_separation_arcsec":offsets[math.ceil(.9*n)-1] if n else None,
        "above_1_arcsec":sum(s>1 for s in offsets),
        "above_3_arcsec":sum(s>3 for s in offsets),
    }


def analyze(lamost, gaia):
    ls=lamost.get("records")
    gs=gaia.get("sources")
    if lamost.get("experiment") != "003" or gaia.get("experiment") != "003G":
        raise ValueError("Wrong original survey experiments")
    if len(ls)!=250 or len(gs)!=250:
        raise ValueError("Original 250 spectra expected in each archive")
    by_l={}
    for spectrum in ls:
        oid=str(spectrum["lamost_obsid"])
        if oid in by_l:raise ValueError("Repeated LAMOST observation")
        by_l[oid]=spectrum
    rows=[]
    for a in gs:
        oid=str(a["lamost_obsid"])
        if oid not in by_l: raise ValueError("Unmatched LAMOST obsid")
        source=a["gaia_record"]
        sid=str(a["gaia_dr3_source_id"])
        if not source or str(source["source_id"])!=sid or str(by_l[oid]["gaia_dr3_id_provisional"])!=sid:
            raise ValueError("Gaia/LAMOST exact published source ID changed")
        g=source.get("phot_g_mean_mag")
        sep=a.get("fiber_to_gaia_position_arcsec_epoch_unqualified")
        if not isinstance(g,(float,int)) or not math.isfinite(g):
            raise ValueError("Gaia G missing; do not silently drop source")
        if not isinstance(sep,(float,int)) or not math.isfinite(sep) or sep<0:
            raise ValueError("Invalid epoch-unqualified separation")
        raw=by_l[oid]["published_raw_row"]
        rows.append({
            "lamost_obsid":oid,"gaia_dr3_source_id":sid,
            "gaia_G_mag":g,
            "separation_arcsec":sep,
            "published_lamost_fiber_ra_deg":raw["RAJ2000"],
            "published_lamost_fiber_dec_deg":raw["DEJ2000"],
            "gaia_pm_available":all(source.get(k) is not None for k in ("pmra","pmdec","pmra_error","pmdec_error")),
            "official_observation_date":None,"official_fiber_offset_flag":None,
            "official_fiber_offset_arcsec":None,
        })
    rows.sort(key=lambda x:int(x["lamost_obsid"]))
    if len(rows)!=250 or len({x["gaia_dr3_source_id"] for x in rows})!=250:
        raise ValueError("Duplicate star/spectrum identity")
    flagged=next((r for r in rows if r["lamost_obsid"]==FLAGGED),None)
    if not flagged:raise ValueError("Pre-identified review source missing")
    partitions={}
    for limit in (10,11):
        partitions[f"G_below_{limit}"] = describe([r for r in rows if r["gaia_G_mag"]<limit])
        partitions[f"G_at_least_{limit}"] = describe([r for r in rows if r["gaia_G_mag"]>=limit])
    result={
        "experiment":"005",
        "status":"post_hoc_exploratory_not_a_confirmed_instrumental_offset",
        "provenance":{"experiment_003_results_sha256":SOURCE_003_SHA,
            "experiment_003g_results_sha256":SOURCE_003G_SHA,
            "protocol_sha256":checksum(PROTOCOL.read_bytes())},
        "rows":250,
        "all_stars":describe(rows),
        "brightness_partitions":partitions,
        "descriptive_spearman_G_vs_separation":spearman(
            [r["gaia_G_mag"] for r in rows],[r["separation_arcsec"] for r in rows]),
        "flagged_source":{
            **flagged,
            "G_brightness_rank_1_is_brightest":1+sum(r["gaia_G_mag"]<flagged["gaia_G_mag"] for r in rows),
            "separation_rank_1_is_largest":1+sum(r["separation_arcsec"]>flagged["separation_arcsec"] for r in rows)},
        "separations_over_1_arcsec":[r for r in rows if r["separation_arcsec"]>1],
        "each_source":rows,
        "interpretation":"Brightness-associated catalog-coordinate offsets warrant checking official LAMOST OFFSET/OFFSET_V/DATE-OBS; no causal, counterpart certification or technology claims."
    }
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--lamost-results",required=True)
    parser.add_argument("--gaia-results",required=True)
    parser.add_argument("--output",default="reports/experiment_005")
    args=parser.parse_args()
    result=analyze(load_exact(args.lamost_results,SOURCE_003_SHA),
                   load_exact(args.gaia_results,SOURCE_003G_SHA))
    target=Path(args.output)
    target.mkdir(parents=True,exist_ok=True)
    (target/"results.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps({key:result[key] for key in ("rows","all_stars",
        "brightness_partitions","descriptive_spearman_G_vs_separation",
        "flagged_source")},indent=2))

if __name__=="__main__":
    main()
