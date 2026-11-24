
# India Arbitrage Lab
# Strategies package

from .base_strategy import BaseStrategy
from .s01_cash_futures_carry import CashFuturesCarryStrategy

__all__ = [
    "BaseStrategy",
    "CashFuturesCarryStrategy",
]
