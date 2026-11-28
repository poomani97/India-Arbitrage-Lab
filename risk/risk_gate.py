"""
India Arbitrage Lab
Risk Gate

Evaluates opportunities against configurable risk limits.
This module is for research and paper trading only.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List
import math

from models.field_access import get_field


@dataclass
class RiskDecision:
    strategy_id: str
    approved: bool
    status: str
    reasons: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)


class RiskGate:
    """Approve or reject opportunities based on risk rules."""

    def __init__(
        self,
        max_capital_per_trade: float = 100000.0,
        max_margin_per_trade: float = 100000.0,
        min_net_edge: float = 0.0,
        min_score: float = 60.0,
        min_confidence: float = 0.50,
        min_fill_probability: float = 0.50,
        min_liquidity: float = 0.0,
    ):
        self.max_capital_per_trade = max_capital_per_trade
        self.max_margin_per_trade = max_margin_per_trade
        self.min_net_edge = min_net_edge
        self.min_score = min_score
        self.min_confidence = min_confidence
        self.min_fill_probability = min_fill_probability
        self.min_liquidity = min_liquidity

    @staticmethod
    def _get(obj: Any, key: str, default: Any = None) -> Any:
        return get_field(obj, key, default)

    @staticmethod
    def _number(value: Any) -> float:
        try:
            number = float(value)
            if math.isfinite(number):
                return number
            return float("nan")
        except (TypeError, ValueError):
            return float("nan")

    def evaluate(self, opportunity: Any) -> RiskDecision:
        strategy_id = str(
            self._get(opportunity, "strategy_id", "UNKNOWN")
        ).upper()

        reasons = []

        net_edge = self._number(
            self._get(opportunity, "net_edge")
        )
        score = self._number(
            self._get(opportunity, "score")
        )
        confidence = self._number(
            self._get(opportunity, "confidence")
        )
        fill_probability = self._number(
            self._get(opportunity, "fill_probability")
        )
        liquidity = self._number(
            self._get(opportunity, "liquidity")
        )
        capital = self._number(
            self._get(opportunity, "capital")
        )
        margin = self._number(
            self._get(opportunity, "margin")
        )

        # Check required numeric values
        required_values = {
            "net_edge": net_edge,
            "score": score,
            "confidence": confidence,
            "fill_probability": fill_probability,
            "liquidity": liquidity,
        }

        for field_name, value in required_values.items():
            if not math.isfinite(value):
                reasons.append(
                    f"Missing or invalid {field_name}."
                )

        # Net edge check
        if math.isfinite(net_edge) and net_edge <= self.min_net_edge:
            reasons.append("Net edge is below the allowed minimum.")

        # Score check
        if math.isfinite(score) and score < self.min_score:
            reasons.append("Opportunity score is too low.")

        # Confidence check
        if math.isfinite(confidence):
            if not 0.0 <= confidence <= 1.0:
                reasons.append("Confidence must be between 0 and 1.")
            elif confidence < self.min_confidence:
                reasons.append("Confidence is below the required minimum.")

        # Fill probability check
        if math.isfinite(fill_probability):
            if not 0.0 <= fill_probability <= 1.0:
                reasons.append(
                    "Fill probability must be between 0 and 1."
                )
            elif fill_probability < self.min_fill_probability:
                reasons.append(
                    "Fill probability is below the required minimum."
                )

        # Liquidity check
        if math.isfinite(liquidity):
            if liquidity < self.min_liquidity:
                reasons.append("Liquidity is below the required minimum.")

        # Capital check
        if not math.isfinite(capital) or capital <= 0:
            reasons.append("Capital requirement is missing or invalid.")
        elif capital > self.max_capital_per_trade:
            reasons.append("Capital requirement exceeds the risk limit.")

        # Margin check
        if not math.isfinite(margin) or margin <= 0:
            reasons.append("Margin requirement is missing or invalid.")
        elif margin > self.max_margin_per_trade:
            reasons.append("Margin requirement exceeds the risk limit.")

        approved = len(reasons) == 0

        return RiskDecision(
            strategy_id=strategy_id,
            approved=approved,
            status="APPROVED" if approved else "REJECTED",
            reasons=reasons,
            metrics={
                "net_edge": net_edge if math.isfinite(net_edge) else 0.0,
                "score": score if math.isfinite(score) else 0.0,
                "confidence": confidence if math.isfinite(confidence) else 0.0,
                "fill_probability": (
                    fill_probability
                    if math.isfinite(fill_probability)
                    else 0.0
                ),
                "liquidity": liquidity if math.isfinite(liquidity) else 0.0,
                "capital": capital if math.isfinite(capital) else 0.0,
                "margin": margin if math.isfinite(margin) else 0.0,
            },
        )

    def evaluate_many(
        self, opportunities: List[Any]
    ) -> List[RiskDecision]:
        return [
            self.evaluate(opportunity)
            for opportunity in opportunities
        ]

    def filter_approved(
        self, opportunities: List[Any]
    ) -> List[Any]:
        """Return approved opportunities and flag them risk_approved=True.

        ExecutionRouter only accepts opportunities that carry this flag.
        """
        approved = []

        for opportunity in opportunities:
            if not self.evaluate(opportunity).approved:
                continue

            if isinstance(opportunity, dict):
                opportunity["risk_approved"] = True
            else:
                try:
                    opportunity.risk_approved = True
                except (AttributeError, TypeError):
                    pass

            approved.append(opportunity)

        return approved

    def get_rejected(
        self, opportunities: List[Any]
    ) -> List[RiskDecision]:
        return [
            decision
            for decision in self.evaluate_many(opportunities)
            if not decision.approved
        ]
