
"""
S10 - Event Implied vs Realized Move Strategy
India Arbitrage Lab

Purpose:
    Compare the movement implied by options pricing before an event
    with the actual underlying movement observed after the event.

Research / backtesting only.
Live execution is disabled.
This is a retrospective event-analysis strategy.

It does NOT create a forward arbitrage opportunity from
future realized movement that is not yet known.

Required columns:
    datetime
    symbol
    event_name
    underlying_price_before_event
    underlying_price_after_event
    implied_move_percent

Optional columns:
    estimated_costs
    lot_size
    estimated_capital_required
    estimated_margin
    liquidity_score
    fill_probability

Interpretation:
    Actual absolute move > implied move:
        Event produced a larger move than options implied.

    Actual absolute move < implied move:
        Event produced a smaller move than options implied.

    Actual move approximately equals implied move:
        Event move was close to options expectation.

Note:
    This module is retrospective research only.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

import pandas as pd

from strategies.base_strategy import BaseStrategy
from models.opportunity import Opportunity


class EventImpliedVsRealizedMoveStrategy(BaseStrategy):
    """S10 - Event implied vs realized movement analysis."""

    STRATEGY_ID = "S10"
    STRATEGY_NAME = "Event Implied vs Realized Move"

    REQUIRED_COLUMNS = [
        "datetime",
        "symbol",
        "event_name",
        "underlying_price_before_event",
        "underlying_price_after_event",
        "implied_move_percent",
    ]

    def __init__(
        self,
        minimum_deviation_percent: float = 1.0,
        risk_buffer_percent: float = 0.10,
        default_lot_size: int = 1,
        enabled: bool = True,
    ) -> None:
        self.minimum_deviation_percent = float(
            minimum_deviation_percent
        )
        self.risk_buffer_percent = float(
            risk_buffer_percent
        )
        self.default_lot_size = int(
            default_lot_size
        )
        self.enabled = bool(enabled)
        self._validate_config()

    # --------------------------------------------------
    # CONFIG VALIDATION
    # --------------------------------------------------

    def _validate_config(self) -> None:
        if self.minimum_deviation_percent < 0:
            raise ValueError(
                "Minimum deviation cannot be negative."
            )

        if self.risk_buffer_percent < 0:
            raise ValueError(
                "Risk buffer cannot be negative."
            )

        if self.default_lot_size <= 0:
            raise ValueError(
                "Default lot size must be positive."
            )

    # --------------------------------------------------
    # METADATA
    # --------------------------------------------------

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.STRATEGY_ID,
            "strategy_name": self.STRATEGY_NAME,
            "description": (
                "Compares options-implied event movement "
                "with realized underlying movement after the event."
            ),
            "enabled": self.enabled,
            "research_only": True,
            "retrospective_analysis": True,
            "paper_trading_only": True,
            "live_trading_enabled": False,
            "required_columns": self.REQUIRED_COLUMNS,
        }

    # --------------------------------------------------
    # IMPLIED MOVE CALCULATION
    # --------------------------------------------------

    @staticmethod
    def calculate_implied_move_percent(
        implied_move_percent: float,
    ) -> float:

        if not math.isfinite(implied_move_percent):
            raise ValueError(
                "Implied move must be finite."
            )

        if implied_move_percent < 0:
            raise ValueError(
                "Implied move cannot be negative."
            )

        return implied_move_percent

    # --------------------------------------------------
    # REALIZED MOVE CALCULATION
    # --------------------------------------------------

    @staticmethod
    def calculate_realized_move_percent(
        price_before: float,
        price_after: float,
    ) -> float:
        """
        Absolute realized movement:
            abs(After - Before) / Before * 100
        """

        if price_before <= 0 or price_after <= 0:
            raise ValueError(
                "Underlying prices must be positive."
            )

        realized_move = (
            abs(price_after - price_before)
            / price_before
        ) * 100.0

        if not math.isfinite(realized_move):
            raise ValueError(
                "Invalid realized move."
            )

        return realized_move

    # --------------------------------------------------
    # SINGLE ROW ANALYSIS
    # --------------------------------------------------

    def analyze_row(
        self,
        row: Dict[str, Any],
    ) -> Any:

        if not self.enabled:
            return None

        try:
            timestamp = row["datetime"]

            symbol = str(
                row["symbol"]
            ).strip()

            event_name = str(
                row["event_name"]
            ).strip()

            price_before = float(
                row["underlying_price_before_event"]
            )

            price_after = float(
                row["underlying_price_after_event"]
            )

            implied_move_percent = float(
                row["implied_move_percent"]
            )

            # ------------------------------------------
            # Validation
            # ------------------------------------------

            if not symbol or not event_name:
                return None

            numeric_values = [
                price_before,
                price_after,
                implied_move_percent,
            ]

            if not all(
                math.isfinite(value)
                for value in numeric_values
            ):
                return None

            if price_before <= 0 or price_after <= 0:
                return None

            if implied_move_percent < 0:
                return None

            # ------------------------------------------
            # Implied move
            # ------------------------------------------

            implied_move = (
                self.calculate_implied_move_percent(
                    implied_move_percent
                )
            )

            # ------------------------------------------
            # Realized move
            # ------------------------------------------

            realized_move = (
                self.calculate_realized_move_percent(
                    price_before,
                    price_after,
                )
            )

            # ------------------------------------------
            # Implied vs Realized deviation
            # ------------------------------------------

            deviation_percent = (
                realized_move - implied_move
            )

            absolute_deviation_percent = abs(
                deviation_percent
            )

            # ------------------------------------------
            # Minimum deviation filter
            # ------------------------------------------

            if (
                absolute_deviation_percent
                < self.minimum_deviation_percent
            ):
                return None

            # ------------------------------------------
            # Event interpretation
            # ------------------------------------------

            if deviation_percent > 0:
                event_result = (
                    "REALIZED_MOVE_EXCEEDED_IMPLIED"
                )

                interpretation = (
                    "Actual movement exceeded implied movement."
                )

            elif deviation_percent < 0:
                event_result = (
                    "REALIZED_MOVE_BELOW_IMPLIED"
                )

                interpretation = (
                    "Actual movement was below implied movement."
                )

            else:
                event_result = (
                    "REALIZED_MOVE_MATCHED_IMPLIED"
                )

                interpretation = (
                    "Actual movement matched implied movement."
                )

            # ------------------------------------------
            # Lot size
            # ------------------------------------------

            lot_size = int(
                row.get(
                    "lot_size",
                    self.default_lot_size,
                )
            )

            if lot_size <= 0:
                lot_size = self.default_lot_size

            # ------------------------------------------
            # Movement difference
            # ------------------------------------------

            gross_edge_per_unit = (
                absolute_deviation_percent
            )

            gross_edge = (
                gross_edge_per_unit * lot_size
            )

            # ------------------------------------------
            # Estimated costs
            # ------------------------------------------

            estimated_costs = float(
                row.get(
                    "estimated_costs",
                    0.0,
                )
            )

            if (
                not math.isfinite(estimated_costs)
                or estimated_costs < 0
            ):
                return None

            total_costs = (
                estimated_costs * lot_size
            )

            # ------------------------------------------
            # Risk buffer
            # ------------------------------------------

            risk_buffer = (
                gross_edge * self.risk_buffer_percent
            )

            # ------------------------------------------
            # Net research value
            # ------------------------------------------

            net_edge = (
                gross_edge
                - total_costs
                - risk_buffer
            )

            # ------------------------------------------
            # Capital / Margin
            # ------------------------------------------

            capital_required = float(
                row.get(
                    "estimated_capital_required",
                    0.0,
                )
            )

            estimated_margin = float(
                row.get(
                    "estimated_margin",
                    capital_required,
                )
            )

            if (
                not math.isfinite(capital_required)
                or capital_required < 0
            ):
                capital_required = 0.0

            if (
                not math.isfinite(estimated_margin)
                or estimated_margin < 0
            ):
                estimated_margin = 0.0

            # ------------------------------------------
            # Liquidity / Fill
            # ------------------------------------------

            liquidity_score = float(
                row.get(
                    "liquidity_score",
                    0.0,
                )
            )

            fill_probability = float(
                row.get(
                    "fill_probability",
                    0.0,
                )
            )

            liquidity_score = max(
                0.0,
                min(100.0, liquidity_score),
            )

            fill_probability = max(
                0.0,
                min(1.0, fill_probability),
            )

            confidence_score = (
                liquidity_score * fill_probability
            )

            # ------------------------------------------
            # Cost breakdown
            # ------------------------------------------

            cost_breakdown = {
                "estimated_costs_per_unit": (
                    estimated_costs
                ),
                "estimated_total_costs": (
                    total_costs
                ),
                "risk_buffer_percent": (
                    self.risk_buffer_percent
                ),
                "risk_buffer_amount": (
                    risk_buffer
                ),
                "charges_verified": False,
            }

            # ------------------------------------------
            # Research legs
            # ------------------------------------------

            legs = [
                {
                    "instrument": symbol,
                    "action": "EVENT_RESEARCH",
                    "event_name": event_name,
                    "price_before_event": price_before,
                    "price_after_event": price_after,
                    "quantity": lot_size,
                    "execution_enabled": False,
                }
            ]

            # ------------------------------------------
            # Metadata
            # ------------------------------------------

            metadata = {
                "strategy_id": self.STRATEGY_ID,
                "strategy_name": self.STRATEGY_NAME,
                "symbol": symbol,
                "event_name": event_name,
                "event_timestamp": str(timestamp),
                "underlying_price_before_event": (
                    price_before
                ),
                "underlying_price_after_event": (
                    price_after
                ),
                "implied_move_percent": implied_move,
                "realized_move_percent": (
                    realized_move
                ),
                "deviation_percent": deviation_percent,
                "absolute_deviation_percent": (
                    absolute_deviation_percent
                ),
                "event_result": event_result,
                "interpretation": interpretation,
                "lot_size": lot_size,
                "research_only": True,
                "retrospective_analysis": True,
                "paper_trading_only": True,
                "live_trading_allowed": False,
                "execution_enabled": False,
                "future_data_required": True,
            }

            # ------------------------------------------
            # Opportunity object
            # ------------------------------------------

            opportunity = Opportunity(
                strategy_id=self.STRATEGY_ID,
                symbol=symbol,
                market="INDIAN_EVENT_RESEARCH",
                opportunity_type=event_result,
                gross_edge=gross_edge,
                estimated_costs=total_costs,
                risk_buffer=risk_buffer,
                net_edge=net_edge,
                capital_required=capital_required,
                estimated_margin=estimated_margin,
                liquidity_score=liquidity_score,
                fill_probability=fill_probability,
                confidence_score=confidence_score,
                cost_breakdown=cost_breakdown,
                legs=legs,
                metadata=metadata,
            )

            return opportunity

        except (
            KeyError,
            TypeError,
            ValueError,
            OverflowError,
        ):
            return None

    # --------------------------------------------------
    # DATAFRAME SCAN
    # --------------------------------------------------

    def scan(
        self,
        data: pd.DataFrame,
    ) -> List[Opportunity]:

        if not self.enabled:
            return []

        if data is None or data.empty:
            return []

        missing_columns = [
            column
            for column in self.REQUIRED_COLUMNS
            if column not in data.columns
        ]

        if missing_columns:
            raise ValueError(
                "S10 missing required columns: "
                + ", ".join(missing_columns)
            )

        opportunities: List[Opportunity] = []

        for _, dataframe_row in data.iterrows():
            opportunity = self.analyze_row(
                dataframe_row.to_dict()
            )

            if opportunity is not None:
                opportunities.append(opportunity)

        return opportunities

    # --------------------------------------------------
    # SAFE SCAN
    # --------------------------------------------------

    def safe_scan(
        self,
        data: pd.DataFrame,
    ) -> List[Opportunity]:

        try:
            return self.scan(data)

        except (
            KeyError,
            TypeError,
            ValueError,
            OverflowError,
        ):
            return []
                
