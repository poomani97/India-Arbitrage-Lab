import pandas as pd
from pricing.cost_model import CostModel, add_cost_column
from strategies import get_strategy


def _frame():
    return pd.DataFrame({
        "datetime": pd.date_range("2026-01-05 09:15", periods=3, freq="1min"),
        "open": 26000.0, "high": 26005.0, "low": 25995.0, "close": 26000.0,
        "symbol": "NIFTY", "spot_price": 26000.0, "futures_price": 26260.0,
        "expiry_date": pd.Timestamp("2026-01-29"),
    })


def test_futures_cost_is_positive_and_realistic():
    cost = CostModel().futures_round_trip_per_unit(26000.0 * 75)
    assert 1000 < cost < 3000  # roughly 0.06-0.15% of Rs 19.5 lakh turnover


def test_cost_column_reduces_net_edge():
    strat = get_strategy("S01", config={"default_lot_size": 75})
    base = strat.scan(_frame())[0]
    costed = strat.scan(add_cost_column(_frame(), lot_size=75))[0]
    assert costed.estimated_costs > 0
    assert costed.net_edge < base.net_edge


def test_existing_cost_values_are_kept():
    df = _frame(); df["estimated_costs_per_unit"] = 5.0
    assert (add_cost_column(df)["estimated_costs_per_unit"] == 5.0).all()
