from typing import Callable, Dict

from brokers.base import BrokerAdapter, BrokerError
from brokers.guard import CONFIRM_PHRASE, GuardedBroker
from brokers.paper_adapter import PaperBrokerAdapter
from brokers.fyers_adapter import FyersBroker
from brokers.stubs import AngelOneBroker, DhanBroker, ForexBroker, GrowwBroker

_REGISTRY: Dict[str, Callable[..., BrokerAdapter]] = {}


def register_broker(name: str, factory: Callable[..., BrokerAdapter]) -> None:
    """Add any new broker: one adapter class, one register_broker() call."""
    _REGISTRY[str(name).strip().upper()] = factory


def create_broker(name: str, **kwargs) -> BrokerAdapter:
    key = str(name).strip().upper()
    if key not in _REGISTRY:
        raise BrokerError(f"Unknown broker: {name}. Available: {sorted(_REGISTRY)}")
    return _REGISTRY[key](**kwargs)


def list_brokers():
    return sorted(_REGISTRY)


register_broker("PAPER", PaperBrokerAdapter)
register_broker("DHAN", DhanBroker)
def _guarded_fyers(**kwargs) -> BrokerAdapter:
    """Fyers is always wrapped: live orders need the settings flag, arming and limits."""
    guard_args = {k: kwargs.pop(k) for k in ("max_order_value", "max_orders_per_day") if k in kwargs}
    return GuardedBroker(FyersBroker(**kwargs), **guard_args)


register_broker("FYERS", _guarded_fyers)
register_broker("ANGELONE", AngelOneBroker)
register_broker("GROWW", GrowwBroker)
register_broker("FOREX", ForexBroker)

__all__ = ["BrokerAdapter", "BrokerError", "GuardedBroker", "CONFIRM_PHRASE",
           "PaperBrokerAdapter", "register_broker", "create_broker", "list_brokers"]
