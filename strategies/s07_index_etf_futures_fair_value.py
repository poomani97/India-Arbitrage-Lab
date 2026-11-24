
"""
S07 - Index / ETF / Futures Fair Value Strategy
India Arbitrage Lab

Purpose:
    Research fair-value deviations between:
        1. Index-derived ETF fair value
        2. Actual ETF market price
        3. Theoretical futures fair value
        4. Actual futures market price

Research / paper trading only.
Live execution is disabled.

Required columns:
    datetime
    symbol
    index_price
    etf_price
    futures_price
    expiry_date
    etf_conversion_factor

Optional columns:
    annual_carry_rate
    estimated_costs_per_unit
    lot_size
    estimated_capital_required
    estimated_margin
    liquidity_score
    fill_probability

Important:
    ETF conversion factor must be supplied from verified instrument data.
    This module does not automatically fetch live market prices.
"""

from __future__ import annotations

import math
from datetime import datetime, date
from typing import Any, Dict, List

import pandas as pd

from strategies.base_strategy import BaseStrategy
from models.opportunity import Opportunity


class IndexETFFuturesFairValueStrategy(BaseStrategy):
    """S07 - Index / ETF / Futures fair-value research engine."""

    STRATEGY_ID = "S07"
    STRATEGY_NAME = "Index ETF Futures Fair Value"

    REQUIRED_COLUMNS = [
        "datetime",
        "symbol",
        "index_price",
        "etf_price",
        "futures_price",
        "expiry_date",
        "etf_conversion_factor",
    ]

    def __init__(
        self,
        default_carry_rate: float = 0.06,
        min_edge_per_unit: float = 1.0,
        risk_buffer_percent: float = 0.10,
        default_lot_size: int = 1,
        enabled: bool = True,
    ) -> None:

        self.default_carry_rate = float(default_carry_rate)
        self.min_edge_per_unit = float(min_edge_per_unit)
        self.risk_buffer_percent = float(risk_buffer_percent)
        self.default_lot_size = int(default_lot_size)
        self.enabled = bool(enabled)

        self._validate_config()

    # --------------------------------------------------
    # CONFIG VALIDATION
    # --------------------------------------------------

    def _validate_config(self) -> None:

        if self.default_carry_rate <= -1:
            raise ValueError("Carry rate must be greater than -1.")

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
                "Analyzes index-derived ETF fair value and "
                "theoretical futures fair value against market prices."
            ),
            "enabled": self.enabled,
            "research_only": True,
            "paper_trading_only": True,
            "live_trading_enabled": False,
            "required_columns": self.REQUIRED_COLUMNS,
        }

    # --------------------------------------------------
    # DATE HELPERS
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

    @classmethod
    def _calculate_time_to_expiry(
        cls,
        current_datetime: Any,
        expiry_date: Any,
    ) -> float:

        current_dt = cls._to_datetime(current_datetime)
        expiry_dt = cls._to_datetime(expiry_date)

        seconds_remaining = (
            expiry_dt - current_dt
        ).total_seconds()

        if seconds_remaining <= 0:
            return 0.0

        seconds_per_year = 365.0 * 24.0 * 60.0 * 60.0

        return seconds_remaining / seconds_per_year

    # --------------------------------------------------
    # ETF FAIR VALUE
    # --------------------------------------------------

    @staticmethod
    def calculate_etf_fair_value(
        index_price: float,
        conversion_factor: float,
    ) -> float:
        """
        ETF Fair Value:

            Index Price * ETF Conversion Factor

        Conversion factor must be verified for the ETF.
        """

        if index_price <= 0:
            raise ValueError("Index price must be positive.")

        if conversion_factor <= 0:
            raise ValueError(
                "ETF conversion factor must be positive."
            )

        fair_value = index_price * conversion_factor

        if not math.isfinite(fair_value):
            raise ValueError("Invalid ETF fair value.")

        return fair_value

    # --------------------------------------------------
    # FUTURES FAIR VALUE
    # --------------------------------------------------

    @staticmethod
    def calculate_futures_fair_value(
        index_price: float,
        carry_rate: float,
        time_to_expiry: float,
    ) -> float:
        """
        Simplified theoretical futures fair value:

            Futures Fair Value = Index * exp(r * T)

        Dividend yield and other market-specific adjustments
        are not included in this simplified calculation.
        """

        if index_price <= 0:
            raise ValueError("Index price must be positive.")

        if carry_rate <= -1:
            raise ValueError("Carry rate must be greater than -1.")

        exponent = carry_rate * time_to_expiry

        try:
            theoretical_price = (
                index_price * math.exp(exponent)
            )
        except OverflowError as exc:
            raise ValueError(
                "Futures fair-value calculation overflow."
            ) from exc

        if not math.isfinite(theoretical_price):
            raise ValueError("Invalid futures fair value.")

        return theoretical_price

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

            index_price = float(row["index_price"])
            etf_price = float(row["etf_price"])
            futures_price = float(row["futures_price"])

            conversion_factor = float(
                row["etf_conversion_factor"]
            )

            expiry_date = row["expiry_date"]

            # ------------------------------------------
            # Basic validation
            # ------------------------------------------

            prices = [
                index_price,
                etf_price,
                futures_price,
                conversion_factor,
            ]

            if not all(
                math.isfinite(value)
                for value in prices
            ):
                return None

            if any(value <= 0 for value in prices):
                return None

            # ------------------------------------------
            # Time to expiry
            # ------------------------------------------

            time_to_expiry = (
                self._calculate_time_to_expiry(
                    current_datetime,
                expiry_date,
                )
            )

            if time_to_expiry <= 0:
                return None

            # ------------------------------------------
            # Carry rate
            # ------------------------------------------

            carry_rate = float(
                row.get(
                    "annual_carry_rate",
                    self.default_carry_rate,
                )
            )

            if (
                not math.isfinite(carry_rate)
                or carry_rate <= -1
            ):
                return None

            # ------------------------------------------
            # Fair value calculations
            # ------------------------------------------

            etf_fair_value = (
                self.calculate_etf_fair_value(
                    index_price,
                    conversion_factor,
                )
            )

            futures_fair_value = (
                self.calculate_futures_fair_value(
                    index_price,
                    carry_rate,
                    time_to_expiry,
                )
            )

            # ------------------------------------------
            # ETF mispricing
            # ------------------------------------------

            etf_deviation = (
                etf_fair_value - etf_price
            )

            # ------------------------------------------
            # Futures mispricing
            # ------------------------------------------

            futures_deviation = (
                futures_fair_value - futures_price
            )

            # ------------------------------------------
            # Relative ETF / Futures deviation
            # ------------------------------------------

            normalized_futures_value = (
                futures_fair_value * conversion_factor
            )

            normalized_futures_market_price = (
                futures_price * conversion_factor
            )

            relative_market_deviation = (
                etf_price
                - normalized_futures_market_price
            )

            # ------------------------------------------
            # Select strongest opportunity
            # ------------------------------------------

            candidates = [
                (
                    "ETF_MISPRICING",
                etf_deviation,
                ),
                (
                    "FUTURES_MISPRICING",
                futures_deviation,
                ),
                (
                    "ETF_FUTURES_RELATIVE_VALUE",
                -relative_market_deviation,
                ),
            ]

            opportunity_type, edge_per_unit = max(
                candidates,
                key=lambda item: abs(item[1]),
            )

            gross_edge_per_unit = abs(edge_per_unit)

            if (
                gross_edge_per_unit
                < self.min_edge_per_unit
            ):
                return None

            # ------------------------------------------
            # Direction
            # ------------------------------------------

            if edge_per_unit > 0:
                direction = "BUY_UNDERVALUED"
            else:
                direction = "SELL_OVERVALUED"

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
            # Capital
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
            # Research legs
            # ------------------------------------------

            if direction == "BUY_UNDERVALUED":

                legs = [
                    {
                        "instrument": "ETF",
                        "action": "BUY",
                        "symbol": symbol,
                        "market_price": etf_price,
                        "fair_value": etf_fair_value,
                        "quantity": lot_size,
                    }
                ]

            else:

                legs = [
                    {
                        "instrument": "ETF",
                        "action": "SELL",
                        "symbol": symbol,
                        "market_price": etf_price,
                        "fair_value": etf_fair_value,
                        "quantity": lot_size,
                    }
                ]

            # ------------------------------------------
            # Metadata
            # ------------------------------------------

            metadata = {
                "strategy_id": self.STRATEGY_ID,
                "strategy_name": self.STRATEGY_NAME,
                "opportunity_type": opportunity_type,
                "direction": direction,
                "index_price": index_price,
                "etf_market_price": etf_price,
                "etf_fair_value": etf_fair_value,
                "etf_deviation": etf_deviation,
                "futures_market_price": futures_price,
                "futures_fair_value": futures_fair_value,
                "futures_deviation": futures_deviation,
                "normalized_futures_value": (
                    normalized_futures_value
                ),
                "normalized_futures_market_price": (
                    normalized_futures_market_price
                ),
                "relative_market_deviation": (
                    relative_market_deviation
                ),
                "conversion_factor": conversion_factor,
                "annual_carry_rate": carry_rate,
                "time_to_expiry_years": time_to_expiry,
                "lot_size": lot_size,
                "research_only": True,
                "paper_trading_only": True,
                "live_trading_allowed": False,
                "dividend_adjustment_included": False,
                "conversion_factor_verified": False,
            }

            # ------------------------------------------
            # Opportunity object
            # ------------------------------------------

            opportunity = Opportunity(
                strategy_id=self.STRATEGY_ID,
                symbol=symbol,
                market="INDIAN_MARKET",
                opportunity_type=opportunity_type,
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
                "S07 missing required columns: "
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
          
