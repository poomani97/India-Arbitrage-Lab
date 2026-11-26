
import unittest

from data.historical_catalog import HistoricalDataCatalog


class TestHistoricalDataCatalog(unittest.TestCase):

    def setUp(self):
        self.catalog = HistoricalDataCatalog()

    def test_register_dataset(self):
        self.catalog.register(
            dataset_id="NIFTY_1M",
            file_path="data/nifty_1m.csv",
            symbol="NIFTY",
            timeframe="1m",
        )

        self.assertEqual(self.catalog.count(), 1)
        self.assertIsNotNone(self.catalog.get("NIFTY_1M"))

    def test_get_dataset(self):
        self.catalog.register(
            "NIFTY_1M",
            "data/nifty_1m.csv",
            "NIFTY",
            "1m",
        )

        dataset = self.catalog.get("NIFTY_1M")

        self.assertEqual(dataset["symbol"], "NIFTY")
        self.assertEqual(dataset["timeframe"], "1m")

    def test_remove_dataset(self):
        self.catalog.register(
            "NIFTY_1M",
            "data/nifty_1m.csv",
            "NIFTY",
            "1m",
        )

        self.assertTrue(self.catalog.remove("NIFTY_1M"))
        self.assertEqual(self.catalog.count(), 0)

    def test_list_by_symbol(self):
        self.catalog.register(
            "NIFTY_1M",
            "data/nifty_1m.csv",
            "NIFTY",
            "1m",
        )

        self.catalog.register(
            "NIFTY_15M",
            "data/nifty_15m.csv",
            "NIFTY",
            "15m",
        )

        self.catalog.register(
            "BANKNIFTY_1M",
            "data/banknifty_1m.csv",
            "BANKNIFTY",
            "1m",
        )

        result = self.catalog.list_by_symbol("NIFTY")

        self.assertEqual(len(result), 2)

    def test_list_by_timeframe(self):
        self.catalog.register(
            "NIFTY_1M",
            "data/nifty_1m.csv",
            "NIFTY",
            "1m",
        )

        self.catalog.register(
            "BANKNIFTY_1M",
            "data/banknifty_1m.csv",
            "BANKNIFTY",
            "1m",
        )

        result = self.catalog.list_by_timeframe("1m")

        self.assertEqual(len(result), 2)

    def test_update_quality(self):
        self.catalog.register(
            "NIFTY_1M",
            "data/nifty_1m.csv",
            "NIFTY",
            "1m",
        )

        report = {"status": "PASS", "valid_rows": 100}

        self.assertTrue(
            self.catalog.update_quality(
                "NIFTY_1M",
                "PASS",
                report,
            )
        )

        dataset = self.catalog.get("NIFTY_1M")

        self.assertEqual(dataset["quality_status"], "PASS")
        self.assertEqual(dataset["quality_report"], report)

    def test_update_unknown_dataset(self):
        result = self.catalog.update_quality(
            "UNKNOWN",
            "PASS",
        )

        self.assertFalse(result)

    def test_summary(self):
        self.catalog.register(
            "NIFTY_1M",
            "data/nifty_1m.csv",
            "NIFTY",
            "1m",
        )

        self.catalog.register(
            "BANKNIFTY_1M",
            "data/banknifty_1m.csv",
            "BANKNIFTY",
            "1m",
        )

        self.catalog.update_quality("NIFTY_1M", "PASS")
        self.catalog.update_quality("BANKNIFTY_1M", "WARNING")

        result = self.catalog.summary()

        self.assertEqual(result["total_datasets"], 2)
        self.assertEqual(result["quality_status_counts"]["PASS"], 1)
        self.assertEqual(result["quality_status_counts"]["WARNING"], 1)
        self.assertIn("NIFTY", result["symbols"])

    def test_clear(self):
        self.catalog.register(
            "NIFTY_1M",
            "data/nifty_1m.csv",
            "NIFTY",
            "1m",
        )

        self.catalog.clear()

        self.assertEqual(self.catalog.count(), 0)


if __name__ == "__main__":
    unittest.main()
  
