import csv
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.catalog import stats
from scripts.import_gaia import COLUMNS, import_csv, parse


def fixture(count):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=COLUMNS)
    writer.writeheader()
    for n in range(count):
        writer.writerow({
            "source_id": str(1000000000000000000 + n),
            "ra": 10 + n / 100000, "dec": -20, "parallax": 2,
            "parallax_error": 0.1, "parallax_over_error": 20,
            "phot_g_mean_mag": 13, "bp_rp": 1.2, "ruwe": 1.1,
            "random_index": 500000000 + n,
        })
    return stream.getvalue().encode()


class ImporterTests(unittest.TestCase):
    def test_rejects_incomplete_download(self):
        with self.assertRaisesRegex(ValueError, "Expected exactly 10000"):
            parse(fixture(3))

    def test_real_import_shape_and_duplicate_guard(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "stars.sqlite"
            raw = fixture(10000)
            result = import_csv(raw, path)
            self.assertEqual(result["row_count"], 10000)
            self.assertEqual(stats(path)["star_count"], 10000)
            with self.assertRaisesRegex(ValueError, "already imported"):
                import_csv(raw, path)
            self.assertEqual(stats(path)["star_count"], 10000)

    def test_duplicate_id_rejected(self):
        raw = fixture(10000)
        lines = raw.decode().splitlines()
        lines[-1] = lines[-2]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse(("\n".join(lines) + "\n").encode())


if __name__ == "__main__":
    unittest.main()
