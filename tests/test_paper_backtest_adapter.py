
import unittest

from backtesting.paper_backtest_adapter import PaperBacktestAdapter


class FakeExecutionEngine:
    def __init__(self):
        self.active_trades = {}
        self.next_id = 1

    def execute_signal(self, signal):
        position_id = self.next_id
        self.next_id += 1

        self.active_trades[position_id] = {
            "symbol": signal["symbol"],
            "side": signal["side"],
            "quantity": signal["quantity"],
            "entry_price": signal["entry_price"],
        }

        return {
            "status": "EXECUTED_PAPER",
            "position_id": position_id,
        }

    def update_trade_price(self, position_id, current_price):
        self.active_trades[position_id]["current_price"] = current_price
        return {"updated": True}

    def close_trade(self, position_id, exit_price):
        trade = self.active_trades.pop(position_id)

        return {
            "status": "CLOSED_PAPER",
            "exit_price": exit_price,
            "trade": trade,
        }


class TestPaperBacktestAdapter(unittest.TestCase):

    def setUp(self):
        self.engine = FakeExecutionEngine()

    def candles(self):
        return [
            {
                "timestamp": "2026-01-01 09:15",
                "open": 100,
                "high": 102,
                "low": 99,
                "close": 101,
            },
            {
                "timestamp": "2026-01-01 09:16",
                "open": 101,
                "high": 104,
                "low": 100,
                "close": 103,
            },
        ]

    def test_backtest_opens_and_finally_closes_trade(self):
        def strategy(bar, history):
            if len(history) == 1:
                return {
                    "side": "BUY",
                    "quantity": 1,
                    "entry_price": bar["close"],
                }
            return None

        adapter = PaperBacktestAdapter(
            self.engine,
            strategy_callback=strategy,
        )

        report = adapter.run(self.candles(), "NIFTY")

        self.assertEqual(report["opened_trades"], 1)
        self.assertEqual(report["closed_trades"], 1)
        self.assertEqual(report["mode"], "HISTORICAL_PAPER_BACKTEST")
        self.assertTrue(report["paper_only"])

    def test_empty_candles_rejected(self):
        adapter = PaperBacktestAdapter(
            self.engine,
            strategy_callback=lambda bar, history: None,
        )

        with self.assertRaises(ValueError):
            adapter.run([], "NIFTY")

    def test_invalid_candle_rejected(self):
        adapter = PaperBacktestAdapter(
            self.engine,
            strategy_callback=lambda bar, history: None,
        )

        bad_candles = [{
            "timestamp": "2026-01-01",
            "open": 100,
            "high": 90,
            "low": 95,
            "close": 98,
        }]

        with self.assertRaises(ValueError):
            adapter.run(bad_candles, "NIFTY")

    def test_exit_callback_closes_trade(self):
        def strategy(bar, history):
            if len(history) == 1:
                return {
                    "side": "BUY",
                    "quantity": 1,
                    "entry_price": bar["close"],
                }
            return None

        def exit_signal(bar, active_trade):
            return bar["close"] >= 103

        adapter = PaperBacktestAdapter(
            self.engine,
            strategy_callback=strategy,
            exit_callback=exit_signal,
        )

        report = adapter.run(self.candles(), "NIFTY")

        self.assertEqual(report["opened_trades"], 1)
        self.assertEqual(report["closed_trades"], 1)


if __name__ == "__main__":
    unittest.main()
  
