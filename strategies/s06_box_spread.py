
"""
S06 - Box Spread Arbitrage Strategy
India Arbitrage Lab

Research / paper analysis only.
Live trading is disabled.

Long Box:
    Buy Lower Strike Call
    Sell Higher Strike Call
    Buy Higher Strike Put
    Sell Lower Strike Put

Box payoff at expiry:
    Higher Strike - Lower Strike

Theoretical Box Value:
    (Higher Strike - Lower Strike) * exp(-r * T)

Long Box Edge:
    Theoretical Box Value - Actual Box Cost

Reverse Box Edge:
    Actual Box Credit - Theoretical Box Value

Required columns:
    datetime
    symbol
    lower_strike
    higher_strike
    call_lower_price
    call_higher_price
    put_lower_price
    put_higher_price
    expiry_date

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


class BoxSpreadStrategy(BaseStrategy):
    """
    S06 - Box Spread Strategy

    Detects potential mispricing in four-leg box spreads by comparing
    observed option prices with theoretical discounted box value.

    This strategy is research-only and does not execute orders.
    """

    STRATEGY_ID = "S06"
    STRATEGY_NAME = "Box Spread"

    REQUIRED_COLUMNS = [
        "datetime",
        "symbol",
        "lower_strike",
        "higher_strike",
        "call_lower_price",
        "call_higher_price",
        "put_lower_price",
        "put_higher_price",
        "expiry_date",
    ]

    def __init__(
        self,
        risk_free_rate: float = 0.06,
        min_edge_per_unit: float = 1.00,
        risk_buffer_percent: float = 0.10,
        default_lot_size: int = 1,
        enabled: bool = True,
    ) -> None:

        self.risk_free_rate = float(risk_free_rate)
        self.min_edge_per_unit = float(min_edge_per_unit)
        self.risk_buffer_percent = float(risk_buffer_percent)
        self.default_lot_size = int(default_lot_size)
        self.enabled = bool(enabled)

        self._validate_config()

    # --------------------------------------------------
    # CONFIG VALIDATION
    # --------------------------------------------------

    def _validate_config(self) -> None:

        if self.risk_free_rate <= -1:
            raise ValueError("Risk-free rate must be greater than -1.")

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
                "Evaluates four-leg box spreads against theoretical "
                "discounted payoff."
            ),
            "enabled": self.enabled,
            "research_only": True,
            "paper_trading_only": True,
            "live_trading_enabled": False,
            "required_columns": self.REQUIRED_COLUMNS,
        }

    # --------------------------------------------------
    # DATE CONVERSION
    # --------------------------------------------------

    @staticmethod
    def _to_datetime(value: Any) -> datetime:

        if isinstance(value, datetime):
            return value

        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())

        converted = pd.to_datetime(value, errors="coerce")

        if pd.isna(converted):
            raise ValueError(f"Invalid date: {value}")

        return converted.to_pydatetime()

    @staticmethod
    def _time_to_expiry(
        current_datetime: Any,
        expiry_date: Any,
    ) -> float:

        current_dt = BoxSpreadStrategy._to_datetime(
            current_datetime
        )

        expiry_dt = BoxSpreadStrategy._to_datetime(
            expiry_date
        )

        seconds_remaining = (
            expiry_dt - current_dt
        ).total_seconds()

        if seconds_remaining <= 0:
            return 0.0

        seconds_per_year = 365.0 * 24.0 * 60.0 * 60.0

        return seconds_remaining / seconds_per_year

    # --------------------------------------------------
    # THEORETICAL BOX VALUE
    # --------------------------------------------------

    def calculate_theoretical_box_value(
        self,
        lower_strike: float,
        higher_strike: float,
        time_to_expiry: float,
    ) -> float:
        """
        Calculates discounted fixed box payoff.

        Formula:
            Box Payoff = Higher Strike - Lower Strike

            Theoretical Box Value =
                Box Payoff * exp(-r * T)
        """

        strike_width = higher_strike - lower_strike

        exponent = -self.risk_free_rate * time_to_expiry

        try:
            discount_factor = math.exp(exponent)
        except OverflowError as exc:
            raise ValueError("Box discount calculation overflow.") from exc

        theoretical_value = strike_width * discount_factor

        if not math.isfinite(theoretical_value):
            raise ValueError("Invalid theoretical box value.")

        return theoretical_value

    # --------------------------------------------------
    # ACTUAL LONG BOX COST
    # --------------------------------------------------

    @staticmethod
    def calculate_long_box_cost(
        call_lower_price: float,
        call_higher_price: float,
        put_lower_price: float,
        put_higher_price: float,
    ) -> float:
        """
        Long Box Cost:

            Buy Lower Call
            Sell Higher Call
            Buy Higher Put
            Sell Lower Put

        Net cost:
            C_low - C_high + P_high - P_low
        """

        return (
            call_lower_price
            - call_higher_price
            + put_higher_price
            - put_lower_price
        )

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
            symbol = str(row["symbol"])

            lower_strike = float(row["lower_strike"])
            higher_strike = float(row["higher_strike"])

            call_lower_price = float(row["call_lower_price"])
            call_higher_price = float(row["call_higher_price"])

            put_lower_price = float(row["put_lower_price"])
            put_higher_price = float(row["put_higher_price"])

            expiry_date = row["expiry_date"]

            # ------------------------------------------
            # Validate strike prices
            # ------------------------------------------

            if lower_strike <= 0 or higher_strike <= 0:
                return None

            if higher_strike <= lower_strike:
                return None

            # ------------------------------------------
            # Validate option prices
            # ------------------------------------------

            option_prices = [
                call_lower_price,
                call_higher_price,
                put_lower_price,
                put_higher_price,
            ]

            if not all(
                math.isfinite(price)
                for price in option_prices
            ):
                return None

            if any(price < 0 for price in option_prices):
                return None

            # ------------------------------------------
            # Time to expiry
            # ------------------------------------------

            time_to_expiry = self._time_to_expiry(
                current_datetime,
                expiry_date,
            )

            if time_to_expiry <= 0:
                return None

            # ------------------------------------------
            # Theoretical box value
            # ------------------------------------------

            theoretical_box_value = (
                self.calculate_theoretical_box_value(
                    lower_strike,
                    higher_strike,
                    time_to_expiry,
                )
            )

            # ------------------------------------------
            # Actual long box cost
            # ------------------------------------------

            actual_long_box_cost = (
                self.calculate_long_box_cost(
                    call_lower_price,
                    call_higher_price,
                    put_lower_price,
                    put_higher_price,
                )
            )

            # ------------------------------------------
            # Mispricing / Edge
            # ------------------------------------------

            edge_difference = (
                theoretical_box_value
                - actual_long_box_cost
            )

            gross_edge_per_unit = abs(edge_difference)

            if (
                gross_edge_per_unit
                < self.min_edge_per_unit
            ):
                return None

            # ------------------------------------------
            # Direction
            # ------------------------------------------

            if edge_difference > 0:

                direction = "LONG_BOX"
                trade_bias = "BUY_LONG_BOX_RESEARCH"

            else:

                direction = "REVERSE_BOX"
                trade_bias = "SELL_OR_REVERSE_BOX_RESEARCH"

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

            estimated_costs_per_unit = float(
                row.get(
                    "estimated_costs_per_unit",
                    0.0,
                )
            )

            if (
                not math.isfinite(estimated_costs_per_unit)
                or estimated_costs_per_unit < 0
            ):
                return None

            total_costs = (
                estimated_costs_per_unit * lot_size
            )

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
            # Liquidity / Fill probability
            # ------------------------------------------

            liquidity_score = float(
                row.get("liquidity_score", 0.0)
            )

            fill_probability = float(
                row.get("fill_probability", 0.0)
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
                    estimated_costs_per_unit
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
                "costs_are_estimates": True,
            }

            # ------------------------------------------
            # Four option legs
            # ------------------------------------------

            if direction == "LONG_BOX":

                legs = [
                    {
                        "instrument": "CALL",
                        "action": "BUY",
                        "strike": lower_strike,
                        "price": call_lower_price,
                    },
                    {
                        "instrument": "CALL",
                        "action": "SELL",
                        "strike": higher_strike,
                        "price": call_higher_price,
                    },
                    {
                        "instrument": "PUT",
                        "action": "BUY",
                        "strike": higher_strike,
                        "price": put_higher_price,
                    },
                    {
                        "instrument": "PUT",
                        "action": "SELL",
                        "strike": lower_strike,
                        "price": put_lower_price,
                    },
                ]

            else:

                legs = [
                    {
                        "instrument": "CALL",
                        "action": "SELL",
                        "strike": lower_strike,
                        "price": call_lower_price,
                    },
                    {
                        "instrument": "CALL",
                        "action": "BUY",
                        "strike": higher_strike,
                        "price": call_higher_price,
                    },
                    {
                        "instrument": "PUT",
                        "action": "SELL",
                        "strike": higher_strike,
                        "price": put_higher_price,
                    },
                    {
                        "instrument": "PUT",
                        "action": "BUY",
                        "strike": lower_strike,
                        "price": put_lower_price,
                    },
                ]

            for leg in legs:
                leg["symbol"] = symbol
                leg["expiry"] = str(expiry_date)
                leg["quantity"] = lot_size
                leg["research_only"] = True

            # ------------------------------------------
            # Metadata
            # ------------------------------------------

            metadata = {
                "strategy_id": self.STRATEGY_ID,
                "strategy_name": self.STRATEGY_NAME,
                "direction": direction,
                "trade_bias": trade_bias,
                "lower_strike": lower_strike,
                "higher_strike": higher_strike,
                "strike_width": higher_strike - lower_strike,
                "call_lower_price": call_lower_price,
                "call_higher_price": call_higher_price,
                "put_lower_price": put_lower_price,
                "put_higher_price": put_higher_price,
                "actual_long_box_cost": actual_long_box_cost,
                "theoretical_box_value": theoretical_box_value,
                "edge_difference": edge_difference,
                "gross_edge_per_unit": gross_edge_per_unit,
                "time_to_expiry_years": time_to_expiry,
                "risk_free_rate": self.risk_free_rate,
                "lot_size": lot_size,
                "research_only": True,
                "paper_trading_only": True,
                "live_trading_allowed": False,
                "four_legs_required": True,
                "simultaneous_fill_required": True,
                "charges_verified": False,
            }

            # ------------------------------------------
            # Opportunity object
            # ------------------------------------------

            opportunity = Opportunity(
                strategy_id=self.STRATEGY_ID,
                symbol=symbol,
                market="INDIAN_DERIVATIVES",
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
                "S06 missing required columns: "
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
           
