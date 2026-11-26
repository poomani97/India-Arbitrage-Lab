
"""
Paper Fill Simulator
Simulates market and limit order fills with slippage and fees.
"""

from typing import Optional
from paper_trading.trade_models import Fill


class FillSimulator:
    def __init__(
        self,
        slippage_bps: float = 2.0,
        fee_bps: float = 0.0,
    ):
        if slippage_bps < 0 or fee_bps < 0:
            raise ValueError("Slippage and fees cannot be negative")

        self.slippage_bps = float(slippage_bps)
        self.fee_bps = float(fee_bps)

    def simulate_fill(
        self,
        order,
        market_price: float,
        high: Optional[float] = None,
        low: Optional[float] = None,
    ) -> Optional[Fill]:
        """
        Returns a simulated Fill or None if the order cannot fill.

        Market orders:
            Fill using market price plus simulated slippage.

        Limit orders:
            Fill only when the bar range reaches the limit price.
        """

        if market_price is None or market_price <= 0:
            return None

        side = str(order.side).upper()
        order_type = str(order.order_type).upper()
        quantity = int(order.quantity) - int(
            getattr(order, "filled_quantity", 0)
        )

        if quantity <= 0:
            return None

        if side not in ("BUY", "SELL"):
            return None

        if order_type == "MARKET":
            slip = self.slippage_bps / 10000.0

            if side == "BUY":
                fill_price = market_price * (1.0 + slip)
            else:
                fill_price = market_price * (1.0 - slip)

        elif order_type == "LIMIT":
            limit_price = getattr(order, "price", None)

            if limit_price is None or limit_price <= 0:
                return None

            if high is None or low is None:
                return None

            if high < low:
                return None

            if side == "BUY":
                if low > limit_price:
                    return None
                fill_price = float(limit_price)
            else:
                if high < limit_price:
                    return None
                fill_price = float(limit_price)

        else:
            return None

        trade_value = fill_price * quantity
        fees = trade_value * (self.fee_bps / 10000.0)

        return Fill(
            order_id=order.order_id,
            symbol=order.symbol,
            side=side,
            quantity=quantity,
            price=round(fill_price, 6),
            fees=round(fees, 6),
        )

    def set_slippage(self, slippage_bps: float):
        if slippage_bps < 0:
            raise ValueError("Slippage cannot be negative")
        self.slippage_bps = float(slippage_bps)

    def set_fees(self, fee_bps: float):
        if fee_bps < 0:
            raise ValueError("Fees cannot be negative")
        self.fee_bps = float(fee_bps)
      
