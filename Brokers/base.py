"""
India Arbitrage Lab
Common broker interface. Every broker (paper, Dhan, Fyers, Angel One, Groww,
forex...) implements BrokerAdapter, so TradingController works with any of them.

submit_order() returns a dict:
    {"success": bool, "order_id": str, "filled": bool,
     "fill_price": float, "reason": str}
A real broker may return filled=False (order accepted, fill pending).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BrokerError(Exception):
    pass


class BrokerAdapter(ABC):
    NAME = "BASE"
    IS_LIVE = False          # True for anything that can move real money

    @abstractmethod
    def submit_order(self, symbol: str, side: str, quantity: int,
                     order_type: str = "LIMIT", price: float = 0.0) -> Dict[str, Any]:
        ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    def get_positions(self) -> List[Any]:
        ...

    @abstractmethod
    def get_funds(self) -> Dict[str, float]:
        ...


class NotConnectedBroker(BrokerAdapter):
    """Base for real brokers whose API is not wired up yet. Fails loudly."""

    IS_LIVE = True
    API_NOTES = ""

    def __init__(self, credentials: Dict[str, str] = None):
        self.credentials = dict(credentials or {})

    def _missing(self):
        raise NotImplementedError(
            f"{self.NAME} API is not connected yet. {self.API_NOTES} "
            "Nothing was sent."
        )

    def submit_order(self, *args, **kwargs):
        self._missing()

    def cancel_order(self, *args, **kwargs):
        self._missing()

    def get_positions(self):
        self._missing()

    def get_funds(self):
        self._missing()
