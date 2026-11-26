
import csv
import json
import math
from datetime import datetime, timezone 
from pathlib import Path
from typing import Any, Dict, List, Optional


class HistoricalQualityChecker:

    REQUIRED_FIELDS = ["timestamp", "open", "high", "low", "close"]

    COLUMN_ALIASES = {
        "timestamp": [
            "timestamp",
            "datetime",
            "date_time",
            "date",
            "time",
            "date time",
        ],
        "open": ["open", "o"],
        "high": ["high", "h"],
        "low": ["low", "l"],
        "close": ["close", "c", "ltp"],
        "volume": ["volume", "vol", "v"],
    }

    def __init__(self):
        self.last_report = None

    def _normalize_header(self, header: str) -> str:
        return (
            str(header)
            .strip()
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )

    def _resolve_columns(self, headers: List[str]) -> Dict[str, str]:
        normalized_headers = {
            self._normalize_header(header): header
            for header in headers
        }

        resolved = {}

        for field, aliases in self.COLUMN_ALIASES.items():
            for alias in aliases:
                normalized_alias = self._normalize_header(alias)

                if normalized_alias in normalized_headers:
                    resolved[field] = normalized_headers[normalized_alias]
                    break

        return resolved

    
    def _parse_timestamp(self, value: Any) -> Optional[datetime]:
        if value is None:
            return None

        value = str(value).strip()

        if not value:
            return None

        try:
            parsed = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )

            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(timezone.utc)
                parsed = parsed.replace(tzinfo=None)

            return parsed

        except ValueError:
            pass

        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d-%m-%Y %H:%M:%S",
            "%d-%m-%Y %H:%M",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%Y-%m-%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue

        return None
        

    def _parse_number(self, value: Any) -> Optional[float]:
        if value is None:
            return None

        text = str(value).strip()

        if not text:
            return None

        text = text.replace(",", "")

        try:
            number = float(text)
        except (ValueError, TypeError):
            return None

        if not math.isfinite(number):
            return None

        return number

    def check_file(self, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)

        report = {
            "file": str(path),
            "exists": path.exists(),
            "total_rows": 0,
            "valid_rows": 0,
            "invalid_rows": 0,
            "columns": [],
            "resolved_columns": {},
            "missing_columns": [],
            "duplicate_timestamps": 0,
            "out_of_order_timestamps": 0,
            "timestamp_errors": 0,
            "missing_values": 0,
            "numeric_errors": 0,
            "price_errors": 0,
            "volume_errors": 0,
            "issues": [],
            "first_timestamp": None,
            "last_timestamp": None,
            "status": "ERROR",
        }

        if not path.exists():
            report["issues"].append("File does not exist")
            self.last_report = report
            return report

        if not path.is_file():
            report["issues"].append("Path is not a file")
            self.last_report = report
            return report

        try:
            with path.open(
                "r",
                newline="",
                encoding="utf-8-sig",
            ) as file:
                reader = csv.DictReader(file)

                headers = reader.fieldnames or []
                report["columns"] = headers

                resolved = self._resolve_columns(headers)
                report["resolved_columns"] = resolved

                missing_columns = [
                    field
                    for field in self.REQUIRED_FIELDS
                    if field not in resolved
                ]

                report["missing_columns"] = missing_columns

                if missing_columns:
                    report["issues"].append(
                        "Missing required columns: "
                        + ", ".join(missing_columns)
                    )
                    report["status"] = "ERROR"
                    self.last_report = report
                    return report

                seen_timestamps = set()
                previous_timestamp = None

                for row_number, row in enumerate(reader, start=2):
                    report["total_rows"] += 1

                    row_valid = True
                    timestamp_text = row.get(resolved["timestamp"])
                    timestamp = self._parse_timestamp(timestamp_text)

                    if timestamp is None:
                        report["timestamp_errors"] += 1
                        report["issues"].append(
                            f"Row {row_number}: Invalid timestamp"
                        )
                        row_valid = False
                    else:
                        if timestamp in seen_timestamps:
                            report["duplicate_timestamps"] += 1
                            report["issues"].append(
                                f"Row {row_number}: Duplicate timestamp"
                            )
                            row_valid = False
                        else:
                            seen_timestamps.add(timestamp)

                        if (
                            previous_timestamp is not None
                            and timestamp < previous_timestamp
                        ):
                            report["out_of_order_timestamps"] += 1
                            report["issues"].append(
                                f"Row {row_number}: Timestamp out of order"
                            )
                            row_valid = False

                        if (
                            previous_timestamp is None
                            or timestamp > previous_timestamp
                        ):
                            previous_timestamp = timestamp

                        if report["first_timestamp"] is None:
                            report["first_timestamp"] = timestamp.isoformat()

                        report["last_timestamp"] = timestamp.isoformat()

                    prices = {}

                    for field in ["open", "high", "low", "close"]:
                        raw_value = row.get(resolved[field])
                        value = self._parse_number(raw_value)

                        if value is None:
                            report["numeric_errors"] += 1
                            report["missing_values"] += (
                                1 if raw_value is None or str(raw_value).strip() == ""
                                else 0
                            )
                            report["issues"].append(
                                f"Row {row_number}: Invalid {field}"
                            )
                            row_valid = False
                        elif value <= 0:
                            report["price_errors"] += 1
                            report["issues"].append(
                                f"Row {row_number}: {field} must be positive"
                            )
                            row_valid = False
                        else:
                            prices[field] = value

                    if len(prices) == 4:
                        o = prices["open"]
                        h = prices["high"]
                        l = prices["low"]
                        c = prices["close"]

                        if h < max(o, c, l):
                            report["price_errors"] += 1
                            report["issues"].append(
                                f"Row {row_number}: High is inconsistent"
                            )
                            row_valid = False

                        if l > min(o, c, h):
                            report["price_errors"] += 1
                            report["issues"].append(
                                f"Row {row_number}: Low is inconsistent"
                            )
                            row_valid = False

                    if "volume" in resolved:
                        raw_volume = row.get(resolved["volume"])

                        if raw_volume is not None and str(raw_volume).strip():
                            volume = self._parse_number(raw_volume)

                            if volume is None or volume < 0:
                                report["volume_errors"] += 1
                                report["issues"].append(
                                    f"Row {row_number}: Invalid volume"
                                )
                                row_valid = False

                    if row_valid:
                        report["valid_rows"] += 1
                    else:
                        report["invalid_rows"] += 1

        except (OSError, csv.Error, UnicodeError) as exc:
            report["issues"].append(f"File reading error: {exc}")
            report["status"] = "ERROR"
            self.last_report = report
            return report

        if report["total_rows"] == 0:
            report["issues"].append("CSV contains no data rows")
            report["status"] = "ERROR"

        elif report["invalid_rows"] == 0:
            report["status"] = "PASS"

        elif report["valid_rows"] > 0:
            report["status"] = "WARNING"

        else:
            report["status"] = "FAIL"

        self.last_report = report
        return report

    def is_usable(self, report: Dict[str, Any]) -> bool:
        return (
            report.get("status") == "PASS"
            and report.get("invalid_rows", 0) == 0
        )

    def save_report(
        self,
        report: Dict[str, Any],
        output_path: str,
    ) -> bool:
        path = Path(output_path)

        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            with path.open("w", encoding="utf-8") as file:
                json.dump(
                    report,
                    file,
                    indent=4,
                    ensure_ascii=False,
                )

            return True

        except (OSError, TypeError, ValueError):
            return False
                              
