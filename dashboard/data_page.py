from collections import Counter

import pandas as pd
import streamlit as st

from brokers.paper_adapter import PaperBrokerAdapter
from dashboard.data_sources import source_picker
from data_engine.schema import check_data_coverage
from execution.paper_broker import PaperBroker
from execution.trading_controller import TradingController, TradingMode
from feeds import FeedRunner, ReplayFeed
from risk.risk_gate import RiskGate


def render() -> None:
    st.subheader("Data coverage and replay test")
    frame, label = source_picker("dp")
    if frame is None:
        st.info("Pick or upload a data file.")
        return

    st.caption(f"{label}: {len(frame)} rows")
    st.dataframe(frame.head(5), width="stretch")

    report = check_data_coverage(frame)
    st.markdown("#### Which strategies can run on this data")
    st.dataframe(pd.DataFrame([{
        "Strategy": sid, "Ready": info["ready"], "Usable rows": info["usable_rows"],
        "Missing columns": ", ".join(info["missing_columns"]),
    } for sid, info in report.items()]), width="stretch")

    st.markdown("#### Replay test (own practice account)")
    st.caption("Plays the file row by row through every ready strategy in AUTO on a separate paper "
               "account. It counts outcomes; it does not calculate profit.")
    lot = st.number_input("Lot size (units)", min_value=1, value=1, key="dp_lot")
    cap = st.number_input("Risk gate capital/margin limit per trade", min_value=1000.0,
                          value=5_000_000.0, key="dp_cap")
    if st.button("Run replay test"):
        controller = TradingController(
            PaperBrokerAdapter(PaperBroker(100_000_000.0, allow_short=True)),
            mode=TradingMode.AUTO,
            risk_gate=RiskGate(max_capital_per_trade=cap, max_margin_per_trade=cap),
        )
        steps = FeedRunner(ReplayFeed(frame), controller, lot_size=int(lot)).run(max_steps=len(frame) + 1)
        ok = [s for s in steps if s["status"] == "OK"]
        outcomes = Counter(r["status"] for s in ok for r in s["results"])
        m1, m2, m3 = st.columns(3)
        m1.metric("Rows played", len(ok))
        m2.metric("Opportunities", sum(s["opportunities"] for s in ok))
        m3.metric("Executed", outcomes.get("EXECUTED", 0))
        if outcomes:
            st.dataframe(pd.DataFrame(sorted(outcomes.items()), columns=["Outcome", "Count"]),
                         width="stretch")
        else:
            st.info("No opportunities: the data lacks the columns the strategies need.")
