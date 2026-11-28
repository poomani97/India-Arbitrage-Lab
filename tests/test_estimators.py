import pandas as pd

from data_engine.schema import merge_derivatives, prepare_spot_frame
from execution.trading_controller import TradingController, TradingMode
from feeds import FeedRunner, ReplayFeed
from models.opportunity import Opportunity
from risk.estimators import (MarginModel, OpportunityEnricher, estimate_confidence,
                             estimate_fill_probability, estimate_liquidity)
from risk.risk_gate import RiskGate


def opp(**kw):
    values = dict(
        strategy_id="S01", symbol="NIFTY", market="NSE", opportunity_type="X",
        gross_edge=1000.0, estimated_costs=100.0, risk_buffer=100.0, net_edge=800.0,
        capital_required=1_950_000.0, cost_breakdown={"cost_input_provided": True},
        legs=[{"instrument": "CASH", "side": "BUY", "price": 26000.0, "quantity": 75},
              {"instrument": "FUTURES", "side": "SELL", "price": 26260.0, "quantity": 75}])
    values.update(kw)
    return Opportunity(**values)


def test_margin_cash_full_futures_percentage():
    result = MarginModel(futures_pct=0.10).estimate(opp())
    assert result["method"] == "leg_percentages"
    assert round(result["margin"]) == round(26000 * 75 + 26260 * 75 * 0.10)


def test_margin_falls_back_to_capital_when_legs_lack_prices():
    o = opp(legs=[{"instrument": "CALL", "action": "SELL", "strike": 26000}])
    result = MarginModel().estimate(o)
    assert result["method"] == "capital_required_fallback"
    assert result["margin"] == o.capital_required


def test_confidence_zero_without_edge_and_higher_with_known_costs():
    assert estimate_confidence(opp(net_edge=0.0)) == 0.0
    known = estimate_confidence(opp())
    unknown = estimate_confidence(opp(cost_breakdown={}, estimated_costs=0.0))
    assert known > unknown and 0 <= known <= 1


def test_fill_probability_drops_with_more_legs_and_thin_volume():
    two = estimate_fill_probability(opp())
    one = estimate_fill_probability(opp(legs=opp().legs[:1]))
    thin = estimate_fill_probability(opp(), volume=500.0)
    assert one > two > thin


def test_liquidity_unknown_stays_zero():
    assert estimate_liquidity(None) == 0.0
    assert estimate_liquidity(500_000) == 50.0


def test_enricher_fills_zeros_but_never_overwrites():
    o = opp(fill_probability=0.7, estimated_margin=123.0)
    OpportunityEnricher().enrich(o, {"volume": 2_000_000})
    assert o.fill_probability == 0.7 and o.estimated_margin == 123.0
    assert o.confidence_score > 0 and o.liquidity_score == 100.0
    assert o.metadata["estimates"]["heuristic"] is True


def test_real_s01_trades_in_auto_when_gate_limits_fit_the_lot():
    s = prepare_spot_frame(pd.DataFrame({
        "datetime": pd.date_range("2026-01-05 09:15", periods=1, freq="1min"),
        "open": 26000.0, "high": 26005.0, "low": 25995.0, "close": 26000.0}))
    fut = pd.DataFrame({"datetime": s["datetime"], "futures_price": 26260.0,
                        "expiry_date": pd.Timestamp("2026-01-29"), "futures_volume": 900000})
    gate = RiskGate(max_capital_per_trade=5_000_000, max_margin_per_trade=5_000_000)
    from brokers.paper_adapter import PaperBrokerAdapter
    from execution.paper_broker import PaperBroker
    c = TradingController(PaperBrokerAdapter(PaperBroker(10_000_000, allow_short=True)),
                          risk_gate=gate, mode=TradingMode.AUTO)
    result = FeedRunner(ReplayFeed(merge_derivatives(s, fut)), c, lot_size=75).step()
    s01 = [r for r in result["results"] if r["strategy"] == "S01"]
    assert s01 and s01[0]["status"] == "EXECUTED"


def test_default_gate_rejects_a_full_nifty_lot_as_too_big():
    o = opp()
    OpportunityEnricher().enrich(o)
    decision = RiskGate().evaluate(o)
    assert not decision.approved
    assert any("exceeds" in r for r in decision.reasons)
