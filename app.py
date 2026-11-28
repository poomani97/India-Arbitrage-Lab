import streamlit as st

from config.settings import APP_MODE, APP_NAME, APP_VERSION

st.set_page_config(page_title=APP_NAME, page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")

from dashboard import (brokers_page, charts_page, data_page, history_page, home_page,  # noqa: E402
                       live_page, live_trading_page, strategies_page, trading_page)

PAGES = {
    "Home": home_page.render,
    "Paper Trading": trading_page.render,
    "Live Trading": live_trading_page.render,
    "Charts": charts_page.render,
    "Strategies": strategies_page.render,
    "Live Prices": live_page.render,
    "Data & Replay": data_page.render,
    "Download History": history_page.render,
    "Brokers": brokers_page.render,
}

st.sidebar.title("📊 " + APP_NAME)
st.sidebar.caption(f"Version {APP_VERSION} | Mode: {APP_MODE}")
choice = st.sidebar.radio("Menu", list(PAGES), key="menu")
PAGES[choice]()
