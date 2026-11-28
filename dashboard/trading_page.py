"""
India Arbitrage Lab
Trading page: mode switch, halt button, funds, manual buy/sell,
approval queue, positions and activity log. Paper account only.
"""

import pandas as pd
import streamlit as st

from data_engine.schema import merge_derivatives, prepare_spot_frame
from execution.paper_broker import PaperBroker
from execution.strategy_controls import StrategyControls
from execution.trading_controller import TradingController
from feeds import FeedRunner, ReplayFeed
from models.opportunity import Opportunity
from strategies import STRATEGY_CLASSES

CONTROLS_FILE = "state/strategy_controls.json"


def get_controller() -> TradingController:
    if "controller" not in st.session_state:
        st.session_state.controller = TradingController(
            PaperBroker(100000.0, allow_short=True),
            controls=StrategyControls(CONTROLS_FILE),
        )
    return st.session_state.controller


def _demo_opportunity() -> Opportunity:
    """Clearly-labelled TEST opportunity so the buttons can be tried."""
    return Opportunity(
        strategy_id="DEMO", symbol="NIFTY", market="NSE",
        opportunity_type="TEST_DATA",
        gross_edge=1000.0, estimated_costs=100.0, risk_buffer=100.0, net_edge=800.0,
        capital_required=50000.0, estimated_margin=20000.0,
        liquidity_score=90.0, fill_probability=0.9, confidence_score=0.9,
        legs=[
            {"instrument": "CASH", "side": "BUY", "price": 26000.0, "quantity": 1},
            {"instrument": "FUTURES", "side": "SELL", "price": 26260.0, "quantity": 1},
        ],
    )


DEMO_PREMIUM = 1.03   # exaggerated on purpose so a demo trade fires; real edges are far smaller


def _demo_frame(rows: int, premium: float = DEMO_PREMIUM) -> pd.DataFrame:
    """Made-up NIFTY spot + futures prices. DEMO ONLY, not market data."""
    spot = prepare_spot_frame(pd.DataFrame({
        "datetime": pd.date_range("2026-01-05 09:15", periods=rows, freq="1min"),
        "open": 26000.0, "high": 26005.0, "low": 25995.0,
        "close": [26000.0 + i for i in range(rows)],
    }))
    futures = pd.DataFrame({
        "datetime": spot["datetime"],
        "futures_price": spot["spot_price"] * premium,
        "expiry_date": pd.Timestamp("2026-01-29"),
        "futures_volume": 900000,
    })
    return merge_derivatives(spot, futures)


def _strategy_panel(c: TradingController) -> None:
    controls = c.controls
    st.markdown("#### Strategy switches")
    st.caption(
        "Paper is ON and Live is OFF by default. Live switches only matter once a live "
        "broker is connected; this page is on the paper account, so nothing live is sent."
    )
    ack = st.checkbox("I understand live orders use real money", key="live_ack")

    for sid in sorted(STRATEGY_CLASSES):
        paper_on = controls.paper_enabled(sid)
        live_on = controls.live_enabled(sid)
        n = controls.paper_trades(sid)
        col_id, col_paper, col_live, col_n = st.columns([1, 2, 2, 2])
        col_id.write(f"**{sid}**")

        if col_paper.button(
            f"Paper: {'ON' if paper_on else 'OFF'} (tap to switch)", key=f"pp_{sid}"
        ):
            controls.set_paper(sid, not paper_on)
            st.rerun()

        if col_live.button(
            f"Live: {'ON' if live_on else 'OFF'} (tap to switch)", key=f"lv_{sid}"
        ):
            result = controls.set_live(sid, not live_on, acknowledge=ack)
            if result["success"]:
                st.rerun()
            else:
                st.error(f"{sid}: {result['reason']}")

        col_n.caption(f"{n} paper trades (live needs {controls.min_paper_trades})")


def _demo_feed(c: TradingController) -> None:
    st.markdown("#### Demo feed")
    st.caption(
        "Plays made-up NIFTY and futures prices through all strategies. DEMO DATA, not the market: "
        "the futures premium is a deliberately large 3% so a demo trade fires. Real edges are far smaller "
        "and most would be rejected by the risk gate."
    )
    rows = st.slider("Steps", 1, 10, 3, key="demo_rows")
    if st.button("Run demo feed"):
        runner = FeedRunner(ReplayFeed(_demo_frame(rows)), c, lot_size=1)
        outcome = runner.run(max_steps=rows + 1)
        shown = [
            {
                "time": r.get("datetime", r["status"]),
                "ready": ",".join(r.get("ready", [])),
                "opportunities": r.get("opportunities", 0),
                "outcomes": "; ".join(
                    f"{x['strategy']}: {x['status']}"
                    + (f" ({'; '.join(x['reasons'])})" if x.get("reasons") else "")
                    + (f" ({x['reason']})" if x.get("reason") else "")
                    for x in r.get("results", [])
                ),
            }
            for r in outcome
        ]
        st.dataframe(pd.DataFrame(shown), width="stretch")


def _show(result: dict) -> None:
    if result.get("success") or result.get("status") in ("EXECUTED", "PENDING_APPROVAL", "REJECTED_BY_USER"):
        st.success(str(result.get("status", "OK")))
    else:
        st.error(result.get("reason") or result.get("reasons") or result.get("status"))


def render() -> None:
    c = get_controller()
    broker = c.broker

    st.subheader("Paper Trading Control")
    st.caption("Paper account only. No real orders are sent.")

    top1, top2, top3 = st.columns([2, 1, 1])
    with top1:
        labels = {"MANUAL": "Manual", "SEMI_AUTO": "Semi-auto (I approve)", "AUTO": "Auto"}
        choice = st.radio(
            "Mode", list(labels), index=list(labels).index(c.mode.value),
            format_func=labels.get, horizontal=True, key="mode_radio",
        )
        if choice != c.mode.value:
            c.set_mode(choice)
    with top2:
        if st.button("STOP all automation", type="primary", width="stretch"):
            c.halt()
    with top3:
        if st.button("Resume automation", width="stretch", disabled=not c.halted):
            c.resume()

    if c.halted:
        st.error("HALTED: automated trading is stopped. Manual orders still work.")

    summary = broker.get_summary()
    pnl = broker.get_pnl()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Cash", f"{summary['cash']:,.2f}")
    m2.metric("Total deposited", f"{pnl['total_deposited']:,.2f}")
    m3.metric("P&L (at cost)", f"{pnl['pnl']:,.2f}")
    m4.metric("Open positions", summary["active_positions"])

    with st.expander("Funds: add money, withdraw or reset"):
        amount = st.number_input("Amount", min_value=0.0, value=10000.0, step=1000.0, key="funds_amount")
        f1, f2, f3 = st.columns(3)
        if f1.button("Add money"):
            _show(broker.deposit(amount))
        if f2.button("Withdraw"):
            _show(broker.withdraw(amount))
        if f3.button("Reset account with this amount"):
            broker.reset(amount)
            c.pending.clear()
            st.success("Account reset.")

    st.markdown("#### Manual buy / sell")
    with st.form("manual_order"):
        o1, o2, o3, o4 = st.columns(4)
        symbol = o1.text_input("Symbol", value="NIFTY")
        side = o2.selectbox("Side", ["BUY", "SELL"])
        qty = o3.number_input("Quantity", min_value=1, value=1, step=1)
        price = o4.number_input("Price", min_value=0.0, value=100.0)
        if st.form_submit_button("Place paper order"):
            _show(c.manual_order(symbol, side, int(qty), price))

    st.markdown("#### Approval queue (Semi-auto)")
    pending = c.list_pending()
    if not pending:
        st.caption("Nothing waiting.")
    for item in pending:
        a1, a2, a3 = st.columns([4, 1, 1])
        a1.write(f"{item['strategy']} {item['symbol']} | net edge {item['net_edge']}")
        if a2.button("Approve", key="ap_" + item["id"]):
            _show(c.approve(item["id"]))
            st.rerun()
        if a3.button("Reject", key="rj_" + item["id"]):
            _show(c.reject(item["id"]))
            st.rerun()

    if st.button("Send TEST opportunity (demo data)"):
        _show(c.submit_opportunity(_demo_opportunity()))
        st.rerun()

    _strategy_panel(c)
    _demo_feed(c)

    st.markdown("#### Positions")
    positions = broker.get_positions()
    if positions:
        st.dataframe(pd.DataFrame([vars(p) for p in positions]), width="stretch")
    else:
        st.caption("No open positions.")

    with st.expander("Activity log"):
        st.write(c.log[-30:] or "Empty")
