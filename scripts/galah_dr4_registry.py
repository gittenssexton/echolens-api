"""Offline GALAH DR4 data-role and provenance validator for EchoLens.

Never downloads bulk catalogues, never interpolates unknown camera data, never
scores anomalies. A passing metadata audit does NOT imply science readiness.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re

SCHEMA = "echolens-galah-dr4-provenance-registry-v1"
ARMS = ("B", "G", "R", "I")
SHA = re.compile(r"[0-9a-f]{64}\Z")
ID = re.compile(r"[1-9][0-9]{9,18}\Z")
CANONICAL_CATALOG_ROLES = {
    "allspec": "authoritative_original_release_per_observation_metadata",
    "allstar": "recommended_star_level_stellar_parameter_abundance_reference",
    "gaia_2mass_wise": "supplemental_crossmatch_only_not_universal_quality_truth",
    "detrended_2025": "SP01_P2B_provisional_source_selection_only_not_original_dr4_release",
}


def _id(value: object, field: str) -> str:
    if not isinstance(value, str) or not ID.fullmatch(value) or int(value) >= 2**63:
        raise ValueError(f"{field} must be an exact decimal source identifier string")
    return value


def _sha(value: object, field: str) -> None:
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise ValueError(f"{field} must be lowercase SHA-256 hex")


def validate(document: dict) -> dict:
    if document.get("schema") != SCHEMA:
        raise ValueError("Unsupported registry schema")
    if document.get("science_ready") is not False:
        raise ValueError("Engineering-only registry must not claim science readiness")
    cats = document.get("catalogue_roles", {})
    if set(cats) != set(CANONICAL_CATALOG_ROLES):
        raise ValueError("Missing or unexpected GALAH catalogue roles")
    for name, role in CANONICAL_CATALOG_ROLES.items():
        item = cats[name]
        if item.get("role") != role:
            raise ValueError(f"Source-role drift: {name}")
        uri = str(item.get("release_uri", ""))
        if not uri.startswith("https://"):
            raise ValueError(f"Missing provenance source URI: {name}")
    for name in ("allspec", "allstar", "gaia_2mass_wise"):
        if cats[name].get("release_full_bytes_downloaded") is not False:
            raise ValueError(f"Cannot claim full original catalogue imported: {name}")
    _sha(cats["allspec"]["two_visit_subset"].get("sha256_of_two_row_original_response"), "original subset")
    policy = document.get("spectrum_product_policy", {})
    url = str(policy.get("datalink_uri_template", ""))
    if "DR=galah_dr4" not in url or "IDX" in url or "RESPONSEFORMAT=fits" not in url:
        raise ValueError("Incorrect DR4 native Datalink template")
    observations = document.get("observations")
    if not isinstance(observations, list) or not observations:
        raise ValueError("Empty observation registry")
    seen_visits = set()
    sha_to_product = {}
    count_valid = count_quarantined = 0
    for observation in observations:
        gaia = _id(observation.get("gaia_dr3_source_id"), "gaia_dr3_source_id")
        visit = _id(observation.get("sobject_id"), "sobject_id")
        if visit in seen_visits:
            raise ValueError(f"Duplicate observation/visit ID {visit}")
        seen_visits.add(visit)
        if observation.get("cohort") != "SP01_P2B_provisional_calibration_only":
            raise ValueError("This registry cannot silently introduce or inspect holdout stars")
        if observation.get("identity_status") != "matched_exact_identifiers_to_original_dr4_allspec_subset":
            raise ValueError("Source/visit not confirmed against original-release subset")
        analysis = observation.get("derived_analysis", {})
        _sha(analysis.get("sha256"), "derived analysis FITS")
        if analysis.get("product_type") != "in_sample_model_and_observation":
            raise ValueError("An analysis fit must not be relabeled as a native CCD spectrum")
        if analysis.get("filename") != f"{visit}_official_allspec.fits":
            raise ValueError("Unexpected analysis FITS filename")
        native = observation.get("cameras", {})
        if set(native) != set(ARMS):
            raise ValueError("Every camera requires an explicit verified or quarantined status")
        for arm, product in native.items():
            state = product.get("status")
            if state == "verified_native_eight_hdu":
                _sha(product.get("sha256"), f"{arm} native FITS")
                if product.get("filename") != f"{visit}_{arm}_original_camera.fits":
                    raise ValueError(f"Wrong {arm} native filename for visit")
                if product.get("lsf_source") != "native_HDU7_resolution_profile":
                    raise ValueError("Native LSF must come from HDU 7")
                fwhm = product.get("fwhm_median_A")
                if not isinstance(fwhm, (int, float)) or not 0 < fwhm < 10:
                    raise ValueError("Invalid measured LSF")
                if not str(product.get("drive_uri", "")).startswith("https://drive.google.com/file/d/"):
                    raise ValueError("Missing original archived FITS file link")
                # A single payload cannot be presented as two independent camera reductions.
                digest = product["sha256"]
                key = (gaia, visit, arm)
                if digest in sha_to_product:
                    raise ValueError(f"Duplicate camera FITS payload {key} vs {sha_to_product[digest]}")
                sha_to_product[digest] = key
                count_valid += 1
            elif state == "quarantined_unverified":
                if "sha256" in product or "fwhm_median_A" in product or not product.get("reason"):
                    raise ValueError("Unverified camera cannot present measured native data")
                count_quarantined += 1
            else:
                raise ValueError(f"Unexpected camera status: {state}")
    return {
        "schema": SCHEMA,
        "source_ids": len({o["gaia_dr3_source_id"] for o in observations}),
        "visits": len(observations),
        "verified_native_cameras": count_valid,
        "quarantined_cameras": count_quarantined,
        "holdout_read": 0,
        "science_ready": False,
        "allstar_and_allspec_separate": True,
        "bulk_original_catalogues_imported": 0,
    }


def verify_local_files(document: dict, path: Path) -> dict:
    """Optional check when a researcher provides copies of archived originals."""
    checked = 0
    for obs in document["observations"]:
        for product in [obs["derived_analysis"], *obs["cameras"].values()]:
            if "filename" not in product:
                continue
            file = path / product["filename"]
            if not file.is_file():
                raise FileNotFoundError(str(file))
            sha = hashlib.sha256(file.read_bytes()).hexdigest()
            if sha != product["sha256"]:
                raise ValueError(f"SHA-256 mismatch: {file.name}")
            checked += 1
    return {"original_file_checksums_verified_this_run": checked}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("data/galah_dr4_source_registry_v1.json"))
    parser.add_argument("--original-files-dir", type=Path,
                        help="Optional directory containing all six archived original products for independent checksums")
    parser.add_argument("--report", type=Path, help="Output metadata validation JSON")
    args = parser.parse_args()
    d = json.loads(args.registry.read_text(encoding="utf-8"))
    result = validate(d)
    if args.original_files_dir is not None:
        result.update(verify_local_files(d, args.original_files_dir))
    else:
        result["original_file_checksums_verified_this_run"] = 0
        result["note"] = "Manifest verified only; original-byte SHA-256 evidence recorded from prior source audits"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
