import pandas as pd
import streamlit as st

from dashboard.data_sources import source_picker
from dashboard.trading_page import get_controller
from pricing.cost_model import add_cost_column
from strategies import STRATEGY_CLASSES, get_strategy

NOTES = {
    "S02": "Single leg (unhedged): blocked unless single legs are allowed.",
    "S07": "Single leg (unhedged): blocked unless single legs are allowed.",
    "S05": "Strategy marks its legs RESEARCH_ONLY with no side: not tradable.",
    "S09": "Observation only: not tradable.",
    "S06": "Paper only (research_only flag); needs its Live switch to go live.",
    "S10": "Needs event data; gave no signal on my sample data.",
}


def _make(sid: str, lot: int):
    try:
        return get_strategy(sid, config={"default_lot_size": lot})
    except Exception:
        return get_strategy(sid)


def render() -> None:
    c = get_controller()
    st.subheader("Strategies S01 to S10")
    st.caption("Notes come from my testing with sample data.")

    rows = []
    for sid in sorted(STRATEGY_CLASSES):
        cls = STRATEGY_CLASSES[sid]
        rows.append({
            "ID": sid,
            "Name": getattr(cls, "STRATEGY_NAME", sid),
            "Needs columns": ", ".join(sorted(getattr(cls, "REQUIRED_COLUMNS", []))),
            "Paper": "ON" if c.controls.paper_enabled(sid) else "OFF",
            "Live": "ON" if c.controls.live_enabled(sid) else "OFF",
            "Paper trades": c.controls.paper_trades(sid),
            "Note": NOTES.get(sid, ""),
        })
    st.dataframe(pd.DataFrame(rows), width="stretch")

    st.markdown("#### Scan one strategy on your data")
    sid = st.selectbox("Strategy", sorted(STRATEGY_CLASSES), key="st_pick")
    cls = STRATEGY_CLASSES[sid]
    st.write(getattr(cls, "STRATEGY_DESCRIPTION", ""))
    lot = st.number_input("Lot size (units)", min_value=1, value=1, key="st_lot")
    with_costs = st.checkbox("Include estimated costs", value=True, key="st_costs")
    frame, label = source_picker("st")

    if st.button("Scan this strategy on the data") and frame is not None:
        missing = [col for col in sorted(getattr(cls, "REQUIRED_COLUMNS", set())) if col not in frame.columns]
        if missing:
            st.warning("This data is missing columns: " + ", ".join(missing))
            return
        data = add_cost_column(frame, lot_size=int(lot)) if with_costs else frame
        try:
            found = _make(sid, int(lot)).scan(data)
        except Exception as exc:
            st.error(f"{type(exc).__name__}: {exc}")
            return
        st.success(f"{len(found)} opportunities found in {len(frame)} rows of {label}.")
        if found:
            st.dataframe(pd.DataFrame([{
                "type": o.opportunity_type, "symbol": o.symbol,
                "gross_edge": round(o.gross_edge, 2), "costs": round(o.estimated_costs, 2),
                "net_edge": round(o.net_edge, 2), "legs": len(o.legs),
            } for o in found[:200]]), width="stretch")
