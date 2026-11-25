"""
India Arbitrage Lab - Execution Package
Paper trading and simulated execution only.
"""

from .paper_broker import PaperBroker, PaperOrder, PaperPosition
from .fill_simulator import FillSimulator, FillResult
from .router import ExecutionRouter, RoutingResult

__all__ = [
    "PaperBroker",
    "PaperOrder",
    "PaperPosition",
    "FillSimulator",
    "FillResult",
    "ExecutionRouter",
    "RoutingResult",
]
