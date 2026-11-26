
"""
Paper Position Tracker
Tracks simulated positions, average prices and P&L.
"""

from typing import Dict
from paper_trading.trade_models import Position, Fill


class PositionTracker:
    def __init__(self):
        self.positions: Dict[str, Position] = {}

    def apply_fill(self, fill: Fill) -> Position:
        symbol = fill.symbol.upper()

        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol)

        position = self.positions[symbol]

        signed_qty = (
            fill.quantity if fill.side == "BUY" else -fill.quantity
        )

        old_qty = position.quantity
        new_qty = old_qty + signed_qty

        # Opening a new position or adding to the same direction
        if old_qty == 0 or (old_qty * signed_qty > 0):
            total_qty = abs(old_qty) + abs(signed_qty)

            if old_qty == 0:
                position.average_price = fill.price
            else:
                position.average_price = (
                    (
                        abs(old_qty) * position.average_price
                        + abs(signed_qty) * fill.price
                    ) / total_qty
                )

        # Closing or reversing a position
        else:
            closing_qty = min(abs(old_qty), abs(signed_qty))

            if old_qty > 0:
                realized = (
                    fill.price - position.average_price
                ) * closing_qty
            else:
                realized = (
                    position.average_price - fill.price
                ) * closing_qty

            position.realized_pnl += realized - fill.fees

            # If position reverses, remaining quantity starts
            # at the new fill price.
            if new_qty != 0 and (old_qty * new_qty < 0):
                position.average_price = fill.price

        # Fees on a fill that opens/adds to a position
        if old_qty == 0 or (old_qty * signed_qty > 0):
            position.realized_pnl -= fill.fees

        position.quantity = new_qty
        position.last_price = fill.price
        position.unrealized_pnl = (
            (fill.price - position.average_price) * new_qty
        )
        position.updated_at = fill.timestamp

        return position

    def update_market_price(self, symbol: str, price: float) -> Position:
        symbol = symbol.upper()

        if symbol not in self.positions:
            raise KeyError(f"No position found for {symbol}")

        self.positions[symbol].update_market_price(price)
        return self.positions[symbol]

    def get_position(self, symbol: str):
        return self.positions.get(symbol.upper())

    def get_all_positions(self) -> Dict[str, Position]:
        return dict(self.positions)

    def get_open_positions(self) -> Dict[str, Position]:
        return {
            symbol: position
            for symbol, position in self.positions.items()
            if position.quantity != 0
        }

    def get_total_realized_pnl(self) -> float:
        return sum(
            p.realized_pnl for p in self.positions.values()
        )

    def get_total_unrealized_pnl(self) -> float:
        return sum(
            p.unrealized_pnl for p in self.positions.values()
        )

    def get_total_pnl(self) -> float:
        return (
            self.get_total_realized_pnl()
            + self.get_total_unrealized_pnl()
        )

    def reset(self):
        self.positions.clear()
      
