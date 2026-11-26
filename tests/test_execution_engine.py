
import unittest

from paper_trading.execution_engine import PaperExecutionEngine


class FakePortfolio:
    def __init__(self):
        self.positions = {}
        self.next_id = 1

    def open_position(self, symbol, side, quantity, entry_price):
        position_id = self.next_id
        self.next_id += 1

        self.positions[position_id] = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "entry_price": entry_price,
        }

        return position_id

    def update_price(self, position_id, current_price):
        self.positions[position_id]["current_price"] = current_price
        return {"updated": True}

    def close_position(self, position_id, exit_price):
        position = self.positions.pop(position_id)
        return {
            "closed": True,
            "exit_price": exit_price,
            "position": position,
        }


class TestPaperExecutionEngine(unittest.TestCase):

    def setUp(self):
        self.portfolio = FakePortfolio()
        self.engine = PaperExecutionEngine(self.portfolio)

    def make_signal(self):
        return {
            "symbol": "NIFTY",
            "side": "BUY",
            "quantity": 50,
            "entry_price": 24000,
        }

    def test_open_paper_trade(self):
        result = self.engine.execute_signal(self.make_signal())

        self.assertEqual(result["status"], "EXECUTED_PAPER")
        self.assertEqual(result["symbol"], "NIFTY")
        self.assertEqual(result["side"], "long")
        self.assertEqual(result["quantity"], 50)

    def test_short_signal(self):
        signal = self.make_signal()
        signal["side"] = "SELL"

        result = self.engine.execute_signal(signal)

        self.assertEqual(result["side"], "short")

    def test_risk_rejection(self):
        engine = PaperExecutionEngine(
            self.portfolio,
            risk_check=lambda signal: False,
        )

        result = engine.execute_signal(self.make_signal())

        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(len(engine.get_active_trades()), 0)

    def test_price_update(self):
        result = self.engine.execute_signal(self.make_signal())
        position_id = result["position_id"]

        update_result = self.engine.update_trade_price(
            position_id, 24100
        )

        self.assertTrue(update_result["updated"])
        self.assertEqual(
            self.engine.active_trades[position_id]["current_price"],
            24100,
        )

    def test_close_trade(self):
        result = self.engine.execute_signal(self.make_signal())
        position_id = result["position_id"]

        closed = self.engine.close_trade(position_id, 24100)

        self.assertEqual(closed["status"], "CLOSED_PAPER")
        self.assertEqual(len(self.engine.get_active_trades()), 0)

    def test_invalid_quantity(self):
        signal = self.make_signal()
        signal["quantity"] = 0

        with self.assertRaises(ValueError):
            self.engine.execute_signal(signal)

    def test_invalid_price(self):
        signal = self.make_signal()
        signal["entry_price"] = -100

        with self.assertRaises(ValueError):
            self.engine.execute_signal(signal)

    def test_unknown_position(self):
        with self.assertRaises(ValueError):
            self.engine.update_trade_price(999, 24000)

    def test_reset(self):
        self.engine.execute_signal(self.make_signal())
        self.engine.reset()

        self.assertEqual(len(self.engine.get_active_trades()), 0)
        self.assertEqual(len(self.engine.get_execution_history()), 0)


if __name__ == "__main__":
    unittest.main()
  
