"""
India Arbitrage Lab
Live-trading guard. Wrap ANY live broker in GuardedBroker.

A live order is only sent when ALL of these hold:
  1. config.settings.LIVE_TRADING_ENABLED is True (you flip it on purpose),
  2. the guard is armed with the exact confirmation phrase,
  3. the order is within max_order_value and max_orders_per_day.
disarm() (also called by the Stop button) blocks everything again.
"""

from datetime import date
from typing import Any, Dict

from brokers.base import BrokerAdapter
from config import settings

CONFIRM_PHRASE = "I UNDERSTAND LIVE ORDERS USE REAL MONEY"


class GuardedBroker(BrokerAdapter):
    def __init__(self, inner: BrokerAdapter, max_order_value: float = 50000.0,
                 max_orders_per_day: int = 20):
        self.inner = inner
        self.NAME = f"GUARDED:{inner.NAME}"
        self.IS_LIVE = inner.IS_LIVE
        self.max_order_value = max_order_value
        self.max_orders_per_day = max_orders_per_day
        self.armed = False
        self._day = date.today()
        self._count = 0

    def arm(self, phrase: str) -> bool:
        if phrase == CONFIRM_PHRASE and settings.LIVE_TRADING_ENABLED:
            self.armed = True
        return self.armed

    def disarm(self) -> None:
        self.armed = False

    def _block(self, reason: str) -> Dict[str, Any]:
        return {"success": False, "filled": False, "reason": reason}

    def submit_order(self, symbol, side, quantity, order_type="LIMIT", price=0.0):
        if self.inner.IS_LIVE:
            if not settings.LIVE_TRADING_ENABLED:
                return self._block("Live trading is disabled in config.settings.")
            if not self.armed:
                return self._block("Live broker is not armed.")
            if date.today() != self._day:
                self._day, self._count = date.today(), 0
            if self._count >= self.max_orders_per_day:
                return self._block("Daily order limit reached.")
            if quantity * float(price) > self.max_order_value:
                return self._block("Order value exceeds the per-order limit.")
            self._count += 1
        return self.inner.submit_order(symbol, side, quantity, order_type, price)

    def cancel_order(self, order_id):
        return self.inner.cancel_order(order_id)

    def get_positions(self):
        return self.inner.get_positions()

    def get_funds(self):
        return self.inner.get_funds()
