import pytest

from brokers import (BrokerError, CONFIRM_PHRASE, GuardedBroker, create_broker,
                     list_brokers, register_broker)
from brokers.base import BrokerAdapter
from config import settings
from execution.trading_controller import TradingController, TradingMode
from tests.test_trading_controller import make_opp


class FakeLive(BrokerAdapter):
    NAME, IS_LIVE = "FAKE", True

    def __init__(self):
        self.sent = []

    def submit_order(self, symbol, side, quantity, order_type="LIMIT", price=0.0):
        self.sent.append((symbol, side, quantity, price))
        return {"success": True, "order_id": "1", "filled": True, "fill_price": price}

    def cancel_order(self, order_id): return {"success": True}
    def get_positions(self): return []
    def get_funds(self): return {"cash": 0.0}


def test_registry_lists_all_brokers_and_rejects_unknown():
    for name in ("PAPER", "DHAN", "FYERS", "ANGELONE", "GROWW", "FOREX"):
        assert name in list_brokers()
    with pytest.raises(BrokerError):
        create_broker("NOPE")


def test_new_broker_can_be_registered():
    register_broker("FAKE", FakeLive)
    assert isinstance(create_broker("fake"), FakeLive)


def test_unconnected_real_broker_fails_loudly():
    with pytest.raises(NotImplementedError):
        create_broker("DHAN").submit_order("X", "BUY", 1, "LIMIT", 100.0)


def test_controller_modes_work_on_paper_adapter():
    c = TradingController(create_broker("PAPER"), mode=TradingMode.AUTO)
    assert c.submit_opportunity(make_opp())["status"] == "EXECUTED"
    assert c.manual_order("X", "BUY", 1, 100.0)["success"]


def test_live_blocked_when_disabled_even_if_armed(monkeypatch):
    monkeypatch.setattr(settings, "LIVE_TRADING_ENABLED", False)
    g = GuardedBroker(FakeLive())
    assert g.arm(CONFIRM_PHRASE) is False
    assert not g.submit_order("X", "BUY", 1, "LIMIT", 100.0)["success"]
    assert g.inner.sent == []


def test_live_needs_flag_phrase_and_limits(monkeypatch):
    monkeypatch.setattr(settings, "LIVE_TRADING_ENABLED", True)
    g = GuardedBroker(FakeLive(), max_order_value=1000.0, max_orders_per_day=2)
    assert not g.submit_order("X", "BUY", 1, "LIMIT", 100.0)["success"]   # not armed
    assert g.arm("wrong phrase") is False
    assert g.arm(CONFIRM_PHRASE) is True
    assert not g.submit_order("X", "BUY", 100, "LIMIT", 100.0)["success"]  # too big
    assert g.submit_order("X", "BUY", 1, "LIMIT", 100.0)["success"]
    assert g.submit_order("X", "BUY", 1, "LIMIT", 100.0)["success"]
    assert not g.submit_order("X", "BUY", 1, "LIMIT", 100.0)["success"]   # daily cap


def test_halt_disarms_live_broker(monkeypatch):
    monkeypatch.setattr(settings, "LIVE_TRADING_ENABLED", True)
    g = GuardedBroker(FakeLive())
    g.arm(CONFIRM_PHRASE)
    TradingController(g, mode=TradingMode.AUTO).halt()
    assert g.armed is False
