
"""
S09 - Cross-Exchange Arbitrage Monitor (NSE vs BSE)
India Arbitrage Lab

Purpose:
    Compare the same instrument's prices between NSE and BSE.

Mode:
    Observation / research / paper only.
    Live trading is disabled.
    This strategy does not place orders.

Required columns:
    datetime
    symbol
    nse_price
    bse_price

Optional columns:
    estimated_costs_per_unit
    lot_size
    estimated_capital_required
    estimated_margin
    liquidity_score
    fill_probability

Important:
    NSE/BSE prices must be synchronized timestamps.
    Price differences may disappear before execution.
    This strategy is observation-only.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

import pandas as pd

from strategies.base_strategy import BaseStrategy
from models.opportunity import Opportunity


class CrossExchangeArbitrageStrategy(BaseStrategy):
    """S09 - NSE vs BSE price-difference observation engine."""

    STRATEGY_ID = "S09"
    STRATEGY_NAME = "Cross Exchange Arbitrage"

    REQUIRED_COLUMNS = [
        "datetime",
        "symbol",
        "nse_price",
        "bse_price",
    ]

    def __init__(
        self,
        min_edge_per_unit: float = 0.50,
        risk_buffer_percent: float = 0.15,
        default_lot_size: int = 1,
        enabled: bool = True,
    ) -> None:
        self.min_edge_per_unit = float(min_edge_per_unit)
        self.risk_buffer_percent = float(risk_buffer_percent)
        self.default_lot_size = int(default_lot_size)
        self.enabled = bool(enabled)
        self._validate_config()

    # --------------------------------------------------
    # CONFIG VALIDATION
    # --------------------------------------------------

    def _validate_config(self) -> None:
        if self.min_edge_per_unit < 0:
            raise ValueError("Minimum edge cannot be negative.")

        if self.risk_buffer_percent < 0:
            raise ValueError("Risk buffer cannot be negative.")

        if self.default_lot_size <= 0:
            raise ValueError("Default lot size must be positive.")

    # --------------------------------------------------
    # METADATA
    # --------------------------------------------------

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.STRATEGY_ID,
            "strategy_name": self.STRATEGY_NAME,
            "description": (
                "Monitors price differences for the same instrument "
                "between NSE and BSE."
            ),
            "enabled": self.enabled,
            "research_only": True,
            "observation_only": True,
            "paper_trading_only": True,
            "live_trading_enabled": False,
            "order_execution_enabled": False,
            "required_columns": self.REQUIRED_COLUMNS,
        }

    # --------------------------------------------------
    # PRICE DIFFERENCE
    # --------------------------------------------------

    @staticmethod
    def calculate_price_difference(
        nse_price: float,
        bse_price: float,
    ) -> float:
        """
        Difference:
            BSE Price - NSE Price

        Positive:
            BSE is higher than NSE.

        Negative:
            NSE is higher than BSE.
        """
        return bse_price - nse_price

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
            symbol = str(row["symbol"]).strip()
            nse_price = float(row["nse_price"])
            bse_price = float(row["bse_price"])

            # ------------------------------------------
            # Validation
            # ------------------------------------------

            if not symbol:
                return None

            if not all(
                math.isfinite(value)
                for value in [nse_price, bse_price]
            ):
                return None

            if nse_price <= 0 or bse_price <= 0:
                return None

            # ------------------------------------------
            # Price difference
            # ------------------------------------------

            price_difference = self.calculate_price_difference(
                nse_price,
                bse_price,
            )

            absolute_difference = abs(price_difference)

            # ------------------------------------------
            # Difference percentage
            # ------------------------------------------

            reference_price = (
                (nse_price + bse_price) / 2.0
            )

            difference_percent = (
                absolute_difference / reference_price
            ) * 100.0

            # ------------------------------------------
            # Minimum threshold
            # ------------------------------------------

            if absolute_difference < self.min_edge_per_unit:
                return None

            # ------------------------------------------
            # Exchange direction
            # ------------------------------------------

            if price_difference > 0:
                cheaper_exchange = "NSE"
                expensive_exchange = "BSE"
                observation = "NSE_LOWER_BSE_HIGHER"

            elif price_difference < 0:
                cheaper_exchange = "BSE"
                expensive_exchange = "NSE"
                observation = "BSE_LOWER_NSE_HIGHER"

            else:
                return None

            # ------------------------------------------
            # Quantity
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
            # Gross difference value
            # ------------------------------------------

            gross_edge = absolute_difference * lot_size

            # ------------------------------------------
            # Risk buffer
            # ------------------------------------------

            risk_buffer = (
                gross_edge * self.risk_buffer_percent
            )

            # ------------------------------------------
            # Estimated net edge
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
            # Liquidity / Fill estimates
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
                "estimated_costs_per_unit": costs_per_unit,
                "estimated_total_costs": total_costs,
                "risk_buffer_percent": (
                    self.risk_buffer_percent
                ),
                "risk_buffer_amount": risk_buffer,
                "charges_verified": False,
                "costs_are_estimates": True,
            }

            # ------------------------------------------
            # Observation legs
            # ------------------------------------------

            legs = [
                {
                    "instrument": symbol,
                    "exchange": cheaper_exchange,
                    "action": "BUY_OBSERVATION",
                    "price": (
                        nse_price
                        if cheaper_exchange == "NSE"
                        else bse_price
                    ),
                    "quantity": lot_size,
                    "execution_enabled": False,
                },
                {
                    "instrument": symbol,
                    "exchange": expensive_exchange,
                    "action": "SELL_OBSERVATION",
                    "price": (
                        bse_price
                        if expensive_exchange == "BSE"
                        else nse_price
                    ),
                    "quantity": lot_size,
                    "execution_enabled": False,
                },
            ]

            # ------------------------------------------
            # Metadata
            # ------------------------------------------

            metadata = {
                "strategy_id": self.STRATEGY_ID,
                "strategy_name": self.STRATEGY_NAME,
                "observation": observation,
                "symbol": symbol,
                "timestamp": str(timestamp),
                "nse_price": nse_price,
                "bse_price": bse_price,
                "price_difference": price_difference,
                "absolute_difference": absolute_difference,
                "difference_percent": difference_percent,
                "cheaper_exchange": cheaper_exchange,
                "expensive_exchange": expensive_exchange,
                "lot_size": lot_size,
                "research_only": True,
                "observation_only": True,
                "paper_trading_only": True,
                "live_trading_allowed": False,
                "execution_enabled": False,
                "simultaneous_execution_required": True,
                "exchange_fees_verified": False,
                "timestamp_synchronization_verified": False,
            }

            # ------------------------------------------
            # Opportunity object
            # ------------------------------------------

            opportunity = Opportunity(
                strategy_id=self.STRATEGY_ID,
                symbol=symbol,
                market="NSE_BSE_CROSS_EXCHANGE",
                opportunity_type=observation,
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
                "S09 missing required columns: "
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
            
