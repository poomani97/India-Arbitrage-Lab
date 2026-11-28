from brokers import create_broker
from brokers.base import BrokerAdapter
from execution.strategy_controls import StrategyControls
from execution.trading_controller import TradingController, TradingMode
from risk.estimators import OpportunityEnricher
from risk.risk_gate import RiskGate
from tests.test_leg_standard import opp, option_legs, s06_opportunity

GATE = dict(max_capital_per_trade=1e9, max_margin_per_trade=1e9)


def enriched_s06():
    """Like FeedRunner: fill margin/confidence/fill/capital before the controller sees it."""
    return OpportunityEnricher().enrich(s06_opportunity(), {"volume": 5_000_000})


class FakeLive(BrokerAdapter):
    NAME, IS_LIVE = "FAKE", True

    def __init__(self):
        self.sent = []

    def submit_order(self, symbol, side, quantity, order_type="LIMIT", price=0.0):
        self.sent.append((symbol, side, quantity, price))
        return {"success": True, "order_id": "1", "filled": True, "fill_price": price}

    def cancel_order(self, order_id): return {"success": True}
    def get_positions(self): return []
    def get_funds(self): return {}


def paper_controller(controls):
    return TradingController(create_broker("PAPER"), mode=TradingMode.AUTO,
                             risk_gate=RiskGate(**GATE), controls=controls)


def live_controller(controls, live=None):
    return TradingController(live or FakeLive(), mode=TradingMode.AUTO,
                             risk_gate=RiskGate(**GATE), controls=controls)


def test_defaults_paper_on_live_off():
    c = StrategyControls()
    assert c.paper_enabled("S01") and not c.live_enabled("S01")


def test_paper_off_blocks_paper_trades():
    c = StrategyControls()
    c.set_paper("X", False)
    result = paper_controller(c).submit_opportunity(opp(option_legs()))
    assert result["status"] == "STRATEGY_OFF"


def test_paper_trades_are_counted():
    c = StrategyControls()
    ctl = paper_controller(c)
    ctl.submit_opportunity(opp(option_legs()))
    assert c.paper_trades("X") == 1


def test_live_needs_acknowledge_and_paper_history():
    c = StrategyControls(min_paper_trades=2)
    assert not c.set_live("X", True)["success"]
    assert not c.set_live("X", True, acknowledge=True)["success"]
    c.record_paper_trade("X"); c.record_paper_trade("X")
    assert not c.set_live("X", True)["success"]
    assert c.set_live("X", True, acknowledge=True)["success"]
    assert c.live_enabled("X")


def test_live_can_always_be_switched_off():
    c = StrategyControls(min_paper_trades=0)
    c.set_live("X", True, acknowledge=True)
    assert c.set_live("X", False)["success"] and not c.live_enabled("X")


def test_live_broker_blocked_when_strategy_live_is_off():
    live = FakeLive()
    c = StrategyControls(min_paper_trades=0)
    result = live_controller(c, live).submit_opportunity(opp(option_legs()))
    assert result["status"] == "STRATEGY_OFF" and live.sent == []


def test_live_switch_on_lifts_research_only_flag_for_that_strategy_only():
    live = FakeLive()
    c = StrategyControls(min_paper_trades=0)
    assert live_controller(c, live).submit_opportunity(enriched_s06())["status"] == "STRATEGY_OFF"
    c.set_live("S06", True, acknowledge=True)
    result = live_controller(c, live).submit_opportunity(enriched_s06())
    assert result["status"] == "EXECUTED" and len(live.sent) == 4
    c.set_live("S06", False)
    assert live_controller(c, live).submit_opportunity(enriched_s06())["status"] == "STRATEGY_OFF"


def test_live_switch_for_one_strategy_does_not_unlock_another():
    live = FakeLive()
    c = StrategyControls(min_paper_trades=0)
    c.set_live("S01", True, acknowledge=True)
    result = live_controller(c, live).submit_opportunity(enriched_s06())
    assert result["status"] == "STRATEGY_OFF" and live.sent == []


def test_live_switch_does_not_bypass_missing_side_or_hedge_checks():
    live = FakeLive()
    c = StrategyControls(min_paper_trades=0)
    c.set_live("X", True, acknowledge=True)
    bad = opp(option_legs(), metadata={"complete_hedge_verified": False})
    assert live_controller(c, live).submit_opportunity(bad)["status"] == "NOT_EXECUTABLE"
    assert live.sent == []


def test_settings_survive_restart(tmp_path):
    path = tmp_path / "controls.json"
    a = StrategyControls(str(path), min_paper_trades=0)
    a.set_paper("S03", False)
    a.set_live("S01", True, acknowledge=True)
    b = StrategyControls(str(path))
    assert not b.paper_enabled("S03") and b.live_enabled("S01")


def test_two_boundary_still_guarded_broker_blocks_without_global_flag():
    from brokers import GuardedBroker
    from config import settings
    assert settings.LIVE_TRADING_ENABLED is False
    live = FakeLive()
    guard = GuardedBroker(live)
    c = StrategyControls(min_paper_trades=0)
    c.set_live("X", True, acknowledge=True)
    ctl = TradingController(guard, mode=TradingMode.AUTO, risk_gate=RiskGate(**GATE), controls=c)
    ctl.submit_opportunity(opp(option_legs()))
    assert live.sent == []
