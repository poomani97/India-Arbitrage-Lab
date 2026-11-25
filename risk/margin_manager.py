"""
India Arbitrage Lab
Margin Manager

Tracks paper-trading capital and margin allocations.
Does not connect to any live broker.
"""

from dataclasses import dataclass
from typing import Dict, Any
import math


@dataclass
class MarginAllocation:
    allocation_id: str
    strategy_id: str
    capital: float
    margin: float
    status: str = "RESERVED"


class MarginManager:
    """Track available capital and reserved margin."""

    def __init__(
        self,
        total_capital: float = 100000.0,
        max_utilization: float = 0.80,
    ):
        if not math.isfinite(total_capital) or total_capital <= 0:
            raise ValueError("Total capital must be greater than zero.")

        if not math.isfinite(max_utilization):
            raise ValueError("Max utilization must be a finite number.")

        if not 0 < max_utilization <= 1:
            raise ValueError("Max utilization must be between 0 and 1.")

        self.total_capital = float(total_capital)
        self.max_utilization = float(max_utilization)
        self.allocations: Dict[str, MarginAllocation] = {}

    @property
    def max_allocatable_capital(self) -> float:
        return self.total_capital * self.max_utilization

    @property
    def reserved_margin(self) -> float:
        return sum(
            allocation.margin
            for allocation in self.allocations.values()
            if allocation.status == "RESERVED"
        )

    @property
    def reserved_capital(self) -> float:
        return sum(
            allocation.capital
            for allocation in self.allocations.values()
            if allocation.status == "RESERVED"
        )

    @property
    def available_margin(self) -> float:
        return max(0.0, self.max_allocatable_capital - self.reserved_margin)

    @property
    def available_capital(self) -> float:
        return max(0.0, self.total_capital - self.reserved_capital)

    def reserve(
        self,
        allocation_id: str,
        strategy_id: str,
        capital: float,
        margin: float,
    ) -> Dict[str, Any]:
        """Reserve capital and margin for a paper-trade allocation."""

        allocation_id = str(allocation_id).strip()
        strategy_id = str(strategy_id).strip().upper()

        if not allocation_id:
            return {
                "success": False,
                "reason": "Allocation ID cannot be empty.",
            }

        if allocation_id in self.allocations:
            return {
                "success": False,
                "reason": "Allocation ID already exists.",
            }

        if not strategy_id:
            return {
                "success": False,
                "reason": "Strategy ID cannot be empty.",
            }

        if not math.isfinite(capital) or capital <= 0:
            return {
                "success": False,
                "reason": "Capital must be a positive finite number.",
            }

        if not math.isfinite(margin) or margin <= 0:
            return {
                "success": False,
                "reason": "Margin must be a positive finite number.",
            }

        capital = float(capital)
        margin = float(margin)

        if capital > self.available_capital:
            return {
                "success": False,
                "reason": "Insufficient available capital.",
            }

        if margin > self.available_margin:
            return {
                "success": False,
                "reason": "Insufficient available margin.",
            }

        allocation = MarginAllocation(
            allocation_id=allocation_id,
            strategy_id=strategy_id,
            capital=capital,
            margin=margin,
        )

        self.allocations[allocation_id] = allocation

        return {
            "success": True,
            "reason": "Capital and margin reserved successfully.",
            "allocation": allocation,
            "available_capital": self.available_capital,
            "available_margin": self.available_margin,
        }

    def release(self, allocation_id: str) -> Dict[str, Any]:
        """Release a previously reserved allocation."""

        allocation = self.allocations.get(str(allocation_id))

        if allocation is None:
            return {
                "success": False,
                "reason": "Allocation ID not found.",
            }

        if allocation.status != "RESERVED":
            return {
                "success": False,
                "reason": "Allocation is not currently reserved.",
            }

        allocation.status = "RELEASED"

        return {
            "success": True,
            "reason": "Allocation released successfully.",
            "allocation_id": allocation.allocation_id,
            "available_capital": self.available_capital,
            "available_margin": self.available_margin,
        }

    def get_allocation(self, allocation_id: str):
        return self.allocations.get(str(allocation_id))

    def get_summary(self) -> Dict[str, Any]:
        active_allocations = [
            allocation
            for allocation in self.allocations.values()
            if allocation.status == "RESERVED"
        ]

        utilization = (
            self.reserved_margin / self.max_allocatable_capital * 100
            if self.max_allocatable_capital > 0
            else 0.0
        )

        return {
            "total_capital": round(self.total_capital, 2),
            "max_allocatable_capital": round(
                self.max_allocatable_capital, 2
            ),
            "reserved_capital": round(self.reserved_capital, 2),
            "available_capital": round(self.available_capital, 2),
            "reserved_margin": round(self.reserved_margin, 2),
            "available_margin": round(self.available_margin, 2),
            "margin_utilization_percent": round(utilization, 2),
            "active_allocations": len(active_allocations),
            "total_allocations_recorded": len(self.allocations),
        }

    def reset(self) -> None:
        """Release all currently reserved allocations."""

        for allocation in self.allocations.values():
            if allocation.status == "RESERVED":
                allocation.status = "RELEASED"
