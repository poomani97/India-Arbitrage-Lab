
"""
India Arbitrage Lab
Opportunity Qualification Engine

Determines whether validated opportunities are eligible
to proceed to ranking.
Research / paper-trading use only.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from models.field_access import get_field


@dataclass
class QualificationResult:
    is_qualified: bool
    opportunity_id: Optional[str]
    strategy_id: Optional[str]
    reasons: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "is_qualified": self.is_qualified,
            "opportunity_id": self.opportunity_id,
            "strategy_id": self.strategy_id,
            "reasons": list(self.reasons),
            "metrics": dict(self.metrics),
        }


class OpportunityQualification:
    """Apply configurable eligibility rules to validated opportunities."""

    def __init__(
        self,
        min_net_edge=0.0,
        min_fill_probability=0.0,
        min_confidence=0.0,
        min_liquidity=0.0,
        require_positive_edge=True,
    ):
        self.min_net_edge = min_net_edge
        self.min_fill_probability = min_fill_probability
        self.min_confidence = min_confidence
        self.min_liquidity = min_liquidity
        self.require_positive_edge = require_positive_edge

    @staticmethod
    def _get(obj, field_name, default=None):
        return get_field(obj, field_name, default)

    @staticmethod
    def _get_id(opportunity):
        value = OpportunityQualification._get(
            opportunity, "opportunity_id"
        )
        if value is None:
            value = OpportunityQualification._get(opportunity, "id")
        return value

    def qualify(self, opportunity, validation_report=None):
        """Qualify one opportunity."""
        reasons = []

        strategy_id = self._get(opportunity, "strategy_id")
        opportunity_id = self._get_id(opportunity)

        net_edge = self._get(opportunity, "net_edge")
        fill_probability = self._get(opportunity, "fill_probability")
        confidence = self._get(opportunity, "confidence")
        liquidity = self._get(opportunity, "liquidity")

        # Validation gate
        if validation_report is not None:
            if isinstance(validation_report, dict):
                is_valid = validation_report.get("is_valid", False)
            else:
                is_valid = getattr(validation_report, "is_valid", False)

            if not is_valid:
                reasons.append("Validation failed.")

        # Net edge gate
        if net_edge is None:
            reasons.append("Net edge is missing.")
        else:
            try:
                edge_value = float(net_edge)

                if self.require_positive_edge and edge_value <= 0:
                    reasons.append("Net edge is not positive.")

                if edge_value < self.min_net_edge:
                    reasons.append(
                        f"Net edge below minimum ({self.min_net_edge})."
                    )
            except (TypeError, ValueError):
                reasons.append("Net edge is not numeric.")

        # Fill probability gate
        if fill_probability is not None:
            try:
                fill_value = float(fill_probability)
                if fill_value < self.min_fill_probability:
                    reasons.append(
                        "Fill probability below minimum threshold."
                    )
            except (TypeError, ValueError):
                reasons.append("Fill probability is not numeric.")
        elif self.min_fill_probability > 0:
            reasons.append("Fill probability is missing.")

        # Confidence gate
        if confidence is not None:
            try:
                confidence_value = float(confidence)
                if confidence_value < self.min_confidence:
                    reasons.append("Confidence below minimum threshold.")
            except (TypeError, ValueError):
                reasons.append("Confidence is not numeric.")
        elif self.min_confidence > 0:
            reasons.append("Confidence is missing.")

        # Liquidity gate
        if liquidity is not None:
            try:
                liquidity_value = float(liquidity)
                if liquidity_value < self.min_liquidity:
                    reasons.append("Liquidity below minimum threshold.")
            except (TypeError, ValueError):
                reasons.append("Liquidity is not numeric.")
        elif self.min_liquidity > 0:
            reasons.append("Liquidity is missing.")

        qualified = len(reasons) == 0

        return QualificationResult(
            is_qualified=qualified,
            opportunity_id=opportunity_id,
            strategy_id=strategy_id,
            reasons=reasons,
            metrics={
                "net_edge": net_edge,
                "fill_probability": fill_probability,
                "confidence": confidence,
                "liquidity": liquidity,
                "min_net_edge": self.min_net_edge,
                "min_fill_probability": self.min_fill_probability,
                "min_confidence": self.min_confidence,
                "min_liquidity": self.min_liquidity,
            },
        )

    def qualify_many(self, opportunities, validation_reports=None):
        """Qualify multiple opportunities."""
        validation_reports = validation_reports or []
        results = []

        for index, opportunity in enumerate(opportunities):
            report = (
                validation_reports[index]
                if index < len(validation_reports)
                else None
            )
            results.append(self.qualify(opportunity, report))

        return results

    def filter_qualified(self, opportunities, validation_reports=None):
        """Separate qualified and rejected opportunities."""
        results = self.qualify_many(
            opportunities,
            validation_reports=validation_reports,
        )

        qualified = []
        rejected = []

        for opportunity, result in zip(opportunities, results):
            if result.is_qualified:
                qualified.append(opportunity)
            else:
                rejected.append(opportunity)

        return {
            "qualified": qualified,
            "rejected": rejected,
            "results": results,
            "qualified_count": len(qualified),
            "rejected_count": len(rejected),
        }
      
