import os

import pandas as pd
import streamlit as st

from brokers import list_brokers
from config import settings
from feeds import list_feeds

STATUS = {
    "PAPER": "Ready (practice account)",
    "FYERS": "Code written; not yet tested on a real account",
}


def render() -> None:
    st.subheader("Brokers and data feeds")
    st.write(f"Global live trading flag (config/settings.py): **{'ON' if settings.LIVE_TRADING_ENABLED else 'OFF'}**")
    creds = bool(os.environ.get("FYERS_APP_ID") and os.environ.get("FYERS_ACCESS_TOKEN"))
    st.write(f"Fyers credentials found in environment: **{'yes' if creds else 'no'}**")
    st.dataframe(pd.DataFrame([{
        "Broker": name, "Status": STATUS.get(name, "Not connected yet"),
        "Live feed": name in list_feeds() or name == "PAPER",
    } for name in list_brokers()]), width="stretch")
    st.caption("Dhan, Angel One, Groww, Delta Exchange and forex adapters are placeholders: choosing them "
               "fails with a clear message and sends nothing.")
