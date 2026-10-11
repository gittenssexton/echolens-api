"""Experiment 002A: preregistered overlap test within the clean Gaia reference screen.

This never modifies catalog observations, serving databases, or the deployed API.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
from statistics import median

from scripts.import_gaia import is_reference, parse_snapshot, validate
from scripts.control_matching import FIELDS, PARAMETERS, STAGES, covariates, differences, maximum_matching

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/EXPERIMENT_002A.md"
RAW = ROOT / "data/gaia_dr3.raw.gz"
MANIFEST = ROOT / "data/gaia_dr3.manifest.json"
RAW_SHA256 = "d193d7e144d5a7fc9f3d877a9323fc3c68ee2baf05b966d997392309a5248fb0"
SALT = "echolens-002a-v1:"
TARGET_COUNT = 100
EXPECTED_REFERENCE_COUNT = 531
MINIMUM_MATCHED = 50


def selected_ids(rows):
    """Return disjoint, reproducible source IDs; selection ignores future match outcomes."""
    references = [r["source_id"] for r in rows if is_reference(r)]
    if len(references) != EXPECTED_REFERENCE_COUNT:
        raise ValueError(f"Reference screen drift: {len(references)} versus {EXPECTED_REFERENCE_COUNT}")
    ranked = sorted(references, key=lambda sid: (
        hashlib.sha256((SALT + sid).encode("ascii")).hexdigest(), int(sid)))
    targets, controls = ranked[:TARGET_COUNT], ranked[TARGET_COUNT:]
    if len(targets) != TARGET_COUNT or set(targets).intersection(controls):
        raise ValueError("Bad target/control partition")
    return targets, controls


def match_vectors(target_vectors, control_vectors, order):
    """Reuses 001A's exact tolerances and maximum-cardinality matching."""
    records, edges = {}, {}
    for sid in order:
        vector = target_vectors[sid]
        eligible, counts = [], [0] * len(STAGES)
        if vector is not None:
            for cid, control in control_vectors.items():
                scaled = differences(vector, control)
                for stage in range(len(STAGES)):
                    if all(d <= 1 for d in scaled[:stage+1]):
                        counts[stage] += 1
                if all(d <= 1 for d in scaled):
                    eligible.append((sum(d*d for d in scaled), int(cid), cid))
        edges[sid] = [candidate[2] for candidate in sorted(eligible)]
        records[sid] = {
            "source_id": sid, "covariates": vector,
            "cumulative_eligible_counts": dict(zip(STAGES, counts)),
            "eligible_control_ids": edges[sid],
        }
    assignment = maximum_matching(edges, order)
    if len(set(assignment.values())) != len(assignment):
        raise ValueError("Control reuse")
    for sid, record in records.items():
        cid = assignment.get(sid)
        record["assigned_control_id"] = cid
        record["status"] = ("matched" if cid else
            "unusable_covariates" if record["covariates"] is None else
            "no_eligible_control" if not edges[sid] else "control_competition")
        if cid:
            record["control_covariates"] = control_vectors[cid]
            record["absolute_tolerance_scaled_differences"] = differences(
                record["covariates"], control_vectors[cid])
    return records, assignment


def summarize(rows, column):
    values = [r.get(column) for r in rows]
    good = [float(v) for v in values if isinstance(v, (int, float)) and math.isfinite(v)]
    return {"available": len(good), "missing": len(values)-len(good),
            "median": median(good) if good else None}


def execute(output):
    """Run only on the committed frozen snapshot and write a deterministic derived report."""
    payload = gzip.decompress(RAW.read_bytes())
    digest = hashlib.sha256(payload).hexdigest()
    if digest != RAW_SHA256:
        raise ValueError("Frozen Gaia raw checksum mismatch")
    manifest = json.loads(MANIFEST.read_text())
    if manifest.get("raw_sha256") != digest or manifest.get("release") != "DR3":
        raise ValueError("Gaia release/manifest changed")
    _, rows = parse_snapshot(payload, manifest, RAW.parent)
    validate(rows, 10000)
    targets, controls = selected_ids(rows)
    by_id = {r["source_id"]: r for r in rows}
    target_vectors = {sid: covariates(by_id[sid])[0] for sid in targets}
    control_vectors = {sid: covariates(by_id[sid])[0] for sid in controls}
    if any(v is None for v in list(target_vectors.values()) + list(control_vectors.values())):
        raise ValueError("Clean-screen vector unexpectedly invalid")
    records, assignment = match_vectors(target_vectors, control_vectors, targets)
    if set(assignment) - set(targets) or set(assignment.values()) - set(controls):
        raise ValueError("Assignment escaped registered cohorts")
    statuses = ("matched", "unusable_covariates", "no_eligible_control", "control_competition")
    result = {
        "experiment": "002A",
        "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
        "raw_sha256": digest,
        "selection_salt": SALT,
        "algorithm": "001A fixed covariates, tolerances and deterministic max-cardinality augmenting paths",
        "target_source_ids": targets,
        "control_source_ids": controls,
        "target_count": TARGET_COUNT,
        "control_count": len(controls),
        "match_count": len(assignment),
        "match_fraction": len(assignment) / TARGET_COUNT,
        "minimum_matched": MINIMUM_MATCHED,
        "operational_criterion_met": len(assignment) >= MINIMUM_MATCHED,
        "tolerances": PARAMETERS,
        "covariates": list(FIELDS[:2]) + ["abs_b_deg"] + list(FIELDS[3:]),
        "status_counts": {name: sum(r["status"] == name for r in records.values())
                          for name in statuses},
        "targets_with_any_eligible_control_by_stage": {
            stage: sum(rec["cumulative_eligible_counts"][stage] > 0
                       for rec in records.values()) for stage in STAGES},
        "population_diagnostics": {
            label: {field: summarize(group, field) for field in
                    ("phot_g_mean_mag", "bp_rp", "parallax_over_error")}
            for label, group in (
                ("all_10000", rows),
                ("heldout_clean_targets", [by_id[sid] for sid in targets]),
                ("remaining_clean_controls", [by_id[sid] for sid in controls]),
            )
        },
        "targets": [records[sid] for sid in targets],
        "interpretation": ("Restricted control-overlap feasibility only. No anomaly, technology, "
                           "independent astrophysical classification or full-population inference."),
    }
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", default="reports/experiment_002a")
    args = p.parse_args()
    result = execute(args.output)
    print(json.dumps({key: result[key] for key in
        ("experiment", "raw_sha256", "target_count", "control_count", "match_count",
         "operational_criterion_met", "status_counts",
         "targets_with_any_eligible_control_by_stage")}, indent=2))


if __name__ == "__main__":
    main()
