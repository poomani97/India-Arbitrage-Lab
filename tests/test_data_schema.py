import pandas as pd

from data_engine import CSVDataLoader
from data_engine.schema import (check_data_coverage, merge_derivatives,
                                prepare_spot_frame, strategy_requirements)
from pathlib import Path

NIFTY = Path(__file__).resolve().parent.parent / "data/historical/nifty/NIFTY50_1min_2026-01.csv"


def _spot():
    return pd.DataFrame({
        "datetime": pd.date_range("2026-01-05 09:15", periods=4, freq="1min"),
        "open": 100.0, "high": 101.0, "low": 99.0, "close": [100.0, 101.0, 102.0, 103.0],
    })


def test_requirements_cover_all_ten_strategies():
    assert len(strategy_requirements()) == 10


def test_prepare_spot_frame_adds_symbol_and_spot_price():
    out = prepare_spot_frame(_spot(), "NIFTY")
    assert list(out["spot_price"]) == [100.0, 101.0, 102.0, 103.0]
    assert (out["symbol"] == "NIFTY").all()


def test_real_nifty_file_alone_is_honestly_not_ready():
    frame = prepare_spot_frame(CSVDataLoader().load(str(NIFTY)).head(50))
    report = check_data_coverage(frame)
    assert not any(info["ready"] for info in report.values())
    assert "futures_price" in report["S01"]["missing_columns"]


def test_merge_makes_s01_ready_and_leaves_gaps_as_nan():
    spot = prepare_spot_frame(_spot())
    fut = pd.DataFrame({
        "datetime": pd.to_datetime(["2026-01-05 09:15", "2026-01-05 09:16"]),
        "futures_price": [110.0, 111.0],
        "expiry_date": pd.Timestamp("2026-01-29"),
    })
    merged = merge_derivatives(spot, fut, tolerance="1min")
    assert merged["futures_price"].notna().sum() == 3  # 09:15, 09:16, 09:17 (within 1 min)
    assert pd.isna(merged["futures_price"].iloc[3])    # 09:18 too old, not reused
    report = check_data_coverage(merged)
    assert report["S01"]["ready"] and report["S01"]["usable_rows"] == 3
    assert not report["S03"]["ready"]


def test_merged_frame_runs_through_strategy():
    from strategies import get_strategy
    spot = prepare_spot_frame(_spot())
    fut = pd.DataFrame({"datetime": spot["datetime"], "futures_price": spot["spot_price"] * 1.01,
                        "expiry_date": pd.Timestamp("2026-01-29")})
    out = get_strategy("S01").scan(merge_derivatives(spot, fut))
    assert len(out) == 4
