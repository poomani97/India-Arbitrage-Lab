from datetime import date

import streamlit as st

from data_engine.history_download import download_to_csv


def render() -> None:
    st.subheader("Download history for backtesting (Fyers)")
    st.caption("Needs FYERS_APP_ID and FYERS_ACCESS_TOKEN environment variables. "
               "Expired futures/options often have little or no history.")
    symbol = st.text_input("Fyers symbol", "NSE:NIFTY50-INDEX", key="hd_symbol")
    c1, c2, c3 = st.columns(3)
    start = c1.date_input("Start", date(2026, 1, 1), key="hd_start")
    end = c2.date_input("End", date.today(), key="hd_end")
    resolution = c3.selectbox("Candle", ["1", "5", "15", "60", "D"], key="hd_res")
    out = st.text_input("Save as", "data/historical/nifty/NIFTY50_download.csv", key="hd_out")

    if st.button("Download"):
        try:
            client = st.session_state.get("history_client_override")
            if client is None:
                from brokers.fyers_adapter import _client_from_env
                client = _client_from_env()
            count = download_to_csv(client, symbol, start, end, out, resolution)
            st.success(f"Saved {count} candles to {out}")
        except Exception as exc:
            st.error(f"{type(exc).__name__}: {exc}")
