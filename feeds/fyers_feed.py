"""
India Arbitrage Lab
Fyers market-data feed (REST quote polling; a websocket version can follow).

You say which Fyers symbol feeds which strategy column:
    columns = {"spot_price": "NSE:NIFTY50-INDEX",
               "futures_price": "NSE:NIFTY26DECFUT"}
    constants = {"symbol": "NIFTY", "expiry_date": "2026-12-29"}
Each poll() asks Fyers for the last price of every symbol and returns one row.
If any symbol fails, poll() returns None, so a half-filled row never trades.
Reads credentials from FYERS_APP_ID / FYERS_ACCESS_TOKEN (same as the broker).
"""

from typing import Any, Dict, Optional

import pandas as pd

from brokers.fyers_adapter import _client_from_env
from feeds.base import DataFeed


class FyersFeed(DataFeed):
    NAME = "FYERS"
    IS_LIVE = True

    def __init__(self, columns: Dict[str, str], constants: Optional[Dict[str, Any]] = None,
                 client: Any = None, volume_columns: Optional[Dict[str, str]] = None):
        if not columns:
            raise ValueError("columns must map at least one column to a Fyers symbol.")
        self.columns = dict(columns)
        self.constants = dict(constants or {})
        # Optional: {"futures_volume": "NSE:NIFTY26DECFUT"} adds today's traded volume.
        # Volume is optional: if Fyers omits it the column is simply left out.
        self.volume_columns = dict(volume_columns or {})
        self.client = client if client is not None else _client_from_env()
        self.last_error = ""

    def poll(self) -> Optional[Dict[str, Any]]:
        symbols = ",".join(sorted(set(self.columns.values()) | set(self.volume_columns.values())))
        try:
            response = self.client.quotes(data={"symbols": symbols})
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            return None

        if not isinstance(response, dict) or response.get("s") != "ok":
            self.last_error = f"Fyers quotes failed: {response}"
            return None

        prices, volumes = {}, {}
        for item in response.get("d", []):
            values = item.get("v") or {}
            price = values.get("lp")
            if item.get("s") == "ok" and isinstance(price, (int, float)) and price > 0:
                prices[item.get("n")] = float(price)
            volume = values.get("volume")
            if item.get("s") == "ok" and isinstance(volume, (int, float)) and volume > 0:
                volumes[item.get("n")] = float(volume)

        row: Dict[str, Any] = {"datetime": pd.Timestamp.now(), **self.constants}
        for column, symbol in self.columns.items():
            if symbol not in prices:
                self.last_error = f"No valid price for {symbol}."
                return None
            row[column] = prices[symbol]

        # A live quote is a single last price. Strategies check for OHLC columns, so a
        # tick-only row would be skipped silently. Use the last spot price for all four
        # (a placeholder: this is NOT a real candle). Real values are never overwritten.
        if "spot_price" in row:
            for column in ("open", "high", "low", "close"):
                row.setdefault(column, row["spot_price"])

        for column, symbol in self.volume_columns.items():
            if symbol in volumes:
                row[column] = volumes[symbol]

        self.last_error = ""
        return row
