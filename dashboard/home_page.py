import streamlit as st

from config import settings
from dashboard.trading_page import get_controller


def render() -> None:
    c = get_controller()
    st.title("📊 India Arbitrage Lab")
    st.caption(f"Version {settings.APP_VERSION} | Mode: {settings.APP_MODE}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Paper mode", c.mode.value)
    m2.metric("Paper cash", f"{c.broker.cash:,.0f}")
    m3.metric("Automation", "HALTED" if c.halted else "Running")
    m4.metric("Live trading flag", "ON" if settings.LIVE_TRADING_ENABLED else "OFF")

    st.info(
        "Use the menu on the left. Paper Trading is the practice account; Live Trading is the "
        "separate real-money area and stays locked until you unlock it on purpose."
    )
    st.markdown(
        "- **Paper Trading**: manual, semi-auto and auto modes, refillable money, stop button\n"
        "- **Live Trading**: connect a broker, arm it, per-strategy Live switches, live manual orders\n"
        "- **Strategies**: S01 to S10 details, and scan any of them on your data\n"
        "- **Live Prices**: Fyers prices into the strategies\n"
        "- **Data & Replay**: check data coverage and replay a file through all strategies\n"
        "- **Download History**: save Fyers candles to CSV for backtesting\n"
        "- **Brokers**: connection status"
    )
    st.warning("Research and simulation tool. Estimates are heuristics; verify every number before real money.")
