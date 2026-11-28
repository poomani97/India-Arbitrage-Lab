from typing import Any, Dict, Optional

import pandas as pd

from feeds.base import DataFeed


class ReplayFeed(DataFeed):
    """Plays a prepared DataFrame back one row per poll(), like a live feed.

    Use it to test the whole system before a real broker feed is connected.
    The frame must have a datetime column (see data_engine.schema).
    """

    NAME = "REPLAY"
    IS_LIVE = False

    def __init__(self, frame: pd.DataFrame):
        if "datetime" not in frame.columns:
            raise ValueError("Replay frame needs a datetime column.")
        self._rows = frame.sort_values("datetime").to_dict("records")
        self._i = 0

    @property
    def finished(self) -> bool:
        return self._i >= len(self._rows)

    def poll(self) -> Optional[Dict[str, Any]]:
        if self.finished:
            return None
        row = self._rows[self._i]
        self._i += 1
        return row

    def remaining(self) -> int:
        return len(self._rows) - self._i
