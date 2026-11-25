"""
India Arbitrage Lab
Capital Efficiency Analyzer

Measures net edge relative to capital required.
This is a research metric, not a guaranteed return.
"""

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class CapitalEfficiencyResult:
    strategy_id: str
    net_edge: float
    capital_required: float
    efficiency_ratio: float
    efficiency_percent: float
    status: str
    reason: str = ""


class CapitalEfficiencyAnalyzer:
    """Analyze and rank opportunities by capital efficiency."""

    def __init__(self):
        pass

    @staticmethod
    def _get_value(obj: Any, field: str, default: Any = 0.0) -> Any:
        if isinstance(obj, dict):
            return obj.get(field, default)
        return getattr(obj, field, default)

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            number = float(value)
            if number != number or number in (float("inf"), float("-inf")):
                return default
            return number
        except (TypeError, ValueError):
            return default

    def analyze_one(self, opportunity: Any) -> CapitalEfficiencyResult:
        strategy_id = str(
            self._get_value(opportunity, "strategy_id", "UNKNOWN")
        ).upper()

        net_edge = self._safe_float(
            self._get_value(opportunity, "net_edge", 0.0)
        )

        # Prefer explicit capital requirement, otherwise use margin.
        capital = self._safe_float(
            self._get_value(opportunity, "capital", 0.0)
        )

        if capital <= 0:
            capital = self._safe_float(
                self._get_value(opportunity, "margin", 0.0)
            )

        if capital <= 0:
            return CapitalEfficiencyResult(
                strategy_id=strategy_id,
                net_edge=net_edge,
                capital_required=0.0,
                efficiency_ratio=0.0,
                efficiency_percent=0.0,
                status="INVALID_CAPITAL",
                reason="Capital or margin must be greater than zero.",
            )

        efficiency_ratio = net_edge / capital

        # Convert ratio to percentage for readability.
        efficiency_percent = efficiency_ratio * 100

        if net_edge <= 0:
            status = "NEGATIVE_EDGE"
            reason = "Net edge is zero or negative."
        elif efficiency_ratio > 0:
            status = "VALID"
            reason = "Capital efficiency calculated."
        else:
            status = "INVALID"
            reason = "Capital efficiency could not be calculated."

        return CapitalEfficiencyResult(
            strategy_id=strategy_id,
            net_edge=round(net_edge, 6),
            capital_required=round(capital, 2),
            efficiency_ratio=round(efficiency_ratio, 8),
            efficiency_percent=round(efficiency_percent, 6),
            status=status,
            reason=reason,
        )

    def analyze_many(
        self, opportunities: List[Any]
    ) -> List[CapitalEfficiencyResult]:
        results = []

        for opportunity in opportunities:
            try:
                results.append(self.analyze_one(opportunity))
            except Exception as exc:
                results.append(
                    CapitalEfficiencyResult(
                        strategy_id=str(
                            self._get_value(
                                opportunity, "strategy_id", "UNKNOWN"
                            )
                        ),
                        net_edge=0.0,
                        capital_required=0.0,
                        efficiency_ratio=0.0,
                        efficiency_percent=0.0,
                        status="ERROR",
                        reason=str(exc),
                    )
                )

        return results

    def rank(self, opportunities: List[Any]) -> List[Any]:
        """Rank opportunities by net edge per unit of capital."""

        scored = []

        for opportunity in opportunities:
            result = self.analyze_one(opportunity)

            if result.status == "VALID":
                scored.append((result.efficiency_ratio, opportunity))

        scored.sort(key=lambda item: item[0], reverse=True)

        return [opportunity for _, opportunity in scored]

    def get_summary(
        self, opportunities: List[Any]
    ) -> Dict[str, Any]:
        results = self.analyze_many(opportunities)

        valid_results = [
            result for result in results
            if result.status == "VALID"
        ]

        return {
            "total_opportunities": len(opportunities),
            "valid_opportunities": len(valid_results),
            "invalid_opportunities": len(opportunities) - len(valid_results),
            "highest_efficiency": (
                max(
                    (r.efficiency_percent for r in valid_results),
                    default=0.0,
                )
            ),
            "average_efficiency": (
                sum(r.efficiency_percent for r in valid_results)
                / len(valid_results)
                if valid_results else 0.0
            ),
            "results": results,
        }
