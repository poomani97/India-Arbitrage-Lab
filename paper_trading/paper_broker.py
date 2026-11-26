
"""
Paper Broker
Virtual order execution for research and paper trading.
Never sends real orders.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid


@dataclass
class PaperOrder:
    order_id: str
    symbol: str
    side: str
    quantity: int
    order_type: str
    price: Optional[float]
    status: str = "OPEN"
    filled_quantity: int = 0
    average_fill_price: float = 0.0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class PaperBroker:
    """A simple virtual broker for simulated orders."""

    VALID_SIDES = {"BUY", "SELL"}
    VALID_ORDER_TYPES = {"MARKET", "LIMIT"}

    def __init__(self, initial_capital: float = 100000.0):
        if initial_capital <= 0:
            raise ValueError("Initial capital must be positive.")

        self.initial_capital = float(initial_capital)
        self.cash_balance = float(initial_capital)
        self.orders: Dict[str, PaperOrder] = {}
        self.trades: List[dict] = []
        self.positions: Dict[str, int] = {}
        self._lock = False

    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "MARKET",
        price: Optional[float] = None,
    ) -> PaperOrder:

        symbol = str(symbol).strip().upper()
        side = str(side).strip().upper()
        order_type = str(order_type).strip().upper()

        if not symbol:
            raise ValueError("Symbol is required.")

        if side not in self.VALID_SIDES:
            raise ValueError("Side must be BUY or SELL.")

        if order_type not in self.VALID_ORDER_TYPES:
            raise ValueError("Order type must be MARKET or LIMIT.")

        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Quantity must be a positive integer.")

        if order_type == "LIMIT":
            if price is None or price <= 0:
                raise ValueError("Valid limit price is required.")

        order = PaperOrder(
            order_id=str(uuid.uuid4()),
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price,
        )

        self.orders[order.order_id] = order
        return order

    def fill_order(
        self,
        order_id: str,
        fill_price: float,
        fill_quantity: Optional[int] = None,
    ) -> PaperOrder:

        if fill_price <= 0:
            raise ValueError("Fill price must be positive.")

        order = self.orders.get(order_id)
        if order is None:
            raise ValueError("Order not found.")

        if order.status not in {"OPEN", "PARTIALLY_FILLED"}:
            raise ValueError("Order cannot be filled in its current state.")

        remaining = order.quantity - order.filled_quantity

        qty = remaining if fill_quantity is None else fill_quantity

        if not isinstance(qty, int) or qty <= 0 or qty > remaining:
            raise ValueError("Invalid fill quantity.")

        value = fill_price * qty

        if order.side == "BUY" and value > self.cash_balance:
            raise ValueError("Insufficient virtual cash.")

        old_qty = order.filled_quantity
        old_value = old_qty * order.average_fill_price
        new_value = old_value + value

        order.filled_quantity += qty
        order.average_fill_price = new_value / order.filled_quantity

        if order.filled_quantity == order.quantity:
            order.status = "FILLED"
        else:
            order.status = "PARTIALLY_FILLED"

        if order.side == "BUY":
            self.cash_balance -= value
            self.positions[order.symbol] = (
                self.positions.get(order.symbol, 0) + qty
            )
        else:
            available = self.positions.get(order.symbol, 0)
            if qty > available:
                raise ValueError("Insufficient virtual position to sell.")

            self.cash_balance += value
            self.positions[order.symbol] = available - qty

        self.trades.append({
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side,
            "quantity": qty,
            "price": float(fill_price),
            "value": value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return order

    def cancel_order(self, order_id: str) -> bool:
        order = self.orders.get(order_id)

        if order is None:
            return False

        if order.status not in {"OPEN", "PARTIALLY_FILLED"}:
            return False

        order.status = "CANCELLED"
        return True

    def get_order(self, order_id: str) -> Optional[PaperOrder]:
        return self.orders.get(order_id)

    def get_orders(self) -> List[PaperOrder]:
        return list(self.orders.values())

    def get_positions(self) -> Dict[str, int]:
        return {
            symbol: qty
            for symbol, qty in self.positions.items()
            if qty != 0
        }

    def get_trade_history(self) -> List[dict]:
        return list(self.trades)

    def get_account_summary(self) -> dict:
        return {
            "initial_capital": self.initial_capital,
            "cash_balance": round(self.cash_balance, 2),
            "positions": self.get_positions(),
            "total_orders": len(self.orders),
            "total_fills": len(self.trades),
            "total_traded_value": round(
                sum(t["value"] for t in self.trades), 2
            ),
        }

    def reset(self) -> None:
        self.cash_balance = self.initial_capital
        self.orders.clear()
        self.trades.clear()
        self.positions.clear()
      
