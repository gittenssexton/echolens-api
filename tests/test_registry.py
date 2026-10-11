import tempfile
import unittest
from pathlib import Path

from app.catalog import connect, get_star, list_stars, stats


class RegistryTests(unittest.TestCase):
    def test_empty_registry_is_not_fake_data(self):
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / "absent.sqlite"
            self.assertEqual(stats(missing)["star_count"], 0)
            self.assertFalse(stats(missing)["database_loaded"])
            self.assertEqual(list_stars(path=missing)["stars"], [])
            self.assertIsNone(get_star("123", path=missing))

    def test_registry_queries_and_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "stars.sqlite"
            db = connect(path, create=True)
            db.execute("""INSERT INTO ingestion_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       ("r1", "Gaia DR3", "https://example.test", "SELECT ...", "a", "b",
                        "2026-10-11T00:00:00Z", "2026-10-11T00:00:01Z", 1, "test fixture"))
            db.execute("""INSERT INTO stars (source_id, ra, dec, phot_g_mean_mag, parallax, run_id)
                          VALUES (?, ?, ?, ?, ?, ?)""", ("1234567890123456789", 10, -20, 11.2, 5.1, "r1"))
            db.commit()
            db.close()
            self.assertEqual(stats(path)["star_count"], 1)
            self.assertEqual(list_stars(max_g_mag=12, path=path)["total"], 1)
            self.assertEqual(list_stars(max_g_mag=10, path=path)["total"], 0)
            self.assertEqual(get_star("1234567890123456789", path)["catalog_release"], "Gaia DR3")
            self.assertEqual(get_star("1234567890123456789", path)["query_sha256"], "a")


if __name__ == "__main__":
    unittest.main()
