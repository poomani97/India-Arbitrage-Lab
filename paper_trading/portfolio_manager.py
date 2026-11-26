
import math


class PaperPortfolioManager:
    """
    Manages a simulated portfolio for research and paper trading.

    No real orders are placed.
    """

    def __init__(self, initial_capital=100000.0):
        self._validate_positive(
            initial_capital, "initial_capital"
        )

        self.initial_capital = float(initial_capital)
        self.realized_pnl = 0.0
        self.positions = {}
        self.closed_positions = []
        self.next_position_id = 1

    @staticmethod
    def _validate_positive(value, name):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError(
                f"{name} must be a finite positive number."
            )

    @staticmethod
    def _validate_non_negative(value, name):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError(
                f"{name} must be a finite non-negative number."
            )

    def open_position(
        self,
        symbol,
        side,
        quantity,
        entry_price,
    ):
        symbol = str(symbol).strip().upper()
        side = str(side).strip().upper()

        if not symbol:
            raise ValueError("Symbol cannot be empty.")

        if side not in ("LONG", "SHORT"):
            raise ValueError("Side must be LONG or SHORT.")

        self._validate_positive(quantity, "quantity")
        self._validate_positive(entry_price, "entry_price")

        position_id = f"P{self.next_position_id:05d}"

        position = {
            "position_id": position_id,
            "symbol": symbol,
            "side": side,
            "quantity": float(quantity),
            "entry_price": float(entry_price),
            "current_price": float(entry_price),
            "unrealized_pnl": 0.0,
            "status": "OPEN",
        }

        self.positions[position_id] = position
        self.next_position_id += 1

        return dict(position)

    def update_price(self, position_id, current_price):
        self._validate_positive(
            current_price, "current_price"
        )

        if position_id not in self.positions:
            raise KeyError(
                f"Position not found: {position_id}"
            )

        position = self.positions[position_id]

        if position["side"] == "LONG":
            pnl = (
                current_price - position["entry_price"]
            ) * position["quantity"]
        else:
            pnl = (
                position["entry_price"] - current_price
            ) * position["quantity"]

        position["current_price"] = float(current_price)
        position["unrealized_pnl"] = pnl

        return dict(position)

    def close_position(self, position_id, exit_price):
        self._validate_positive(exit_price, "exit_price")

        if position_id not in self.positions:
            raise KeyError(
                f"Position not found: {position_id}"
            )

        position = self.positions.pop(position_id)

        if position["side"] == "LONG":
            pnl = (
                exit_price - position["entry_price"]
            ) * position["quantity"]
        else:
            pnl = (
                position["entry_price"] - exit_price
            ) * position["quantity"]

        closed = dict(position)
        closed["exit_price"] = float(exit_price)
        closed["realized_pnl"] = pnl
        closed["unrealized_pnl"] = 0.0
        closed["status"] = "CLOSED"

        self.realized_pnl += pnl
        self.closed_positions.append(closed)

        return dict(closed)

    def get_open_positions(self):
        return [
            dict(position)
            for position in self.positions.values()
        ]

    def get_closed_positions(self):
        return [
            dict(position)
            for position in self.closed_positions
        ]

    def get_unrealized_pnl(self):
        return sum(
            position["unrealized_pnl"]
            for position in self.positions.values()
        )

    def get_total_exposure(self):
        return sum(
            position["quantity"] * position["current_price"]
            for position in self.positions.values()
        )

    def get_portfolio_value(self):
        return (
            self.initial_capital
            + self.realized_pnl
            + self.get_unrealized_pnl()
        )

    def get_summary(self):
        open_count = len(self.positions)
        closed_count = len(self.closed_positions)

        winning_positions = sum(
            1 for position in self.closed_positions
            if position["realized_pnl"] > 0
        )

        losing_positions = sum(
            1 for position in self.closed_positions
            if position["realized_pnl"] < 0
        )

        win_rate = (
            winning_positions / closed_count * 100
            if closed_count > 0
            else 0.0
        )

        return {
            "initial_capital": self.initial_capital,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.get_unrealized_pnl(),
            "total_pnl": (
                self.realized_pnl
                + self.get_unrealized_pnl()
            ),
            "portfolio_value": self.get_portfolio_value(),
            "total_exposure": self.get_total_exposure(),
            "open_positions": open_count,
            "closed_positions": closed_count,
            "winning_positions": winning_positions,
            "losing_positions": losing_positions,
            "win_rate": win_rate,
        }

    def reset(self):
        self.realized_pnl = 0.0
        self.positions.clear()
        self.closed_positions.clear()
        self.next_position_id = 1

        return self.get_summary()
          
