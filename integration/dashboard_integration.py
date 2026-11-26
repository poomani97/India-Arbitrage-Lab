
from datetime import datetime, timezone
import copy


class DashboardIntegration:
    """
    Collects status/data from system components and builds a dashboard snapshot.

    Read-only integration layer.
    Does not execute trades or change market/system components.
    """

    SECTION_NAMES = (
        "system",
        "market",
        "strategies",
        "signals",
        "risk",
        "paper_trading",
        "backtesting",
        "validation",
    )

    def __init__(self, providers=None, dashboard_adapter=None):
        self.providers = providers or {}
        self.dashboard_adapter = dashboard_adapter

        self.last_snapshot = {}
        self.provider_errors = {}

    def register_provider(self, section, callback):
        if section not in self.SECTION_NAMES:
            raise ValueError(f"Unknown dashboard section: {section}")

        if not callable(callback):
            raise ValueError("Provider must be callable.")

        self.providers[section] = callback

    def remove_provider(self, section):
        self.providers.pop(section, None)

    @staticmethod
    def _safe_call(callback):
        try:
            result = callback()
            return result, None
        except Exception as exc:
            return None, str(exc)

    def collect(self):
        snapshot = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_status": "AVAILABLE",
            "sections": {},
        }

        self.provider_errors = {}

        for section in self.SECTION_NAMES:
            callback = self.providers.get(section)

            if callback is None:
                snapshot["sections"][section] = {
                    "status": "NOT_CONNECTED",
                    "data": None,
                }
                continue

            data, error = self._safe_call(callback)

            if error is not None:
                snapshot["sections"][section] = {
                    "status": "ERROR",
                    "data": None,
                }
                self.provider_errors[section] = error
            else:
                snapshot["sections"][section] = {
                    "status": "CONNECTED",
                    "data": data,
                }

        if self.provider_errors:
            snapshot["overall_status"] = "PARTIAL"

        self.last_snapshot = copy.deepcopy(snapshot)
        return snapshot

    def publish(self):
        snapshot = self.collect()

        if self.dashboard_adapter is not None:
            update_method = getattr(
                self.dashboard_adapter, "update_snapshot", None
            )

            if callable(update_method):
                update_method(snapshot)

        return copy.deepcopy(snapshot)

    def get_last_snapshot(self):
        return copy.deepcopy(self.last_snapshot)

    def get_section(self, section):
        if section not in self.SECTION_NAMES:
            raise ValueError(f"Unknown dashboard section: {section}")

        return copy.deepcopy(
            self.last_snapshot.get("sections", {}).get(section)
        )

    def get_provider_errors(self):
        return dict(self.provider_errors)

    def reset(self):
        self.last_snapshot = {}
        self.provider_errors = {}
      
