from typing import Any, Dict, List

from brokers.base import BrokerAdapter
from execution.paper_broker import PaperBroker


class PaperBrokerAdapter(BrokerAdapter):
    NAME = "PAPER"
    IS_LIVE = False

    def __init__(self, broker: PaperBroker = None):
        self.broker = broker or PaperBroker(100000.0, allow_short=True)

    def submit_order(self, symbol, side, quantity, order_type="LIMIT", price=0.0) -> Dict[str, Any]:
        placed = self.broker.place_order(symbol, side, quantity, order_type, price)
        if not placed.get("success"):
            return {"success": False, "reason": placed.get("reason"), "filled": False}
        order = placed["order"]
        fill = self.broker.execute_fill(order.order_id, quantity, price)
        if not fill.get("success"):
            self.broker.cancel_order(order.order_id)
            return {"success": False, "reason": fill.get("reason"), "filled": False}
        return {"success": True, "order_id": order.order_id, "filled": True,
                "fill_price": float(price), "reason": "Paper fill."}

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        return self.broker.cancel_order(order_id)

    def get_positions(self) -> List[Any]:
        return self.broker.get_positions()

    def get_funds(self) -> Dict[str, float]:
        return {"cash": self.broker.cash}
