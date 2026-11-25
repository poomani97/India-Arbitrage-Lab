
"""
India Arbitrage Lab - P&L Calculator

Calculates realized, unrealized and net P&L.
Research and paper-trading use only.
"""

from dataclasses import dataclass
from typing import Iterable


@dataclass
class PnLResult:
    symbol: str
    realized_pnl: float
    unrealized_pnl: float
    transaction_costs: float
    gross_pnl: float
    net_pnl: float


class PnLCalculator:
    """
    P&L calculations.

    Long:
        (Exit Price - Entry Price) * Quantity * Multiplier

    Short:
        (Entry Price - Exit Price) * Quantity * Multiplier

    Net P&L:
        Realized + Unrealized - Costs
    """

    @staticmethod
    def calculate_realized_pnl(
        entry_price: float,
        exit_price: float,
        quantity: float,
        direction: str,
        multiplier: float = 1.0,
    ) -> float:

        if entry_price < 0 or exit_price < 0:
            raise ValueError("Prices cannot be negative.")

        if quantity < 0 or multiplier <= 0:
            raise ValueError(
                "Quantity cannot be negative and multiplier must be positive."
            )

        direction = direction.upper()

        if direction == "LONG":
            return (
                exit_price - entry_price
            ) * quantity * multiplier

        elif direction == "SHORT":
            return (
                entry_price - exit_price
            ) * quantity * multiplier

        else:
            raise ValueError(
                "Direction must be LONG or SHORT."
            )

    @staticmethod
    def calculate_unrealized_pnl(
        entry_price: float,
        current_price: float,
        quantity: float,
        direction: str,
        multiplier: float = 1.0,
    ) -> float:

        if entry_price < 0 or current_price < 0:
            raise ValueError("Prices cannot be negative.")

        if quantity < 0 or multiplier <= 0:
            raise ValueError(
                "Quantity cannot be negative and multiplier must be positive."
            )

        direction = direction.upper()

        if direction == "LONG":
            return (
                current_price - entry_price
            ) * quantity * multiplier

        elif direction == "SHORT":
            return (
                entry_price - current_price
            ) * quantity * multiplier

        else:
            raise ValueError(
                "Direction must be LONG or SHORT."
            )

    @staticmethod
    def calculate_gross_pnl(
        realized_pnl: float,
        unrealized_pnl: float,
    ) -> float:
        return realized_pnl + unrealized_pnl

    @staticmethod
    def calculate_net_pnl(
        realized_pnl: float,
        unrealized_pnl: float,
        transaction_costs: float = 0.0,
    ) -> float:
        if transaction_costs < 0:
            raise ValueError(
                "Transaction costs cannot be negative."
            )

        return (
            realized_pnl
            + unrealized_pnl
            - transaction_costs
        )

    @classmethod
    def calculate_position_result(
        cls,
        position,
    ) -> PnLResult:

        realized = float(position.realized_pnl)
        unrealized = float(position.unrealized_pnl)
        costs = float(position.transaction_costs)

        gross = cls.calculate_gross_pnl(
            realized,
            unrealized,
        )

        net = cls.calculate_net_pnl(
            realized,
            unrealized,
            costs,
        )

        return PnLResult(
            symbol=position.symbol,
            realized_pnl=realized,
            unrealized_pnl=unrealized,
            transaction_costs=costs,
            gross_pnl=gross,
            net_pnl=net,
        )

    @classmethod
    def calculate_portfolio_result(
        cls,
        positions: Iterable,
    ) -> dict:

        results = [
            cls.calculate_position_result(position)
            for position in positions
        ]

        return {
            "positions": results,
            "total_realized_pnl": sum(
                r.realized_pnl for r in results
            ),
            "total_unrealized_pnl": sum(
                r.unrealized_pnl for r in results
            ),
            "total_transaction_costs": sum(
                r.transaction_costs for r in results
            ),
            "total_gross_pnl": sum(
                r.gross_pnl for r in results
            ),
            "total_net_pnl": sum(
                r.net_pnl for r in results
            ),
        }
      
