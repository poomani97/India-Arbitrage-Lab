
"""
S08 - Index Relative Value Strategy
India Arbitrage Lab

Research / paper trading only.
Live execution is disabled.

Purpose:
    Compare two related indices or market instruments and
    detect relative-value deviations.

Spread:
    Spread = Price A - Price B

Spread Deviation:
    Current Spread - Historical Mean Spread

Z-Score:
    (Current Spread - Historical Mean) / Historical Std

When spread is above its historical mean:
    SELL A / BUY B (research signal)

When spread is below its historical mean:
    BUY A / SELL B (research signal)

Required columns:
    datetime
    symbol_a
    symbol_b
    price_a
    price_b
    historical_spread_mean
    historical_spread_std

Optional columns:
    estimated_costs_per_unit
    lot_size
    estimated_capital_required
    estimated_margin
    liquidity_score
    fill_probability
"""

from __future__ import annotations

import math
from datetime import datetime, date
from typing import Any, Dict, List

import pandas as pd

from strategies.base_strategy import BaseStrategy
from models.opportunity import Opportunity


class IndexRelativeValueStrategy(BaseStrategy):
    """S08 - Relative-value strategy for related indices/instruments."""

    STRATEGY_ID = "S08"
    STRATEGY_NAME = "Index Relative Value"

    REQUIRED_COLUMNS = [
        "datetime",
        "symbol_a",
        "symbol_b",
        "price_a",
        "price_b",
        "historical_spread_mean",
        "historical_spread_std",
    ]

    def __init__(
        self,
        min_zscore: float = 2.0,
        min_edge_per_unit: float = 1.0,
        risk_buffer_percent: float = 0.10,
        default_lot_size: int = 1,
        enabled: bool = True,
    ) -> None:

        self.min_zscore = float(min_zscore)
        self.min_edge_per_unit = float(min_edge_per_unit)
        self.risk_buffer_percent = float(risk_buffer_percent)
        self.default_lot_size = int(default_lot_size)
        self.enabled = bool(enabled)

        self._validate_config()

    # --------------------------------------------------
    # CONFIG VALIDATION
    # --------------------------------------------------

    def _validate_config(self) -> None:

        if self.min_zscore <= 0:
            raise ValueError("Minimum Z-score must be positive.")

        if self.min_edge_per_unit < 0:
            raise ValueError("Minimum edge cannot be negative.")

        if self.risk_buffer_percent < 0:
            raise ValueError("Risk buffer cannot be negative.")

        if self.default_lot_size <= 0:
            raise ValueError("Lot size must be positive.")

    # --------------------------------------------------
    # METADATA
    # --------------------------------------------------

    def get_metadata(self) -> Dict[str, Any]:

        return {
            "strategy_id": self.STRATEGY_ID,
            "strategy_name": self.STRATEGY_NAME,
            "description": (
                "Detects relative-value deviations between two "
                "related indices or instruments."
            ),
            "enabled": self.enabled,
            "research_only": True,
            "paper_trading_only": True,
            "live_trading_enabled": False,
            "min_zscore": self.min_zscore,
            "required_columns": self.REQUIRED_COLUMNS,
        }

    # --------------------------------------------------
    # SPREAD CALCULATION
    # --------------------------------------------------

    @staticmethod
    def calculate_spread(
        price_a: float,
        price_b: float,
    ) -> float:

        return price_a - price_b

    # --------------------------------------------------
    # SPREAD DEVIATION
    # --------------------------------------------------

    @staticmethod
    def calculate_spread_deviation(
        current_spread: float,
        historical_mean: float,
    ) -> float:

        return current_spread - historical_mean

    # --------------------------------------------------
    # Z-SCORE
    # --------------------------------------------------

    @staticmethod
    def calculate_zscore(
        current_spread: float,
        historical_mean: float,
        historical_std: float,
    ) -> float:

        if historical_std <= 0:
            raise ValueError(
                "Historical spread standard deviation must be positive."
            )

        zscore = (
            current_spread - historical_mean
        ) / historical_std

        if not math.isfinite(zscore):
            raise ValueError("Invalid Z-score.")

        return zscore

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

            current_datetime = row["datetime"]

            symbol_a = str(row["symbol_a"]).strip()
            symbol_b = str(row["symbol_b"]).strip()

            price_a = float(row["price_a"])
            price_b = float(row["price_b"])

            historical_mean = float(
                row["historical_spread_mean"]
            )

            historical_std = float(
                row["historical_spread_std"]
            )

            # ------------------------------------------
            # Validation
            # ------------------------------------------

            if not symbol_a or not symbol_b:
                return None

            if symbol_a == symbol_b:
                return None

            numeric_values = [
                price_a,
                price_b,
                historical_mean,
                historical_std,
            ]

            if not all(
                math.isfinite(value)
                for value in numeric_values
            ):
                return None

            if price_a <= 0 or price_b <= 0:
                return None

            if historical_std <= 0:
                return None

            # ------------------------------------------
            # Spread
            # ------------------------------------------

            current_spread = (
                self.calculate_spread(
                    price_a,
                    price_b,
                )
            )

            spread_deviation = (
                self.calculate_spread_deviation(
                    current_spread,
                    historical_mean,
                )
            )

            zscore = (
                self.calculate_zscore(
                    current_spread,
                    historical_mean,
                    historical_std,
                )
            )

            # ------------------------------------------
            # Signal threshold
            # ------------------------------------------

            if abs(zscore) < self.min_zscore:
                return None

            # ------------------------------------------
            # Direction
            # ------------------------------------------

            if zscore > 0:

                direction = "SHORT_SPREAD"
                action_a = "SELL"
                action_b = "BUY"

            else:

                direction = "LONG_SPREAD"
                action_a = "BUY"
                action_b = "SELL"

            # ------------------------------------------
            # Edge estimation
            # ------------------------------------------

            gross_edge_per_unit = abs(
                spread_deviation
            )

            if (
                gross_edge_per_unit
                < self.min_edge_per_unit
            ):
                return None

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
            # Estimated costs
            # ------------------------------------------

            costs_per_unit = float(
                row.get(
                    "estimated_costs_per_unit",
                    0.0,
                )
            )

            if (
                not math.isfinite(costs_per_unit)
                or costs_per_unit < 0
            ):
                return None

            total_costs = costs_per_unit * lot_size

            # ------------------------------------------
            # Gross edge
            # ------------------------------------------

            gross_edge = (
                gross_edge_per_unit * lot_size
            )

            # ------------------------------------------
            # Risk buffer
            # ------------------------------------------

            risk_buffer = (
                gross_edge * self.risk_buffer_percent
            )

            # ------------------------------------------
            # Net edge
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
            # Liquidity / Fill Probability
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
                    costs_per_unit
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
            # Pair legs
            # ------------------------------------------

            legs = [
                {
                    "instrument": symbol_a,
                    "action": action_a,
                    "market_price": price_a,
                    "quantity": lot_size,
                },
                {
                    "instrument": symbol_b,
                    "action": action_b,
                    "market_price": price_b,
                    "quantity": lot_size,
                },
            ]

            # ------------------------------------------
            # Metadata
            # ------------------------------------------

            metadata = {
                "strategy_id": self.STRATEGY_ID,
                "strategy_name": self.STRATEGY_NAME,
                "direction": direction,
                "symbol_a": symbol_a,
                "symbol_b": symbol_b,
                "price_a": price_a,
                "price_b": price_b,
                "current_spread": current_spread,
                "historical_spread_mean": (
                    historical_mean
                ),
                "historical_spread_std": (
                    historical_std
                ),
                "spread_deviation": spread_deviation,
                "zscore": zscore,
                "min_zscore": self.min_zscore,
                "lot_size": lot_size,
                "research_only": True,
                "paper_trading_only": True,
                "live_trading_allowed": False,
                "hedge_ratio_used": 1.0,
                "hedge_ratio_calibrated": False,
                "historical_relationship_verified": False,
            }

            # ------------------------------------------
            # Opportunity
            # ------------------------------------------

            opportunity = Opportunity(
                strategy_id=self.STRATEGY_ID,
                symbol=f"{symbol_a}/{symbol_b}",
                market="INDIAN_INDEX_RELATIVE_VALUE",
                opportunity_type=direction,
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
                "S08 missing required columns: "
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
      
