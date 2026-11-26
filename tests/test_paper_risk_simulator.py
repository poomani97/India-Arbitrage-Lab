
import unittest

from paper_trading.risk_simulator import PaperRiskSimulator


class TestPaperRiskSimulator(unittest.TestCase):

    def setUp(self):
        self.simulator = PaperRiskSimulator(
            initial_capital=100000,
            risk_per_trade_pct=1,
            max_risk_per_trade_pct=2,
        )

    def test_initial_capital(self):
        self.assertEqual(
            self.simulator.current_capital,
            100000
        )

    def test_position_size_calculation(self):
        result = self.simulator.calculate_position_size(
            entry_price=100,
            stop_loss=95,
        )

        self.assertEqual(result["risk_amount"], 1000)
        self.assertEqual(result["risk_per_unit"], 5)
        self.assertEqual(result["quantity"], 200)

    def test_profitable_long_trade(self):
        trade = self.simulator.simulate_trade(
            side="LONG",
            entry_price=100,
            exit_price=110,
            stop_loss=95,
        )

        self.assertEqual(trade["gross_pnl"], 2000)
        self.assertEqual(trade["net_pnl"], 2000)
        self.assertEqual(
            self.simulator.current_capital,
            102000
        )

    def test_losing_long_trade(self):
        trade = self.simulator.simulate_trade(
            side="LONG",
            entry_price=100,
            exit_price=98,
            stop_loss=95,
        )

        self.assertEqual(trade["net_pnl"], -400)
        self.assertEqual(
            self.simulator.current_capital,
            99600
        )

    def test_profitable_short_trade(self):
        trade = self.simulator.simulate_trade(
            side="SHORT",
            entry_price=100,
            exit_price=90,
            stop_loss=105,
        )

        self.assertEqual(trade["net_pnl"], 2000)

    def test_invalid_side(self):
        with self.assertRaises(ValueError):
            self.simulator.simulate_trade(
                side="BUY",
                entry_price=100,
                exit_price=110,
                stop_loss=95,
            )

    def test_long_stop_loss_direction(self):
        with self.assertRaises(ValueError):
            self.simulator.simulate_trade(
                side="LONG",
                entry_price=100,
                exit_price=110,
                stop_loss=105,
            )

    def test_short_stop_loss_direction(self):
        with self.assertRaises(ValueError):
            self.simulator.simulate_trade(
                side="SHORT",
                entry_price=100,
                exit_price=90,
                stop_loss=95,
            )

    def test_risk_limit(self):
        with self.assertRaises(ValueError):
            self.simulator.calculate_position_size(
                entry_price=100,
                stop_loss=95,
                risk_percent=3,
            )

    def test_trade_history(self):
        self.simulator.simulate_trade(
            side="LONG",
            entry_price=100,
            exit_price=110,
            stop_loss=95,
        )

        history = self.simulator.get_trade_history()

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["trade_id"], 1)

    def test_summary(self):
        self.simulator.simulate_trade(
            side="LONG",
            entry_price=100,
            exit_price=110,
            stop_loss=95,
        )

        self.simulator.simulate_trade(
            side="LONG",
            entry_price=100,
            exit_price=98,
            stop_loss=95,
        )

        summary = self.simulator.get_summary()

        self.assertEqual(summary["total_trades"], 2)
        self.assertEqual(summary["winning_trades"], 1)
        self.assertEqual(summary["losing_trades"], 1)
        self.assertEqual(summary["win_rate"], 50)

    def test_reset(self):
        self.simulator.simulate_trade(
            side="LONG",
            entry_price=100,
            exit_price=110,
            stop_loss=95,
        )

        self.simulator.reset()

        self.assertEqual(
            self.simulator.current_capital,
            100000
        )
        self.assertEqual(len(self.simulator.trades), 0)


if __name__ == "__main__":
    unittest.main()
  
