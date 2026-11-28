from execution.paper_broker import PaperBroker
from execution.trading_controller import TradingController, TradingMode
from models.opportunity import Opportunity


def make_opp(sell_price=26260.0):
    return Opportunity(
        strategy_id="S01", symbol="NIFTY", market="NSE",
        opportunity_type="CASH_FUTURES_CARRY",
        gross_edge=1000.0, estimated_costs=100.0, risk_buffer=100.0, net_edge=800.0,
        capital_required=50000.0, estimated_margin=20000.0,
        liquidity_score=90.0, fill_probability=0.9, confidence_score=0.9,
        legs=[
            {"instrument": "CASH", "side": "BUY", "price": 26000.0, "quantity": 1},
            {"instrument": "FUTURES", "side": "SELL", "price": sell_price, "quantity": 1},
        ],
    )


def controller(mode=TradingMode.MANUAL, cash=1_000_000.0, short=True):
    return TradingController(PaperBroker(cash, allow_short=short), mode=mode)


def test_manual_buy_then_sell():
    c = controller()
    assert c.manual_order("RELIANCE", "BUY", 10, 100.0)["success"]
    assert c.manual_order("RELIANCE", "SELL", 4, 110.0)["success"]
    assert c.broker.get_positions()[0].quantity == 6


def test_manual_rejects_bad_input_and_oversell():
    c = controller(short=False)
    assert not c.manual_order("X", "BUY", 0, 100.0)["success"]
    assert not c.manual_order("X", "BUY", 1, 0)["success"]
    assert not c.manual_order("X", "SELL", 1, 100.0)["success"]


def test_manual_mode_ignores_opportunities():
    c = controller(TradingMode.MANUAL)
    assert c.submit_opportunity(make_opp())["status"] == "IGNORED"
    assert c.broker.get_positions() == []


def test_semi_auto_waits_for_approval():
    c = controller(TradingMode.SEMI_AUTO)
    result = c.submit_opportunity(make_opp())
    assert result["status"] == "PENDING_APPROVAL"
    assert c.broker.get_positions() == []
    assert c.approve(result["id"])["status"] == "EXECUTED"
    assert len(c.broker.get_positions()) == 2


def test_semi_auto_reject_discards():
    c = controller(TradingMode.SEMI_AUTO)
    opp_id = c.submit_opportunity(make_opp())["id"]
    assert c.reject(opp_id)["status"] == "REJECTED_BY_USER"
    assert c.list_pending() == []


def test_auto_executes_both_legs():
    c = controller(TradingMode.AUTO)
    assert c.submit_opportunity(make_opp())["status"] == "EXECUTED"
    quantities = sorted(p.quantity for p in c.broker.get_positions())
    assert quantities == [-1, 1]


def test_auto_respects_risk_gate():
    c = controller(TradingMode.AUTO)
    bad = make_opp()
    bad.estimated_margin = 0.0
    assert c.submit_opportunity(bad)["status"] == "RISK_REJECTED"


def test_halt_stops_automation_but_not_manual():
    c = controller(TradingMode.AUTO)
    c.halt()
    assert c.submit_opportunity(make_opp())["status"] == "HALTED"
    assert c.manual_order("X", "BUY", 1, 100.0)["success"]
    c.resume()
    assert c.submit_opportunity(make_opp())["status"] == "EXECUTED"


def test_halt_clears_pending_queue():
    c = controller(TradingMode.SEMI_AUTO)
    c.submit_opportunity(make_opp())
    c.halt()
    assert c.list_pending() == []


def test_failed_second_leg_unwinds_first():
    c = controller(TradingMode.AUTO, cash=30000.0, short=False)  # cannot short
    result = c.submit_opportunity(make_opp())
    assert result["status"] == "FAILED"
    assert c.broker.get_positions() == []
    assert abs(c.broker.cash - 30000.0) < 1e-6


def test_short_then_cover_pnl():
    b = PaperBroker(100000.0, allow_short=True)
    o = b.place_order("F", "SELL", 5)["order"]; b.execute_fill(o.order_id, 5, 100.0)
    o = b.place_order("F", "BUY", 5)["order"]; b.execute_fill(o.order_id, 5, 90.0)
    assert b.get_positions() == []
    assert round(b.cash, 2) == 100050.0
