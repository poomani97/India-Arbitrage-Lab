import pytest

from brokers import BrokerError, GuardedBroker, create_broker, CONFIRM_PHRASE
from brokers.fyers_adapter import FyersBroker
from config import settings
from execution.trading_controller import TradingController, TradingMode
from feeds.fyers_feed import FyersFeed
from risk.risk_gate import RiskGate
from tests.test_leg_standard import opp

MAP = {"NIFTY:CASH": "NSE:NIFTY50-INDEX", "NIFTY:FUTURES": "NSE:NIFTY26DECFUT"}


class FakeClient:
    def __init__(self, accept=True, quotes=None):
        self.orders, self.accept, self.cancelled = [], accept, []
        self._quotes = quotes

    def place_order(self, data):
        self.orders.append(data)
        return {"s": "ok", "id": f"ID{len(self.orders)}"} if self.accept else {"s": "error", "message": "RMS reject"}

    def cancel_order(self, data):
        self.cancelled.append(data["id"])
        return {"s": "ok"}

    def positions(self):
        return {"s": "ok", "netPositions": [{"symbol": "NSE:NIFTY26DECFUT", "netQty": 75}]}

    def funds(self):
        return {"s": "ok", "fund_limit": [{"title": "Available Balance", "equityAmount": 12345.5}]}

    def quotes(self, data):
        return self._quotes if self._quotes is not None else {"s": "ok", "d": [
            {"n": "NSE:NIFTY50-INDEX", "s": "ok", "v": {"lp": 26000.5}},
            {"n": "NSE:NIFTY26DECFUT", "s": "ok", "v": {"lp": 26120.0}}]}


def broker(**kw):
    return FyersBroker(client=kw.pop("client", FakeClient()), symbol_map=MAP, **kw)


def test_order_payload_matches_fyers_format():
    client = FakeClient()
    result = broker(client=client).submit_order("NIFTY:FUTURES", "SELL", 75, "LIMIT", 26120.0)
    assert result["success"] and result["order_id"] == "ID1" and result["filled"] is False
    sent = client.orders[0]
    assert sent["symbol"] == "NSE:NIFTY26DECFUT" and sent["side"] == -1 and sent["type"] == 1
    assert sent["qty"] == 75 and sent["limitPrice"] == 26120.0 and sent["validity"] == "DAY"


def test_unmapped_symbol_is_refused_and_nothing_is_sent():
    client = FakeClient()
    result = broker(client=client).submit_order("NIFTY:CALL:26000", "BUY", 75, "LIMIT", 100.0)
    assert not result["success"] and client.orders == []


def test_bad_inputs_refused():
    b = broker()
    assert not b.submit_order("NIFTY:CASH", "HOLD", 1, "LIMIT", 1.0)["success"]
    assert not b.submit_order("NIFTY:CASH", "BUY", 0, "LIMIT", 1.0)["success"]
    assert not b.submit_order("NIFTY:CASH", "BUY", 1, "LIMIT", 0.0)["success"]


def test_broker_rejection_is_reported():
    result = broker(client=FakeClient(accept=False)).submit_order("NIFTY:CASH", "BUY", 1, "LIMIT", 1.0)
    assert not result["success"] and "RMS reject" in result["reason"]


def test_positions_and_funds_parsed():
    b = broker()
    assert b.get_positions()[0]["netQty"] == 75
    assert b.get_funds() == {"Available Balance": 12345.5}


def test_missing_credentials_fail_loudly(monkeypatch):
    monkeypatch.delenv("FYERS_APP_ID", raising=False)
    monkeypatch.delenv("FYERS_ACCESS_TOKEN", raising=False)
    with pytest.raises(BrokerError):
        create_broker("FYERS")


def test_registry_returns_guarded_broker(monkeypatch):
    monkeypatch.setenv("FYERS_APP_ID", "X-100")
    monkeypatch.setenv("FYERS_ACCESS_TOKEN", "t")
    try:
        import fyers_apiv3  # noqa: F401
    except ImportError:
        pytest.skip("fyers-apiv3 not installed")
    assert isinstance(create_broker("FYERS"), GuardedBroker)


def test_guard_blocks_fyers_when_global_flag_off(monkeypatch):
    monkeypatch.setattr(settings, "LIVE_TRADING_ENABLED", False)
    client = FakeClient()
    g = GuardedBroker(broker(client=client))
    g.arm(CONFIRM_PHRASE)
    assert not g.submit_order("NIFTY:CASH", "BUY", 1, "LIMIT", 100.0)["success"]
    assert client.orders == []


def test_unconfirmed_fill_halts_automation_instead_of_guessing(monkeypatch):
    monkeypatch.setattr(settings, "LIVE_TRADING_ENABLED", True)
    from execution.strategy_controls import StrategyControls
    client = FakeClient()
    g = GuardedBroker(broker(client=client), max_order_value=1e9)
    g.arm(CONFIRM_PHRASE)
    controls = StrategyControls(min_paper_trades=0)
    controls.set_live("X", True, acknowledge=True)
    ctl = TradingController(g, mode=TradingMode.AUTO, controls=controls,
                            risk_gate=RiskGate(max_capital_per_trade=1e9, max_margin_per_trade=1e9))
    legs = [{"instrument": "CASH", "side": "BUY", "price": 26000.0, "quantity": 75},
            {"instrument": "FUTURES", "side": "SELL", "price": 26120.0, "quantity": 75}]
    result = ctl.submit_opportunity(opp(legs))
    assert result["status"] == "UNCONFIRMED_FILL"
    assert len(client.orders) == 1 and ctl.halted and g.armed is False


def test_feed_returns_a_row_with_prices_and_constants():
    feed = FyersFeed({"spot_price": "NSE:NIFTY50-INDEX", "futures_price": "NSE:NIFTY26DECFUT"},
                     constants={"symbol": "NIFTY", "expiry_date": "2026-12-29"}, client=FakeClient())
    row = feed.poll()
    assert row["spot_price"] == 26000.5 and row["futures_price"] == 26120.0
    assert row["symbol"] == "NIFTY" and "datetime" in row


def test_feed_returns_none_if_any_price_is_missing():
    bad = {"s": "ok", "d": [{"n": "NSE:NIFTY50-INDEX", "s": "ok", "v": {"lp": 26000.5}}]}
    feed = FyersFeed({"spot_price": "NSE:NIFTY50-INDEX", "futures_price": "NSE:NIFTY26DECFUT"},
                     client=FakeClient(quotes=bad))
    assert feed.poll() is None and "NIFTY26DECFUT" in feed.last_error
