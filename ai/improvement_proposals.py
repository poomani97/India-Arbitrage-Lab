
"""
India Arbitrage Lab - Improvement Proposals

Creates research proposals from strategy metrics.
Proposals are informational and never auto-applied.
"""

from typing import Any, Dict, List


class ImprovementProposals:
    """Rule-based strategy improvement proposal generator."""

    def __init__(self):
        self.proposals: List[Dict[str, Any]] = []

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        try:
            result = float(value)

            if result != result:
                return default

            if result in (float("inf"), float("-inf")):
                return default

            return result

        except (TypeError, ValueError):
            return default

    def analyze_metrics(
        self,
        strategy_id: str,
        metrics: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate improvement proposals from strategy metrics."""

        if not metrics:
            return []

        proposals = []

        net_pnl = self._safe_float(
            metrics.get("total_net_pnl")
        )
        profit_factor = self._safe_float(
            metrics.get("profit_factor")
        )
        win_rate = self._safe_float(
            metrics.get("win_rate_pct")
        )
        drawdown = self._safe_float(
            metrics.get("max_drawdown")
        )
        trades = int(
            self._safe_float(
                metrics.get("total_trades")
            )
        )
        expectancy = self._safe_float(
            metrics.get("expectancy_per_trade")
        )

        strategy_id = str(strategy_id).upper()

        def add_proposal(
            category: str,
            priority: str,
            observation: str,
            proposal: str,
            validation: str,
        ):
            proposals.append({
                "strategy_id": strategy_id,
                "category": category,
                "priority": priority,
                "observation": observation,
                "proposal": proposal,
                "validation_required": validation,
                "status": "PENDING_RESEARCH",
            })

        # Sample-size review
        if trades < 30:
            add_proposal(
                category="DATA_QUALITY",
                priority="HIGH",
                observation=(
                    f"Only {trades} trades are available."
                ),
                proposal=(
                    "Collect more historical and out-of-sample "
                    "observations before judging strategy performance."
                ),
                validation=(
                    "Repeat testing across multiple periods "
                    "and market conditions."
                ),
            )

        # Negative performance review
        if net_pnl < 0:
            add_proposal(
                category="PERFORMANCE",
                priority="HIGH",
                observation="Net P&L is negative.",
                proposal=(
                    "Review entry conditions, exit logic, "
                    "execution costs and losing-trade distribution."
                ),
                validation=(
                    "Compare revised research results with the "
                    "unchanged baseline strategy."
                ),
            )

        # Profit factor review
        if profit_factor < 1.0:
            add_proposal(
                category="TRADE_QUALITY",
                priority="HIGH",
                observation="Profit factor is below 1.",
                proposal=(
                    "Study gross profit, gross loss, average win, "
                    "average loss and trade selection."
                ),
                validation=(
                    "Test changes on untouched out-of-sample data."
                ),
            )

        elif 1.0 <= profit_factor < 1.2:
            add_proposal(
                category="TRADE_QUALITY",
                priority="MEDIUM",
                observation=(
                    "Profit factor is positive but has a "
                    "relatively small margin above 1."
                ),
                proposal=(
                    "Investigate costs, slippage and robustness "
                    "across different market regimes."
                ),
                validation=(
                    "Use realistic costs and walk-forward testing."
                ),
            )

        # Drawdown review
        if drawdown > 0:
            add_proposal(
                category="RISK",
                priority="HIGH" if drawdown > 0.2 else "MEDIUM",
                observation=(
                    f"Recorded maximum drawdown: {drawdown:.2f}."
                ),
                proposal=(
                    "Review exposure, loss concentration, "
                    "capital usage and drawdown behavior."
                ),
                validation=(
                    "Evaluate risk changes against the baseline "
                    "without improving results through hindsight."
                ),
            )

        # Win rate review
        if win_rate < 40:
            add_proposal(
                category="ENTRY_EXIT",
                priority="MEDIUM",
                observation=(
                    f"Win rate is relatively low ({win_rate:.2f}%)."
                ),
                proposal=(
                    "Study entry filtering and average winning "
                    "versus losing trade size. Low win rate alone "
                    "does not prove the strategy is unprofitable."
                ),
                validation=(
                    "Evaluate expectancy, payoff ratio and "
                    "out-of-sample performance."
                ),
            )

        # Expectancy review
        if expectancy <= 0:
            add_proposal(
                category="EXPECTANCY",
                priority="HIGH",
                observation="Average net expectancy is non-positive.",
                proposal=(
                    "Review the full trade distribution, "
                    "execution costs and strategy assumptions."
                ),
                validation=(
                    "Confirm positive expectancy on independent "
                    "data before considering further use."
                ),
            )

        # Cost review
        if "total_transaction_costs" in metrics:
            costs = self._safe_float(
                metrics.get("total_transaction_costs")
            )

            if costs > 0:
                add_proposal(
                    category="COSTS",
                    priority="MEDIUM",
                    observation=(
                        f"Recorded transaction costs: {costs:.2f}."
                    ),
                    proposal=(
                        "Review brokerage, taxes, spread, slippage "
                        "and liquidity assumptions."
                    ),
                    validation=(
                        "Re-run tests with complete realistic "
                        "cost assumptions."
                    ),
                )

        self.proposals.extend(proposals)
        return proposals

    def compare_strategies(
        self,
        strategy_results: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Identify strategies that may need further review."""

        results = []

        if not strategy_results:
            return results

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

            if net_pnl < 0 or profit_factor < 1.0 or trades < 30:
                results.append({
                    "strategy_id": str(strategy_id).upper(),
                    "net_pnl": net_pnl,
                    "profit_factor": profit_factor,
                    "total_trades": trades,
                    "review_required": True,
                    "reason": (
                        "Negative P&L, low profit factor, "
                        "or insufficient trade sample."
                    ),
                })

        return results

    def get_all_proposals(self) -> List[Dict[str, Any]]:
        return list(self.proposals)

    def clear_proposals(self) -> None:
        self.proposals.clear()

    def export_proposals(self) -> List[Dict[str, Any]]:
        """Return proposals in export-friendly format."""
        return [
            proposal.copy()
            for proposal in self.proposals
        ]
      
