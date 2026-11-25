
"""
India Arbitrage Lab - Portfolio Manager

Tracks portfolio positions, exposure and position updates.
Research and paper-trading use only.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class PortfolioPosition:
    symbol: str
    quantity: float
    average_price: float
    mark_price: float
    multiplier: float = 1.0
    realized_pnl: float = 0.0
    transaction_costs: float = 0.0

    @property
    def direction(self) -> str:
        if self.quantity > 0:
            return "LONG"
        if self.quantity < 0:
            return "SHORT"
        return "FLAT"

    @property
    def absolute_quantity(self) -> float:
        return abs(self.quantity)

    @property
    def market_value(self) -> float:
        return (
            abs(self.quantity)
            * self.mark_price
            * self.multiplier
        )

    @property
    def unrealized_pnl(self) -> float:
        return (
            self.quantity
            * (self.mark_price - self.average_price)
            * self.multiplier
        )

    @property
    def total_pnl(self) -> float:
        return (
            self.realized_pnl
            + self.unrealized_pnl
            - self.transaction_costs
        )


class PortfolioManager:
    """
    Maintains positions and portfolio-level summaries.

    Signed quantity convention:
        Positive quantity = Long
        Negative quantity = Short
    """

    def __init__(self):
        self.positions: Dict[str, PortfolioPosition] = {}

    def get_position(
        self,
        symbol: str,
    ) -> Optional[PortfolioPosition]:
        return self.positions.get(symbol.upper())

    def update_mark_price(
        self,
        symbol: str,
        mark_price: float,
    ) -> bool:
        symbol = symbol.upper()

        if mark_price <= 0:
            raise ValueError("Mark price must be positive.")

        position = self.positions.get(symbol)

        if position is None:
            return False

        position.mark_price = float(mark_price)
        return True

    def open_position(
        self,
        symbol: str,
        quantity: float,
        price: float,
        multiplier: float = 1.0,
        transaction_cost: float = 0.0,
    ) -> PortfolioPosition:
        symbol = symbol.upper()

        if quantity == 0:
            raise ValueError("Quantity cannot be zero.")

        if price <= 0 or multiplier <= 0:
            raise ValueError("Price and multiplier must be positive.")

        if transaction_cost < 0:
            raise ValueError("Transaction cost cannot be negative.")

        signed_quantity = float(quantity)
        position = self.positions.get(symbol)

        if position is None:
            position = PortfolioPosition(
                symbol=symbol,
                quantity=signed_quantity,
                average_price=float(price),
                mark_price=float(price),
                multiplier=float(multiplier),
                transaction_costs=float(transaction_cost),
            )
            self.positions[symbol] = position
            return position

        if position.multiplier != float(multiplier):
            raise ValueError(
                "Multiplier mismatch for existing position."
            )

        old_quantity = position.quantity
        new_quantity = old_quantity + signed_quantity

        # Adding in the same direction or opening a new position.
        if old_quantity == 0 or old_quantity * signed_quantity > 0:
            total_abs_quantity = (
                abs(old_quantity) + abs(signed_quantity)
            )

            position.average_price = (
                (
                    abs(old_quantity) * position.average_price
                    + abs(signed_quantity) * float(price)
                )
                / total_abs_quantity
            )

            position.quantity = new_quantity

        else:
            # Opposite-side order reduces or closes existing position.
            closing_quantity = min(
                abs(old_quantity),
                abs(signed_quantity),
            )

            if old_quantity > 0:
                position.realized_pnl += (
                    float(price) - position.average_price
                ) * closing_quantity * position.multiplier
            else:
                position.realized_pnl += (
                    position.average_price - float(price)
                ) * closing_quantity * position.multiplier

            # If position crosses zero, the excess opens
            # a new position in the opposite direction.
            if new_quantity == 0:
                position.quantity = 0.0
                position.average_price = 0.0

            elif old_quantity * new_quantity < 0:
                position.quantity = new_quantity
                position.average_price = float(price)

            else:
                position.quantity = new_quantity

        position.mark_price = float(price)
        position.transaction_costs += float(transaction_cost)

        return position

    def close_position(
        self,
        symbol: str,
        price: float,
        quantity: Optional[float] = None,
        transaction_cost: float = 0.0,
    ) -> Optional[PortfolioPosition]:
        symbol = symbol.upper()
        position = self.positions.get(symbol)

        if position is None or position.quantity == 0:
            return None

        if price <= 0:
            raise ValueError("Price must be positive.")

        if transaction_cost < 0:
            raise ValueError("Transaction cost cannot be negative.")

        close_quantity = (
            abs(position.quantity)
            if quantity is None
            else float(quantity)
        )

        if close_quantity <= 0:
            raise ValueError("Close quantity must be positive.")

        if close_quantity > abs(position.quantity):
            raise ValueError(
                "Cannot close more than the open quantity."
            )

        # Closing a long position.
        if position.quantity > 0:
            position.realized_pnl += (
                float(price) - position.average_price
            ) * close_quantity * position.multiplier

            position.quantity -= close_quantity

        # Closing a short position.
        else:
            position.realized_pnl += (
                position.average_price - float(price)
            ) * close_quantity * position.multiplier

            position.quantity += close_quantity

        position.mark_price = float(price)
        position.transaction_costs += float(transaction_cost)

        if position.quantity == 0:
            position.average_price = 0.0

        return position

    def remove_flat_positions(self) -> int:
        flat_symbols = [
            symbol
            for symbol, position in self.positions.items()
            if position.quantity == 0
        ]

        for symbol in flat_symbols:
            del self.positions[symbol]

        return len(flat_symbols)

    def get_all_positions(self) -> Dict[str, PortfolioPosition]:
        return dict(self.positions)

    def get_open_positions(self) -> Dict[str, PortfolioPosition]:
        return {
            symbol: position
            for symbol, position in self.positions.items()
            if position.quantity != 0
        }

    def get_total_realized_pnl(self) -> float:
        return sum(
            position.realized_pnl
            for position in self.positions.values()
        )

    def get_total_unrealized_pnl(self) -> float:
        return sum(
            position.unrealized_pnl
            for position in self.positions.values()
        )

    def get_total_transaction_costs(self) -> float:
        return sum(
            position.transaction_costs
            for position in self.positions.values()
        )

    def get_total_pnl(self) -> float:
        return (
            self.get_total_realized_pnl()
            + self.get_total_unrealized_pnl()
            - self.get_total_transaction_costs()
        )

    def get_total_market_value(self) -> float:
        return sum(
            position.market_value
            for position in self.get_open_positions().values()
        )

    def get_portfolio_summary(self) -> dict:
        open_positions = self.get_open_positions()

        return {
            "total_positions": len(self.positions),
            "open_positions": len(open_positions),
            "long_positions": sum(
                1 for p in open_positions.values()
                if p.quantity > 0
            ),
            "short_positions": sum(
                1 for p in open_positions.values()
                if p.quantity < 0
            ),
            "market_value": self.get_total_market_value(),
            "realized_pnl": self.get_total_realized_pnl(),
            "unrealized_pnl": self.get_total_unrealized_pnl(),
            "transaction_costs": self.get_total_transaction_costs(),
            "net_pnl": self.get_total_pnl(),
      }
      
