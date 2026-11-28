import pandas as pd
import pytest

from brokers import create_broker
from data_engine.schema import merge_derivatives, prepare_spot_frame
from execution.trading_controller import TradingController, TradingMode
from feeds import FeedRunner, ReplayFeed, create_feed, list_feeds
from models.opportunity import Opportunity


def spot(n=4):
    return prepare_spot_frame(pd.DataFrame({
        "datetime": pd.date_range("2026-01-05 09:15", periods=n, freq="1min"),
        "open": 26000.0, "high": 26005.0, "low": 25995.0,
        "close": [26000.0 + i for i in range(n)],
    }))


def with_futures(n=4):
    s = spot(n)
    fut = pd.DataFrame({"datetime": s["datetime"], "futures_price": s["spot_price"] * 1.01,
                        "expiry_date": pd.Timestamp("2026-01-29")})
    return merge_derivatives(s, fut)


class GoodStrategy:
    """Test strategy that emits a fully risk-ready opportunity."""
    REQUIRED_COLUMNS = {"futures_price"}

    def scan(self, df):
        r = df.iloc[0]
        return [Opportunity(
            strategy_id="T1", symbol="NIFTY", market="NSE", opportunity_type="TEST",
            gross_edge=1000.0, estimated_costs=100.0, risk_buffer=100.0, net_edge=800.0,
            capital_required=50000.0, estimated_margin=20000.0, liquidity_score=90.0,
            fill_probability=0.9, confidence_score=0.9,
            legs=[{"instrument": "CASH", "side": "BUY", "price": float(r["spot_price"]), "quantity": 1},
                  {"instrument": "FUTURES", "side": "SELL", "price": float(r["futures_price"]), "quantity": 1}])]


def controller(mode):
    return TradingController(create_broker("PAPER"), mode=mode)


def test_replay_feed_plays_rows_in_order_then_finishes():
    feed = ReplayFeed(spot(3))
    rows = [feed.poll() for _ in range(3)]
    assert [r["spot_price"] for r in rows] == [26000.0, 26001.0, 26002.0]
    assert feed.poll() is None and feed.finished


def test_registry_and_unconnected_live_feeds():
    for name in ("REPLAY", "DHAN", "FYERS", "ANGELONE"):
        assert name in list_feeds()
    with pytest.raises(NotImplementedError):
        create_feed("DHAN").poll()
    with pytest.raises(ValueError):
        create_feed("NOPE")


def test_spot_only_feed_reports_strategies_not_ready_and_trades_nothing():
    c = controller(TradingMode.AUTO)
    result = FeedRunner(ReplayFeed(spot()), c).step()
    assert result["status"] == "OK" and result["ready"] == []
    assert "futures_price" in result["not_ready"]["S01"]
    assert c.broker.get_positions() == []


def test_auto_mode_trades_from_feed():
    c = controller(TradingMode.AUTO)
    runner = FeedRunner(ReplayFeed(with_futures(2)), c, strategies={"T1": GoodStrategy()}, add_costs=False)
    out = runner.run()
    assert [r["status"] for r in out] == ["OK", "OK", "ENDED"]
    assert all(r["results"][0]["status"] == "EXECUTED" for r in out[:2])


def test_semi_auto_queues_for_approval():
    c = controller(TradingMode.SEMI_AUTO)
    FeedRunner(ReplayFeed(with_futures(1)), c, strategies={"T1": GoodStrategy()}, add_costs=False).step()
    assert len(c.list_pending()) == 1 and c.broker.get_positions() == []


def test_halt_stops_the_runner():
    c = controller(TradingMode.AUTO)
    runner = FeedRunner(ReplayFeed(with_futures(3)), c, strategies={"T1": GoodStrategy()}, add_costs=False)
    runner.step()
    c.halt()
    assert runner.step()["status"] == "HALTED"


def test_stale_rows_are_skipped():
    c = controller(TradingMode.AUTO)
    runner = FeedRunner(ReplayFeed(with_futures(1)), c, strategies={"T1": GoodStrategy()},
                        add_costs=False, max_age_seconds=5,
                        now_fn=lambda: pd.Timestamp("2026-01-05 09:30"))
    assert runner.step()["status"] == "STALE"
    assert c.broker.get_positions() == []


def test_real_s01_is_rejected_without_estimators():
    c = controller(TradingMode.AUTO)
    result = FeedRunner(ReplayFeed(with_futures(1)), c, lot_size=75, enricher=None).step()
    s01 = [r for r in result["results"] if r["strategy"] == "S01"]
    assert s01 and s01[0]["status"] == "RISK_REJECTED"
