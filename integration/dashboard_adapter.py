
from datetime import datetime, timezone
import math


class DashboardAdapter:
    """
    Converts system outputs into a consistent dashboard snapshot.

    This module does not execute trades or modify trading decisions.
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

    def __init__(self):
        self._snapshot = self._empty_snapshot()

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def _empty_snapshot(cls):
        return {
            "updated_at": None,
            "system": {},
            "market": {},
            "strategies": {},
            "signals": [],
            "risk": {},
            "paper_trading": {},
            "backtesting": {},
            "validation": {},
        }

    @classmethod
    def _normalize(cls, value):
        """Convert values into JSON-friendly data."""

        if value is None or isinstance(value, (str, bool, int)):
            return value

        if isinstance(value, float):
            if math.isfinite(value):
                return value
            return None

        if isinstance(value, datetime):
            return value.isoformat()

        if isinstance(value, dict):
            return {
                str(key): cls._normalize(item)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple, set)):
            return [
                cls._normalize(item)
                for item in value
            ]

        if hasattr(value, "to_dict") and callable(value.to_dict):
            try:
                return cls._normalize(value.to_dict())
            except Exception:
                return str(value)

        if hasattr(value, "__dict__"):
            try:
                return cls._normalize(vars(value))
            except Exception:
                return str(value)

        return str(value)

    def update_section(self, section, data):
        """
        Update one dashboard section.

        Supported sections:
        system, market, strategies, signals, risk,
        paper_trading, backtesting, validation.
        """

        if section not in self.SECTION_NAMES:
            raise ValueError(
                f"Unknown dashboard section: {section}"
            )

        normalized = self._normalize(data)

        self._snapshot[section] = normalized
        self._snapshot["updated_at"] = self._now()

        return self.get_snapshot()

    def update_snapshot(self, data):
        """Update multiple dashboard sections at once."""

        if not isinstance(data, dict):
            raise TypeError(
                "Dashboard snapshot data must be a dictionary."
            )

        for section, value in data.items():
            if section not in self.SECTION_NAMES:
                continue

            self._snapshot[section] = self._normalize(value)

        self._snapshot["updated_at"] = self._now()

        return self.get_snapshot()

    def get_snapshot(self):
        """Return a normalized copy of the current snapshot."""

        return self._normalize(self._snapshot)

    def get_section(self, section):
        """Return one dashboard section."""

        if section not in self.SECTION_NAMES:
            raise ValueError(
                f"Unknown dashboard section: {section}"
            )

        return self._normalize(self._snapshot[section])

    def get_system_status(self):
        """Return a compact status summary."""

        system = self._snapshot.get("system", {})
        validation = self._snapshot.get("validation", {})

        if not isinstance(system, dict):
            system = {}

        if not isinstance(validation, dict):
            validation = {}

        return {
            "status": system.get("status", "UNKNOWN"),
            "validation_status": validation.get(
                "status", "UNKNOWN"
            ),
            "updated_at": self._snapshot.get("updated_at"),
        }

    def reset(self):
        """Reset dashboard data to its initial state."""

        self._snapshot = self._empty_snapshot()
        return self.get_snapshot()
      
