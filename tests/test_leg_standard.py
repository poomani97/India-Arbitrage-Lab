import pandas as pd

from brokers import create_broker
from brokers.base import BrokerAdapter
from execution.trading_controller import TradingController, TradingMode
from models.legs import executable_problems, live_problems, normalize_leg
from models.opportunity import Opportunity
from risk.estimators import OpportunityEnricher
from risk.risk_gate import RiskGate
from strategies import get_strategy


def base_frame():
    dt = pd.date_range("2026-01-05 09:15", periods=1, freq="1min")
    return pd.DataFrame({"datetime": dt, "open": 26000.0, "high": 26005.0, "low": 25995.0,
                         "close": 26000.0, "symbol": "NIFTY"})


def s06_opportunity():
    d = base_frame()
    d["lower_strike"], d["higher_strike"] = 25900, 26100
    d["call_lower_price"], d["call_higher_price"] = 250.0, 120.0
    d["put_lower_price"], d["put_higher_price"] = 90.0, 210.0
    d["expiry_date"] = pd.Timestamp("2026-01-29")
    return get_strategy("S06").scan(d)[0]


def opp(legs, **kw):
    values = dict(strategy_id="X", symbol="NIFTY", market="NSE", opportunity_type="T",
                  gross_edge=1000.0, estimated_costs=100.0, risk_buffer=100.0, net_edge=800.0,
                  capital_required=500000.0, estimated_margin=200000.0, liquidity_score=90.0,
                  fill_probability=0.9, confidence_score=0.9, legs=legs)
    values.update(kw)
    return Opportunity(**values)


def option_legs():
    def leg(kind, side, strike, price):
        return {"instrument": kind, "side": side, "price": price, "quantity": 1,
                "strike": strike, "expiry_date": "2026-01-29"}
    return [leg("CALL", "SELL", 25900, 250.0), leg("CALL", "BUY", 26100, 120.0),
            leg("PUT", "SELL", 26100, 210.0), leg("PUT", "BUY", 25900, 90.0)]


def controller(mode=TradingMode.AUTO, **kw):
    return TradingController(create_broker("PAPER"), mode=mode,
                             risk_gate=RiskGate(max_capital_per_trade=1e9, max_margin_per_trade=1e9), **kw)


def test_normalize_reads_action_and_market_price():
    leg = normalize_leg({"instrument": "NIFTY", "action": "BUY", "market_price": 26000.0, "quantity": 1})
    assert leg["side"] == "BUY" and leg["price"] == 26000.0 and leg["problems"] == []


def test_observation_and_research_legs_are_not_executable():
    leg = normalize_leg({"instrument": "NIFTY", "action": "BUY_OBSERVATION", "price": 1.0, "quantity": 1})
    assert leg["problems"]
    assert normalize_leg({"instrument": "CALL", "action": "RESEARCH_ONLY", "price": 1.0, "quantity": 1})["problems"]


def test_contract_keys_separate_strikes_and_exchanges():
    keys = {normalize_leg(l, "NIFTY")["contract_key"] for l in option_legs()}
    assert len(keys) == 4
    nse = normalize_leg({"instrument": "NIFTY", "exchange": "NSE", "side": "BUY", "price": 1.0, "quantity": 1})
    bse = normalize_leg({"instrument": "NIFTY", "exchange": "BSE", "side": "SELL", "price": 1.0, "quantity": 1})
    assert nse["contract_key"] != bse["contract_key"]


def s05_opportunity():
    d = base_frame()
    d["spot_price"], d["strike_price"] = 26000.0, 26000
    d["call_price"], d["put_price"], d["futures_price"] = 300.0, 200.0, 26260.0
    d["expiry_date"] = pd.Timestamp("2026-01-29")
    return get_strategy("S05").scan(d)[0]


def test_real_s06_is_paper_executable_but_blocked_for_live():
    o = s06_opportunity()
    assert executable_problems(o) == []
    assert any("research" in r.lower() for r in live_problems(o))


def test_real_s05_has_no_sides_so_controller_refuses_it_before_approval():
    c = controller(TradingMode.SEMI_AUTO)
    result = c.submit_opportunity(s05_opportunity())
    assert result["status"] == "NOT_EXECUTABLE" and c.list_pending() == []
    assert any("side" in r.lower() or "research" in r.lower() for r in result["reasons"])


def test_live_broker_refuses_research_only_strategy():
    live = FakeLive()
    c = TradingController(live, mode=TradingMode.AUTO,
                          risk_gate=RiskGate(max_capital_per_trade=1e9, max_margin_per_trade=1e9))
    result = c.submit_opportunity(s06_opportunity())
    assert result["status"] == "NOT_EXECUTABLE" and live.sent == []


def test_four_option_legs_keep_four_separate_positions():
    c = controller()
    assert c.submit_opportunity(opp(option_legs()))["status"] == "EXECUTED"
    assert len(c.broker.get_positions()) == 4


def test_single_leg_blocked_by_default_and_allowed_on_request():
    one = [{"instrument": "FUTURES", "side": "SELL", "price": 26260.0, "quantity": 1}]
    assert controller().submit_opportunity(opp(one))["status"] == "NOT_EXECUTABLE"
    assert controller(allow_single_leg=True).submit_opportunity(opp(one))["status"] == "EXECUTED"


def test_unverified_hedge_blocks_execution():
    o = opp(option_legs(), metadata={"complete_hedge_verified": False})
    assert any("hedge" in r.lower() for r in executable_problems(o))


class FakeLive(BrokerAdapter):
    NAME, IS_LIVE = "FAKE", True
    def __init__(self): self.sent = []
    def submit_order(self, *a, **k): self.sent.append(a); return {"success": True, "filled": True}
    def cancel_order(self, order_id): return {"success": True}
    def get_positions(self): return []
    def get_funds(self): return {}


def test_live_broker_refuses_strategies_that_forbid_live():
    live = FakeLive()
    c = TradingController(live, mode=TradingMode.AUTO,
                          risk_gate=RiskGate(max_capital_per_trade=1e9, max_margin_per_trade=1e9))
    o = opp(option_legs(), metadata={"live_trading_allowed": False})
    assert c.submit_opportunity(o)["status"] == "NOT_EXECUTABLE"
    assert live.sent == []


def test_enricher_fills_capital_from_legs_when_strategy_left_it_zero():
    o = opp(option_legs(), capital_required=0.0, estimated_margin=0.0)
    OpportunityEnricher().enrich(o)
    assert o.capital_required > 0 and o.estimated_margin > 0
