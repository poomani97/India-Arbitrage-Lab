
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4
from typing import Any, Dict, Optional


class OpportunityStatus(str, Enum):
    DETECTED = "DETECTED"
    VALIDATED = "VALIDATED"
    QUALIFIED = "QUALIFIED"
    REJECTED = "REJECTED"
    RANKED = "RANKED"
    PAPER_READY = "PAPER_READY"


@dataclass
class Opportunity:
    """
    Standard data model for every arbitrage opportunity.

    All strategy engines will produce this common object.
    """

    strategy_id: str
    symbol: str
    market: str
    opportunity_type: str

    # Unique identification
    opportunity_id: str = field(default_factory=lambda: str(uuid4()))

    # Detection timestamp (UTC)
    detected_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Price and edge information
    gross_edge: float = 0.0
    estimated_costs: float = 0.0
    risk_buffer: float = 0.0
    net_edge: float = 0.0

    # Capital and liquidity
    capital_required: float = 0.0
    estimated_margin: float = 0.0
    liquidity_score: float = 0.0

    # Confidence and quality
    fill_probability: float = 0.0
    confidence_score: float = 0.0
    opportunity_score: float = 0.0

    # Current lifecycle status
    status: OpportunityStatus = OpportunityStatus.DETECTED

    # Optional details
    cost_breakdown: Dict[str, float] = field(default_factory=dict)
    legs: list = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    rejection_reason: Optional[str] = None

    def __post_init__(self):
        self.validate()

    def validate(self):
        """Validate opportunity data."""

        if not self.strategy_id:
            raise ValueError("strategy_id cannot be empty")

        if not self.symbol:
            raise ValueError("symbol cannot be empty")

        if not self.market:
            raise ValueError("market cannot be empty")

        if not self.opportunity_type:
            raise ValueError("opportunity_type cannot be empty")

        numeric_fields = {
            "gross_edge": self.gross_edge,
            "estimated_costs": self.estimated_costs,
            "risk_buffer": self.risk_buffer,
            "net_edge": self.net_edge,
            "capital_required": self.capital_required,
            "estimated_margin": self.estimated_margin,
            "liquidity_score": self.liquidity_score,
            "fill_probability": self.fill_probability,
            "confidence_score": self.confidence_score,
            "opportunity_score": self.opportunity_score,
        }

        for field_name, value in numeric_fields.items():
            if not isinstance(value, (int, float)):
                raise TypeError(f"{field_name} must be numeric")

            if value != value:  # NaN check
                raise ValueError(f"{field_name} cannot be NaN")

        if self.capital_required < 0:
            raise ValueError("capital_required cannot be negative")

        if self.estimated_margin < 0:
            raise ValueError("estimated_margin cannot be negative")

        if not 0 <= self.fill_probability <= 1:
            raise ValueError("fill_probability must be between 0 and 1")

        if not 0 <= self.confidence_score <= 100:
            raise ValueError("confidence_score must be between 0 and 100")

        if not 0 <= self.opportunity_score <= 100:
            raise ValueError("opportunity_score must be between 0 and 100")

        if not 0 <= self.liquidity_score <= 100:
            raise ValueError("liquidity_score must be between 0 and 100")

        if self.estimated_costs < 0:
            raise ValueError("estimated_costs cannot be negative")

        if self.risk_buffer < 0:
            raise ValueError("risk_buffer cannot be negative")

        for cost_name, cost_value in self.cost_breakdown.items():
            if not isinstance(cost_value, (int, float)):
                raise TypeError(
                    f"Cost value for {cost_name} must be numeric"
                )

            if cost_value < 0:
                raise ValueError(
                    f"Cost value for {cost_name} cannot be negative"
                )

        return True

    def calculate_net_edge(self):
        """Calculate net edge after costs and risk buffer."""

        self.net_edge = (
            self.gross_edge
            - self.estimated_costs
            - self.risk_buffer
        )

        return self.net_edge

    def mark_validated(self):
        """Mark the opportunity as validated."""

        self.status = OpportunityStatus.VALIDATED

    def mark_qualified(self):
        """Mark the opportunity as qualified."""

        self.status = OpportunityStatus.QUALIFIED

    def mark_ranked(self):
        """Mark the opportunity as ranked."""

        self.status = OpportunityStatus.RANKED

    def mark_paper_ready(self):
        """Mark the opportunity as ready for paper trading."""

        self.status = OpportunityStatus.PAPER_READY

    def reject(self, reason: str):
        """Reject an opportunity and store the reason."""

        self.status = OpportunityStatus.REJECTED
        self.rejection_reason = reason

    def to_dict(self):
        """Convert the opportunity into a dictionary."""

        return {
            "opportunity_id": self.opportunity_id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "market": self.market,
            "opportunity_type": self.opportunity_type,
            "detected_at": self.detected_at.isoformat(),
            "gross_edge": self.gross_edge,
            "estimated_costs": self.estimated_costs,
            "risk_buffer": self.risk_buffer,
            "net_edge": self.net_edge,
            "capital_required": self.capital_required,
            "estimated_margin": self.estimated_margin,
            "liquidity_score": self.liquidity_score,
            "fill_probability": self.fill_probability,
            "confidence_score": self.confidence_score,
            "opportunity_score": self.opportunity_score,
            "status": self.status.value,
            "cost_breakdown": self.cost_breakdown,
            "legs": self.legs,
            "metadata": self.metadata,
            "rejection_reason": self.rejection_reason,
        }
