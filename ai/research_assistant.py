
"""
India Arbitrage Lab - AI Research Assistant

Rule-based research assistant for summarizing strategy,
backtest and portfolio data.

This module does not connect to an external AI API.
It produces research observations using Python rules.
Research only. No live trading.
"""

from typing import Any, Dict, List, Optional


class ResearchAssistant:
    """Generate structured research observations from supplied data."""

    def __init__(self):
        self.reports: List[Dict[str, Any]] = []

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        try:
            result = float(value)
            if result != result:  # NaN
                return default
            if result in (float("inf"), float("-inf")):
                return default
            return result
        except (TypeError, ValueError):
            return default

    def analyze_performance(
        self,
        performance: Dict[str, Any],
    ) -> List[str]:
        """Create observations from performance metrics."""

        observations = []

        if not performance:
            return ["Performance data is unavailable."]

        net_pnl = self._safe_float(
            performance.get("total_net_pnl")
        )
        win_rate = self._safe_float(
            performance.get("win_rate_pct")
        )
        profit_factor = self._safe_float(
            performance.get("profit_factor")
        )
        drawdown = self._safe_float(
            performance.get("max_drawdown")
        )
        trades = int(
            self._safe_float(
                performance.get("total_trades")
            )
        )
        expectancy = self._safe_float(
            performance.get("expectancy_per_trade")
        )

        if net_pnl > 0:
            observations.append(
                "Net P&L is positive for the supplied period."
            )
        elif net_pnl < 0:
            observations.append(
                "Net P&L is negative for the supplied period."
            )
        else:
            observations.append(
                "Net P&L is approximately breakeven."
            )

        if trades < 30:
            observations.append(
                "Sample size is small; conclusions may be unreliable."
            )

        if win_rate >= 60:
            observations.append(
                "Win rate is relatively high; inspect average win "
                "and average loss to confirm profitability quality."
            )
        elif win_rate < 40:
            observations.append(
                "Win rate is low; examine payoff ratio and "
                "loss-control behavior."
            )

        if profit_factor > 1:
            observations.append(
                "Gross profit exceeds gross loss in the supplied data."
            )
        elif profit_factor == 1:
            observations.append(
                "Gross profit and gross loss are approximately equal."
            )
        else:
            observations.append(
                "Gross loss exceeds gross profit in the supplied data."
            )

        if drawdown > 0:
            observations.append(
                "Drawdown is present; review capital exposure "
                "and loss clustering."
            )

        if expectancy > 0:
            observations.append(
                "Average net expectancy per trade is positive."
            )
        elif expectancy < 0:
            observations.append(
                "Average net expectancy per trade is negative."
            )

        return observations

    def analyze_strategy_results(
        self,
        strategy_results: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Compare strategies based on supplied metrics.

        Expected example:
        {
            "S01": {"total_net_pnl": 1000,
                    "profit_factor": 1.4,
                    "total_trades": 50,
                    "max_drawdown": 200},
            "S02": {...}
        }
        """

        if not strategy_results:
            return {
                "strategies_analyzed": 0,
                "ranking": [],
                "observations": [
                    "No strategy results supplied."
                ],
            }

        ranking = []

        for strategy_id, metrics in strategy_results.items():
            net_pnl = self._safe_float(
                metrics.get("total_net_pnl")
            )
            profit_factor = self._safe_float(
                metrics.get("profit_factor")
            )
            trades = int(
                self._safe_float(
                    metrics.get("total_trades")
                )
            )
            win_rate = self._safe_float(
                metrics.get("win_rate_pct")
            )
            drawdown = self._safe_float(
                metrics.get("max_drawdown")
            )

            ranking.append({
                "strategy_id": str(strategy_id),
                "net_pnl": net_pnl,
                "profit_factor": profit_factor,
                "total_trades": trades,
                "win_rate_pct": win_rate,
                "max_drawdown": drawdown,
            })

        ranking.sort(
            key=lambda item: (
                item["net_pnl"],
                item["profit_factor"],
            ),
            reverse=True,
        )

        observations = []

        if ranking:
            best = ranking[0]
            observations.append(
                f"Highest net P&L in this dataset: "
                f"{best['strategy_id']}."
            )

            negative = [
                item for item in ranking
                if item["net_pnl"] < 0
            ]

            if negative:
                observations.append(
                    f"{len(negative)} strategies have negative "
                    "net P&L in the supplied results."
                )

            small_sample = [
                item for item in ranking
                if item["total_trades"] < 30
            ]

            if small_sample:
                observations.append(
                    f"{len(small_sample)} strategies have fewer "
                    "than 30 trades; their results need further validation."
                )

        report = {
            "strategies_analyzed": len(ranking),
            "ranking": ranking,
            "observations": observations,
        }

        self.reports.append(report)
        return report

    def analyze_failure_report(
        self,
        failure_data: Dict[str, Any],
    ) -> List[str]:
        """Summarize failure-analysis information."""

        observations = []

        if not failure_data:
            return ["Failure-analysis data is unavailable."]

        loss_rate = self._safe_float(
            failure_data.get("loss_rate_pct")
        )
        losing_trades = int(
            self._safe_float(
                failure_data.get("losing_trades")
            )
        )
        total_loss = self._safe_float(
            failure_data.get("total_loss")
        )
        average_loss = self._safe_float(
            failure_data.get("average_loss")
        )

        observations.append(
            f"Losing trades: {losing_trades}."
        )

        observations.append(
            f"Loss rate: {loss_rate:.2f}%."
        )

        observations.append(
            f"Total recorded loss: {total_loss:.2f}."
        )

        observations.append(
            f"Average losing trade: {average_loss:.2f}."
        )

        if loss_rate > 50:
            observations.append(
                "More than half of supplied trades are losing; "
                "review strategy conditions and execution assumptions."
            )

        return observations

    def create_research_report(
        self,
        strategy_id: str,
        performance: Optional[Dict[str, Any]] = None,
        failure_data: Optional[Dict[str, Any]] = None,
        additional_notes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Build a complete structured research report."""

        performance_observations = (
            self.analyze_performance(performance)
            if performance else []
        )

        failure_observations = (
            self.analyze_failure_report(failure_data)
            if failure_data else []
        )

        report = {
            "strategy_id": str(strategy_id).upper(),
            "performance_observations": performance_observations,
            "failure_observations": failure_observations,
            "additional_notes": list(additional_notes or []),
            "disclaimer": (
                "Research observations only. "
                "Not a trading recommendation."
            ),
        }

        self.reports.append(report)
        return report

    def get_reports(self) -> List[Dict[str, Any]]:
        return list(self.reports)

    def clear_reports(self) -> None:
        self.reports.clear()
      
