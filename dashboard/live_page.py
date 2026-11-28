import os
import time

import pandas as pd
import streamlit as st

from brokers.base import BrokerError
from dashboard.trading_page import get_controller
from feeds.fyers_feed import FyersFeed
from feeds.live import run_live_step


def _feed(spot: str, fut: str, expiry: str):
    override = st.session_state.get("feed_override")
    if override is not None:
        return override
    return FyersFeed(
        {"spot_price": spot, "futures_price": fut},
        constants={"symbol": "NIFTY", "expiry_date": expiry},
        volume_columns={"futures_volume": fut},
    )


def _show(result: dict) -> None:
    status = result["status"]
    if status == "MARKET_CLOSED":
        st.info(result["reason"])
    elif status == "NO_DATA":
        st.warning(result.get("reason", "No data."))
    elif status in ("HALTED", "BAD_ROW", "STALE"):
        st.error(f"{status}: {result.get('reason', '')}")
    else:
        st.success(f"{result.get('datetime')}: ready {result.get('ready')}, "
                   f"{result.get('opportunities')} opportunities")
        if result.get("results"):
            st.dataframe(pd.DataFrame([{
                "strategy": r["strategy"], "outcome": r["status"],
                "why": "; ".join(r.get("reasons", [])) or r.get("reason", ""),
            } for r in result["results"]]), width="stretch")
        if result.get("not_ready"):
            st.caption("Not ready: " + "; ".join(
                f"{k} needs {', '.join(v)}" for k, v in result["not_ready"].items()))


def render() -> None:
    st.subheader("Live prices (Fyers) into the strategies")
    paper = get_controller()
    live = st.session_state.get("live_controller")

    options = ["Paper account"] + (["LIVE controller (real money, if unlocked)"] if live else [])
    target = st.radio("Send opportunities to", options, key="lv_target")
    controller = live if (live and target != "Paper account") else paper
    if controller is live:
        st.error("Target is the LIVE controller. Real orders still need the global flag, armed broker, "
                 "Live switch per strategy, and the risk gate.")
    else:
        st.caption("Prices are real; orders go to the paper account only.")
    st.write(f"Mode of this target: **{controller.mode.value}**" + ("  |  HALTED" if controller.halted else ""))

    if not (os.environ.get("FYERS_APP_ID") and os.environ.get("FYERS_ACCESS_TOKEN")) \
            and st.session_state.get("feed_override") is None:
        st.warning("Set FYERS_APP_ID and FYERS_ACCESS_TOKEN environment variables, then restart the app.")

    spot = st.text_input("Spot symbol", "NSE:NIFTY50-INDEX", key="lv_spot")
    fut = st.text_input("Futures symbol", "NSE:NIFTY26DECFUT", key="lv_fut")
    expiry = st.text_input("Futures expiry (YYYY-MM-DD)", "2026-12-29", key="lv_exp")
    lot = st.number_input("Lot size (units)", min_value=1, value=1, key="lv_lot")
    ignore = st.checkbox("Run even if the market is closed", key="lv_ignore")
    keep = st.checkbox("Keep polling", key="lv_keep")
    interval = st.number_input("Seconds between polls", min_value=3, value=5, key="lv_int")

    def poll() -> None:
        try:
            _show(run_live_step(controller, _feed(spot, fut, expiry), int(lot), ignore_hours=ignore))
        except BrokerError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"{type(exc).__name__}: {exc}")

    if st.button("Fetch live prices once"):
        poll()
    if keep:
        poll()
        time.sleep(float(interval))
        st.rerun()
