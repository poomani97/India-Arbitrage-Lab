
from .base_strategy import BaseStrategy

from .s01_cash_futures_carry import CashFuturesCarryStrategy
from .s02_futures_fair_value import FuturesFairValueStrategy
from .s03_futures_calendar_spread import FuturesCalendarSpreadStrategy
from .s04_put_call_parity import PutCallParityStrategy
from .s05_synthetic_vs_actual_futures import SyntheticVsActualFuturesStrategy
from .s06_box_spread import BoxSpreadStrategy
from .s07_index_etf_futures_fair_value import IndexETFFuturesFairValueStrategy
from .s08_index_relative_value import IndexRelativeValueStrategy
from .s09_cross_exchange_arbitrage import CrossExchangeArbitrageStrategy
from .s10_event_implied_vs_realized_move import EventImpliedVsRealizedMoveStrategy


STRATEGY_CLASSES = {
    "S01": CashFuturesCarryStrategy,
    "S02": FuturesFairValueStrategy,
    "S03": FuturesCalendarSpreadStrategy,
    "S04": PutCallParityStrategy,
    "S05": SyntheticVsActualFuturesStrategy,
    "S06": BoxSpreadStrategy,
    "S07": IndexETFFuturesFairValueStrategy,
    "S08": IndexRelativeValueStrategy,
    "S09": CrossExchangeArbitrageStrategy,
    "S10": EventImpliedVsRealizedMoveStrategy,
}


def get_strategy_registry():
    """Return all registered strategy classes."""
    return STRATEGY_CLASSES.copy()


def get_strategy(strategy_id, **kwargs):
    """Create a strategy instance by its ID."""
    strategy_class = STRATEGY_CLASSES.get(strategy_id.upper())

    if strategy_class is None:
        raise ValueError(f"Unknown strategy ID: {strategy_id}")

    return strategy_class(**kwargs)


def get_all_strategies(**kwargs):
    """Create instances of all ten strategy engines."""
    return {
        strategy_id: strategy_class(**kwargs)
        for strategy_id, strategy_class in STRATEGY_CLASSES.items()
    }


def get_strategy_ids():
    """Return all registered strategy IDs."""
    return list(STRATEGY_CLASSES.keys())


def __all__ = [
    "BaseStrategy",
    "STRATEGY_CLASSES",
    "get_strategy_registry",
    "get_strategy",
    "get_all_strategies",
    "get_strategy_ids",
    "CashFuturesCarryStrategy",
    "FuturesFairValueStrategy",
    "FuturesCalendarSpreadStrategy",
    "PutCallParityStrategy",
    "SyntheticVsActualFuturesStrategy",
    "BoxSpreadStrategy",
    "IndexETFFuturesFairValueStrategy",
    "IndexRelativeValueStrategy",
    "CrossExchangeArbitrageStrategy",
    "EventImpliedVsRealizedMoveStrategy",
]
