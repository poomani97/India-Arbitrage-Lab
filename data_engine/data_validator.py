from dataclasses import dataclass, asdict
from typing import List, Optional

import pandas as pd


@dataclass
class ValidationIssue:
    severity: str
    issue_type: str
    message: str
    affected_rows: int = 0

    def to_dict(self):
        return asdict(self)


@dataclass
class ValidationReport:
    is_valid: bool
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_timestamps: int
    missing_values: int
    invalid_ohlc_rows: int
    negative_volume_rows: int
    timestamp_gaps: int
    issues: List[ValidationIssue]

    def to_dict(self):
        return {
            "is_valid": self.is_valid,
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "invalid_rows": self.invalid_rows,
            "duplicate_timestamps": self.duplicate_timestamps,
            "missing_values": self.missing_values,
            "invalid_ohlc_rows": self.invalid_ohlc_rows,
            "negative_volume_rows": self.negative_volume_rows,
            "timestamp_gaps": self.timestamp_gaps,
            "issues": [issue.to_dict() for issue in self.issues],
        }


class DataValidator:
    """
    Validates historical OHLCV market data.

    Timestamp gaps are reported as warnings by default because gaps
    may be caused by holidays, market breaks, or missing source data.

    This validator does not automatically modify or delete data.
    """

    REQUIRED_COLUMNS = [
        "datetime",
        "open",
        "high",
        "low",
        "close",
    ]

    def __init__(
        self,
        expected_interval_minutes: Optional[int] = None,
    ):
        if expected_interval_minutes is not None:
            if expected_interval_minutes <= 0:
                raise ValueError(
                    "expected_interval_minutes must be positive"
                )

        self.expected_interval_minutes = (
            expected_interval_minutes
        )

    def validate(self, df: pd.DataFrame) -> ValidationReport:
        """Validate a market-data DataFrame."""

        if not isinstance(df, pd.DataFrame):
            raise TypeError("Input must be a pandas DataFrame")

        issues = []

        if df.empty:
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    issue_type="EMPTY_DATA",
                    message="Dataset contains no rows.",
                )
            )

            return ValidationReport(
                is_valid=False,
                total_rows=0,
                valid_rows=0,
                invalid_rows=0,
                duplicate_timestamps=0,
                missing_values=0,
                invalid_ohlc_rows=0,
                negative_volume_rows=0,
                timestamp_gaps=0,
                issues=issues,
            )

        missing_columns = [
            column
            for column in self.REQUIRED_COLUMNS
            if column not in df.columns
        ]

        if missing_columns:
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    issue_type="MISSING_COLUMNS",
                    message=(
                        "Missing required columns: "
                        + ", ".join(missing_columns)
                    ),
                )
            )

            return ValidationReport(
                is_valid=False,
                total_rows=len(df),
                valid_rows=0,
                invalid_rows=len(df),
                duplicate_timestamps=0,
                missing_values=0,
                invalid_ohlc_rows=0,
                negative_volume_rows=0,
                timestamp_gaps=0,
                issues=issues,
            )

        data = df.copy()

        # Convert columns for validation without altering original data.
        data["datetime"] = pd.to_datetime(
            data["datetime"],
            errors="coerce",
        )

        numeric_columns = ["open", "high", "low", "close"]

        if "volume" in data.columns:
            numeric_columns.append("volume")

        for column in numeric_columns:
            data[column] = pd.to_numeric(
                data[column],
                errors="coerce",
            )

        # 1. Missing / invalid values
        required_for_check = [
            "datetime", "open", "high", "low", "close"
        ]

        if "volume" in data.columns:
            required_for_check.append("volume")

        missing_mask = data[required_for_check].isna().any(axis=1)
        missing_values = int(missing_mask.sum())

        if missing_values:
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    issue_type="MISSING_VALUES",
                    message=(
                        "Rows contain missing or invalid "
                        "datetime/numeric values."
                    ),
                    affected_rows=missing_values,
                )
            )

        # 2. Duplicate timestamps
        duplicate_mask = data["datetime"].duplicated(
            keep=False
        )

        duplicate_timestamps = int(
            data.loc[duplicate_mask, "datetime"].nunique()
        )

        duplicate_rows = int(duplicate_mask.sum())

        if duplicate_rows:
            issues.append(
                ValidationIssue(
                    severity="WARNING",
                    issue_type="DUPLICATE_TIMESTAMPS",
                    message=(
                        "Duplicate timestamps detected. "
                        "Review duplicates before backtesting."
                    ),
                    affected_rows=duplicate_rows,
                )
            )

        # 3. OHLC integrity
        valid_numeric = ~missing_mask

        invalid_ohlc_mask = (
            (data["high"] < data["low"])
            | (data["high"] < data["open"])
            | (data["high"] < data["close"])
            | (data["low"] > data["open"])
            | (data["low"] > data["close"])
        ) & valid_numeric

        invalid_ohlc_rows = int(invalid_ohlc_mask.sum())

        if invalid_ohlc_rows:
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    issue_type="INVALID_OHLC",
                    message=(
                        "OHLC relationships are invalid "
                        "in one or more candles."
                    ),
                    affected_rows=invalid_ohlc_rows,
                )
            )

        # 4. Negative volume
        negative_volume_rows = 0

        if "volume" in data.columns:
            negative_volume_mask = (
                (data["volume"] < 0)
                & data["volume"].notna()
            )

            negative_volume_rows = int(
                negative_volume_mask.sum()
            )

            if negative_volume_rows:
                issues.append(
                    ValidationIssue(
                        severity="ERROR",
                        issue_type="NEGATIVE_VOLUME",
                        message="Negative volume values detected.",
                        affected_rows=negative_volume_rows,
                    )
                )

        # 5. Timestamp gap detection
        timestamp_gaps = 0

        if self.expected_interval_minutes is not None:
            sorted_times = (
                data["datetime"]
                .dropna()
                .drop_duplicates()
                .sort_values()
            )

            differences = sorted_times.diff()

            expected_gap = pd.Timedelta(
                minutes=self.expected_interval_minutes
            )

            gap_mask = differences > expected_gap

            timestamp_gaps = int(gap_mask.sum())

            if timestamp_gaps:
                issues.append(
                    ValidationIssue(
                        severity="WARNING",
                        issue_type="TIMESTAMP_GAPS",
                        message=(
                            "Time gaps larger than the expected "
                            "interval were detected. Gaps may be "
                            "due to missing candles, market breaks, "
                            "holidays, or source-data limitations."
                        ),
                        affected_rows=timestamp_gaps,
                    )
                )

        # Count unique rows containing critical errors.
        critical_mask = (
            missing_mask
            | invalid_ohlc_mask
        )

        if "volume" in data.columns:
            critical_mask = (
                critical_mask
                | negative_volume_mask
            )

        invalid_rows = int(critical_mask.sum())
        valid_rows = len(data) - invalid_rows

        # Dataset validity: critical errors make it invalid.
        has_critical_error = any(
            issue.severity == "ERROR"
            for issue in issues
        )

        return ValidationReport(
            is_valid=not has_critical_error,
            total_rows=len(data),
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            duplicate_timestamps=duplicate_timestamps,
            missing_values=missing_values,
            invalid_ohlc_rows=invalid_ohlc_rows,
            negative_volume_rows=negative_volume_rows,
            timestamp_gaps=timestamp_gaps,
            issues=issues,
      )
