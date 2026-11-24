
"""
India Arbitrage Lab
Opportunity Scanner
Controls scanning, collects opportunities, and builds scan summaries.
Research / paper-trading use only.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from scanner.detector import ScannerDetector


class OpportunityScanner:
    """Central controller for scanning arbitrage strategies."""

    def __init__(self, detector=None):
        self.detector = detector or ScannerDetector()
        self.last_report = None

    def run_scan(self, market_data):
        """
        Execute a scan across registered strategies.

        Args:
            market_data: Market data passed to the strategy engines.

        Returns:
            Dictionary containing scan report, opportunities, errors and summary.
        """
        started_at = datetime.now(timezone.utc).isoformat()

        try:
            report = self.detector.scan_all(market_data)

            opportunities = self.detector.get_opportunities(report)
            errors = self.detector.get_errors(report)
            summary = self.detector.summary(report)

            result = {
                "status": "success",
                "scan_started_at": started_at,
                "scan_finished_at": datetime.now(timezone.utc).isoformat(),
                "summary": summary,
                "opportunities": opportunities,
                "opportunity_count": len(opportunities),
                "errors": errors,
                "raw_report": report,
            }

            self.last_report = result
            return result

        except Exception as exc:
            result = {
                "status": "error",
                "scan_started_at": started_at,
                "scan_finished_at": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "opportunities_found": 0,
                },
                "opportunities": [],
                "opportunity_count": 0,
                "errors": {
                    "scanner": f"{type(exc).__name__}: {exc}"
                },
                "raw_report": None,
            }

            self.last_report = result
            return result

    def scan_strategy(self, strategy_id, market_data):
        """
        Run only one strategy from the detector.

        Args:
            strategy_id: Strategy ID such as S01 or S10.
            market_data: Market data supplied to that strategy.
        """
        strategy_id = str(strategy_id).upper()

        strategy = self.detector.strategies.get(strategy_id)

        if strategy is None:
            return {
                "status": "error",
                "strategy_id": strategy_id,
                "opportunities": [],
                "opportunity_count": 0,
                "error": "Strategy not loaded or unknown strategy ID.",
            }

        try:
            result = self.detector.scan_one(
                strategy_id=strategy_id,
                strategy=strategy,
                market_data=market_data,
            )

            return {
                "status": result.get("status", "error"),
                "strategy_id": strategy_id,
                "opportunities": result.get("opportunities", []),
                "opportunity_count": result.get("count", 0),
                "error": result.get("error"),
            }

        except Exception as exc:
            return {
                "status": "error",
                "strategy_id": strategy_id,
                "opportunities": [],
                "opportunity_count": 0,
                "error": f"{type(exc).__name__}: {exc}",
            }

    def get_last_report(self):
        """Return the most recent scan report."""
        return self.last_report

    def get_opportunities(self):
        """Return opportunities from the most recent scan."""
        if not self.last_report:
            return []

        return self.last_report.get("opportunities", [])

    def get_scan_errors(self):
        """Return errors from the most recent scan."""
        if not self.last_report:
            return {}

        return self.last_report.get("errors", {})

    def get_summary(self):
        """Return summary from the most recent scan."""
        if not self.last_report:
            return {
                "status": "not_scanned",
                "message": "No scan has been executed yet.",
            }

        return self.last_report.get("summary", {})

    @staticmethod
    def filter_by_strategy(opportunities, strategy_id):
        """Filter opportunities by strategy ID."""
        strategy_id = str(strategy_id).upper()
        filtered = []

        for opportunity in opportunities:
            if isinstance(opportunity, dict):
                current_id = opportunity.get("strategy_id")
            else:
                current_id = getattr(opportunity, "strategy_id", None)

            if current_id and str(current_id).upper() == strategy_id:
                filtered.append(opportunity)

        return filtered

    @staticmethod
    def filter_valid_objects(opportunities):
        """Remove None entries without making profitability assumptions."""
        return [
            opportunity
            for opportunity in opportunities
            if opportunity is not None
        ]

    @staticmethod
    def count_by_strategy(opportunities):
        """Count collected opportunities per strategy."""
        counts = {}

        for opportunity in opportunities:
            if isinstance(opportunity, dict):
                strategy_id = opportunity.get("strategy_id", "UNKNOWN")
            else:
                strategy_id = getattr(
                    opportunity, "strategy_id", "UNKNOWN"
                )

            counts[strategy_id] = counts.get(strategy_id, 0) + 1

        return counts

    @staticmethod
    def build_opportunity_summary(opportunities):
        """Build a count summary without ranking opportunities."""
        cleaned = OpportunityScanner.filter_valid_objects(opportunities)

        return {
            "total_opportunities": len(cleaned),
            "by_strategy": OpportunityScanner.count_by_strategy(cleaned),
        }
      
