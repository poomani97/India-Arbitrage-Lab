"""
India Arbitrage Lab
Cost model: fills estimated_costs_per_unit for the strategies.

Rates are percentages (0.05 means 0.05%).
STT, stamp duty, SEBI fee and GST follow figures published for April 2026
(futures STT 0.05% sell side, options STT 0.15% of premium sell side).
Exchange transaction charges and broker brokerage MUST be confirmed against
the NSE circular and your broker (Angel One / Dhan / Fyers) before real use.
Profiles stay verified=False until you do that.
"""

import pandas as pd

from config.charges_config import ChargeRates, ChargesConfig
from pricing.charges import ChargesCalculator


def build_default_costs_config() -> ChargesConfig:
    config = ChargesConfig(require_verified_rates=False)

    config.add_profile("FUTURES", ChargeRates(
        brokerage_percent=0.0,
        stt_percent=0.05,                       # sell side, from Apr 2026
        exchange_transaction_percent=0.00183,   # CONFIRM with NSE circular
        sebi_fee_percent=0.0001,                # Rs 10 per crore
        gst_percent=18.0,
        stamp_duty_percent=0.002,               # buy side
        miscellaneous_per_order=20.0,           # flat broker fee, CONFIRM
        slippage_percent=0.01,
    ))
    config.add_profile("OPTIONS", ChargeRates(
        stt_percent=0.15,                       # on premium, sell side
        exchange_transaction_percent=0.03503,   # on premium, CONFIRM
        sebi_fee_percent=0.0001,
        gst_percent=18.0,
        stamp_duty_percent=0.003,
        miscellaneous_per_order=20.0,
        slippage_percent=0.05,
    ))
    return config


class CostModel:
    def __init__(self, config: ChargesConfig = None):
        self.calculator = ChargesCalculator(config or build_default_costs_config())

    def futures_round_trip_per_unit(self, price: float, orders: int = 2) -> float:
        """Buy one unit and sell one unit of a future at `price`."""
        b = self.calculator.calculate("FUTURES", price, price, order_count=orders)
        return b.total_charges

    def options_round_trip_per_unit(self, premium: float, orders: int = 2) -> float:
        b = self.calculator.calculate("OPTIONS", premium, premium, order_count=orders)
        return b.total_charges


def _per_unit(total_rupees, lot_size):
    return total_rupees / max(int(lot_size), 1)


def add_cost_column(df: pd.DataFrame, lot_size: int = 1, model: CostModel = None) -> pd.DataFrame:
    """Return a copy of df with estimated_costs_per_unit filled in.

    Futures-based rows (S01, S02, S03, S05, S07) use futures turnover.
    Option-only rows (S04, S06) use the option premiums.
    A flat Rs 20 per order is spread over the lot, so pass the real lot_size.
    Existing non-null values in the column are kept.
    """
    model = model or CostModel()
    out = df.copy()

    def row_cost(row):
        if "futures_price" in row.index and pd.notna(row["futures_price"]):
            return _per_unit(model.futures_round_trip_per_unit(float(row["futures_price"] * lot_size)), lot_size)
        if "near_futures_price" in row.index and pd.notna(row["near_futures_price"]):
            near = model.futures_round_trip_per_unit(float(row["near_futures_price"] * lot_size), orders=4)
            far = model.futures_round_trip_per_unit(float(row["far_futures_price"] * lot_size), orders=0)
            return _per_unit(near + far, lot_size)
        if "call_price" in row.index and pd.notna(row.get("call_price")):
            prem = float(row["call_price"]) + float(row.get("put_price", 0.0))
            return _per_unit(model.options_round_trip_per_unit(prem * lot_size, orders=4), lot_size)
        if "call_lower_price" in row.index:
            prem = sum(float(row[c]) for c in ("call_lower_price", "call_higher_price", "put_lower_price", "put_higher_price"))
            return _per_unit(model.options_round_trip_per_unit(prem * lot_size, orders=8), lot_size)
        return float("nan")

    computed = out.apply(row_cost, axis=1)
    if "estimated_costs_per_unit" in out.columns:
        out["estimated_costs_per_unit"] = out["estimated_costs_per_unit"].fillna(computed)
    else:
        out["estimated_costs_per_unit"] = computed
    return out
