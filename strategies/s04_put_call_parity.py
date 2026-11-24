
# India Arbitrage Lab
# Strategy 04 - Put-Call Parity / Conversion
# Research-only options parity scanner

from typing import List
import math

import pandas as pd

from models.opportunity import Opportunity
from strategies.base_strategy import BaseStrategy


class PutCallParityStrategy(BaseStrategy):
    """Scan call-put pairs for deviations from theoretical parity."""

    STRATEGY_ID = "S04"
    STRATEGY_NAME = "Put-Call Parity / Conversion"
    STRATEGY_DESCRIPTION = (
        "Measures call-put price relationship against theoretical "
        "European put-call parity for research purposes."
    )
    STRATEGY_VERSION = "1.0.0"

    REQUIRED_COLUMNS = {
        "datetime",
        "symbol",
        "spot_price",
        "strike_price",
        "call_price",
        "put_price",
        "expiry_date",
    }

    DEFAULT_CONFIG = {
        "annual_funding_rate": 0.07,
        "annual_dividend_yield": 0.00,
        "minimum_parity_deviation_per_unit": 0.0,
        "risk_buffer_fraction": 0.10,
        "default_lot_size": 1,
    }

    def __init__(self, enabled=True, config=None):
        merged = self.DEFAULT_CONFIG.copy()
        if config:
            merged.update(config)

        super().__init__(enabled=enabled, config=merged)

    def validate_config(self):
        super().validate_config()

        rate = self.config.get("annual_funding_rate")
        dividend = self.config.get("annual_dividend_yield")
        minimum = self.config.get("minimum_parity_deviation_per_unit")
        buffer_fraction = self.config.get("risk_buffer_fraction")
        lot_size = self.config.get("default_lot_size")

        if rate is None or rate <= -1:
            raise ValueError("Invalid annual funding rate")

        if dividend is None or dividend <= -1:
            raise ValueError("Invalid annual dividend yield")

        if minimum is None or minimum < 0:
            raise ValueError("Minimum parity deviation cannot be negative")

        if not 0 <= buffer_fraction <= 1:
            raise ValueError("Risk buffer fraction must be between 0 and 1")

        if lot_size is None or int(lot_size) <= 0:
            raise ValueError("Default lot size must be positive")

    def scan(
        self,
        data: pd.DataFrame,
        contract_master=None,
    ) -> List[Opportunity]:

        if not self.enabled or data is None or data.empty:
            return []

        missing = self.REQUIRED_COLUMNS - set(data.columns)
        if missing:
            raise ValueError(
                "Missing S04 columns: " + ", ".join(sorted(missing))
            )

        results = []

        for _, row in data.iterrows():
            try:
                opportunity = self._analyze_row(row)
                if opportunity is not None:
                    results.append(opportunity)
            except (ValueError, TypeError, KeyError, OverflowError):
                continue

        return results

    def _analyze_row(self, row) -> Opportunity:

        spot = float(row["spot_price"])
        strike = float(row["strike_price"])
        call_price = float(row["call_price"])
        put_price = float(row["put_price"])

        if min(spot, strike, call_price, put_price) < 0:
            raise ValueError("Prices cannot be negative")

        if spot <= 0 or strike <= 0:
            raise ValueError("Spot and strike must be positive")

        timestamp = pd.to_datetime(row["datetime"], errors="coerce")
        expiry = pd.to_datetime(row["expiry_date"], errors="coerce")

        if pd.isna(timestamp) or pd.isna(expiry):
            raise ValueError("Invalid datetime or expiry")

        days_to_expiry = max(
            (expiry.date() - timestamp.date()).days,
            0,
        )
        years_to_expiry = days_to_expiry / 365.0

        rate = float(self.config["annual_funding_rate"])
        dividend = float(self.config["annual_dividend_yield"])

        discounted_spot = spot * math.exp(-dividend * years_to_expiry)
        discounted_strike = strike * math.exp(-rate * years_to_expiry)

        theoretical_call_minus_put = (
            discounted_spot - discounted_strike
        )

        actual_call_minus_put = call_price - put_price

        parity_deviation = (
            actual_call_minus_put - theoretical_call_minus_put
        )

        minimum = float(
            self.config["minimum_parity_deviation_per_unit"]
        )

        if abs(parity_deviation) < minimum:
            return None

        # Positive deviation means Call-Put is rich versus parity.
        # Negative deviation means Call-Put is cheap versus parity.
        if parity_deviation > 0:
            direction = "CALL_PUT_RICH"
            call_side = "SELL"
            put_side = "BUY"
        elif parity_deviation < 0:
            direction = "CALL_PUT_CHEAP"
            call_side = "BUY"
            put_side = "SELL"
        else:
            return None

        lot_size = int(
            row.get("lot_size", self.config["default_lot_size"])
        )
        if lot_size <= 0:
            raise ValueError("Lot size must be positive")

        gross_edge = abs(parity_deviation) * lot_size

        costs_present = (
            "estimated_costs_per_unit" in row.index
            and pd.notna(row["estimated_costs_per_unit"])
        )

        costs_per_unit = (
            float(row["estimated_costs_per_unit"])
            if costs_present
            else 0.0
        )

        if costs_per_unit < 0:
            raise ValueError("Estimated costs cannot be negative")

        estimated_costs = costs_per_unit * lot_size

        risk_buffer = gross_edge * float(
            self.config["risk_buffer_fraction"]
        )
        net_edge = gross_edge - estimated_costs - risk_buffer

        capital_required = float(
            row.get("estimated_capital_required", 0.0)
        )

        return Opportunity(
            strategy_id=self.STRATEGY_ID,
            symbol=str(row["symbol"]),
            market=str(row.get("market", "NSE")),
            opportunity_type="PUT_CALL_PARITY_DEVIATION",
            gross_edge=gross_edge,
            estimated_costs=estimated_costs,
            risk_buffer=risk_buffer,
            net_edge=net_edge,
            capital_required=capital_required,
            estimated_margin=float(row.get("estimated_margin", 0.0)),
            liquidity_score=float(row.get("liquidity_score", 0.0)),
            fill_probability=float(row.get("fill_probability", 0.0)),
            confidence_score=0.0,
            cost_breakdown={
                "parity_deviation_per_unit": parity_deviation,
                "estimated_costs_per_unit": costs_per_unit,
                "cost_input_provided": costs_present,
                "costs_verified": False,
                "lot_size": lot_size,
            },
            legs=[
                {
                    "instrument": "CALL",
                    "side": call_side,
                    "price": call_price,
                    "quantity": lot_size,
                    "strike": strike,
                    "expiry_date": expiry.date().isoformat(),
                },
                {
                    "instrument": "PUT",
                    "side": put_side,
                    "price": put_price,
                    "quantity": lot_size,
                    "strike": strike,
                    "expiry_date": expiry.date().isoformat(),
                },
            ],
            metadata={
                "strategy_name": self.STRATEGY_NAME,
                "direction": direction,
                "datetime": timestamp.isoformat(),
                "expiry_date": expiry.date().isoformat(),
                "days_to_expiry": days_to_expiry,
                "spot_price": spot,
                "strike_price": strike,
                "call_price": call_price,
                "put_price": put_price,
                "actual_call_minus_put": actual_call_minus_put,
                "theoretical_call_minus_put": (
                    theoretical_call_minus_put
                ),
                "discounted_spot": discounted_spot,
                "discounted_strike": discounted_strike,
                "parity_deviation": parity_deviation,
                "annual_funding_rate": rate,
                "annual_dividend_yield": dividend,
                "risk_buffer_fraction": self.config[
                    "risk_buffer_fraction"
                ],
                "research_only": True,
                "costs_verified": False,
                "complete_hedge_not_constructed": True,
            },
        )
      
