import pandas as pd

from brokers.paper_adapter import PaperBrokerAdapter
from execution.paper_broker import PaperBroker
from execution.trading_controller import TradingController, TradingMode
from feeds.fyers_feed import FyersFeed
from feeds.live import market_open, run_live_step
from risk.risk_gate import RiskGate
from tests.test_fyers import FakeClient

OPEN_TIME = pd.Timestamp("2026-12-01 10:30")      # a Tuesday
COLUMNS = {"spot_price": "NSE:NIFTY50-INDEX", "futures_price": "NSE:NIFTY26DECFUT"}


def quotes(premium=1.03, volume=900000):
    return {"s": "ok", "d": [
        {"n": "NSE:NIFTY50-INDEX", "s": "ok", "v": {"lp": 26000.0}},
        {"n": "NSE:NIFTY26DECFUT", "s": "ok", "v": {"lp": 26000.0 * premium, "volume": volume}}]}


def setup(mode, client, **feed_kw):
    feed = FyersFeed(COLUMNS, constants={"symbol": "NIFTY", "expiry_date": "2026-12-29"},
                     client=client, **feed_kw)
    controller = TradingController(
        PaperBrokerAdapter(PaperBroker(10_000_000, allow_short=True)), mode=mode,
        risk_gate=RiskGate(max_capital_per_trade=5e6, max_margin_per_trade=5e6))
    return feed, controller


def test_market_hours():
    assert market_open(OPEN_TIME)
    assert not market_open(pd.Timestamp("2026-12-01 16:00"))
    assert not market_open(pd.Timestamp("2026-12-05 11:00"))   # Saturday


def test_closed_market_skips_without_polling():
    client = FakeClient(quotes=quotes())
    feed, controller = setup(TradingMode.AUTO, client)
    result = run_live_step(controller, feed, now=pd.Timestamp("2026-12-05 11:00"))
    assert result["status"] == "MARKET_CLOSED"
    assert controller.broker.get_positions() == []


def test_live_prices_trade_on_paper_and_never_touch_fyers_orders():
    client = FakeClient(quotes=quotes())
    feed, controller = setup(TradingMode.AUTO, client, volume_columns={"futures_volume": "NSE:NIFTY26DECFUT"})
    result = run_live_step(controller, feed, now=OPEN_TIME)
    assert result["status"] == "OK" and "S01" in result["ready"]
    assert [r["status"] for r in result["results"] if r["strategy"] == "S01"] == ["EXECUTED"]
    assert len(controller.broker.get_positions()) == 2
    assert client.orders == []                 # the live broker API was never asked to trade


def test_missing_price_gives_no_data_with_reason():
    bad = {"s": "ok", "d": [{"n": "NSE:NIFTY50-INDEX", "s": "ok", "v": {"lp": 26000.0}}]}
    feed, controller = setup(TradingMode.AUTO, FakeClient(quotes=bad))
    result = run_live_step(controller, feed, now=OPEN_TIME)
    assert result["status"] == "NO_DATA" and "NIFTY26DECFUT" in result["reason"]


def test_volume_is_optional():
    feed, _ = setup(TradingMode.AUTO, FakeClient(quotes=quotes()),
                    volume_columns={"futures_volume": "NSE:NIFTY26DECFUT"})
    row = feed.poll()
    assert row["futures_volume"] == 900000
    no_volume = {"s": "ok", "d": [
        {"n": "NSE:NIFTY50-INDEX", "s": "ok", "v": {"lp": 26000.0}},
        {"n": "NSE:NIFTY26DECFUT", "s": "ok", "v": {"lp": 26100.0}}]}
    feed2, _ = setup(TradingMode.AUTO, FakeClient(quotes=no_volume),
                     volume_columns={"futures_volume": "NSE:NIFTY26DECFUT"})
    assert "futures_volume" not in feed2.poll()


def test_live_row_carries_ohlc_placeholders_so_strategies_do_not_skip_it():
    feed, _ = setup(TradingMode.AUTO, FakeClient(quotes=quotes()))
    row = feed.poll()
    assert row["open"] == row["high"] == row["low"] == row["close"] == row["spot_price"]
