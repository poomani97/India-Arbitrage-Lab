from execution.paper_broker import PaperBroker


def _buy(b, symbol="NIFTY", qty=10, price=100.0):
    order = b.place_order(symbol, "BUY", qty)["order"]
    return b.execute_fill(order.order_id, qty, price)


def test_deposit_adds_cash_any_time_repeatedly():
    b = PaperBroker(1000.0)
    assert b.deposit(500)["cash"] == 1500.0
    assert b.deposit(250)["cash"] == 1750.0
    assert b.total_deposited == 1750.0


def test_deposit_rejects_bad_amounts():
    b = PaperBroker(1000.0)
    assert not b.deposit(0)["success"]
    assert not b.deposit(-5)["success"]
    assert not b.deposit(float("nan"))["success"]


def test_topup_makes_a_blocked_buy_possible():
    b = PaperBroker(500.0)
    assert not _buy(b)["success"]
    b.deposit(1000)
    assert _buy(b)["success"]


def test_withdraw_cannot_exceed_cash():
    b = PaperBroker(1000.0)
    assert not b.withdraw(2000)["success"]
    assert b.withdraw(400)["cash"] == 600.0


def test_pnl_ignores_deposits():
    b = PaperBroker(1000.0)
    b.deposit(1000)
    assert b.get_pnl()["pnl"] == 0.0
    _buy(b, qty=10, price=100.0)
    assert b.get_pnl({"NIFTY": 110.0})["pnl"] == 100.0


def test_reset_with_new_amount_and_default():
    b = PaperBroker(1000.0)
    _buy(b)
    b.reset(5000)
    assert b.cash == 5000.0 and b.get_positions() == []
    b.deposit(100)
    b.reset()
    assert b.cash == 5000.0
