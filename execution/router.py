"""
India Arbitrage Lab
Paper Execution Router

Routes approved opportunities to the paper broker.
Live trading is intentionally not supported.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class RoutingResult:
    opportunity_id: str
    strategy_id: str
    success: bool
    status: str
    orders: List[Dict[str, Any]] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)


class ExecutionRouter:
    """Route qualified opportunities to the paper broker only."""

    def __init__(self, paper_broker: Any):
        self.paper_broker = paper_broker
        self.routing_history: List[RoutingResult] = []

    @staticmethod
    def _get(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    @staticmethod
    def _normalize_side(side: Any) -> str:
        value = str(side).strip().upper()

        if value in ("BUY", "LONG"):
            return "BUY"

        if value in ("SELL", "SHORT"):
            return "SELL"

        return value

    def _extract_legs(self, opportunity: Any) -> List[Any]:
        legs = self._get(opportunity, "legs", [])

        if not isinstance(legs, list) or not legs:
            return []

        return legs

    def _prepare_leg(self, leg: Any) -> Dict[str, Any]:
        symbol = str(self._get(leg, "symbol", "")).strip().upper()
        side = self._normalize_side(self._get(leg, "side", ""))
        quantity = self._get(leg, "quantity", 0)
        order_type = str(
            self._get(leg, "order_type", "MARKET")
        ).strip().upper()
        price = self._get(leg, "price", 0.0)

        if not symbol:
            raise ValueError("Leg symbol is missing.")

        if side not in ("BUY", "SELL"):
            raise ValueError(f"Invalid side for {symbol}.")

        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise ValueError(f"Quantity must be an integer for {symbol}.")

        if quantity <= 0:
            raise ValueError(f"Quantity must be positive for {symbol}.")

        if order_type not in ("MARKET", "LIMIT"):
            raise ValueError(f"Unsupported order type for {symbol}.")

        try:
            price = float(price)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid price for {symbol}.")

        if order_type == "LIMIT" and price <= 0:
            raise ValueError(f"Limit price must be positive for {symbol}.")

        return {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "order_type": order_type,
            "price": price,
        }

    def route(self, opportunity: Any) -> RoutingResult:
        strategy_id = str(
            self._get(opportunity, "strategy_id", "UNKNOWN")
        ).upper()

        opportunity_id = str(
            self._get(opportunity, "opportunity_id", "")
            or self._get(opportunity, "id", "")
            or f"{strategy_id}-route-{len(self.routing_history) + 1}"
        )

        # Only risk-approved opportunities are allowed.
        risk_approved = self._get(opportunity, "risk_approved", False)

        if risk_approved is not True:
            result = RoutingResult(
                opportunity_id=opportunity_id,
                strategy_id=strategy_id,
                success=False,
                status="RISK_REJECTED",
                reasons=[
                    "Opportunity must be explicitly risk-approved before routing."
                ],
            )
            self.routing_history.append(result)
            return result

        legs = self._extract_legs(opportunity)

        if not legs:
            result = RoutingResult(
                opportunity_id=opportunity_id,
                strategy_id=strategy_id,
                success=False,
                status="NO_LEGS",
                reasons=["Opportunity has no valid execution legs."],
            )
            self.routing_history.append(result)
            return result

        # Validate every leg before placing any order.
        prepared_legs = []

        try:
            for leg in legs:
                prepared_legs.append(self._prepare_leg(leg))
        except Exception as exc:
            result = RoutingResult(
                opportunity_id=opportunity_id,
                strategy_id=strategy_id,
                success=False,
                status="INVALID_LEGS",
                reasons=[str(exc)],
            )
            self.routing_history.append(result)
            return result

        placed_orders = []
        errors = []

        # Paper orders only. No automatic fills are performed here.
        for leg in prepared_legs:
            order_result = self.paper_broker.place_order(
                symbol=leg["symbol"],
                side=leg["side"],
                quantity=leg["quantity"],
                order_type=leg["order_type"],
                price=leg["price"],
            )

            if order_result.get("success"):
                order = order_result.get("order")

                placed_orders.append({
                    "symbol": leg["symbol"],
                    "side": leg["side"],
                    "quantity": leg["quantity"],
                    "order_id": getattr(order, "order_id", ""),
                    "status": getattr(order, "status", "UNKNOWN"),
                })
            else:
                errors.append(
                    f"{leg['symbol']}: {order_result.get('reason', 'Order failed')}"
                )

        if errors and placed_orders:
            status = "PARTIAL_ROUTING"
            success = False
        elif errors:
            status = "ROUTING_FAILED"
            success = False
        else:
            status = "ROUTED"
            success = True

        result = RoutingResult(
            opportunity_id=opportunity_id,
            strategy_id=strategy_id,
            success=success,
            status=status,
            orders=placed_orders,
            reasons=errors,
        )

        self.routing_history.append(result)
        return result

    def route_many(self, opportunities: List[Any]) -> List[RoutingResult]:
        return [
            self.route(opportunity)
            for opportunity in opportunities
        ]

    def get_history(self) -> List[RoutingResult]:
        return list(self.routing_history)

    def get_summary(self) -> Dict[str, Any]:
        total = len(self.routing_history)

        routed = sum(
            result.status == "ROUTED"
            for result in self.routing_history
        )

        failed = sum(
            result.status == "ROUTING_FAILED"
            for result in self.routing_history
        )

        partial = sum(
            result.status == "PARTIAL_ROUTING"
            for result in self.routing_history
        )

        rejected = sum(
            result.status == "RISK_REJECTED"
            for result in self.routing_history
        )

        return {
            "total_routing_attempts": total,
            "fully_routed": routed,
            "partially_routed": partial,
            "failed": failed,
            "risk_rejected": rejected,
        }
