
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4
from typing import Optional


class TradeStatus(str, Enum):
    CREATED = "CREATED"
    OPEN = "OPEN"
    PARTIALLY_CLOSED = "PARTIALLY_CLOSED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class TradeSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class Trade:
    """
    Standard trade model for India Arbitrage Lab.

    Used by paper trading, backtesting, portfolio tracking,
    P&L reporting and trade journal modules.
    """

    strategy_id: str
    symbol: str
    market: str
    side: TradeSide
    quantity: int

    # Unique trade identification
    trade_id: str = field(default_factory=lambda: str(uuid4()))

    # Entry information
    entry_price: float = 0.0
    entry_time: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Exit information
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None

    # Costs
    entry_costs: float = 0.0
    exit_costs: float = 0.0

    # Contract information
    multiplier: float = 1.0

    # Capital and margin
    capital_used: float = 0.0
    margin_used: float = 0.0

    # Trade status
    status: TradeStatus = TradeStatus.CREATED

    # P&L
    gross_pnl: float = 0.0
    net_pnl: float = 0.0

    # Additional information
    notes: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        self.validate()

    def validate(self):
        """Validate trade inputs."""

        if not self.strategy_id:
            raise ValueError("strategy_id cannot be empty")

        if not self.symbol:
            raise ValueError("symbol cannot be empty")

        if not self.market:
            raise ValueError("market cannot be empty")

        if not isinstance(self.side, TradeSide):
            raise TypeError("side must be a TradeSide value")

        if not isinstance(self.quantity, int) or self.quantity <= 0:
            raise ValueError("quantity must be a positive integer")

        if self.entry_price < 0:
            raise ValueError("entry_price cannot be negative")

        if self.exit_price is not None and self.exit_price < 0:
            raise ValueError("exit_price cannot be negative")

        if self.entry_costs < 0 or self.exit_costs < 0:
            raise ValueError("trade costs cannot be negative")

        if self.multiplier <= 0:
            raise ValueError("multiplier must be greater than zero")

        if self.capital_used < 0 or self.margin_used < 0:
            raise ValueError("capital and margin cannot be negative")

        return True

    def open_trade(self):
        """Mark trade as open."""

        if self.status != TradeStatus.CREATED:
            raise ValueError("Only CREATED trades can be opened")

        if self.entry_price <= 0:
            raise ValueError("Entry price must be greater than zero")

        self.status = TradeStatus.OPEN
        return self.status

    def calculate_gross_pnl(self, exit_price: float):
        """Calculate gross profit or loss before costs."""

        if exit_price <= 0:
            raise ValueError("Exit price must be greater than zero")

        price_difference = exit_price - self.entry_price

        if self.side == TradeSide.SHORT:
            price_difference = -price_difference

        self.gross_pnl = (
            price_difference * self.quantity * self.multiplier
        )

        return self.gross_pnl

    def calculate_net_pnl(self, exit_price: float):
        """Calculate net P&L after entry and exit costs."""

        gross = self.calculate_gross_pnl(exit_price)

        total_costs = self.entry_costs + self.exit_costs

        self.net_pnl = gross - total_costs

        return self.net_pnl

    def close_trade(self, exit_price: float, exit_costs: float = 0.0):
        """Close an open trade and record final P&L."""

        if self.status not in (
            TradeStatus.OPEN,
            TradeStatus.PARTIALLY_CLOSED,
        ):
            raise ValueError("Trade is not open")

        if exit_price <= 0:
            raise ValueError("Exit price must be greater than zero")

        if exit_costs < 0:
            raise ValueError("exit_costs cannot be negative")

        self.exit_price = exit_price
        self.exit_costs = exit_costs
        self.exit_time = datetime.now(timezone.utc)

        self.calculate_net_pnl(exit_price)

        self.status = TradeStatus.CLOSED

        return self.net_pnl

    def cancel_trade(self):
        """Cancel a trade that has not been opened."""

        if self.status != TradeStatus.CREATED:
            raise ValueError("Only CREATED trades can be cancelled")

        self.status = TradeStatus.CANCELLED
        return self.status

    @property
    def total_costs(self):
        """Return total entry and exit costs."""

        return self.entry_costs + self.exit_costs

    @property
    def is_open(self):
        """Check if trade is currently open."""

        return self.status == TradeStatus.OPEN

    @property
    def is_closed(self):
        """Check if trade is closed."""

        return self.status == TradeStatus.CLOSED

    def to_dict(self):
        """Convert trade to dictionary format."""

        return {
            "trade_id": self.trade_id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "market": self.market,
            "side": self.side.value,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "entry_time": self.entry_time.isoformat(),
            "exit_price": self.exit_price,
            "exit_time": (
                self.exit_time.isoformat()
                if self.exit_time else None
            ),
            "entry_costs": self.entry_costs,
            "exit_costs": self.exit_costs,
            "total_costs": self.total_costs,
            "multiplier": self.multiplier,
            "capital_used": self.capital_used,
            "margin_used": self.margin_used,
            "gross_pnl": self.gross_pnl,
            "net_pnl": self.net_pnl,
            "status": self.status.value,
            "notes": self.notes,
            "metadata": self.metadata,
        }
