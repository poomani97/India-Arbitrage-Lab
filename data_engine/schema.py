"""
India Arbitrage Lab
Data schema helpers.

- prepare_spot_frame(): turns the loaded Nifty OHLC file into the spot_price
  / symbol layout the strategies expect.
- merge_derivatives(): attaches futures / options / ETF / BSE columns that YOU
  supply in a separate file, matched to the nearest earlier timestamp.
- check_data_coverage(): tells you which of S01-S10 can run on a frame and
  exactly which columns are missing.

Nothing here invents prices. Missing columns stay missing.
"""

from typing import Dict, List

import pandas as pd

from strategies import STRATEGY_CLASSES


def strategy_requirements() -> Dict[str, List[str]]:
    return {
        sid: sorted(getattr(cls, "REQUIRED_COLUMNS", set()))
        for sid, cls in STRATEGY_CLASSES.items()
    }


def prepare_spot_frame(df: pd.DataFrame, symbol: str = "NIFTY") -> pd.DataFrame:
    """Add symbol and spot_price (= close) to a loaded OHLC frame."""
    out = df.copy()
    if "close" not in out.columns:
        raise ValueError("Frame needs a close column.")
    out["datetime"] = pd.to_datetime(out["datetime"])
    out["symbol"] = symbol
    out["spot_price"] = out["close"].astype(float)
    return out.sort_values("datetime").reset_index(drop=True)


def merge_derivatives(
    spot_df: pd.DataFrame,
    derivatives_df: pd.DataFrame,
    tolerance: str = "1min",
) -> pd.DataFrame:
    """Attach derivative columns by nearest earlier timestamp.

    derivatives_df needs a datetime column plus any strategy columns, for
    example futures_price, expiry_date, call_price, put_price, strike_price.
    Rows with no derivative quote within `tolerance` keep NaN, so stale
    prices are never reused silently.
    """
    if "datetime" not in derivatives_df.columns:
        raise ValueError("derivatives_df needs a datetime column.")

    left = spot_df.copy()
    right = derivatives_df.copy()
    left["datetime"] = pd.to_datetime(left["datetime"])
    right["datetime"] = pd.to_datetime(right["datetime"])

    clash = [c for c in right.columns if c in left.columns and c != "datetime"]
    if clash:
        right = right.drop(columns=clash)

    return pd.merge_asof(
        left.sort_values("datetime"),
        right.sort_values("datetime"),
        on="datetime",
        direction="backward",
        tolerance=pd.Timedelta(tolerance),
    )


def check_data_coverage(df: pd.DataFrame) -> Dict[str, Dict[str, object]]:
    """For every strategy: ready True/False, missing columns, usable rows."""
    report = {}
    columns = set(df.columns)

    for sid, needed in strategy_requirements().items():
        missing = [c for c in needed if c not in columns]
        usable = 0
        if not missing and needed:
            usable = int(df[needed].notna().all(axis=1).sum())
        report[sid] = {
            "ready": not missing and usable > 0,
            "missing_columns": missing,
            "usable_rows": usable,
        }
    return report


def format_coverage(report: Dict[str, Dict[str, object]]) -> str:
    lines = []
    for sid, info in report.items():
        if info["ready"]:
            lines.append(f"{sid}: READY ({info['usable_rows']} usable rows)")
        elif info["missing_columns"]:
            lines.append(f"{sid}: missing {', '.join(info['missing_columns'])}")
        else:
            lines.append(f"{sid}: columns present but no complete rows")
    return "\n".join(lines)
