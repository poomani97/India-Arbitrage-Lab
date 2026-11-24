
"""
India Arbitrage Lab
Strategy Detector
Runs registered strategies S01-S10 and collects scan results.
Research / paper-trading use only.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from strategies import STRATEGY_CLASSES


class ScannerDetector:
    """Runs multiple strategy engines and collects their outputs."""

    def __init__(self, strategy_classes=None):
        self.strategy_classes = strategy_classes or STRATEGY_CLASSES
        self.strategies = {}
        self.errors = {}

        self._load_strategies()

    def _load_strategies(self):
        """Load all registered strategy classes independently."""
        for strategy_id, strategy_class in self.strategy_classes.items():
            try:
                self.strategies[strategy_id] = strategy_class()
            except Exception as exc:
                self.errors[strategy_id] = (
                    f"Initialization failed: {type(exc).__name__}: {exc}"
                )

    @staticmethod
    def _normalize_result(result):
        """Convert strategy output into a list."""
        if result is None:
            return []
        if isinstance(result, list):
            return result
        if isinstance(result, tuple):
            return list(result)
        return [result]

    def scan_one(self, strategy_id, strategy, market_data):
        """Run one strategy and return its result safely."""
        try:
            scan_method = getattr(strategy, "safe_scan", None)

            if not callable(scan_method):
                scan_method = getattr(strategy, "scan", None)

            if not callable(scan_method):
                return {
                    "strategy_id": strategy_id,
                    "status": "error",
                    "opportunities": [],
                    "error": "Strategy has no callable scan/safe_scan method.",
                }

            result = scan_method(market_data)

            opportunities = self._normalize_result(result)

            return {
                "strategy_id": strategy_id,
                "status": "success",
                "opportunities": opportunities,
                "count": len(opportunities),
                "error": None,
            }

        except Exception as exc:
            return {
                "strategy_id": strategy_id,
                "status": "error",
                "opportunities": [],
                "count": 0,
                "error": f"{type(exc).__name__}: {exc}",
            }

    def scan_all(self, market_data):
        """Run all successfully loaded strategies."""
        scan_time = datetime.now(timezone.utc).isoformat()
        results = {}

        for strategy_id, strategy in self.strategies.items():
            results[strategy_id] = self.scan_one(
                strategy_id=strategy_id,
                strategy=strategy,
                market_data=market_data,
            )

        total_opportunities = sum(
            item.get("count", 0) for item in results.values()
        )

        successful = sum(
            1 for item in results.values()
            if item.get("status") == "success"
        )

        failed = sum(
            1 for item in results.values()
            if item.get("status") == "error"
        )

        return {
            "scan_timestamp": scan_time,
            "total_strategies_registered": len(self.strategy_classes),
            "total_strategies_loaded": len(self.strategies),
            "successful_scans": successful,
            "failed_scans": failed,
            "total_opportunities": total_opportunities,
            "initialization_errors": self.errors.copy(),
            "results": results,
        }

    @staticmethod
    def get_opportunities(scan_report):
        """Collect all opportunities from a scan report."""
        opportunities = []

        for result in scan_report.get("results", {}).values():
            if result.get("status") == "success":
                opportunities.extend(result.get("opportunities", []))

        return opportunities

    @staticmethod
    def get_errors(scan_report):
        """Collect scan and initialization errors."""
        errors = dict(scan_report.get("initialization_errors", {}))

        for strategy_id, result in scan_report.get("results", {}).items():
            if result.get("status") == "error":
                errors[strategy_id] = result.get("error")

        return errors

    @staticmethod
    def summary(scan_report):
        """Return a compact scanner summary."""
        return {
            "timestamp": scan_report.get("scan_timestamp"),
            "strategies_loaded": scan_report.get(
                "total_strategies_loaded", 0
            ),
            "scans_successful": scan_report.get("successful_scans", 0),
            "scans_failed": scan_report.get("failed_scans", 0),
            "opportunities_found": scan_report.get(
                "total_opportunities", 0
            ),
        }
      
