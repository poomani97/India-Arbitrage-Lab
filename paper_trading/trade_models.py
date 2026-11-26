
"""
Paper Trading Models
Common data models for simulated trading.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TradeSignal:
    symbol: str
    side: str
    quantity: int
    strategy_id: str = ""
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    confidence: float = 0.0
    timestamp: str = field(default_factory=utc_now)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        self.symbol = str(self.symbol).strip().upper()
        self.side = str(self.side).strip().upper()

        if self.side not in ("BUY", "SELL"):
            raise ValueError("side must be BUY or SELL")

        if not self.symbol:
            raise ValueError("symbol is required")

        if self.quantity <= 0:
            raise ValueError("quantity must be positive")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass
class Fill:
    fill_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str = ""
    symbol: str = ""
    side: str = ""
    quantity: int = 0
    price: float = 0.0
    fees: float = 0.0
    timestamp: str = field(default_factory=utc_now)

    def __post_init__(self):
        self.symbol = str(self.symbol).strip().upper()
        self.side = str(self.side).strip().upper()

        if self.side not in ("BUY", "SELL"):
            raise ValueError("Fill side must be BUY or SELL")

        if not self.symbol:
            raise ValueError("Fill symbol is required")

        if self.quantity <= 0:
            raise ValueError("Fill quantity must be positive")

        if self.price <= 0:
            raise ValueError("Fill price must be positive")

        if self.fees < 0:
            raise ValueError("Fees cannot be negative")


@dataclass
class Position:
    symbol: str
    quantity: int = 0
    average_price: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    last_price: float = 0.0
    opened_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    @property
    def market_value(self) -> float:
        return self.quantity * self.last_price

    @property
    def cost_value(self) -> float:
        return self.quantity * self.average_price

    def update_market_price(self, price: float):
        if price <= 0:
            raise ValueError("Market price must be positive")

        self.last_price = float(price)
        self.unrealized_pnl = (
            (self.last_price - self.average_price) * self.quantity
        )
        self.updated_at = utc_now()


@dataclass
class TradeRecord:
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    side: str = ""
    quantity: int = 0
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    pnl: float = 0.0
    fees: float = 0.0
    strategy_id: str = ""
    status: str = "OPEN"
    opened_at: str = field(default_factory=utc_now)
    closed_at: Optional[str] = None
    notes: str = ""

    def close(self, exit_price: float, fees: float = 0.0):
        if self.status != "OPEN":
            raise ValueError("Trade is already closed")

        if exit_price <= 0:
            raise ValueError("Exit price must be positive")

        if fees < 0:
            raise ValueError("Fees cannot be negative")

        if self.side == "BUY":
            gross_pnl = (exit_price - self.entry_price) * self.quantity
        else:
            gross_pnl = (self.entry_price - exit_price) * self.quantity

        self.exit_price = float(exit_price)
        self.fees += fees
        self.pnl = gross_pnl - self.fees
        self.status = "CLOSED"
        self.closed_at = utc_now()

        return self.pnl
      
