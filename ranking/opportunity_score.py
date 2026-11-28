"""
India Arbitrage Lab
Opportunity Scoring Engine

Ranks arbitrage opportunities using:
- Net edge quality
- Fill probability
- Confidence
- Liquidity

Score range: 0 to 100
"""

from dataclasses import dataclass
from typing import Any, Dict, List

from models.field_access import get_field


@dataclass
class ScoreResult:
    strategy_id: str
    score: float
    components: Dict[str, float]
    status: str
    reason: str = ""


class OpportunityScorer:
    """Calculate a weighted score for an opportunity."""

    def __init__(
        self,
        edge_weight: float = 0.40,
        fill_weight: float = 0.25,
        confidence_weight: float = 0.20,
        liquidity_weight: float = 0.15,
        target_liquidity: float = 100000.0,
    ):
        self.weights = {
            "edge": edge_weight,
            "fill": fill_weight,
            "confidence": confidence_weight,
            "liquidity": liquidity_weight,
        }

        total_weight = sum(self.weights.values())

        if total_weight <= 0:
            raise ValueError("Total scoring weight must be greater than zero.")

        # Normalize weights to sum to 1
        self.weights = {
            key: value / total_weight
            for key, value in self.weights.items()
        }

        if target_liquidity <= 0:
            raise ValueError("target_liquidity must be greater than zero.")

        self.target_liquidity = target_liquidity

    @staticmethod
    def _get_value(obj: Any, field: str, default: Any = 0.0) -> Any:
        return get_field(obj, field, default)

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            number = float(value)
            if number != number or number in (float("inf"), float("-inf")):
                return default
            return number
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
        return max(minimum, min(maximum, value))

    def score_one(self, opportunity: Any) -> ScoreResult:
        strategy_id = str(
            self._get_value(opportunity, "strategy_id", "UNKNOWN")
        ).upper()

        net_edge = self._safe_float(
            self._get_value(opportunity, "net_edge", 0.0)
        )

        gross_edge = self._safe_float(
            self._get_value(opportunity, "gross_edge", 0.0)
        )

        fill_probability = self._safe_float(
            self._get_value(opportunity, "fill_probability", 0.0)
        )

        confidence = self._safe_float(
            self._get_value(opportunity, "confidence", 0.0)
        )

        liquidity = self._safe_float(
            self._get_value(opportunity, "liquidity", 0.0)
        )

        # 1. Edge quality
        if gross_edge > 0:
            edge_quality = self._clamp(net_edge / gross_edge)
        else:
            edge_quality = 0.0

        # 2. Fill probability
        fill_score = self._clamp(fill_probability)

        # 3. Confidence
        confidence_score = self._clamp(confidence)

        # 4. Liquidity
        liquidity_score = self._clamp(
            liquidity / self.target_liquidity
        )

        components = {
            "edge": round(edge_quality * 100, 2),
            "fill": round(fill_score * 100, 2),
            "confidence": round(confidence_score * 100, 2),
            "liquidity": round(liquidity_score * 100, 2),
        }

        final_score = (
            edge_quality * self.weights["edge"]
            + fill_score * self.weights["fill"]
            + confidence_score * self.weights["confidence"]
            + liquidity_score * self.weights["liquidity"]
        ) * 100

        final_score = round(self._clamp(final_score, 0, 100), 2)

        if net_edge <= 0:
            status = "REJECTED"
            reason = "Net edge is not positive."
        elif final_score >= 80:
            status = "HIGH"
            reason = "High scoring opportunity."
        elif final_score >= 60:
            status = "MEDIUM"
            reason = "Moderate scoring opportunity."
        else:
            status = "LOW"
            reason = "Low scoring opportunity."

        # Update score if the object supports it
        if not isinstance(opportunity, dict):
            try:
                opportunity.score = final_score
                if hasattr(opportunity, "opportunity_score"):
                    opportunity.opportunity_score = final_score
            except (AttributeError, TypeError):
                pass
        else:
            opportunity["score"] = final_score

        return ScoreResult(
            strategy_id=strategy_id,
            score=final_score,
            components=components,
            status=status,
            reason=reason,
        )

    def score_many(self, opportunities: List[Any]) -> List[ScoreResult]:
        results = []

        for opportunity in opportunities:
            try:
                result = self.score_one(opportunity)
                results.append(result)
            except Exception as exc:
                results.append(
                    ScoreResult(
                        strategy_id=str(
                            self._get_value(
                                opportunity, "strategy_id", "UNKNOWN"
                            )
                        ),
                        score=0.0,
                        components={},
                        status="ERROR",
                        reason=str(exc),
                    )
                )

        return results

    def rank(self, opportunities: List[Any]) -> List[Any]:
        """Return opportunities sorted by score, highest first."""

        scored = []

        for opportunity in opportunities:
            result = self.score_one(opportunity)
            scored.append((result.score, opportunity))

        scored.sort(key=lambda item: item[0], reverse=True)

        return [opportunity for _, opportunity in scored]
