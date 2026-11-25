
"""
India Arbitrage Lab - Backtesting Package

Historical backtesting and walk-forward analysis.
Research and paper-trading use only.
"""

from .backtest_engine import BacktestEngine, BacktestTrade
from .walk_forward import WalkForwardAnalyzer

__all__ = [
    "BacktestEngine",
    "BacktestTrade",
    "WalkForwardAnalyzer",
]
