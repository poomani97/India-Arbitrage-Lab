
import unittest

from paper_trading.portfolio_manager import (
    PaperPortfolioManager,
)


class TestPaperPortfolioManager(unittest.TestCase):

    def setUp(self):
        self.portfolio = PaperPortfolioManager(
            initial_capital=100000
        )

    def test_initial_portfolio(self):
        summary = self.portfolio.get_summary()

        self.assertEqual(summary["initial_capital"], 100000)
        self.assertEqual(summary["portfolio_value"], 100000)
        self.assertEqual(summary["open_positions"], 0)

    def test_open_long_position(self):
        position = self.portfolio.open_position(
            symbol="NIFTY",
            side="LONG",
            quantity=10,
            entry_price=20000,
        )

        self.assertEqual(position["symbol"], "NIFTY")
        self.assertEqual(position["side"], "LONG")
        self.assertEqual(position["status"], "OPEN")

    def test_open_short_position(self):
        position = self.portfolio.open_position(
            symbol="BANKNIFTY",
            side="SHORT",
            quantity=2,
            entry_price=45000,
        )

        self.assertEqual(position["side"], "SHORT")

    def test_update_long_price(self):
        position = self.portfolio.open_position(
            symbol="NIFTY",
            side="LONG",
            quantity=10,
            entry_price=20000,
        )

        updated = self.portfolio.update_price(
            position["position_id"],
            current_price=20100,
        )

        self.assertEqual(
            updated["unrealized_pnl"],
            1000,
        )

    def test_update_short_price(self):
        position = self.portfolio.open_position(
            symbol="NIFTY",
            side="SHORT",
            quantity=10,
            entry_price=20000,
        )

        updated = self.portfolio.update_price(
            position["position_id"],
            current_price=19900,
        )

        self.assertEqual(
            updated["unrealized_pnl"],
            1000,
        )

    def test_close_long_position(self):
        position = self.portfolio.open_position(
            symbol="NIFTY",
            side="LONG",
            quantity=10,
            entry_price=20000,
        )

        closed = self.portfolio.close_position(
            position["position_id"],
            exit_price=20100,
        )

        self.assertEqual(closed["realized_pnl"], 1000)
        self.assertEqual(closed["status"], "CLOSED")
        self.assertEqual(
            self.portfolio.realized_pnl,
            1000,
        )

    def test_close_short_position(self):
        position = self.portfolio.open_position(
            symbol="NIFTY",
            side="SHORT",
            quantity=10,
            entry_price=20000,
        )

        closed = self.portfolio.close_position(
            position["position_id"],
            exit_price=19900,
        )

        self.assertEqual(closed["realized_pnl"], 1000)

    def test_total_exposure(self):
        self.portfolio.open_position(
            symbol="NIFTY",
            side="LONG",
            quantity=2,
            entry_price=20000,
        )

        self.portfolio.open_position(
            symbol="BANKNIFTY",
            side="SHORT",
            quantity=1,
            entry_price=45000,
        )

        self.assertEqual(
            self.portfolio.get_total_exposure(),
            85000,
        )

    def test_portfolio_value_with_unrealized_pnl(self):
        position = self.portfolio.open_position(
            symbol="NIFTY",
            side="LONG",
            quantity=10,
            entry_price=20000,
        )

        self.portfolio.update_price(
            position["position_id"],
            current_price=20100,
        )

        self.assertEqual(
            self.portfolio.get_portfolio_value(),
            101000,
        )

    def test_close_unknown_position(self):
        with self.assertRaises(KeyError):
            self.portfolio.close_position(
                "UNKNOWN",
                exit_price=100,
            )

    def test_invalid_side(self):
        with self.assertRaises(ValueError):
            self.portfolio.open_position(
                symbol="NIFTY",
                side="BUY",
                quantity=1,
                entry_price=20000,
            )

    def test_reset(self):
        self.portfolio.open_position(
            symbol="NIFTY",
            side="LONG",
            quantity=1,
            entry_price=20000,
        )

        summary = self.portfolio.reset()

        self.assertEqual(summary["open_positions"], 0)
        self.assertEqual(summary["realized_pnl"], 0)
        self.assertEqual(summary["portfolio_value"], 100000)


if __name__ == "__main__":
    unittest.main()
  
