"""
India Arbitrage Lab
Common market-data feed interface.

A feed hands out one snapshot row (a dict) per poll(). A row holds a
datetime plus whatever columns the feed knows: open/high/low/close, symbol,
spot_price, futures_price, expiry_date, call_price, ... Real broker feeds
and the CSV replay feed implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class DataFeed(ABC):
    NAME = "BASE"
    IS_LIVE = False
    finished = False

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    @abstractmethod
    def poll(self) -> Optional[Dict[str, Any]]:
        """Return the next snapshot row, or None if nothing new."""


class NotConnectedFeed(DataFeed):
    IS_LIVE = True
    API_NOTES = ""

    def __init__(self, credentials: Dict[str, str] = None):
        self.credentials = dict(credentials or {})

    def poll(self):
        raise NotImplementedError(
            f"{self.NAME} live feed is not connected yet. {self.API_NOTES}"
        )


class DhanFeed(NotConnectedFeed):
    NAME = "DHAN"
    API_NOTES = "Needs Dhan credentials and its market-feed websocket."


class AngelOneFeed(NotConnectedFeed):
    NAME = "ANGELONE"
    API_NOTES = "Needs Angel One SmartAPI credentials and its websocket."
