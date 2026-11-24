
# India Arbitrage Lab
# Contract Master
# Instrument and Contract Registry

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4


class InstrumentType(str, Enum):
    INDEX = "INDEX"
    EQUITY = "EQUITY"
    ETF = "ETF"
    FUTURE = "FUTURE"
    OPTION = "OPTION"


class OptionType(str, Enum):
    CALL = "CALL"
    PUT = "PUT"


@dataclass
class Contract:
    """Metadata for a market instrument or derivative contract."""

    symbol: str
    exchange: str
    instrument_type: InstrumentType

    contract_id: str = field(default_factory=lambda: str(uuid4()))
    trading_symbol: Optional[str] = None
    underlying: Optional[str] = None
    expiry_date: Optional[date] = None
    strike_price: Optional[float] = None
    option_type: Optional[OptionType] = None

    lot_size: int = 1
    tick_size: float = 0.05
    multiplier: float = 1.0
    active: bool = True

    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.instrument_type, str):
            self.instrument_type = InstrumentType(
                self.instrument_type.upper()
            )

        if isinstance(self.option_type, str):
            self.option_type = OptionType(self.option_type.upper())

        self.validate()

    def validate(self) -> None:
        if not self.symbol or not self.symbol.strip():
            raise ValueError("Contract symbol cannot be empty")

        if not self.exchange or not self.exchange.strip():
            raise ValueError("Exchange cannot be empty")

        if self.lot_size <= 0:
            raise ValueError("Lot size must be greater than zero")

        if self.tick_size <= 0:
            raise ValueError("Tick size must be greater than zero")

        if self.multiplier <= 0:
            raise ValueError("Multiplier must be greater than zero")

        if self.strike_price is not None and self.strike_price <= 0:
            raise ValueError("Strike price must be greater than zero")

        if self.instrument_type == InstrumentType.OPTION:
            if self.strike_price is None:
                raise ValueError("Options require a strike price")
            if self.option_type is None:
                raise ValueError("Options require CALL or PUT type")
            if self.expiry_date is None:
                raise ValueError("Options require an expiry date")

        if self.instrument_type == InstrumentType.FUTURE:
            if self.expiry_date is None:
                raise ValueError("Futures require an expiry date")

        if self.expiry_date is not None and not isinstance(
            self.expiry_date, date
        ):
            raise TypeError("Expiry date must be a datetime.date object")

    def to_dict(self) -> dict:
        return {
            "contract_id": self.contract_id,
            "symbol": self.symbol,
            "trading_symbol": self.trading_symbol,
            "exchange": self.exchange,
            "instrument_type": self.instrument_type.value,
            "underlying": self.underlying,
            "expiry_date": (
                self.expiry_date.isoformat()
                if self.expiry_date else None
            ),
            "strike_price": self.strike_price,
            "option_type": (
                self.option_type.value
                if self.option_type else None
            ),
            "lot_size": self.lot_size,
            "tick_size": self.tick_size,
            "multiplier": self.multiplier,
            "active": self.active,
            "metadata": self.metadata,
        }


class ContractMaster:
    """Central registry for instruments and derivative contracts."""

    def __init__(self):
        self._contracts: Dict[str, Contract] = {}

    def add(self, contract: Contract) -> Contract:
        """Register a contract. Contract IDs must be unique."""

        if not isinstance(contract, Contract):
            raise TypeError("Only Contract objects can be registered")

        if contract.contract_id in self._contracts:
            raise ValueError(
                f"Contract ID already exists: {contract.contract_id}"
            )

        self._contracts[contract.contract_id] = contract
        return contract

    def get(self, contract_id: str) -> Optional[Contract]:
        """Retrieve a contract by its unique ID."""

        return self._contracts.get(contract_id)

    def remove(self, contract_id: str) -> bool:
        """Remove a contract by ID. Returns True if removed."""

        return self._contracts.pop(contract_id, None) is not None

    def list_all(self, active_only: bool = False) -> List[Contract]:
        """Return all registered contracts."""

        contracts = list(self._contracts.values())

        if active_only:
            contracts = [
                contract for contract in contracts
                if contract.active
            ]

        return contracts

    def find(
        self,
        symbol: Optional[str] = None,
        exchange: Optional[str] = None,
        instrument_type: Optional[InstrumentType] = None,
        underlying: Optional[str] = None,
        expiry_date: Optional[date] = None,
        active_only: bool = True,
    ) -> List[Contract]:
        """Filter contracts using the supplied criteria."""

        results = list(self._contracts.values())

        if active_only:
            results = [
                c for c in results if c.active
            ]

        if symbol is not None:
            results = [
                c for c in results
                if c.symbol.upper() == symbol.upper()
                or (
                    c.trading_symbol is not None
                    and c.trading_symbol.upper() == symbol.upper()
                )
            ]

        if exchange is not None:
            results = [
                c for c in results
                if c.exchange.upper() == exchange.upper()
            ]

        if instrument_type is not None:
            if isinstance(instrument_type, str):
                instrument_type = InstrumentType(
                    instrument_type.upper()
                )
            results = [
                c for c in results
                if c.instrument_type == instrument_type
            ]

        if underlying is not None:
            results = [
                c for c in results
                if c.underlying is not None
                and c.underlying.upper() == underlying.upper()
            ]

        if expiry_date is not None:
            results = [
                c for c in results
                if c.expiry_date == expiry_date
            ]

        return results

    def find_by_underlying(
        self,
        underlying: str,
        instrument_type: Optional[InstrumentType] = None,
        active_only: bool = True,
    ) -> List[Contract]:
        """Find contracts belonging to a specified underlying."""

        return self.find(
            underlying=underlying,
            instrument_type=instrument_type,
            active_only=active_only,
        )

    def expiring_on(self, expiry_date: date) -> List[Contract]:
        """Return active contracts expiring on a specific date."""

        return self.find(
            expiry_date=expiry_date,
            active_only=True,
        )

    def deactivate(self, contract_id: str) -> bool:
        """Mark a contract inactive without deleting it."""

        contract = self.get(contract_id)

        if contract is None:
            return False

        contract.active = False
        return True

    def count(self, active_only: bool = False) -> int:
        """Return number of registered contracts."""

        return len(self.list_all(active_only=active_only))

    def clear(self) -> None:
        """Remove all contracts from memory."""

        self._contracts.clear()
      
