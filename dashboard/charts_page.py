import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from analytics.candle_patterns import BEARISH, BULLISH, PATTERN_NAMES, detect_patterns, pattern_counts
from dashboard.data_sources import source_picker

RULES = {"1 minute": None, "5 minutes": "5min", "15 minutes": "15min", "1 hour": "1h", "1 day": "1D"}


def resample_ohlc(frame: pd.DataFrame, rule) -> pd.DataFrame:
    data = frame.set_index(pd.to_datetime(frame["datetime"]))
    if rule is None:
        return data.reset_index(drop=True).assign(datetime=data.index)
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    if "volume" in data.columns:
        agg["volume"] = "sum"
    out = data.resample(rule).agg(agg).dropna(subset=["open", "close"])
    out.index.name = "datetime"
    return out.reset_index()


def build_figure(data: pd.DataFrame, patterns: pd.DataFrame, chosen, sma: int, ema: int) -> go.Figure:
    fig = go.Figure(go.Candlestick(
        x=data["datetime"], open=data["open"], high=data["high"],
        low=data["low"], close=data["close"], name="Price"))
    if sma:
        fig.add_trace(go.Scatter(x=data["datetime"], y=data["close"].rolling(sma).mean(),
                                 name=f"SMA {sma}", line=dict(width=1)))
    if ema:
        fig.add_trace(go.Scatter(x=data["datetime"], y=data["close"].ewm(span=ema, adjust=False).mean(),
                                 name=f"EMA {ema}", line=dict(width=1)))
    for name in chosen:
        mask = patterns[name]
        if not mask.any():
            continue
        below = name in BULLISH
        y = data["low"][mask] if below else data["high"][mask]
        fig.add_trace(go.Scatter(
            x=data["datetime"][mask], y=y, mode="markers", name=name.replace("_", " "),
            marker=dict(symbol="triangle-up" if below else "triangle-down" if name in BEARISH else "circle",
                        size=10)))
    fig.update_layout(xaxis_rangeslider_visible=False, height=600, margin=dict(l=10, r=10, t=30, b=10))
    return fig


def _tradingview(symbol: str, interval: str) -> None:
    config = {"autosize": True, "symbol": symbol, "interval": interval, "timezone": "Asia/Kolkata",
              "theme": "dark", "style": "1", "locale": "en", "allow_symbol_change": True,
              "support_host": "https://www.tradingview.com"}
    components.html(
        '<div class="tradingview-widget-container" style="height:600px;width:100%">'
        '<div class="tradingview-widget-container__widget" style="height:calc(100% - 32px);width:100%"></div>'
        '<script type="text/javascript" '
        'src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>'
        + json.dumps(config) + "</script></div>", height=620)


def render() -> None:
    st.subheader("Charts")
    own, tv = st.tabs(["My data (candles + patterns)", "TradingView (view only)"])

    with own:
        frame, label = source_picker("ch")
        timeframe = st.selectbox("Candle size", list(RULES), key="ch_tf")
        c1, c2 = st.columns(2)
        sma = c1.number_input("SMA length (0 = off)", min_value=0, value=20, key="ch_sma")
        ema = c2.number_input("EMA length (0 = off)", min_value=0, value=0, key="ch_ema")
        chosen = st.multiselect("Show patterns", PATTERN_NAMES, default=["bullish_engulfing", "bearish_engulfing"],
                                key="ch_pat")
        if frame is None:
            st.info("Pick or upload a data file.")
        else:
            data = resample_ohlc(frame, RULES[timeframe])
            patterns = detect_patterns(data)
            st.plotly_chart(build_figure(data, patterns, chosen, int(sma), int(ema)), width="stretch")
            st.caption(f"{label}: {len(data)} candles. Pattern markers show candle shapes only; "
                       "they are not trade signals.")
            st.dataframe(pd.DataFrame(sorted(pattern_counts(patterns).items()),
                                      columns=["Pattern", "Count"]), width="stretch")

    with tv:
        st.caption("TradingView hosts this chart, so it needs internet. It is view only: no orders and no "
                   "link to your strategies. If a symbol does not load, change it inside the chart. "
                   "NSE data in free widgets is usually delayed.")
        symbol = st.text_input("Symbol", "NSE:NIFTY", key="tv_symbol")
        interval = st.selectbox("Interval", ["1", "5", "15", "60", "D"], index=1, key="tv_interval")
        _tradingview(symbol, interval)
