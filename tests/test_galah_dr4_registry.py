"""Metadata-only synthetic tampering tests plus canonical archival manifest audit."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.galah_dr4_registry import validate, verify_local_files

HERE = Path(__file__).parents[1] / "data" / "galah_dr4_source_registry_v1.json"


class TestGALAHProvenance(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(HERE.read_text())

    def test_canonical_existing_evidence(self):
        stats = validate(self.data)
        self.assertEqual(stats["visits"], 2)
        self.assertEqual(stats["verified_native_cameras"], 4)
        self.assertEqual(stats["quarantined_cameras"], 4)
        self.assertEqual(stats["holdout_read"], 0)
        self.assertFalse(stats["science_ready"])

    def test_star_level_allstar_role_not_confused_with_allspec(self):
        self.data["catalogue_roles"]["allstar"]["role"] = self.data["catalogue_roles"]["allspec"]["role"]
        with self.assertRaisesRegex(ValueError, "Source-role drift"):
            validate(self.data)

    def test_gaia_source_must_not_be_float(self):
        self.data["observations"][0]["gaia_dr3_source_id"] = float(self.data["observations"][0]["gaia_dr3_source_id"])
        with self.assertRaisesRegex(ValueError, "exact decimal"):
            validate(self.data)

    def test_duplicate_visit_rejected(self):
        self.data["observations"][1]["sobject_id"] = self.data["observations"][0]["sobject_id"]
        with self.assertRaisesRegex(ValueError, "Duplicate observation"):
            validate(self.data)

    def test_duplicated_camera_payload_rejected(self):
        self.data["observations"][0]["cameras"]["R"]["sha256"] = self.data["observations"][0]["cameras"]["B"]["sha256"]
        with self.assertRaisesRegex(ValueError, "Duplicate camera"):
            validate(self.data)

    def test_quarantine_cannot_have_fictitious_lsf(self):
        self.data["observations"][0]["cameras"]["G"]["fwhm_median_A"] = 0.2
        with self.assertRaisesRegex(ValueError, "Unverified camera"):
            validate(self.data)

    def test_reject_DR3_datalink_parameter(self):
        self.data["spectrum_product_policy"]["datalink_uri_template"] = self.data["spectrum_product_policy"]["datalink_uri_template"].replace("dr4", "dr3")
        with self.assertRaisesRegex(ValueError, "Incorrect DR4"):
            validate(self.data)

    def test_reject_idx_extraction_as_native(self):
        self.data["spectrum_product_policy"]["datalink_uri_template"] += "&IDX=0"
        with self.assertRaisesRegex(ValueError, "Incorrect DR4"):
            validate(self.data)

    def test_holdout_cannot_be_promoted(self):
        self.data["observations"][1]["cohort"] = "holdout"
        with self.assertRaisesRegex(ValueError, "holdout"):
            validate(self.data)

    def test_optional_real_bytes_sha_check(self):
        d = copy.deepcopy(self.data)
        d["observations"] = [d["observations"][0]]
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            # Fixtures are explicitly synthetic bytes, not astronomy observations.
            for product in [d["observations"][0]["derived_analysis"], *d["observations"][0]["cameras"].values()]:
                if "filename" not in product:
                    continue
                data = product["filename"].encode("ascii")
                (base / product["filename"]).write_bytes(data)
                product["sha256"] = hashlib.sha256(data).hexdigest()
            self.assertEqual(verify_local_files(d, base)["original_file_checksums_verified_this_run"], 3)
            (base / d["observations"][0]["derived_analysis"]["filename"]).write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                verify_local_files(d, base)


if __name__ == "__main__":
    unittest.main()
