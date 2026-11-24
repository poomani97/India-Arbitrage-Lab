
# India Arbitrage Lab
# Strategy 02 - Futures Fair Value / Basis
# Research-only mispricing scanner

from typing import List

import pandas as pd

from models.opportunity import Opportunity
from strategies.base_strategy import BaseStrategy


class FuturesFairValueStrategy(BaseStrategy):
    """Scan futures prices against theoretical fair value."""

    STRATEGY_ID = "S02"
    STRATEGY_NAME = "Futures Fair Value / Basis"
    STRATEGY_DESCRIPTION = (
        "Measures actual futures price deviation from theoretical "
        "fair value and records research opportunities."
    )
    STRATEGY_VERSION = "1.0.0"

    REQUIRED_COLUMNS = {
        "datetime",
        "symbol",
        "spot_price",
        "futures_price",
        "expiry_date",
    }

    DEFAULT_CONFIG = {
        "annual_funding_rate": 0.07,
        "annual_dividend_yield": 0.00,
        "minimum_mispricing_per_unit": 0.0,
        "risk_buffer_fraction": 0.10,
        "default_lot_size": 1,
        "allow_long_futures": True,
        "allow_short_futures": True,
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
        minimum = self.config.get("minimum_mispricing_per_unit")
        buffer_fraction = self.config.get("risk_buffer_fraction")
        lot_size = self.config.get("default_lot_size")

        if rate is None or rate <= -1:
            raise ValueError("Invalid annual funding rate")

        if dividend is None or dividend <= -1:
            raise ValueError("Invalid annual dividend yield")

        if minimum is None or minimum < 0:
            raise ValueError("Minimum mispricing cannot be negative")

        if not 0 <= buffer_fraction <= 1:
            raise ValueError("Risk buffer fraction must be between 0 and 1")

        if lot_size is None or int(lot_size) <= 0:
            raise ValueError("Default lot size must be positive")

        if not isinstance(self.config.get("allow_long_futures"), bool):
            raise TypeError("allow_long_futures must be boolean")

        if not isinstance(self.config.get("allow_short_futures"), bool):
            raise TypeError("allow_short_futures must be boolean")

    def scan(self, data: pd.DataFrame, contract_master=None) -> List[Opportunity]:

        if not self.enabled or data is None or data.empty:
            return []

        missing = self.REQUIRED_COLUMNS - set(data.columns)
        if missing:
            raise ValueError(
                "Missing S02 columns: " + ", ".join(sorted(missing))
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
        futures = float(row["futures_price"])

        if spot <= 0 or futures <= 0:
            raise ValueError("Prices must be positive")

        timestamp = pd.to_datetime(row["datetime"], errors="coerce")
        expiry = pd.to_datetime(row["expiry_date"], errors="coerce")

        if pd.isna(timestamp) or pd.isna(expiry):
            raise ValueError("Invalid timestamp or expiry")

        days = max((expiry.date() - timestamp.date()).days, 0)
        years = days / 365.0

        rate = float(self.config["annual_funding_rate"])
        dividend = float(self.config["annual_dividend_yield"])

        fair_value = spot * (
            (1 + rate) ** years
        ) / (
            (1 + dividend) ** years
        )

        mispricing = futures - fair_value

        min_mispricing = float(
            self.config["minimum_mispricing_per_unit"]
        )

        if abs(mispricing) < min_mispricing:
            return None

        if mispricing > 0:
            direction = "SHORT_FUTURES"
            if not self.config["allow_short_futures"]:
                return None
        elif mispricing < 0:
            direction = "LONG_FUTURES"
            if not self.config["allow_long_futures"]:
                return None
        else:
            return None

        lot_size = int(
            row.get("lot_size", self.config["default_lot_size"])
        )

        if lot_size <= 0:
            raise ValueError("Invalid lot size")

        gross_edge = abs(mispricing) * lot_size

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

        buffer_fraction = float(
            self.config["risk_buffer_fraction"]
        )
        risk_buffer = gross_edge * buffer_fraction
        net_edge = gross_edge - estimated_costs - risk_buffer

        capital_required = spot * lot_size

        return Opportunity(
            strategy_id=self.STRATEGY_ID,
            symbol=str(row["symbol"]),
            market=str(row.get("market", "NSE")),
            opportunity_type="FUTURES_FAIR_VALUE_BASIS",
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
                "mispricing_per_unit": mispricing,
                "estimated_costs_per_unit": costs_per_unit,
                "cost_input_provided": costs_present,
                "costs_verified": False,
                "lot_size": lot_size,
            },
            legs=[
                {
                    "instrument": "FUTURES",
                    "side": "SELL" if direction == "SHORT_FUTURES" else "BUY",
                    "price": futures,
                    "quantity": lot_size,
                }
            ],
            metadata={
                "strategy_name": self.STRATEGY_NAME,
                "direction": direction,
                "datetime": timestamp.isoformat(),
                "expiry_date": expiry.date().isoformat(),
                "days_to_expiry": days,
                "spot_price": spot,
                "actual_futures_price": futures,
                "theoretical_futures_price": fair_value,
                "actual_basis": futures - spot,
                "theoretical_basis": fair_value - spot,
                "mispricing_per_unit": mispricing,
                "annual_funding_rate": rate,
                "annual_dividend_yield": dividend,
                "risk_buffer_fraction": buffer_fraction,
                "research_only": True,
                "costs_verified": False,
            },
        )
      
