
# India Arbitrage Lab
# Strategies package

from .base_strategy import BaseStrategy
from .s01_cash_futures_carry import CashFuturesCarryStrategy
from .s02_futures_fair_value import FuturesFairValueStrategy

__all__ = [
    "BaseStrategy",
    "CashFuturesCarryStrategy",
    "FuturesFairValueStrategy",
]
