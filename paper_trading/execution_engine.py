
import math
from datetime import datetime, timezone


class PaperExecutionEngine:
    """
    Paper-only execution engine.

    Connects validated trading signals to a PaperPortfolioManager.
    Does not place real broker orders.
    """

    def __init__(self, portfolio_manager, risk_check=None):
        self.portfolio = portfolio_manager
        self.risk_check = risk_check

        self.active_trades = {}
        self.execution_history = []

    @staticmethod
    def _valid_number(value, name):
        if isinstance(value, bool):
                raise ValueError(f"{name} must be numeric.")

        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be numeric.")

        if not math.isfinite(number):
            raise ValueError(f"{name} must be finite.")

        return number

    @staticmethod
    def _normalize_side(side):
        side = str(side).strip().upper()

        if side in ("BUY", "LONG"):
            return "long"

        if side in ("SELL", "SHORT"):
            return "short"

        raise ValueError("Side must be BUY/LONG or SELL/SHORT.")

    def execute_signal(self, signal):
        """
        Execute a signal in paper mode only.

        Required signal fields:
        symbol, side, quantity, entry_price
        """

        if not isinstance(signal, dict):
            raise ValueError("Signal must be a dictionary.")

        symbol = str(signal.get("symbol", "")).strip()

        if not symbol:
            raise ValueError("Symbol is required.")

        side = self._normalize_side(signal.get("side", ""))

        quantity = self._valid_number(
            signal.get("quantity"), "quantity"
        )

        entry_price = self._valid_number(
            signal.get("entry_price"), "entry_price"
        )

        if quantity <= 0:
            raise ValueError("Quantity must be positive.")

        if entry_price <= 0:
            raise ValueError("Entry price must be positive.")

        normalized_signal = {
            **signal,
            "symbol": symbol.upper(),
            "side": side,
            "quantity": quantity,
            "entry_price": entry_price,
        }

        # Risk check: if configured, it must approve the signal.
        if self.risk_check is not None:
            approved = self.risk_check(normalized_signal)

            if approved is not True:
                return {
                    "status": "REJECTED",
                    "reason": "Risk check failed.",
                    "symbol": symbol.upper(),
                }

        # Open paper position only.
        position_id = self.portfolio.open_position(
            symbol=symbol.upper(),
            side=side,
            quantity=quantity,
            entry_price=entry_price,
        )

        trade = {
            "position_id": position_id,
            "symbol": symbol.upper(),
            "side": side,
            "quantity": quantity,
            "entry_price": entry_price,
            "status": "OPEN",
            "opened_at": datetime.now(timezone.utc).isoformat(),
        }

        self.active_trades[position_id] = trade
        self.execution_history.append({
            **trade,
            "event": "OPEN",
        })

        return {
            "status": "EXECUTED_PAPER",
            "position_id": position_id,
            "symbol": symbol.upper(),
            "side": side,
            "quantity": quantity,
            "entry_price": entry_price,
        }

    def update_trade_price(self, position_id, current_price):
        if position_id not in self.active_trades:
            raise ValueError("Unknown active position.")

        current_price = self._valid_number(
            current_price, "current_price"
        )

        if current_price <= 0:
            raise ValueError("Current price must be positive.")

        result = self.portfolio.update_price(
            position_id=position_id,
            current_price=current_price,
        )

        self.active_trades[position_id]["current_price"] = current_price

        return result

    def close_trade(self, position_id, exit_price):
        if position_id not in self.active_trades:
            raise ValueError("Unknown active position.")

        exit_price = self._valid_number(exit_price, "exit_price")

        if exit_price <= 0:
            raise ValueError("Exit price must be positive.")

        trade = self.active_trades[position_id]

        result = self.portfolio.close_position(
            position_id=position_id,
            exit_price=exit_price,
        )

        closed_trade = {
            **trade,
            "exit_price": exit_price,
            "status": "CLOSED",
            "closed_at": datetime.now(timezone.utc).isoformat(),
        }

        self.execution_history.append({
            **closed_trade,
            "event": "CLOSE",
        })

        del self.active_trades[position_id]

        return {
            "status": "CLOSED_PAPER",
            "position_id": position_id,
            "symbol": trade["symbol"],
            "exit_price": exit_price,
            "portfolio_result": result,
        }

    def get_active_trades(self):
        return list(self.active_trades.values())

    def get_execution_history(self):
        return list(self.execution_history)

    def get_summary(self):
        return {
            "active_trades": len(self.active_trades),
            "total_execution_events": len(self.execution_history),
            "paper_only": True,
        }

    def reset(self):
        self.active_trades.clear()
        self.execution_history.clear()
      
