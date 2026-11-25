
"""
India Arbitrage Lab
STEP 19 - Module Adapters

Normalizes module inputs and outputs for the Main Application Engine.

Adapters do not invent trading signals, modify market prices,
or execute orders. They standardize data passed between components.
"""

from typing import Any, Callable, Dict, List, Optional


class AdapterError(Exception):
    """Raised when an adapter receives invalid data or fails."""


def normalize_list(data: Any) -> List[Any]:
    """Convert supported outputs into a standard list."""

    if data is None:
        return []

    if isinstance(data, list):
        return data

    if isinstance(data, tuple):
        return list(data)

    return [data]


def validate_callable(function: Optional[Callable], name: str):
    """Ensure a required callback is callable."""

    if function is None:
        raise AdapterError(f"{name} callback is missing.")

    if not callable(function):
        raise AdapterError(f"{name} must be callable.")

    return function


class DataAdapter:
    """Adapter for market-data loading and normalization."""

    def __init__(self, loader: Callable):
        self.loader = validate_callable(loader, "Data loader")

    def load(self, source: Any = None) -> Any:
        try:
            if source is None:
                data = self.loader()
            else:
                data = self.loader(source)

            if data is None:
                raise AdapterError("Data loader returned None.")

            return data

        except AdapterError:
            raise

        except Exception as exc:
            raise AdapterError(
                f"Data adapter failed: {exc}"
            ) from exc


class ScannerAdapter:
    """Adapter for opportunity-scanner outputs."""

    def __init__(self, scanner: Callable):
        self.scanner = validate_callable(scanner, "Scanner")

    def scan(self, market_data: Any) -> List[Any]:
        try:
            output = self.scanner(market_data)
            return normalize_list(output)

        except Exception as exc:
            raise AdapterError(
                f"Scanner adapter failed: {exc}"
            ) from exc


class ValidationAdapter:
    """Adapter for opportunity validation."""

    def __init__(self, validator: Callable):
        self.validator = validate_callable(
            validator, "Validator"
        )

    def validate(self, opportunities: Any) -> List[Any]:
        items = normalize_list(opportunities)

        try:
            output = self.validator(items)
            return normalize_list(output)

        except Exception as exc:
            raise AdapterError(
                f"Validation adapter failed: {exc}"
            ) from exc


class QualificationAdapter:
    """Adapter for qualification rules."""

    def __init__(self, qualification_function: Callable):
        self.qualification_function = validate_callable(
            qualification_function, "Qualification"
        )

    def qualify(self, opportunities: Any) -> List[Any]:
        items = normalize_list(opportunities)

        try:
            output = self.qualification_function(items)
            return normalize_list(output)

        except Exception as exc:
            raise AdapterError(
                f"Qualification adapter failed: {exc}"
            ) from exc


class RankingAdapter:
    """Adapter for opportunity ranking."""

    def __init__(self, ranking_function: Callable):
        self.ranking_function = validate_callable(
            ranking_function, "Ranking"
        )

    def rank(self, opportunities: Any) -> List[Any]:
        items = normalize_list(opportunities)

        try:
            output = self.ranking_function(items)
            return normalize_list(output)

        except Exception as exc:
            raise AdapterError(
                f"Ranking adapter failed: {exc}"
            ) from exc


class RiskAdapter:
    """
    Adapter for risk checks.

    Risk callback must return only approved items.
    This adapter does not approve trades on its own.
    """

    def __init__(self, risk_function: Callable):
        self.risk_function = validate_callable(
            risk_function, "Risk check"
        )

    def check(self, opportunities: Any) -> List[Any]:
        items = normalize_list(opportunities)

        try:
            output = self.risk_function(items)
            return normalize_list(output)

        except Exception as exc:
            raise AdapterError(
                f"Risk adapter failed: {exc}"
            ) from exc


class AdapterBundle:
    """
    Groups all adapters into one object.

    Each callback must be supplied from the actual project module.
    No fake strategy or market data is created here.
    """

    def __init__(
        self,
        data_loader: Callable,
        scanner: Callable,
        validator: Callable,
        qualification: Callable,
        ranking: Callable,
        risk_check: Callable,
    ):
        self.data = DataAdapter(data_loader)
        self.scanner = ScannerAdapter(scanner)
        self.validation = ValidationAdapter(validator)
        self.qualification = QualificationAdapter(qualification)
        self.ranking = RankingAdapter(ranking)
        self.risk = RiskAdapter(risk_check)

    def describe(self) -> Dict[str, str]:
        return {
            "data": "DataAdapter",
            "scanner": "ScannerAdapter",
            "validation": "ValidationAdapter",
            "qualification": "QualificationAdapter",
            "ranking": "RankingAdapter",
            "risk": "RiskAdapter",
        }
      
