from typing import Callable, Dict

from feeds.base import AngelOneFeed, DataFeed, DhanFeed
from feeds.fyers_feed import FyersFeed
from feeds.replay import ReplayFeed
from feeds.runner import FeedRunner

_REGISTRY: Dict[str, Callable[..., DataFeed]] = {}


def register_feed(name: str, factory: Callable[..., DataFeed]) -> None:
    _REGISTRY[str(name).strip().upper()] = factory


def create_feed(name: str, **kwargs) -> DataFeed:
    key = str(name).strip().upper()
    if key not in _REGISTRY:
        raise ValueError(f"Unknown feed: {name}. Available: {sorted(_REGISTRY)}")
    return _REGISTRY[key](**kwargs)


def list_feeds():
    return sorted(_REGISTRY)


register_feed("REPLAY", ReplayFeed)
register_feed("DHAN", DhanFeed)
register_feed("FYERS", FyersFeed)
register_feed("ANGELONE", AngelOneFeed)

__all__ = ["DataFeed", "ReplayFeed", "FeedRunner", "register_feed", "create_feed", "list_feeds"]
