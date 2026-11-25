"""
India Arbitrage Lab
Fill Simulator

Simulates order fills using historical OHLCV candles.
Paper trading only. No live broker connection.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
import math


@dataclass
class FillResult:
    order_id: str
    filled: bool
    fill_quantity: int
    fill_price: float
    status: str
    reason: str = ""


class FillSimulator:
    """Simulate fills from historical candle data."""

    def __init__(
        self,
        slippage_bps: float = 5.0,
        volume_participation: float = 0.05,
    ):
        if not math.isfinite(slippage_bps) or slippage_bps < 0:
            raise ValueError("Slippage must be finite and non-negative.")

        if (
            not math.isfinite(volume_participation)
            or not 0 < volume_participation <= 1
        ):
            raise ValueError(
                "Volume participation must be between 0 and 1."
            )

        self.slippage_bps = float(slippage_bps)
        self.volume_participation = float(volume_participation)

    @staticmethod
    def _get(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    @staticmethod
    def _number(value: Any) -> Optional[float]:
        try:
            number = float(value)
            if math.isfinite(number):
                return number
            return None
        except (TypeError, ValueError):
            return None

    def _validate_bar(self, bar: Dict[str, Any]) -> Optional[str]:
        required = ("open", "high", "low", "close")

        values = {}

        for field in required:
            number = self._number(bar.get(field))

            if number is None or number <= 0:
                return f"Missing or invalid candle field: {field}"

            values[field] = number

        o = values["open"]
        h = values["high"]
        l = values["low"]
        c = values["close"]

        if h < l:
            return "Candle high is lower than candle low."

        if h < max(o, c):
            return "Candle high is inconsistent with open/close."

        if l > min(o, c):
            return "Candle low is inconsistent with open/close."

        return None

    def _get_fill_quantity(
        self,
        order: Any,
        bar: Dict[str, Any],
    ) -> int:
        remaining = (
            int(self._get(order, "quantity", 0))
            - int(self._get(order, "filled_quantity", 0))
        )

        if remaining <= 0:
            return 0

        volume = self._number(bar.get("volume"))

        # If volume is unavailable, do not assume unlimited liquidity.
        if volume is None or volume <= 0:
            return 0

        max_fill = int(volume * self.volume_participation)

        if max_fill <= 0:
            return 0

        return min(remaining, max_fill)

    def _market_fill_price(
        self,
        side: str,
        bar: Dict[str, Any],
    ) -> float:
        open_price = float(bar["open"])

        slippage = self.slippage_bps / 10000.0

        if side == "BUY":
            return open_price * (1 + slippage)

        return open_price * (1 - slippage)

    def _limit_fill_price(
        self,
        side: str,
        limit_price: float,
        bar: Dict[str, Any],
    ) -> Optional[float]:
        open_price = float(bar["open"])
        high = float(bar["high"])
        low = float(bar["low"])

        if side == "BUY":
            # Price improvement if market opens below the limit.
            if open_price <= limit_price:
                return open_price

            # Limit price reached during the candle.
            if low <= limit_price:
                return limit_price

            return None

        if side == "SELL":
            # Price improvement if market opens above the limit.
            if open_price >= limit_price:
                return open_price

            # Limit price reached during the candle.
            if high >= limit_price:
                return limit_price

            return None

        return None

    def simulate(
        self,
        order: Any,
        bar: Dict[str, Any],
        paper_broker: Any,
    ) -> FillResult:
        """Attempt a simulated fill using one historical candle."""

        order_id = str(self._get(order, "order_id", ""))
        side = str(self._get(order, "side", "")).upper()
        order_type = str(self._get(order, "order_type", "")).upper()
        limit_price = self._number(self._get(order, "price", 0))

        order_status = str(self._get(order, "status", ""))

        if order_status not in ("PENDING", "PARTIALLY_FILLED"):
            return FillResult(
                order_id=order_id,
                filled=False,
                fill_quantity=0,
                fill_price=0.0,
                status="NOT_EXECUTABLE",
                reason="Order is not pending or partially filled.",
            )

        if side not in ("BUY", "SELL"):
            return FillResult(
                order_id=order_id,
                filled=False,
                fill_quantity=0,
                fill_price=0.0,
                status="INVALID",
                reason="Invalid order side.",
            )

        if order_type not in ("MARKET", "LIMIT"):
            return FillResult(
                order_id=order_id,
                filled=False,
                fill_quantity=0,
                fill_price=0.0,
                status="INVALID",
                reason="Unsupported order type.",
            )

        bar_error = self._validate_bar(bar)

        if bar_error:
            return FillResult(
                order_id=order_id,
                filled=False,
                fill_quantity=0,
                fill_price=0.0,
                status="INVALID_BAR",
                reason=bar_error,
            )

        if order_type == "LIMIT":
            if limit_price is None or limit_price <= 0:
                return FillResult(
                    order_id=order_id,
                    filled=False,
                    fill_quantity=0,
                    fill_price=0.0,
                    status="INVALID",
                    reason="Invalid limit price.",
                )

            fill_price = self._limit_fill_price(
                side, limit_price, bar
            )

            if fill_price is None:
                return FillResult(
                    order_id=order_id,
                    filled=False,
                    fill_quantity=0,
                    fill_price=0.0,
                    status="NOT_FILLED",
                    reason="Limit price was not reached in this candle.",
                )

        else:
            fill_price = self._market_fill_price(side, bar)

        fill_quantity = self._get_fill_quantity(order, bar)

        if fill_quantity <= 0:
            return FillResult(
                order_id=order_id,
                filled=False,
                fill_quantity=0,
                fill_price=0.0,
                status="NOT_FILLED",
                reason="Insufficient or unavailable candle volume.",
            )

        broker_result = paper_broker.execute_fill(
            order_id=order_id,
            fill_quantity=fill_quantity,
            fill_price=fill_price,
        )

        if not broker_result.get("success", False):
            return FillResult(
                order_id=order_id,
                filled=False,
                fill_quantity=0,
                fill_price=0.0,
                status="BROKER_REJECTED",
                reason=broker_result.get("reason", "Fill rejected."),
            )

        updated_order = paper_broker.get_order(order_id)

        updated_status = (
            updated_order.status
            if updated_order is not None
            else "UNKNOWN"
        )

        return FillResult(
            order_id=order_id,
            filled=True,
            fill_quantity=fill_quantity,
            fill_price=round(fill_price, 4),
            status=updated_status,
            reason="Simulated fill completed.",
        )
