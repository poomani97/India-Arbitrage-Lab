
"""
S05 - Synthetic Futures vs Actual Futures
India Arbitrage Lab

Research / paper analysis only.
Live trading is disabled.

Required columns:
datetime, symbol, spot_price, strike_price, call_price,
put_price, futures_price, expiry_date

Optional columns:
estimated_costs_per_unit, lot_size, estimated_capital_required,
estimated_margin, liquidity_score, fill_probability
"""

from __future__ import annotations

import math
from datetime import datetime, date
from typing import Any, Dict, List

import pandas as pd

from strategies.base_strategy import BaseStrategy
from models.opportunity import Opportunity


class SyntheticVsActualFuturesStrategy(BaseStrategy):

    STRATEGY_ID = "S05"
    STRATEGY_NAME = "Synthetic Futures vs Actual Futures"

    REQUIRED_COLUMNS = [
        "datetime",
        "symbol",
        "spot_price",
        "strike_price",
        "call_price",
        "put_price",
        "futures_price",
        "expiry_date",
    ]

    def __init__(
        self,
        risk_free_rate: float = 0.06,
        dividend_yield: float = 0.00,
        min_deviation_per_unit: float = 1.00,
        risk_buffer_percent: float = 0.10,
        default_lot_size: int = 1,
        enabled: bool = True,
    ) -> None:

        self.risk_free_rate = float(risk_free_rate)
        self.dividend_yield = float(dividend_yield)
        self.min_deviation_per_unit = float(min_deviation_per_unit)
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

        if self.dividend_yield <= -1:
            raise ValueError("Dividend yield must be greater than -1.")

        if self.min_deviation_per_unit < 0:
            raise ValueError("Minimum deviation cannot be negative.")

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
                "Compare option-implied synthetic forward price "
                "with actual futures price."
            ),
            "enabled": self.enabled,
            "research_only": True,
            "live_trading_enabled": False,
            "required_columns": self.REQUIRED_COLUMNS,
        }

    # --------------------------------------------------
    # DATETIME CONVERSION
    # --------------------------------------------------

    @staticmethod
    def _to_datetime(value: Any) -> datetime:

        if isinstance(value, datetime):
            return value

        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())

        converted = pd.to_datetime(value, errors="coerce")

        if pd.isna(converted):
            raise ValueError(f"Invalid datetime: {value}")

        return converted.to_pydatetime()

    @staticmethod
    def _calculate_time_to_expiry(
        current_datetime: Any,
        expiry_date: Any,
    ) -> float:

        current_dt = S05DateHelper.to_datetime(current_datetime)
        expiry_dt = S05DateHelper.to_datetime(expiry_date)

        seconds_remaining = (
            expiry_dt - current_dt
        ).total_seconds()

        if seconds_remaining <= 0:
            return 0.0

        seconds_per_year = 365.0 * 24.0 * 60.0 * 60.0

        return seconds_remaining / seconds_per_year

    # --------------------------------------------------
    # SYNTHETIC FORWARD PRICE
    # --------------------------------------------------

    def calculate_synthetic_forward(
        self,
        strike_price: float,
        call_price: float,
        put_price: float,
        time_to_expiry: float,
    ) -> float:

        exponent = self.risk_free_rate * time_to_expiry

        try:
            discount_adjustment = math.exp(exponent)
        except OverflowError as exc:
            raise ValueError("Synthetic price overflow.") from exc

        synthetic_forward = (
            strike_price
            + (call_price - put_price) * discount_adjustment
        )

        if not math.isfinite(synthetic_forward):
            raise ValueError("Invalid synthetic forward price.")

        return synthetic_forward

    # --------------------------------------------------
    # THEORETICAL FORWARD REFERENCE
    # --------------------------------------------------

    def calculate_theoretical_forward(
        self,
        spot_price: float,
        time_to_expiry: float,
    ) -> float:

        exponent = (
            self.risk_free_rate - self.dividend_yield
        ) * time_to_expiry

        try:
            theoretical_forward = spot_price * math.exp(exponent)
        except OverflowError as exc:
            raise ValueError("Theoretical forward overflow.") from exc

        if not math.isfinite(theoretical_forward):
            raise ValueError("Invalid theoretical forward price.")

        return theoretical_forward

    # --------------------------------------------------
    # ANALYZE ONE ROW
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

            spot_price = float(row["spot_price"])
            strike_price = float(row["strike_price"])
            call_price = float(row["call_price"])
            put_price = float(row["put_price"])
            futures_price = float(row["futures_price"])
            expiry_date = row["expiry_date"]

            # Price validation
            price_values = [
                spot_price,
                strike_price,
                call_price,
                put_price,
                futures_price,
            ]

            if not all(math.isfinite(v) for v in price_values):
                return None

            if (
                spot_price <= 0
                or strike_price <= 0
                or futures_price <= 0
                or call_price < 0
                or put_price < 0
            ):
                return None

            # Time to expiry
            time_to_expiry = (
                self._calculate_time_to_expiry(
                    current_datetime,
                expiry_date,
                )
            )

            if time_to_expiry <= 0:
                return None

            # Synthetic forward
            synthetic_forward = (
                self.calculate_synthetic_forward(
                    strike_price,
                    call_price,
                    put_price,
                    time_to_expiry,
                )
            )

            # Theoretical forward reference
            theoretical_forward = (
                self.calculate_theoretical_forward(
                    spot_price,
                    time_to_expiry,
                )
            )

            # Price difference
            price_difference = (
                synthetic_forward - futures_price
            )

            gross_edge_per_unit = abs(price_difference)

            if (
                gross_edge_per_unit
                < self.min_deviation_per_unit
            ):
                return None

            # Direction
            if price_difference > 0:

                direction = "SYNTHETIC_EXPENSIVE"
                trade_bias = "SELL_SYNTHETIC_BUY_FUTURES_RESEARCH"

            else:

                direction = "SYNTHETIC_CHEAP"
                trade_bias = "BUY_SYNTHETIC_SELL_FUTURES_RESEARCH"

            # Lot size
            lot_size = int(
                row.get("lot_size", self.default_lot_size)
            )

            if lot_size <= 0:
                lot_size = self.default_lot_size

            # Estimated costs
            estimated_costs_per_unit = float(
                row.get("estimated_costs_per_unit", 0.0)
            )

            if (
                not math.isfinite(estimated_costs_per_unit)
                or estimated_costs_per_unit < 0
            ):
                return None

            estimated_total_costs = (
                estimated_costs_per_unit * lot_size
            )

            # Gross edge
            gross_edge = gross_edge_per_unit * lot_size

            # Risk buffer
            risk_buffer = (
                gross_edge * self.risk_buffer_percent
            )

            # Net edge
            net_edge = (
                gross_edge
                - estimated_total_costs
                - risk_buffer
            )

            # Capital
            capital_required = float(
                row.get("estimated_capital_required", 0.0)
            )

            estimated_margin = float(
                row.get("estimated_margin", capital_required)
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

            # Liquidity and fill probability
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

            # Cost breakdown
            cost_breakdown = {
                "estimated_costs_per_unit": (
                    estimated_costs_per_unit
                ),
                "estimated_total_costs": (
                    estimated_total_costs
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

            # Research legs
            legs = [
                {
                    "instrument": "CALL",
                    "symbol": symbol,
                    "action": "RESEARCH_ONLY",
                    "strike": strike_price,
                    "price": call_price,
                    "expiry": str(expiry_date),
                    "quantity": lot_size,
                },
                {
                    "instrument": "PUT",
                    "symbol": symbol,
                    "action": "RESEARCH_ONLY",
                    "strike": strike_price,
                    "price": put_price,
                    "expiry": str(expiry_date),
                    "quantity": lot_size,
                },
                {
                    "instrument": "FUTURES",
                    "symbol": symbol,
                    "action": "RESEARCH_ONLY",
                    "price": futures_price,
                    "expiry": str(expiry_date),
                    "quantity": lot_size,
                },
            ]

            # Metadata
            metadata = {
                "strategy_id": self.STRATEGY_ID,
                "strategy_name": self.STRATEGY_NAME,
                "direction": direction,
                "trade_bias": trade_bias,
                "spot_price": spot_price,
                "strike_price": strike_price,
                "call_price": call_price,
                "put_price": put_price,
                "actual_futures_price": futures_price,
                "synthetic_forward_price": synthetic_forward,
                "theoretical_forward_price": theoretical_forward,
                "price_difference": price_difference,
                "gross_edge_per_unit": gross_edge_per_unit,
                "time_to_expiry_years": time_to_expiry,
                "risk_free_rate": self.risk_free_rate,
                "dividend_yield": self.dividend_yield,
                "lot_size": lot_size,
                "research_only": True,
                "paper_trading_only": True,
                "live_trading_allowed": False,
                "complete_hedge_verified": False,
                "fill_simulation_required": True,
                "charges_verified": False,
            }

            # Opportunity
            opportunity = Opportunity(
                strategy_id=self.STRATEGY_ID,
                symbol=symbol,
                market="INDIAN_DERIVATIVES",
                opportunity_type=direction,
                gross_edge=gross_edge,
                estimated_costs=estimated_total_costs,
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
                "S05 missing required columns: "
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


# ------------------------------------------------------
# DATETIME HELPER
# ------------------------------------------------------

class S05DateHelper:

    @staticmethod
    def to_datetime(value: Any) -> datetime:

        if isinstance(value, datetime):
            return value

        if isinstance(value, date):
            return datetime.combine(
                value,
                datetime.min.time(),
            )

        converted = pd.to_datetime(
            value,
            errors="coerce",
        )

        if pd.isna(converted):
            raise ValueError(
                f"Invalid datetime value: {value}"
            )

        return converted.to_pydatetime()
      
