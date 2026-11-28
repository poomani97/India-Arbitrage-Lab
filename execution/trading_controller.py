"""
India Arbitrage Lab
Trading controller: MANUAL, SEMI_AUTO and AUTO modes.

MANUAL     you place every buy/sell yourself; opportunities are ignored.
SEMI_AUTO  opportunities that pass the risk gate wait in a queue until
           you approve or reject them.
AUTO       opportunities that pass the risk gate are executed at once.

halt() stops all automated execution immediately (manual orders still work).
Works with any broker object exposing place_order / execute_fill, so the
same controller can later sit on top of a real-broker adapter.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from models.legs import executable_problems, live_problems, normalize_leg
from ranking.opportunity_score import OpportunityScorer
from risk.risk_gate import RiskGate


class TradingMode(str, Enum):
    MANUAL = "MANUAL"
    SEMI_AUTO = "SEMI_AUTO"
    AUTO = "AUTO"


class TradingController:
    def __init__(
        self,
        broker: Any,
        risk_gate: Optional[RiskGate] = None,
        mode: TradingMode = TradingMode.MANUAL,
        max_quantity_per_order: int = 10000,
        allow_single_leg: bool = False,
        controls: Optional[Any] = None,
    ):
        self.broker = broker
        self.risk_gate = risk_gate or RiskGate()
        self.scorer = OpportunityScorer()
        self.mode = TradingMode(mode)
        self.max_quantity_per_order = max_quantity_per_order
        self.allow_single_leg = allow_single_leg
        self.controls = controls
        self.halted = False
        self.pending: Dict[str, Any] = {}
        self.log: List[Dict[str, Any]] = []

    def _send(self, symbol: str, side: str, quantity: int, price: float) -> Dict[str, Any]:
        """One order. Uses broker.submit_order (BrokerAdapter) when present,
        otherwise the two-step PaperBroker place/fill."""
        if hasattr(self.broker, "submit_order"):
            return self.broker.submit_order(symbol, side, quantity, "LIMIT", price)

        placed = self.broker.place_order(symbol, side, quantity, "LIMIT", price)
        if not placed.get("success"):
            return placed
        order = placed["order"]
        filled = self.broker.execute_fill(order.order_id, quantity, price)
        if not filled.get("success"):
            self.broker.cancel_order(order.order_id)
        return filled

    def _is_live(self) -> bool:
        return bool(getattr(self.broker, "IS_LIVE", False))

    def _strategy_off(self, opportunity: Any) -> Optional[str]:
        """Per-strategy switch for the kind of broker currently connected."""
        if self.controls is None:
            return None
        sid = str(getattr(opportunity, "strategy_id", "")).upper()
        if self._is_live():
            if not self.controls.live_enabled(sid):
                return f"Live trading is switched off for {sid}."
        elif not self.controls.paper_enabled(sid):
            return f"Paper trading is switched off for {sid}."
        return None

    def _blocking_for_broker(self, opportunity: Any) -> List[str]:
        """Strategy research-only flags block live, unless YOU switched that
        strategy to Live (explicit, acknowledged, after paper trades)."""
        if not self._is_live():
            return []
        sid = str(getattr(opportunity, "strategy_id", "")).upper()
        if self.controls is not None and self.controls.live_enabled(sid):
            return []
        return live_problems(opportunity)

    # ---------- controls ----------
    def set_mode(self, mode) -> TradingMode:
        self.mode = TradingMode(mode)
        self._log("MODE", mode=self.mode.value)
        return self.mode

    def halt(self) -> None:
        """Emergency stop for automated trading; clears the approval queue."""
        self.halted = True
        self.pending.clear()
        if hasattr(self.broker, "disarm"):
            self.broker.disarm()     # also lock a live broker
        self._log("HALT")

    def resume(self) -> None:
        self.halted = False
        self._log("RESUME")

    def _log(self, event: str, **info) -> None:
        self.log.append({"event": event, **info})

    # ---------- manual ----------
    def manual_order(self, symbol: str, side: str, quantity: int, price: float) -> Dict[str, Any]:
        """Your own buy/sell. Paper fills immediately at the price you give."""
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            return {"success": False, "reason": "Quantity must be a positive integer."}
        if quantity > self.max_quantity_per_order:
            return {"success": False, "reason": "Quantity exceeds the per-order limit."}
        try:
            price = float(price)
        except (TypeError, ValueError):
            return {"success": False, "reason": "Price must be a number."}
        if not price > 0:
            return {"success": False, "reason": "Price must be positive."}

        filled = self._send(symbol, side, quantity, price)
        self._log("MANUAL", symbol=symbol, side=side, quantity=quantity,
                  price=price, success=filled.get("success"))
        return filled

    # ---------- automated ----------
    def submit_opportunity(self, opportunity: Any) -> Dict[str, Any]:
        if self.mode == TradingMode.MANUAL:
            return {"status": "IGNORED", "reason": "Manual mode: opportunities are not traded."}
        if self.halted:
            return {"status": "HALTED", "reason": "Trading is halted."}

        off = self._strategy_off(opportunity)
        if off:
            self._log("STRATEGY_OFF", reason=off)
            return {"status": "STRATEGY_OFF", "reason": off}

        problems = executable_problems(opportunity, self.allow_single_leg)
        problems.extend(self._blocking_for_broker(opportunity))
        if problems:
            self._log("NOT_EXECUTABLE", reasons=problems)
            return {"status": "NOT_EXECUTABLE", "reasons": problems}

        self.scorer.score_one(opportunity)
        decision = self.risk_gate.evaluate(opportunity)
        if not decision.approved:
            self._log("RISK_REJECT", reasons=decision.reasons)
            return {"status": "RISK_REJECTED", "reasons": decision.reasons}

        opp_id = str(getattr(opportunity, "opportunity_id", id(opportunity)))

        if self.mode == TradingMode.SEMI_AUTO:
            self.pending[opp_id] = opportunity
            self._log("PENDING", id=opp_id)
            return {"status": "PENDING_APPROVAL", "id": opp_id}

        return self._execute(opportunity, opp_id)

    def list_pending(self) -> List[Dict[str, Any]]:
        return [
            {"id": key, "strategy": o.strategy_id, "symbol": o.symbol,
             "net_edge": round(o.net_edge, 2), "legs": o.legs}
            for key, o in self.pending.items()
        ]

    def approve(self, opp_id: str) -> Dict[str, Any]:
        if self.halted:
            return {"status": "HALTED", "reason": "Trading is halted."}
        opportunity = self.pending.pop(opp_id, None)
        if opportunity is None:
            return {"status": "NOT_FOUND", "reason": "No such pending opportunity."}
        return self._execute(opportunity, opp_id)

    def reject(self, opp_id: str) -> Dict[str, Any]:
        if self.pending.pop(opp_id, None) is None:
            return {"status": "NOT_FOUND", "reason": "No such pending opportunity."}
        self._log("REJECTED_BY_USER", id=opp_id)
        return {"status": "REJECTED_BY_USER"}

    def _prepare_legs(self, opportunity: Any) -> List[Dict[str, Any]]:
        problems = executable_problems(opportunity, self.allow_single_leg)
        problems.extend(self._blocking_for_broker(opportunity))
        if problems:
            raise ValueError("; ".join(problems))

        prepared = []
        for leg in opportunity.legs:
            norm = normalize_leg(leg, opportunity.symbol)
            if norm["quantity"] > self.max_quantity_per_order:
                raise ValueError("Leg quantity exceeds the per-order limit.")
            prepared.append({"symbol": norm["contract_key"], "side": norm["side"],
                             "quantity": norm["quantity"], "price": norm["price"]})
        return prepared

    def _execute(self, opportunity: Any, opp_id: str) -> Dict[str, Any]:
        off = self._strategy_off(opportunity)
        if off:
            return {"status": "STRATEGY_OFF", "reason": off}
        try:
            legs = self._prepare_legs(opportunity)
        except ValueError as exc:
            self._log("EXEC_FAIL", id=opp_id, reason=str(exc))
            return {"status": "FAILED", "reason": str(exc)}

        done = []
        for leg in legs:
            filled = self._send(leg["symbol"], leg["side"], leg["quantity"], leg["price"])
            if filled.get("success") and filled.get("filled") is False:
                # Accepted but fill not confirmed (real brokers). Do not guess: stop
                # all automation and let the user check the broker's order book.
                done.append(leg)
                self.halt()
                self._log("UNCONFIRMED_FILL", id=opp_id, legs_sent=len(done))
                return {"status": "UNCONFIRMED_FILL", "id": opp_id, "legs_sent": done,
                        "reason": "Order accepted but fill not confirmed. Automation halted; "
                                  "check your broker's order book and positions."}
            if not filled.get("success"):
                self._unwind(done)   # never leave a one-legged position
                self._log("EXEC_FAIL", id=opp_id, reason=filled.get("reason"))
                return {"status": "FAILED", "reason": filled.get("reason"),
                        "unwound_legs": len(done)}
            done.append(leg)

        if self.controls is not None and not self._is_live():
            self.controls.record_paper_trade(getattr(opportunity, "strategy_id", ""))
        self._log("EXECUTED", id=opp_id, legs=len(done))
        return {"status": "EXECUTED", "id": opp_id, "legs": done}

    def _unwind(self, done_legs: List[Dict[str, Any]]) -> None:
        for leg in reversed(done_legs):
            opposite = "SELL" if leg["side"] == "BUY" else "BUY"
            self._send(leg["symbol"], opposite, leg["quantity"], leg["price"])
