"""
India Arbitrage Lab
Paper Broker

Simulation-only broker.
No live orders are sent to any exchange.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any
from datetime import datetime, timezone
import uuid
import math


@dataclass
class PaperOrder:
    order_id: str
    symbol: str
    side: str
    quantity: int
    order_type: str
    price: float
    status: str = "PENDING"
    filled_quantity: int = 0
    average_fill_price: float = 0.0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class PaperPosition:
    symbol: str
    quantity: int = 0
    average_price: float = 0.0


class PaperBroker:
    """Simulation-only order and position manager."""

    def __init__(self, initial_cash: float = 100000.0):
        if not math.isfinite(initial_cash) or initial_cash < 0:
            raise ValueError("Initial cash must be finite and non-negative.")

        self.initial_cash = float(initial_cash)
        self.cash = float(initial_cash)

        self.orders: Dict[str, PaperOrder] = {}
        self.positions: Dict[str, PaperPosition] = {}
        self.trade_history: List[Dict[str, Any]] = []

    @staticmethod
    def _valid_number(value: float) -> bool:
        try:
            return math.isfinite(float(value))
        except (TypeError, ValueError):
            return False

    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "MARKET",
        price: float = 0.0,
    ) -> Dict[str, Any]:
        """Create a simulated order. It is not automatically filled."""

        symbol = str(symbol).strip().upper()
        side = str(side).strip().upper()
        order_type = str(order_type).strip().upper()

        if not symbol:
            return {"success": False, "reason": "Symbol is required."}

        if side not in ("BUY", "SELL"):
            return {"success": False, "reason": "Side must be BUY or SELL."}

        if order_type not in ("MARKET", "LIMIT"):
            return {
                "success": False,
                "reason": "Order type must be MARKET or LIMIT.",
            }

        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
            return {
                "success": False,
                "reason": "Quantity must be a positive integer.",
            }

        if not self._valid_number(price) or price < 0:
            return {
                "success": False,
                "reason": "Price must be a valid non-negative number.",
            }

        if order_type == "LIMIT" and price <= 0:
            return {
                "success": False,
                "reason": "Limit orders require a positive price.",
            }

        if side == "SELL":
            current_position = self.positions.get(
                symbol, PaperPosition(symbol=symbol)
            )
            if quantity > current_position.quantity:
                return {
                    "success": False,
                    "reason": "Insufficient position quantity to sell.",
                }

        order_id = str(uuid.uuid4())

        order = PaperOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=float(price),
        )

        self.orders[order_id] = order

        return {
            "success": True,
            "reason": "Paper order created. Awaiting fill simulation.",
            "order": order,
        }

    def execute_fill(
        self,
        order_id: str,
        fill_quantity: int,
        fill_price: float,
    ) -> Dict[str, Any]:
        """Apply a simulated fill to cash and position records."""

        order = self.orders.get(order_id)

        if order is None:
            return {"success": False, "reason": "Order not found."}

        if order.status not in ("PENDING", "PARTIALLY_FILLED"):
            return {
                "success": False,
                "reason": f"Order cannot be filled in status {order.status}.",
            }

        if (
            not isinstance(fill_quantity, int)
            or isinstance(fill_quantity, bool)
            or fill_quantity <= 0
        ):
            return {
                "success": False,
                "reason": "Fill quantity must be a positive integer.",
            }

        if not self._valid_number(fill_price) or fill_price <= 0:
            return {
                "success": False,
                "reason": "Fill price must be positive and finite.",
            }

        remaining = order.quantity - order.filled_quantity

        if fill_quantity > remaining:
            return {
                "success": False,
                "reason": "Fill quantity exceeds remaining order quantity.",
            }

        symbol = order.symbol
        old_position = self.positions.get(
            symbol, PaperPosition(symbol=symbol)
        )

        new_quantity = old_position.quantity
        new_average = old_position.average_price

        if order.side == "BUY":
            required_cash = fill_quantity * fill_price

            if required_cash > self.cash:
                return {
                    "success": False,
                    "reason": "Insufficient cash for simulated buy fill.",
                }

            total_cost = (
                old_position.quantity * old_position.average_price
                + fill_quantity * fill_price
            )

            new_quantity = old_position.quantity + fill_quantity
            new_average = total_cost / new_quantity
            self.cash -= required_cash

        elif order.side == "SELL":
            if fill_quantity > old_position.quantity:
                return {
                    "success": False,
                    "reason": "Insufficient position for simulated sell fill.",
                }

            new_quantity = old_position.quantity - fill_quantity

            if new_quantity == 0:
                new_average = 0.0

            self.cash += fill_quantity * fill_price

        self.positions[symbol] = PaperPosition(
            symbol=symbol,
            quantity=new_quantity,
            average_price=new_average,
        )

        previous_filled = order.filled_quantity
        total_filled = previous_filled + fill_quantity

        order.average_fill_price = (
            (
                previous_filled * order.average_fill_price
                + fill_quantity * fill_price
            ) / total_filled
        )

        order.filled_quantity = total_filled

        if total_filled == order.quantity:
            order.status = "FILLED"
        else:
            order.status = "PARTIALLY_FILLED"

        trade_record = {
            "order_id": order_id,
            "symbol": symbol,
            "side": order.side,
            "quantity": fill_quantity,
            "fill_price": float(fill_price),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.trade_history.append(trade_record)

        return {
            "success": True,
            "reason": "Simulated fill recorded.",
            "order": order,
            "position": self.positions[symbol],
            "cash": round(self.cash, 2),
        }

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        order = self.orders.get(order_id)

        if order is None:
            return {"success": False, "reason": "Order not found."}

        if order.status not in ("PENDING", "PARTIALLY_FILLED"):
            return {
                "success": False,
                "reason": "Order cannot be cancelled in its current status.",
            }

        order.status = "CANCELLED"

        return {
            "success": True,
            "reason": "Order cancelled.",
            "order": order,
        }

    def get_order(self, order_id: str):
        return self.orders.get(order_id)

    def get_orders(self) -> List[PaperOrder]:
        return list(self.orders.values())

    def get_positions(self) -> List[PaperPosition]:
        return [
            position
            for position in self.positions.values()
            if position.quantity != 0
        ]

    def get_trade_history(self) -> List[Dict[str, Any]]:
        return list(self.trade_history)

    def get_summary(self) -> Dict[str, Any]:
        return {
            "initial_cash": round(self.initial_cash, 2),
            "cash": round(self.cash, 2),
            "total_orders": len(self.orders),
            "open_orders": sum(
                1
                for order in self.orders.values()
                if order.status in ("PENDING", "PARTIALLY_FILLED")
            ),
            "filled_orders": sum(
                1
                for order in self.orders.values()
                if order.status == "FILLED"
            ),
            "cancelled_orders": sum(
                1
                for order in self.orders.values()
                if order.status == "CANCELLED"
            ),
            "active_positions": len(self.get_positions()),
            "total_fills": len(self.trade_history),
        }

    def reset(self) -> None:
        """Reset paper account to initial cash and clear records."""

        self.cash = self.initial_cash
        self.orders.clear()
        self.positions.clear()
        self.trade_history.clear()
