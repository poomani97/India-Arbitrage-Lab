"""
India Arbitrage Lab
Per-strategy switches: Paper on/off and Live on/off, saved to a JSON file.

- Paper is ON by default, Live is OFF by default for every strategy.
- Turning Live ON needs acknowledge=True and at least `min_paper_trades`
  executed paper trades for that strategy (you can set the minimum to 0).
  This explicit switch is the only thing that lifts a strategy's own
  research_only / live_trading_allowed=False flag for a live broker.
- Turning anything OFF always works immediately.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional


class StrategyControls:
    def __init__(self, path: Optional[str] = None, min_paper_trades: int = 10):
        self.path = Path(path) if path else None
        self.min_paper_trades = int(min_paper_trades)
        self.state: Dict[str, Dict[str, Any]] = {}
        self.load()

    @staticmethod
    def _key(strategy_id: Any) -> str:
        return str(strategy_id).strip().upper()

    def _get(self, strategy_id: Any) -> Dict[str, Any]:
        return self.state.setdefault(
            self._key(strategy_id), {"paper": True, "live": False, "paper_trades": 0}
        )

    def paper_enabled(self, strategy_id: Any) -> bool:
        return bool(self._get(strategy_id)["paper"])

    def live_enabled(self, strategy_id: Any) -> bool:
        return bool(self._get(strategy_id)["live"])

    def paper_trades(self, strategy_id: Any) -> int:
        return int(self._get(strategy_id)["paper_trades"])

    def set_paper(self, strategy_id: Any, on: bool) -> Dict[str, Any]:
        self._get(strategy_id)["paper"] = bool(on)
        self.save()
        return {"success": True}

    def set_live(self, strategy_id: Any, on: bool, acknowledge: bool = False) -> Dict[str, Any]:
        entry = self._get(strategy_id)
        if not on:
            entry["live"] = False
            self.save()
            return {"success": True}
        if not acknowledge:
            return {"success": False, "reason": "Confirm that you understand live orders use real money."}
        if entry["paper_trades"] < self.min_paper_trades:
            return {"success": False,
                    "reason": f"Needs {self.min_paper_trades} paper trades first "
                              f"(has {entry['paper_trades']})."}
        entry["live"] = True
        self.save()
        return {"success": True}

    def record_paper_trade(self, strategy_id: Any) -> None:
        self._get(strategy_id)["paper_trades"] += 1
        self.save()

    def all(self) -> Dict[str, Dict[str, Any]]:
        return {k: dict(v) for k, v in self.state.items()}

    def save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(
            {"min_paper_trades": self.min_paper_trades, "strategies": self.state}, indent=2))

    def load(self) -> None:
        if self.path is None or not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text())
            self.min_paper_trades = int(data.get("min_paper_trades", self.min_paper_trades))
            self.state = {k: dict(v) for k, v in data.get("strategies", {}).items()}
        except (ValueError, OSError):
            self.state = {}
