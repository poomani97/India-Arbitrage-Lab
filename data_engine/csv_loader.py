
from pathlib import Path
from typing import Optional

import pandas as pd


class DataLoadError(Exception):
    """Raised when market data cannot be loaded or normalized."""
    pass


class CSVDataLoader:
    """
    Loads historical market data from CSV files.

    Supports common OHLC column names and normalizes them to:
        datetime, open, high, low, close, volume

    This loader does not repair questionable market data.
    It raises errors when required fields are missing or invalid.
    """

    REQUIRED_COLUMNS = [
        "datetime",
        "open",
        "high",
        "low",
        "close",
    ]

    COLUMN_ALIASES = {
        "datetime": [
            "datetime", "date_time", "timestamp", "time_stamp",
            "date", "time", "date/time", "date time"
        ],
        "open": ["open", "o"],
        "high": ["high", "h"],
        "low": ["low", "l"],
        "close": ["close", "c", "ltp", "last"],
        "volume": ["volume", "vol", "qty", "quantity"],
    }

    def __init__(self):
        self.last_loaded_file: Optional[str] = None

    @staticmethod
    def _normalize_column_name(name: str) -> str:
        return (
            str(name)
            .strip()
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )

    def _map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map input column names to standard names."""

        normalized_columns = {
            original: self._normalize_column_name(original)
            for original in df.columns
        }

        df = df.rename(columns=normalized_columns)

        rename_map = {}

        for standard_name, aliases in self.COLUMN_ALIASES.items():
            normalized_aliases = [
                self._normalize_column_name(alias)
                for alias in aliases
            ]

            for column in df.columns:
                if column in normalized_aliases:
                    rename_map[column] = standard_name
                    break

        df = df.rename(columns=rename_map)

        # Combine separate date and time columns if both exist.
        if "datetime" not in df.columns:
            date_col = next(
                (c for c in df.columns if c == "date"),
                None,
            )
            time_col = next(
                (c for c in df.columns if c == "time"),
                None,
            )

            if date_col and time_col:
                df["datetime"] = (
                    df[date_col].astype(str)
                    + " "
                    + df[time_col].astype(str)
                )

        return df

    def load(
        self,
        file_path: str,
        parse_dates: bool = True,
    ) -> pd.DataFrame:
        """
        Load and normalize a CSV file.

        Parameters
        ----------
        file_path : str
            Path to the CSV file.
        parse_dates : bool
            Convert datetime column to pandas datetime.

        Returns
        -------
        pandas.DataFrame
            Normalized market data.
        """

        path = Path(file_path)

        if not path.exists():
            raise DataLoadError(f"File not found: {file_path}")

        if not path.is_file():
            raise DataLoadError(f"Path is not a file: {file_path}")

        if path.suffix.lower() != ".csv":
            raise DataLoadError("Only CSV files are supported")

        try:
            df = pd.read_csv(path)
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(path, encoding="latin-1")
            except Exception as exc:
                raise DataLoadError(
                    f"Could not decode CSV file: {exc}"
                ) from exc
        except Exception as exc:
            raise DataLoadError(
                f"Could not read CSV file: {exc}"
            ) from exc

        if df.empty:
            raise DataLoadError("CSV file contains no data rows")

        df = self._map_columns(df)

        missing_columns = [
            column for column in self.REQUIRED_COLUMNS
            if column not in df.columns
        ]

        if missing_columns:
            raise DataLoadError(
                "Missing required columns: "
                + ", ".join(missing_columns)
            )

        if parse_dates:
            try:
                df["datetime"] = pd.to_datetime(
                    df["datetime"],
                    errors="coerce",
                )
            except Exception as exc:
                raise DataLoadError(
                    f"Datetime conversion failed: {exc}"
                ) from exc

            invalid_dates = df["datetime"].isna()

            if invalid_dates.any():
                raise DataLoadError(
                    f"Found {invalid_dates.sum()} invalid datetime rows"
                )

        numeric_columns = [
            "open", "high", "low", "close"
        ]

        if "volume" in df.columns:
            numeric_columns.append("volume")

        for column in numeric_columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

        invalid_numeric = df[numeric_columns].isna().any(axis=1)

        if invalid_numeric.any():
            raise DataLoadError(
                f"Found {invalid_numeric.sum()} rows with "
                "missing or non-numeric OHLC/volume values"
            )

        # Basic OHLC integrity checks.
        invalid_ohlc = (
            (df["high"] < df["low"])
            | (df["high"] < df["open"])
            | (df["high"] < df["close"])
            | (df["low"] > df["open"])
            | (df["low"] > df["close"])
        )

        if invalid_ohlc.any():
            raise DataLoadError(
                f"Found {invalid_ohlc.sum()} invalid OHLC rows"
            )

        if "volume" in df.columns and (df["volume"] < 0).any():
            raise DataLoadError("Volume cannot be negative")

        # Sort chronologically.
        df = df.sort_values("datetime").reset_index(drop=True)

        # Keep standard columns first, additional columns after.
        standard_columns = [
            column for column in self.REQUIRED_COLUMNS
            if column in df.columns
        ]

        if "volume" in df.columns:
            standard_columns.append("volume")

        additional_columns = [
            column for column in df.columns
            if column not in standard_columns
        ]

        df = df[standard_columns + additional_columns]

        self.last_loaded_file = str(path.resolve())

        return df

    def load_preview(
        self,
        file_path: str,
        rows: int = 10,
    ) -> pd.DataFrame:
        """Load CSV and return the first requested rows."""

        if rows <= 0:
            raise ValueError("rows must be greater than zero")

        df = self.load(file_path)
        return df.head(rows)

    def get_file_info(self, file_path: str) -> dict:
        """Return basic file information."""

        path = Path(file_path)

        if not path.exists() or not path.is_file():
            raise DataLoadError(f"File not found: {file_path}")

        df = self.load(file_path)

        return {
            "file_name": path.name,
            "file_size_bytes": path.stat().st_size,
            "rows": len(df),
            "columns": list(df.columns),
            "start_datetime": str(df["datetime"].iloc[0]),
            "end_datetime": str(df["datetime"].iloc[-1]),
        }
      
