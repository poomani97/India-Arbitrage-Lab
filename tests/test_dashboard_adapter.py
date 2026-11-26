
import unittest

from integration.dashboard_adapter import DashboardAdapter


class TestDashboardAdapter(unittest.TestCase):

    def setUp(self):
        self.adapter = DashboardAdapter()

    def test_initial_snapshot(self):
        snapshot = self.adapter.get_snapshot()

        self.assertIsNone(snapshot["updated_at"])
        self.assertEqual(snapshot["signals"], [])
        self.assertEqual(snapshot["system"], {})

    def test_update_single_section(self):
        self.adapter.update_section(
            "system",
            {"status": "RUNNING"}
        )

        snapshot = self.adapter.get_snapshot()

        self.assertEqual(
            snapshot["system"]["status"],
            "RUNNING"
        )
        self.assertIsNotNone(snapshot["updated_at"])

    def test_update_multiple_sections(self):
        data = {
            "system": {"status": "RUNNING"},
            "market": {"symbol": "NIFTY"},
            "signals": [{"side": "BUY"}],
        }

        snapshot = self.adapter.update_snapshot(data)

        self.assertEqual(
            snapshot["market"]["symbol"],
            "NIFTY"
        )
        self.assertEqual(len(snapshot["signals"]), 1)

    def test_unknown_section_is_ignored_in_bulk_update(self):
        snapshot = self.adapter.update_snapshot(
            {"unknown_section": {"value": 1}}
        )

        self.assertNotIn("unknown_section", snapshot)

    def test_unknown_section_raises_error(self):
        with self.assertRaises(ValueError):
            self.adapter.update_section(
                "unknown_section",
                {}
            )

    def test_get_section(self):
        self.adapter.update_section(
            "risk",
            {"approved": True}
        )

        risk = self.adapter.get_section("risk")

        self.assertTrue(risk["approved"])

    def test_system_status(self):
        self.adapter.update_snapshot({
            "system": {"status": "RUNNING"},
            "validation": {"status": "PASS"},
        })

        status = self.adapter.get_system_status()

        self.assertEqual(status["status"], "RUNNING")
        self.assertEqual(
            status["validation_status"],
            "PASS"
        )

    def test_reset(self):
        self.adapter.update_section(
            "system",
            {"status": "RUNNING"}
        )

        snapshot = self.adapter.reset()

        self.assertEqual(snapshot["system"], {})
        self.assertIsNone(snapshot["updated_at"])

    def test_nested_data_normalization(self):
        data = {
            "metrics": {
                "pnl": 100.5,
                "trades": [1, 2, 3],
            }
        }

        self.adapter.update_section("backtesting", data)

        result = self.adapter.get_section("backtesting")

        self.assertEqual(
            result["metrics"]["pnl"],
            100.5
        )
        self.assertEqual(
            result["metrics"]["trades"],
            [1, 2, 3]
        )


if __name__ == "__main__":
    unittest.main()
  
