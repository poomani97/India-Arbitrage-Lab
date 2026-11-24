
# India Arbitrage Lab
# Market Data Service
# Integrates CSV Loader and Data Validator

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from .csv_loader import CSVDataLoader, DataLoadError
from .data_validator import DataValidator, ValidationReport


class MarketDataError(Exception):
    """Raised when market data service operations fail."""
    pass


@dataclass
class MarketDataResult:
    """Combined result of loading and validating market data."""

    file_path: str
    dataframe: pd.DataFrame
    validation_report: ValidationReport

    @property
    def is_valid(self) -> bool:
        return self.validation_report.is_valid

    @property
    def total_rows(self) -> int:
        return len(self.dataframe)

    def preview(self, rows: int = 10) -> pd.DataFrame:
        if rows < 1:
            raise ValueError("rows must be greater than zero")
        return self.dataframe.head(rows).copy()

    def get_summary(self) -> dict:
        return {
            "file_path": self.file_path,
            "total_rows": self.total_rows,
            "is_valid": self.is_valid,
            "validation_report": self.validation_report.to_dict(),
            "columns": list(self.dataframe.columns),
            "start_datetime": (
                str(self.dataframe["datetime"].min())
                if "datetime" in self.dataframe.columns
                and not self.dataframe.empty
                else None
            ),
            "end_datetime": (
                str(self.dataframe["datetime"].max())
                if "datetime" in self.dataframe.columns
                and not self.dataframe.empty
                else None
            ),
        }


class MarketDataService:
    """Loads, validates, and summarizes historical market data."""

    def __init__(
        self,
        expected_interval_minutes: Optional[int] = None,
    ):
        self.loader = CSVDataLoader()
        self.validator = DataValidator(
            expected_interval_minutes=expected_interval_minutes
        )

    def load_and_validate(
        self,
        file_path: str,
        parse_dates: bool = True,
    ) -> MarketDataResult:
        """Load a CSV file and validate its market data."""

        try:
            dataframe = self.loader.load(
                file_path=file_path,
                parse_dates=parse_dates,
            )

            report = self.validator.validate(dataframe)

            return MarketDataResult(
                file_path=str(file_path),
                dataframe=dataframe,
                validation_report=report,
            )

        except DataLoadError as exc:
            raise MarketDataError(
                f"Could not load market data: {exc}"
            ) from exc

        except Exception as exc:
            raise MarketDataError(
                f"Market data processing failed: {exc}"
            ) from exc

    def validate_dataframe(
        self,
        dataframe: pd.DataFrame,
    ) -> ValidationReport:
        """Validate an already-loaded DataFrame."""

        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError("Input must be a pandas DataFrame")

        return self.validator.validate(dataframe)

    def preview_file(
        self,
        file_path: str,
        rows: int = 10,
    ) -> pd.DataFrame:
        """Load and return a preview of the CSV file."""

        if rows < 1:
            raise ValueError("rows must be greater than zero")

        try:
            return self.loader.load_preview(
                file_path=file_path,
                rows=rows,
            )
        except DataLoadError as exc:
            raise MarketDataError(
                f"Could not preview market data: {exc}"
            ) from exc

    def get_file_info(self, file_path: str) -> dict:
        """Return basic information about the source file."""

        try:
            return self.loader.get_file_info(file_path)
        except DataLoadError as exc:
            raise MarketDataError(
                f"Could not read file information: {exc}"
            ) from exc
          
