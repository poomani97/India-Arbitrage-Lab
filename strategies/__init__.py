
"""
India Arbitrage Lab - Strategy Registry

All strategy modules are imported and registered here.
"""

from strategies.base_strategy import BaseStrategy

from strategies.s01_cash_futures_carry import CashFuturesCarryStrategy
from strategies.s02_futures_fair_value import FuturesFairValueStrategy
from strategies.s03_futures_calendar_spread import FuturesCalendarSpreadStrategy
from strategies.s04_put_call_parity import PutCallParityStrategy
from strategies.s05_synthetic_vs_actual_futures import (
    SyntheticVsActualFuturesStrategy,
)

__all__ = [
    "BaseStrategy",
    "CashFuturesCarryStrategy",
    "FuturesFairValueStrategy",
    "FuturesCalendarSpreadStrategy",
    "PutCallParityStrategy",
    "SyntheticVsActualFuturesStrategy",
]
