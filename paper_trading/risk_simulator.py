
import math


class PaperRiskSimulator:
    """
    Educational paper-trading risk and PnL simulator.
    Does not connect to brokers or place real orders.
    """

    def __init__(
        self,
        initial_capital=100000.0,
        risk_per_trade_pct=1.0,
        max_risk_per_trade_pct=2.0,
        fee_per_unit=0.0,
    ):
        self._validate_positive(
            initial_capital, "initial_capital"
        )
        self._validate_positive(
            risk_per_trade_pct, "risk_per_trade_pct"
        )
        self._validate_positive(
            max_risk_per_trade_pct, "max_risk_per_trade_pct"
        )
        self._validate_non_negative(
            fee_per_unit, "fee_per_unit"
        )

        if risk_per_trade_pct > max_risk_per_trade_pct:
            raise ValueError(
                "Risk per trade cannot exceed the maximum risk limit."
            )

        self.initial_capital = float(initial_capital)
        self.current_capital = float(initial_capital)
        self.risk_per_trade_pct = float(risk_per_trade_pct)
        self.max_risk_per_trade_pct = float(
            max_risk_per_trade_pct
        )
        self.fee_per_unit = float(fee_per_unit)

        self.trades = []
        self.next_trade_id = 1

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

    def calculate_position_size(
        self,
        entry_price,
        stop_loss,
        risk_percent=None,
    ):
        self._validate_positive(entry_price, "entry_price")
        self._validate_positive(stop_loss, "stop_loss")

        if entry_price == stop_loss:
            raise ValueError(
                "Entry price and stop loss cannot be equal."
            )

        if risk_percent is None:
            risk_percent = self.risk_per_trade_pct

        self._validate_positive(
            risk_percent, "risk_percent"
        )

        if risk_percent > self.max_risk_per_trade_pct:
            raise Value ValueError(
                "Requested risk exceeds the maximum risk limit."
            )

        risk_amount = (
            self.current_capital * risk_percent / 100.0
        )

        risk_per_unit = abs(entry_price - stop_loss)

        quantity = risk_amount / risk_per_unit

        return {
            "risk_amount": risk_amount,
            "risk_per_unit": risk_per_unit,
            "quantity": quantity,
            "risk_percent": risk_percent,
        }

    def simulate_trade(
        self,
        side,
        entry_price,
        exit_price,
        stop_loss,
        risk_percent=None,
    ):
        side = str(side).upper()

        if side not in ("LONG", "SHORT"):
            raise ValueError(
                "side must be LONG or SHORT."
            )

        self._validate_positive(entry_price, "entry_price")
        self._validate_positive(exit_price, "exit_price")
        self._validate_positive(stop_loss, "stop_loss")

        if side == "LONG" and stop_loss >= entry_price:
            raise ValueError(
                "LONG trade stop loss must be below entry price."
            )

        if side == "SHORT" and stop_loss <= entry_price:
            raise ValueError(
                "SHORT trade stop loss must be above entry price."
            )

        sizing = self.calculate_position_size(
            entry_price=entry_price,
            stop_loss=stop_loss,
            risk_percent=risk_percent,
        )

        quantity = sizing["quantity"]

        if side == "LONG":
            gross_pnl = (exit_price - entry_price) * quantity
        else:
            gross_pnl = (entry_price - exit_price) * quantity

        fees = quantity * self.fee_per_unit * 2
        net_pnl = gross_pnl - fees

        capital_before = self.current_capital
        capital_after = capital_before + net_pnl

        trade = {
            "trade_id": self.next_trade_id,
            "side": side,
            "entry_price": float(entry_price),
            "exit_price": float(exit_price),
            "stop_loss": float(stop_loss),
            "quantity": quantity,
            "risk_amount": sizing["risk_amount"],
            "risk_percent": sizing["risk_percent"],
            "gross_pnl": gross_pnl,
            "fees": fees,
            "net_pnl": net_pnl,
            "capital_before": capital_before,
            "capital_after": capital_after,
            "status": "CLOSED",
        }

        self.trades.append(trade)
        self.current_capital = capital_after
        self.next_trade_id += 1

        return dict(trade)

    def get_trade_history(self):
        return [dict(trade) for trade in self.trades]

    def get_summary(self):
        total_trades = len(self.trades)
        winning_trades = sum(
            1 for trade in self.trades
            if trade["net_pnl"] > 0
        )
        losing_trades = sum(
            1 for trade in self.trades
            if trade["net_pnl"] < 0
        )

        total_pnl = sum(
            trade["net_pnl"] for trade in self.trades
        )

        win_rate = (
            winning_trades / total_trades * 100
            if total_trades > 0
            else 0.0
        )

        return {
            "initial_capital": self.initial_capital,
            "current_capital": self.current_capital,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "return_pct": (
                total_pnl / self.initial_capital * 100
            ),
        }

    def reset(self):
        self.current_capital = self.initial_capital
        self.trades.clear()
        self.next_trade_id = 1
        return self.get_summary()
      
