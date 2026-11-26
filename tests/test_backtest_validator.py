
import unittest

from backtesting.backtest_validator import (
    BacktestValidator,
)


class TestBacktestValidator(unittest.TestCase):

    def setUp(self):
        self.validator = BacktestValidator()

    def test_valid_trade(self):
        trade = {
            "trade_id": "T001",
            "entry_price": 100,
            "exit_price": 110,
            "pnl": 10,
            "side": "BUY",
        }

        report = self.validator.validate_trade(trade)
        self.assertTrue(report.is_valid)

    def test_invalid_entry_price(self):
        trade = {
            "entry_price": -10,
            "exit_price": 110,
            "pnl": 10,
        }

        report = self.validator.validate_trade(trade)
        self.assertFalse(report.is_valid)

    def test_missing_pnl(self):
        trade = {
            "entry_price": 100,
            "exit_price": 110,
        }

        report = self.validator.validate_trade(trade)
        self.assertFalse(report.is_valid)

    def test_duplicate_trade_id(self):
        trades = [
            {
                "trade_id": "T001",
                "entry_price": 100,
                "exit_price": 110,
                "pnl": 10,
            },
            {
                "trade_id": "T001",
                "entry_price": 110,
                "exit_price": 120,
                "pnl": 10,
            },
        ]

        report = self.validator.validate_trades(trades)
        self.assertFalse(report.is_valid)

    def test_valid_metrics(self):
        metrics = {
            "total_trades": 2,
            "win_rate": 50.0,
            "total_pnl": 100.0,
        }

        report = self.validator.validate_metrics(metrics)
        self.assertTrue(report.is_valid)

    def test_invalid_win_rate(self):
        metrics = {
            "total_trades": 10,
            "win_rate": 150,
            "total_pnl": 100,
        }

        report = self.validator.validate_metrics(metrics)
        self.assertFalse(report.is_valid)

    def test_trade_count_mismatch(self):
        result = {
            "trades": [
                {
                    "entry_price": 100,
                    "exit_price": 110,
                    "pnl": 10,
                }
            ],
            "metrics": {
                "total_trades": 5,
                "win_rate": 100,
                "total_pnl": 10,
            },
        }

        report = self.validator.validate_result(result)
        self.assertFalse(report.is_valid)

    def test_valid_backtest_result(self):
        result = {
            "trades": [
                {
                    "trade_id": "T001",
                    "entry_price": 100,
                    "exit_price": 110,
                    "pnl": 10,
                    "side": "BUY",
                },
                {
                    "trade_id": "T002",
                    "entry_price": 200,
                    "exit_price": 190,
                    "pnl": -10,
                    "side": "SELL",
                },
            ],
            "metrics": {
                "total_trades": 2,
                "win_rate": 50.0,
                "total_pnl": 0.0,
            },
        }

        report = self.validator.validate_result(result)
        self.assertTrue(report.is_valid)
        self.assertEqual(report.status, "PASS")


if __name__ == "__main__":
    unittest.main()
  
