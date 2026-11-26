
import unittest

from integration.dashboard_integration import DashboardIntegration


class FakeDashboardAdapter:
    def __init__(self):
        self.snapshot = None

    def update_snapshot(self, snapshot):
        self.snapshot = snapshot


class TestDashboardIntegration(unittest.TestCase):

    def test_collect_connected_provider(self):
        integration = DashboardIntegration(
            providers={
                "market": lambda: {"symbol": "NIFTY", "price": 24000}
            }
        )

        snapshot = integration.collect()

        self.assertEqual(snapshot["overall_status"], "AVAILABLE")
        self.assertEqual(
            snapshot["sections"]["market"]["status"],
            "CONNECTED",
        )
        self.assertEqual(
            snapshot["sections"]["market"]["data"]["symbol"],
            "NIFTY",
        )

    def test_unconnected_provider(self):
        integration = DashboardIntegration()
        snapshot = integration.collect()

        self.assertEqual(
            snapshot["sections"]["market"]["status"],
            "NOT_CONNECTED",
        )

    def test_provider_error(self):
        def failing_provider():
            raise RuntimeError("Provider failed")

        integration = DashboardIntegration(
            providers={"market": failing_provider}
        )

        snapshot = integration.collect()

        self.assertEqual(snapshot["overall_status"], "PARTIAL")
        self.assertEqual(
            snapshot["sections"]["market"]["status"],
            "ERROR",
        )
        self.assertIn("market", integration.get_provider_errors())

    def test_register_provider(self):
        integration = DashboardIntegration()

        integration.register_provider(
            "risk",
            lambda: {"approved": True},
        )

        snapshot = integration.collect()

        self.assertEqual(
            snapshot["sections"]["risk"]["data"]["approved"],
            True,
        )

    def test_remove_provider(self):
        integration = DashboardIntegration(
            providers={"risk": lambda: {"approved": True}}
        )

        integration.remove_provider("risk")
        snapshot = integration.collect()

        self.assertEqual(
            snapshot["sections"]["risk"]["status"],
            "NOT_CONNECTED",
        )

    def test_publish_to_dashboard_adapter(self):
        adapter = FakeDashboardAdapter()
        integration = DashboardIntegration(
            providers={"system": lambda: {"running": True}},
            dashboard_adapter=adapter,
        )

        result = integration.publish()

        self.assertIsNotNone(adapter.snapshot)
        self.assertEqual(
            adapter.snapshot["sections"]["system"]["data"]["running"],
            True,
        )
        self.assertEqual(result["overall_status"], "AVAILABLE")

    def test_get_last_snapshot(self):
        integration = DashboardIntegration(
            providers={"system": lambda: {"running": True}}
        )

        integration.collect()
        snapshot = integration.get_last_snapshot()

        self.assertIn("sections", snapshot)
        self.assertIn("generated_at", snapshot)

    def test_get_section(self):
        integration = DashboardIntegration(
            providers={"risk": lambda: {"approved": False}}
        )

        integration.collect()
        section = integration.get_section("risk")

        self.assertEqual(section["status"], "CONNECTED")
        self.assertFalse(section["data"]["approved"])

    def test_invalid_section_rejected(self):
        integration = DashboardIntegration()

        with self.assertRaises(ValueError):
            integration.register_provider(
                "invalid_section",
                lambda: {},
            )

    def test_reset(self):
        integration = DashboardIntegration(
            providers={"system": lambda: {"running": True}}
        )

        integration.collect()
        integration.reset()

        self.assertEqual(integration.get_last_snapshot(), {})
        self.assertEqual(integration.get_provider_errors(), {})


if __name__ == "__main__":
    unittest.main()
  
