"""
India Arbitrage Lab
Live prices, paper orders.

run_live_step() pulls ONE snapshot from a live feed (e.g. FyersFeed), runs the
strategies and hands opportunities to a TradingController. The controller is
expected to sit on the PAPER broker: the Fyers feed only reads quotes and never
places an order, and a test below checks that.

Outside NSE market hours prices are not moving, so a step is skipped unless
you pass ignore_hours=True. Exchange holidays are NOT known here.
"""

from typing import Any, Dict, Optional

import pandas as pd

from feeds.runner import FeedRunner

IST = "Asia/Kolkata"
OPEN, CLOSE = (9, 15), (15, 30)


def ist_now() -> pd.Timestamp:
    return pd.Timestamp.now(tz=IST).tz_localize(None)


def market_open(now: Optional[pd.Timestamp] = None) -> bool:
    """Mon-Fri 09:15-15:30 India time (holidays are not checked)."""
    now = now if now is not None else ist_now()
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return OPEN[0] * 60 + OPEN[1] <= minutes <= CLOSE[0] * 60 + CLOSE[1]


def run_live_step(controller: Any, feed: Any, lot_size: int = 1,
                  ignore_hours: bool = False,
                  now: Optional[pd.Timestamp] = None) -> Dict[str, Any]:
    if not ignore_hours and not market_open(now):
        return {"status": "MARKET_CLOSED",
                "reason": "Outside 09:15-15:30 IST Mon-Fri; prices are not live."}

    result = FeedRunner(feed, controller, lot_size=lot_size).step()
    if result["status"] == "NO_DATA":
        result["reason"] = getattr(feed, "last_error", "") or "Feed returned nothing."
    return result
