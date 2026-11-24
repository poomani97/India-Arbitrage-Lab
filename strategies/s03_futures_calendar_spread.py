
# India Arbitrage Lab
# Strategy 03 - Futures Calendar Spread
# Research-only calendar spread scanner

from typing import List

import pandas as pd

from models.opportunity import Opportunity
from strategies.base_strategy import BaseStrategy


class FuturesCalendarSpreadStrategy(BaseStrategy):
    """Analyze near-expiry and far-expiry futures spread deviations."""

    STRATEGY_ID = "S03"
    STRATEGY_NAME = "Futures Calendar Spread"
    STRATEGY_DESCRIPTION = (
        "Compares near and far futures spreads with theoretical carry spread."
    )
    STRATEGY_VERSION = "1.0.0"

    REQUIRED_COLUMNS = {
        "datetime",
        "symbol",
        "spot_price",
        "near_futures_price",
        "far_futures_price",
        "near_expiry_date",
        "far_expiry_date",
    }

    DEFAULT_CONFIG = {
        "annual_funding_rate": 0.07,
        "annual_dividend_yield": 0.00,
        "minimum_spread_mispricing_per_unit": 0.0,
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
        minimum = self.config.get("minimum_spread_mispricing_per_unit")
        buffer_fraction = self.config.get("risk_buffer_fraction")
        lot_size = self.config.get("default_lot_size")

        if rate is None or rate <= -1:
            raise ValueError("Invalid annual funding rate")

        if dividend is None or dividend <= -1:
            raise ValueError("Invalid annual dividend yield")

        if minimum is None or minimum < 0:
            raise ValueError("Minimum spread mispricing cannot be negative")

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
                "Missing S03 columns: " + ", ".join(sorted(missing))
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
        near_price = float(row["near_futures_price"])
        far_price = float(row["far_futures_price"])

        if spot <= 0 or near_price <= 0 or far_price <= 0:
            raise ValueError("Prices must be positive")

        timestamp = pd.to_datetime(row["datetime"], errors="coerce")
        near_expiry = pd.to_datetime(
            row["near_expiry_date"], errors="coerce"
        )
        far_expiry = pd.to_datetime(
            row["far_expiry_date"], errors="coerce"
        )

        if pd.isna(timestamp) or pd.isna(near_expiry) or pd.isna(far_expiry):
            raise ValueError("Invalid timestamp or expiry")

        if far_expiry.date() <= near_expiry.date():
            raise ValueError("Far expiry must be after near expiry")

        near_days = max((near_expiry.date() - timestamp.date()).days, 0)
        far_days = max((far_expiry.date() - timestamp.date()).days, 0)

        rate = float(self.config["annual_funding_rate"])
        dividend = float(self.config["annual_dividend_yield"])

        near_years = near_days / 365.0
        far_years = far_days / 365.0

        near_fair_value = spot * (
            (1 + rate) ** near_years
        ) / (
            (1 + dividend) ** near_years
        )

        far_fair_value = spot * (
            (1 + rate) ** far_years
        ) / (
            (1 + dividend) ** far_years
        )

        actual_spread = far_price - near_price
        theoretical_spread = far_fair_value - near_fair_value
        spread_mispricing = actual_spread - theoretical_spread

        minimum = float(
            self.config["minimum_spread_mispricing_per_unit"]
        )

        if abs(spread_mispricing) < minimum:
            return None

        lot_size = int(
            row.get("lot_size", self.config["default_lot_size"])
        )
        if lot_size <= 0:
            raise ValueError("Lot size must be positive")

        if spread_mispricing > 0:
            # Far contract is relatively rich: short far, long near.
            direction = "SHORT_FAR_LONG_NEAR"
            near_side = "BUY"
            far_side = "SELL"
        else:
            # Far contract is relatively cheap: long far, short near.
            direction = "LONG_FAR_SHORT_NEAR"
            near_side = "SELL"
            far_side = "BUY"

        gross_edge = abs(spread_mispricing) * lot_size

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

        # Approximate capital placeholder; actual margin/capital
        # must be supplied by a later margin model.
        capital_required = 2 * spot * lot_size

        return Opportunity(
            strategy_id=self.STRATEGY_ID,
            symbol=str(row["symbol"]),
            market=str(row.get("market", "NSE")),
            opportunity_type="FUTURES_CALENDAR_SPREAD",
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
                "actual_spread": actual_spread,
                "theoretical_spread": theoretical_spread,
                "spread_mispricing_per_unit": spread_mispricing,
                "estimated_costs_per_unit": costs_per_unit,
                "cost_input_provided": costs_present,
                "costs_verified": False,
                "lot_size": lot_size,
            },
            legs=[
                {
                    "instrument": "NEAR_FUTURES",
                    "side": near_side,
                    "price": near_price,
                    "quantity": lot_size,
                    "expiry_date": near_expiry.date().isoformat(),
                },
                {
                    "instrument": "FAR_FUTURES",
                    "side": far_side,
                    "price": far_price,
                    "quantity": lot_size,
                    "expiry_date": far_expiry.date().isoformat(),
                },
            ],
            metadata={
                "strategy_name": self.STRATEGY_NAME,
                "direction": direction,
                "datetime": timestamp.isoformat(),
                "near_expiry_date": near_expiry.date().isoformat(),
                "far_expiry_date": far_expiry.date().isoformat(),
                "near_days_to_expiry": near_days,
                "far_days_to_expiry": far_days,
                "spot_price": spot,
                "near_futures_price": near_price,
                "far_futures_price": far_price,
                "near_theoretical_price": near_fair_value,
                "far_theoretical_price": far_fair_value,
                "actual_spread": actual_spread,
                "theoretical_spread": theoretical_spread,
                "spread_mispricing": spread_mispricing,
                "annual_funding_rate": rate,
                "annual_dividend_yield": dividend,
                "research_only": True,
                "costs_verified": False,
                "capital_estimate_is_approximate": True,
            },
        )
      
