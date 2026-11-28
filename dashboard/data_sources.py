"""
Shared data picker for dashboard pages: a local CSV or an uploaded CSV,
optionally merged with a futures/options CSV. Nothing is invented.
"""

import tempfile
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import streamlit as st

from data_engine import CSVDataLoader
from data_engine.schema import merge_derivatives, prepare_spot_frame

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "historical"


def list_local_csvs():
    return sorted(str(p.relative_to(ROOT)) for p in DATA_DIR.rglob("*.csv"))


def load_prepared(path: str, rows: int = 500, symbol: str = "NIFTY",
                  deriv_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    full = Path(path)
    if not full.is_absolute():
        full = ROOT / full
    frame = prepare_spot_frame(CSVDataLoader().load(str(full)).head(rows), symbol)
    if deriv_df is not None:
        frame = merge_derivatives(frame, deriv_df)
    return frame


def source_picker(key: str) -> Tuple[Optional[pd.DataFrame], str]:
    files = list_local_csvs()
    choice = st.selectbox("Data file", files or ["(no CSV files found)"], key=f"{key}_file")
    upload = st.file_uploader("...or upload your own CSV", type="csv", key=f"{key}_up")
    deriv = st.file_uploader(
        "Optional: futures/options CSV (needs a datetime column)", type="csv", key=f"{key}_dv"
    )
    rows = st.slider("Rows to use", 50, 5000, 500, key=f"{key}_rows")
    symbol = st.text_input("Symbol", "NIFTY", key=f"{key}_sym")

    try:
        deriv_df = pd.read_csv(deriv) if deriv is not None else None
        if upload is not None:
            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as handle:
                handle.write(upload.getvalue())
            return load_prepared(handle.name, rows, symbol, deriv_df), upload.name
        if not files:
            return None, ""
        return load_prepared(choice, rows, symbol, deriv_df), choice
    except Exception as exc:
        st.error(f"Could not load data: {type(exc).__name__}: {exc}")
        return None, ""
