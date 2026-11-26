
import csv
import tempfile
import unittest
from pathlib import Path

from data.historical_quality import HistoricalQualityChecker


class TestHistoricalQualityChecker(unittest.TestCase):

    def setUp(self):
        self.checker = HistoricalQualityChecker()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_csv(self, filename, headers, rows):
        file_path = self.base_path / filename

        with file_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            writer.writerows(rows)

        return str(file_path)

    def test_valid_csv(self):
        path = self.create_csv(
            "valid.csv",
            ["timestamp", "open", "high", "low", "close", "volume"],
            [
                ["2026-01-01 09:15:00", 100, 105, 98, 102, 1000],
                ["2026-01-01 09:16:00", 102, 106, 101, 104, 1200],
            ],
        )

        report = self.checker.check_file(path)

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["total_rows"], 2)
        self.assertEqual(report["valid_rows"], 2)
        self.assertEqual(report["invalid_rows"], 0)

    def test_invalid_price(self):
        path = self.create_csv(
            "invalid_price.csv",
            ["timestamp", "open", "high", "low", "close"],
            [
                ["2026-01-01 09:15:00", 100, 90, 95, 102],
            ],
        )

        report = self.checker.check_file(path)

        self.assertNotEqual(report["status"], "PASS")
        self.assertGreater(report["price_errors"], 0)

    def test_duplicate_timestamp(self):
        path = self.create_csv(
            "duplicate.csv",
            ["timestamp", "open", "high", "low", "close"],
            [
                ["2026-01-01 09:15:00", 100, 105, 98, 102],
                ["2026-01-01 09:15:00", 102, 106, 101, 104],
            ],
        )

        report = self.checker.check_file(path)

        self.assertEqual(report["duplicate_timestamps"], 1)
        self.assertEqual(report["invalid_rows"], 1)

    def test_out_of_order_timestamp(self):
        path = self.create_csv(
            "order.csv",
            ["timestamp", "open", "high", "low", "close"],
            [
                ["2026-01-01 09:16:00", 100, 105, 98, 102],
                ["2026-01-01 09:15:00", 102, 106, 101, 104],
            ],
        )

        report = self.checker.check_file(path)

        self.assertEqual(report["out_of_order_timestamps"], 1)
        self.assertEqual(report["invalid_rows"], 1)

    def test_missing_required_column(self):
        path = self.create_csv(
            "missing.csv",
            ["timestamp", "open", "high", "close"],
            [
                ["2026-01-01 09:15:00", 100, 105, 102],
            ],
        )

        report = self.checker.check_file(path)

        self.assertEqual(report["status"], "ERROR")
        self.assertIn("low", report["missing_columns"])

    def test_missing_file(self):
        path = str(self.base_path / "does_not_exist.csv")

        report = self.checker.check_file(path)

        self.assertEqual(report["status"], "ERROR")
        self.assertFalse(report["exists"])

    def test_empty_csv(self):
        path = self.create_csv(
            "empty.csv",
            ["timestamp", "open", "high", "low", "close"],
            [],
        )

        report = self.checker.check_file(path)

        self.assertEqual(report["status"], "ERROR")
        self.assertEqual(report["total_rows"], 0)

    def test_negative_volume(self):
        path = self.create_csv(
            "volume.csv",
            ["timestamp", "open", "high", "low", "close", "volume"],
            [
                ["2026-01-01 09:15:00", 100, 105, 98, 102, -50],
            ],
        )

        report = self.checker.check_file(path)

        self.assertGreater(report["volume_errors"], 0)
        self.assertEqual(report["invalid_rows"], 1)

    def test_missing_price_value(self):
        path = self.create_csv(
            "missing_price.csv",
            ["timestamp", "open", "high", "low", "close"],
            [
                ["2026-01-01 09:15:00", 100, 105, 98, ""],
            ],
        )

        report = self.checker.check_file(path)

        self.assertGreater(report["numeric_errors"], 0)
        self.assertGreater(report["missing_values"], 0)

    def test_is_usable(self):
        path = self.create_csv(
            "usable.csv",
            ["timestamp", "open", "high", "low", "close"],
            [
                ["2026-01-01 09:15:00", 100, 105, 98, 102],
            ],
        )

        report = self.checker.check_file(path)

        self.assertTrue(self.checker.is_usable(report))

    def test_save_report(self):
        path = self.create_csv(
            "report.csv",
            ["timestamp", "open", "high", "low", "close"],
            [
                ["2026-01-01 09:15:00", 100, 105, 98, 102],
            ],
        )

        report = self.checker.check_file(path)
        output_path = str(self.base_path / "reports" / "quality.json")

        saved = self.checker.save_report(report, output_path)

        self.assertTrue(saved)
        self.assertTrue(Path(output_path).exists())


if __name__ == "__main__":
    unittest.main()
  
