
"""
India Arbitrage Lab - Trade Journal

Trade recording, tracking, reviewing and exporting.
Research and paper trading use only.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, List
from pathlib import Path
import json
import csv
import uuid


@dataclass
class TradeRecord:
    trade_id: str
    strategy_id: str
    symbol: str
    direction: str
    entry_time: str
    entry_price: float
    quantity: float
    exit_time: Optional[str] = None
    exit_price: Optional[float] = None
    gross_pnl: float = 0.0
    transaction_costs: float = 0.0
    net_pnl: float = 0.0
    status: str = "OPEN"
    notes: str = ""
    tags: Optional[List[str]] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    @property
    def is_closed(self) -> bool:
        return self.status.upper() == "CLOSED"

    @property
    def is_open(self) -> bool:
        return self.status.upper() == "OPEN"


class TradeJournal:
    """
    Trade journal manager.

    Supports:
    - Creating trade records
    - Updating and closing trades
    - Searching trades
    - JSON persistence
    - CSV export
    """

    VALID_DIRECTIONS = {"LONG", "SHORT"}
    VALID_STATUSES = {"OPEN", "CLOSED", "CANCELLED"}

    def __init__(self):
        self.trades: List[TradeRecord] = []

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _validate_positive(value: float, field: str) -> None:
        if value <= 0:
            raise ValueError(f"{field} must be positive.")

    def create_trade(
        self,
        strategy_id: str,
        symbol: str,
        direction: str,
        entry_price: float,
        quantity: float,
        entry_time: Optional[str] = None,
        notes: str = "",
        tags: Optional[List[str]] = None,
    ) -> TradeRecord:

        direction = direction.upper().strip()

        if direction not in self.VALID_DIRECTIONS:
            raise ValueError(
                "Direction must be LONG or SHORT."
            )

        self._validate_positive(entry_price, "Entry price")
        self._validate_positive(quantity, "Quantity")

        trade = TradeRecord(
            trade_id=str(uuid.uuid4()),
            strategy_id=str(strategy_id).upper(),
            symbol=str(symbol).upper(),
            direction=direction,
            entry_time=entry_time or self._now(),
            entry_price=float(entry_price),
            quantity=float(quantity),
            notes=notes,
            tags=list(tags or []),
        )

        self.trades.append(trade)
        return trade

    def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        exit_time: Optional[str] = None,
        transaction_costs: float = 0.0,
        notes: Optional[str] = None,
    ) -> TradeRecord:

        self._validate_positive(exit_price, "Exit price")

        if transaction_costs < 0:
            raise ValueError(
                "Transaction costs cannot be negative."
            )

        trade = self.get_trade(trade_id)

        if trade is None:
            raise ValueError("Trade not found.")

        if trade.status != "OPEN":
            raise ValueError("Trade is not open.")

        if trade.direction == "LONG":
            gross_pnl = (
                exit_price - trade.entry_price
            ) * trade.quantity
        else:
            gross_pnl = (
                trade.entry_price - exit_price
            ) * trade.quantity

        trade.exit_price = float(exit_price)
        trade.exit_time = exit_time or self._now()
        trade.gross_pnl = float(gross_pnl)
        trade.transaction_costs = float(transaction_costs)
        trade.net_pnl = gross_pnl - transaction_costs
        trade.status = "CLOSED"

        if notes:
            trade.notes = (
                f"{trade.notes}\n{notes}".strip()
            )

        return trade

    def cancel_trade(
        self,
        trade_id: str,
        reason: str = "",
    ) -> TradeRecord:

        trade = self.get_trade(trade_id)

        if trade is None:
            raise ValueError("Trade not found.")

        if trade.status != "OPEN":
            raise ValueError("Only open trades can be cancelled.")

        trade.status = "CANCELLED"

        if reason:
            trade.notes = (
                f"{trade.notes}\nCancellation: {reason}".strip()
            )

        return trade

    def update_notes(
        self,
        trade_id: str,
        notes: str,
    ) -> TradeRecord:

        trade = self.get_trade(trade_id)

        if trade is None:
            raise ValueError("Trade not found.")

        trade.notes = notes
        return trade

    def add_tags(
        self,
        trade_id: str,
        tags: List[str],
    ) -> TradeRecord:

        trade = self.get_trade(trade_id)

        if trade is None:
            raise ValueError("Trade not found.")

        for tag in tags:
            clean_tag = str(tag).strip()

            if clean_tag and clean_tag not in trade.tags:
                trade.tags.append(clean_tag)

        return trade

    def get_trade(
        self,
        trade_id: str,
    ) -> Optional[TradeRecord]:

        for trade in self.trades:
            if trade.trade_id == trade_id:
                return trade

        return None

    def get_all_trades(self) -> List[TradeRecord]:
        return list(self.trades)

    def get_open_trades(self) -> List[TradeRecord]:
        return [
            trade for trade in self.trades
            if trade.status == "OPEN"
        ]

    def get_closed_trades(self) -> List[TradeRecord]:
        return [
            trade for trade in self.trades
            if trade.status == "CLOSED"
        ]

    def filter_trades(
        self,
        strategy_id: Optional[str] = None,
        symbol: Optional[str] = None,
        direction: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[TradeRecord]:

        results = self.trades

        if strategy_id:
            strategy_id = strategy_id.upper()
            results = [
                t for t in results
                if t.strategy_id == strategy_id
            ]

        if symbol:
            symbol = symbol.upper()
            results = [
                t for t in results
                if t.symbol == symbol
            ]

        if direction:
            direction = direction.upper()
            results = [
                t for t in results
                if t.direction == direction
            ]

        if status:
            status = status.upper()
            results = [
                t for t in results
                if t.status == status
            ]

        return list(results)

    def get_journal_summary(self) -> dict:
        closed = self.get_closed_trades()
        open_trades = self.get_open_trades()

        wins = [
            trade for trade in closed
            if trade.net_pnl > 0
        ]

        losses = [
            trade for trade in closed
            if trade.net_pnl < 0
        ]

        total_net_pnl = sum(
            trade.net_pnl for trade in closed
        )

        total_costs = sum(
            trade.transaction_costs for trade in closed
        )

        win_rate = (
            len(wins) / len(closed) * 100
            if closed else 0.0
        )

        return {
            "total_trades": len(self.trades),
            "open_trades": len(open_trades),
            "closed_trades": len(closed),
            "cancelled_trades": sum(
                1 for trade in self.trades
                if trade.status == "CANCELLED"
            ),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate_pct": win_rate,
            "total_net_pnl": total_net_pnl,
            "total_transaction_costs": total_costs,
            "average_net_pnl": (
                total_net_pnl / len(closed)
                if closed else 0.0
            ),
        }

    def delete_trade(self, trade_id: str) -> bool:
        trade = self.get_trade(trade_id)

        if trade is None:
            return False

        self.trades.remove(trade)
        return True

    def save_json(self, filepath: str) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = [
            asdict(trade)
            for trade in self.trades
        ]

        with path.open("w", encoding="utf-8") as file:
            json.dump(
                payload,
                file,
                indent=4,
                ensure_ascii=False,
            )

    def load_json(self, filepath: str) -> int:
        path = Path(filepath)

        if not path.exists():
            return 0

        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        if not isinstance(payload, list):
            raise ValueError(
                "Journal JSON must contain a list of trades."
            )

        loaded_trades = []

        for item in payload:
            trade = TradeRecord(**item)
            loaded_trades.append(trade)

        self.trades = loaded_trades
        return len(self.trades)

    def export_csv(self, filepath: str) -> int:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = list(
            asdict(TradeRecord(
                trade_id="",
                strategy_id="",
                symbol="",
                direction="",
                entry_time="",
                entry_price=0.0,
                quantity=0.0,
            )).keys()
        )

        with path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
            )

            writer.writeheader()

            for trade in self.trades:
                row = asdict(trade)
                row["tags"] = ",".join(trade.tags or [])
                writer.writerow(row)

        return len(self.trades)
      
