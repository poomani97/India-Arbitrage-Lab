"""
India Arbitrage Lab
FeedRunner: pulls one snapshot per step() from a DataFeed, runs every
strategy whose required columns are present and complete in that snapshot,
and sends the opportunities to the TradingController (which applies the
mode, risk gate and halt rules).

Nothing is invented: a strategy with a missing column is reported as
not ready and skipped.
"""

from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from feeds.base import DataFeed
from pricing.cost_model import add_cost_column
from risk.estimators import OpportunityEnricher
from strategies import STRATEGY_CLASSES, get_strategy


def _default_strategies(lot_size: int) -> Dict[str, Any]:
    found = {}
    for sid in STRATEGY_CLASSES:
        try:
            found[sid] = get_strategy(sid, config={"default_lot_size": lot_size})
        except Exception:
            found[sid] = get_strategy(sid)
    return found


class FeedRunner:
    def __init__(
        self,
        feed: DataFeed,
        controller: Any,
        strategies: Optional[Dict[str, Any]] = None,
        lot_size: int = 1,
        add_costs: bool = True,
        max_age_seconds: Optional[float] = None,
        now_fn: Callable[[], pd.Timestamp] = pd.Timestamp.now,
        buffer_size: int = 500,
        enricher: Optional[OpportunityEnricher] = OpportunityEnricher(),
    ):
        self.feed = feed
        self.controller = controller
        self.strategies = strategies if strategies is not None else _default_strategies(lot_size)
        self.lot_size = lot_size
        self.add_costs = add_costs
        self.max_age_seconds = max_age_seconds
        self.now_fn = now_fn
        self.buffer_size = buffer_size
        self.enricher = enricher
        self.buffer: List[Dict[str, Any]] = []

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.buffer)

    @staticmethod
    def _not_ready(strategy: Any, latest: pd.DataFrame) -> List[str]:
        needed = sorted(getattr(strategy, "REQUIRED_COLUMNS", set()))
        return [
            c for c in needed
            if c not in latest.columns or pd.isna(latest.iloc[0][c])
        ]

    def step(self) -> Dict[str, Any]:
        if getattr(self.controller, "halted", False):
            return {"status": "HALTED"}

        row = self.feed.poll()
        if row is None:
            return {"status": "ENDED" if self.feed.finished else "NO_DATA"}

        timestamp = pd.to_datetime(row.get("datetime"), errors="coerce")
        if pd.isna(timestamp):
            return {"status": "BAD_ROW", "reason": "Row has no valid datetime."}

        if self.max_age_seconds is not None:
            age = (self.now_fn() - timestamp).total_seconds()
            if age > self.max_age_seconds:
                return {"status": "STALE", "age_seconds": round(age, 1)}

        self.buffer.append(row)
        del self.buffer[:-self.buffer_size]

        latest = pd.DataFrame([row])
        if self.add_costs:
            try:
                latest = add_cost_column(latest, lot_size=self.lot_size)
            except Exception:
                pass

        ready, skipped, errors, results = [], {}, {}, []
        opportunities = 0

        for sid, strategy in self.strategies.items():
            missing = self._not_ready(strategy, latest)
            if missing:
                skipped[sid] = missing
                continue
            try:
                found = strategy.scan(latest) or []
            except Exception as exc:
                errors[sid] = f"{type(exc).__name__}: {exc}"
                continue
            ready.append(sid)
            for opportunity in found:
                opportunities += 1
                if self.enricher is not None:
                    self.enricher.enrich(opportunity, row)
                results.append({"strategy": sid, **self.controller.submit_opportunity(opportunity)})

        return {
            "status": "OK",
            "datetime": str(timestamp),
            "ready": ready,
            "not_ready": skipped,
            "opportunities": opportunities,
            "results": results,
            "errors": errors,
        }

    def run(self, max_steps: int = 1000) -> List[Dict[str, Any]]:
        out = []
        for _ in range(max_steps):
            result = self.step()
            out.append(result)
            if result["status"] in ("ENDED", "HALTED", "NO_DATA"):
                break
        return out
