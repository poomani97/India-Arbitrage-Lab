import json

import streamlit as st

from brokers import CONFIRM_PHRASE, BrokerError, create_broker
from config import settings
from dashboard.trading_page import get_controller
from execution.trading_controller import TradingController
from risk.risk_gate import RiskGate
from strategies import STRATEGY_CLASSES

DEFAULT_MAP = {"NIFTY:CASH": "NSE:NIFTY50-INDEX", "NIFTY:FUTURES:2026-12-29": "NSE:NIFTY26DECFUT"}


def _live_controller():
    return st.session_state.get("live_controller")


def render() -> None:
    paper = get_controller()
    controls = paper.controls
    st.subheader("Live Trading (real money)")
    st.error("Everything here can use real money. Nothing is sent unless ALL of these are true: "
             "the global flag is ON, the broker is armed, that strategy's Live switch is ON, "
             "and the risk gate and limits pass.")

    live = _live_controller()
    s1, s2, s3 = st.columns(3)
    s1.metric("Global flag", "ON" if settings.LIVE_TRADING_ENABLED else "OFF")
    s2.metric("Broker connected", "yes" if live else "no")
    s3.metric("Armed", "yes" if live and getattr(live.broker, "armed", False) else "no")
    st.caption("The global flag is set by editing LIVE_TRADING_ENABLED in config/settings.py and restarting. "
               "It is deliberately not a button on this page.")

    st.markdown("#### 1. Connect Fyers (sends nothing)")
    map_text = st.text_area("Symbol map (JSON: your contract key to Fyers symbol)",
                            json.dumps(DEFAULT_MAP, indent=2), key="lt_map")
    c1, c2 = st.columns(2)
    max_value = c1.number_input("Max value per order", min_value=1.0, value=50000.0, key="lt_maxval")
    max_orders = c2.number_input("Max orders per day", min_value=1, value=20, key="lt_maxord")
    cap = st.number_input("Risk gate capital/margin limit per trade", min_value=1000.0, value=100000.0, key="lt_cap")
    if st.button("Connect Fyers live broker"):
        try:
            broker = create_broker("FYERS", symbol_map=json.loads(map_text),
                                   max_order_value=float(max_value), max_orders_per_day=int(max_orders))
            st.session_state.live_controller = TradingController(
                broker, controls=controls,
                risk_gate=RiskGate(max_capital_per_trade=cap, max_margin_per_trade=cap))
            st.rerun()
        except (BrokerError, ValueError) as exc:
            st.error(str(exc))

    live = _live_controller()
    if live is None:
        st.info("Connect a broker to continue.")
        return

    st.markdown("#### 2. Arm / disarm")
    phrase = st.text_input(f"Type exactly: {CONFIRM_PHRASE}", key="lt_phrase")
    a1, a2 = st.columns(2)
    if a1.button("Arm live broker"):
        if live.broker.arm(phrase):
            st.success("Armed.")
        elif not settings.LIVE_TRADING_ENABLED:
            st.error("Not armed: the global flag in config/settings.py is OFF.")
        else:
            st.error("Not armed: the confirmation phrase is wrong.")
    if a2.button("STOP and disarm LIVE", type="primary"):
        live.halt()
        st.warning("Live automation halted and broker disarmed.")
    if live.halted and st.button("Resume live automation"):
        live.resume()

    labels = {"MANUAL": "Manual", "SEMI_AUTO": "Semi-auto (I approve)", "AUTO": "Auto"}
    mode = st.radio("Live mode", list(labels), index=list(labels).index(live.mode.value),
                    format_func=labels.get, horizontal=True, key="lt_mode")
    if mode != live.mode.value:
        live.set_mode(mode)

    st.markdown("#### 3. Live switch per strategy")
    ack = st.checkbox("I understand live orders use real money", key="lt_ack")
    for sid in sorted(STRATEGY_CLASSES):
        on = controls.live_enabled(sid)
        col_a, col_b = st.columns([1, 4])
        col_a.write(f"**{sid}**")
        if col_b.button(f"Live: {'ON' if on else 'OFF'} (tap to switch)", key=f"ltsw_{sid}"):
            result = controls.set_live(sid, not on, acknowledge=ack)
            if result["success"]:
                st.rerun()
            st.error(f"{sid}: {result['reason']}")

    st.markdown("#### 4. Live manual order")
    with st.form("live_manual"):
        f1, f2, f3, f4 = st.columns(4)
        symbol = f1.text_input("Contract key", "NIFTY:FUTURES:2026-12-29")
        side = f2.selectbox("Side", ["BUY", "SELL"])
        qty = f3.number_input("Quantity", min_value=1, value=1, step=1)
        price = f4.number_input("Limit price", min_value=0.0, value=0.0)
        sure = st.checkbox("Send this REAL order")
        if st.form_submit_button("Send live order") and sure:
            result = live.manual_order(symbol, side, int(qty), price)
            (st.success if result.get("success") else st.error)(
                str(result.get("reason") or "Sent. Check your broker's order book."))

    pending = live.list_pending()
    if pending:
        st.markdown("#### Waiting for your approval")
    for item in pending:
        p1, p2, p3 = st.columns([4, 1, 1])
        p1.write(f"{item['strategy']} {item['symbol']} | net edge {item['net_edge']}")
        if p2.button("Approve", key="lap_" + item["id"]):
            st.write(live.approve(item["id"]))
        if p3.button("Reject", key="lrj_" + item["id"]):
            live.reject(item["id"])
            st.rerun()
