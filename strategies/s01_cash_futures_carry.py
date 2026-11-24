
# India Arbitrage Lab
# Strategy 01 - Cash Futures Carry
# Research-only opportunity scanner

from datetime import date, datetime
from typing import List, Optional

import pandas as pd

from models.opportunity import Opportunity
from strategies.base_strategy import BaseStrategy


class CashFuturesCarryStrategy(BaseStrategy):
    """Compare cash/futures prices against theoretical carry fair value."""

    STRATEGY_ID = "S01"
    STRATEGY_NAME = "Cash-Futures Carry"
    STRATEGY_DESCRIPTION = (
        "Scans cash and futures prices for deviations from "
        "theoretical carry fair value."
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
        "risk_buffer_fraction": 0.10,
        "minimum_gross_edge_per_unit": 0.0,
        "default_lot_size": 1,
        "allow_reverse_carry": True,
    }

    def __init__(self, enabled=True, config=None):
        merged_config = self.DEFAULT_CONFIG.copy()
        if config:
            merged_config.update(config)

        super().__init__(enabled=enabled, config=merged_config)

    def validate_config(self):
        super().validate_config()

        rate = self.config.get("annual_funding_rate")
        dividend = self.config.get("annual_dividend_yield")
        buffer_fraction = self.config.get("risk_buffer_fraction")
        lot_size = self.config.get("default_lot_size")
        minimum_edge = self.config.get("minimum_gross_edge_per_unit")

        if rate is None or rate <= -1:
            raise ValueError("Invalid annual funding rate")

        if dividend is None or dividend <= -1:
            raise ValueError("Invalid annual dividend yield")

        if not 0 <= buffer_fraction <= 1:
            raise ValueError("Risk buffer fraction must be 0 to 1")

        if lot_size is None or int(lot_size) <= 0:
            raise ValueError("Default lot size must be positive")

        if minimum_edge is None or minimum_edge < 0:
            raise ValueError("Minimum gross edge cannot be negative")

    def scan(
        self,
        data: pd.DataFrame,
        contract_master=None,
    ) -> List[Opportunity]:

        if not self.enabled or not self.check_data(data):
            return []

        missing = self.REQUIRED_COLUMNS - set(data.columns)
        if missing:
            raise ValueError(
                "Missing required S01 columns: "
                + ", ".join(sorted(missing))
            )

        results = []

        for _, row in data.iterrows():
            try:
                opportunity = self._analyze_row(row)
                if opportunity is not None:
                    results.append(opportunity)
            except (ValueError, TypeError, KeyError, OverflowError):
                # Skip malformed rows; data quality should be reviewed separately.
                continue

        return results

    def _analyze_row(self, row) -> Optional[Opportunity]:

        spot = float(row["spot_price"])
        futures = float(row["futures_price"])

        if spot <= 0 or futures <= 0:
            return None

        expiry = pd.to_datetime(row["expiry_date"], errors="coerce")
        timestamp = pd.to_datetime(row["datetime"], errors="coerce")

        if pd.isna(expiry) or pd.isna(timestamp):
            return None

        days_to_expiry = max(
            (expiry.date() - timestamp.date()).days,
            0,
        )

        years_to_expiry = days_to_expiry / 365.0

        funding_rate = float(self.config["annual_funding_rate"])
        dividend_yield = float(self.config["annual_dividend_yield"])

        theoretical_futures = spot * (
            (1 + funding_rate) ** years_to_expiry
        ) / (
            (1 + dividend_yield) ** years_to_expiry
        )

        basis = futures - spot
        fair_basis = theoretical_futures - spot

        gross_edge_per_unit = futures - theoretical_futures

        # Positive gross edge: futures appear rich relative to fair value.
        # Negative gross edge: futures appear cheap relative to fair value.
        direction = (
            "CASH_LONG_FUTURES_SHORT"
            if gross_edge_per_unit > 0
            else "CASH_SHORT_FUTURES_LONG"
        )

        if (
            gross_edge_per_unit < 0
            and not self.config["allow_reverse_carry"]
        ):
            return None

        absolute_gross_edge = abs(gross_edge_per_unit)

        if absolute_gross_edge < float(
            self.config["minimum_gross_edge_per_unit"]
        ):
            return None

        lot_size = int(
            row.get("lot_size", self.config["default_lot_size"])
        )

        if lot_size <= 0:
            return None

        gross_edge = absolute_gross_edge * lot_size

        # Optional cost input. If absent, costs are unknown, not zero in reality.
        cost_input_present = (
            "estimated_costs_per_unit" in row.index
            and pd.notna(row["estimated_costs_per_unit"])
        )

        estimated_costs_per_unit = (
            float(row["estimated_costs_per_unit"])
            if cost_input_present
            else 0.0
        )

        if estimated_costs_per_unit < 0:
            return None

        estimated_costs = estimated_costs_per_unit * lot_size

        risk_buffer = gross_edge * float(
            self.config["risk_buffer_fraction"]
        )

        net_edge = gross_edge - estimated_costs - risk_buffer

        capital_required = spot * lot_size

        # Do not qualify the opportunity. This is a scanner observation only.
        expiry_date = expiry.date().isoformat()

        symbol = str(row["symbol"])

        return Opportunity(
            strategy_id=self.STRATEGY_ID,
            symbol=symbol,
            market=str(row.get("market", "NSE")),
            opportunity_type="CASH_FUTURES_CARRY",
            gross_edge=gross_edge,
            estimated_costs=estimated_costs,
            risk_buffer=risk_buffer,
            net_edge=net_edge,
            capital_required=capital_required,
            estimated_margin=float(
                row.get("estimated_margin", 0.0)
            ),
            liquidity_score=float(
                row.get("liquidity_score", 0.0)
            ),
            fill_probability=float(
                row.get("fill_probability", 0.0)
            ),
            confidence_score=0.0,
            cost_breakdown={
                "estimated_costs_per_unit": estimated_costs_per_unit,
                "lot_size": lot_size,
                "cost_input_provided": cost_input_present,
                "costs_verified": False,
            },
            legs=[
                {
                    "instrument": "CASH",
                    "side": (
                        "BUY" if direction == "CASH_LONG_FUTURES_SHORT"
                        else "SELL"
                    ),
                    "price": spot,
                    "quantity": lot_size,
                },
                {
                    "instrument": "FUTURES",
                    "side": (
                        "SELL" if direction == "CASH_LONG_FUTURES_SHORT"
                        else "BUY"
                    ),
                    "price": futures,
                    "quantity": lot_size,
                },
            ],
            metadata={
                "strategy_name": self.STRATEGY_NAME,
                "direction": direction,
                "datetime": timestamp.isoformat(),
                "expiry_date": expiry_date,
                "days_to_expiry": days_to_expiry,
                "spot_price": spot,
                "futures_price": futures,
                "theoretical_futures_price": theoretical_futures,
                "actual_basis": basis,
                "theoretical_basis": fair_basis,
                "gross_edge_per_unit": gross_edge_per_unit,
                "annual_funding_rate": funding_rate,
                "annual_dividend_yield": dividend_yield,
                "risk_buffer_fraction": self.config[
                    "risk_buffer_fraction"
                ],
                "costs_verified": False,
                "research_only": True,
            },
        )
      
