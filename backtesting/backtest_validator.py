
import math


class ValidationReport:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.checks_passed = 0
        self.checks_failed = 0

    @property
    def is_valid(self):
        return len(self.errors) == 0

    @property
    def status(self):
        if self.errors:
            return "FAIL"
        if self.warnings:
            return "WARNING"
        return "PASS"

    def add_error(self, message):
        self.errors.append(message)
        self.checks_failed += 1

    def add_warning(self, message):
        self.warnings.append(message)

    def add_pass(self):
        self.checks_passed += 1

    def to_dict(self):
        return {
            "status": self.status,
            "is_valid": self.is_valid,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


class BacktestValidator:
    REQUIRED_TRADE_FIELDS = (
        "entry_price",
        "exit_price",
        "pnl",
    )

    REQUIRED_METRICS = (
        "total_trades",
        "win_rate",
        "total_pnl",
    )

    @staticmethod
    def _get(item, key, default=None):
        if isinstance(item, dict):
            return item.get(key, default)
        return getattr(item, key, default)

    @staticmethod
    def _is_number(value):
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        )

    def validate_trade(self, trade, report=None):
        if report is None:
            report = ValidationReport()

        for field in self.REQUIRED_TRADE_FIELDS:
            value = self._get(trade, field)

            if value is None:
                report.add_error(
                    f"Missing required trade field: {field}"
                )
            else:
                report.add_pass()

        for field in ("entry_price", "exit_price"):
            value = self._get(trade, field)

            if value is None:
                continue
                
                if not self._is_number(value):
    report.add_error(
        f"{field} must be a finite number."
    )
elif value <= 0:
    report.add_error(
        f"{field} must be greater than zero."
    )
            )
            else:
                report.add_pass()

        pnl = self._get(trade, "pnl")

        if pnl is not None:
            if not self._is_number(pnl):
                report.add_error(
                    "PnL must be a finite number."
"
            )
            else:
                report.add_pass()

        side = self._get(trade, "side")

        if side is not None:
            if str(side).upper() not in (
                "BUY", "SELL", "LONG", "SHORT"
            ):
                report.add_error(
                    f"Invalid trade side: {side}"
                )
            else:
                report.add_pass()

        entry_time = self._get(trade, "entry_time")
        exit_time = self._get(trade, "exit_time")

        if entry_time is not None and exit_time is not None:
            try:
                if exit_time < entry_time:
                    report.add_error(
                        "Exit time is before entry time."
"
                )
                else:
                    report.add_pass()
            except TypeError:
                report.add_error(
                    "Entry and exit times cannot be compared."
"
            )

        for field in ("stop_loss", "take_profit"):
            value = self._get(trade, field)

            if value is None:
                continue

            if not self._is_number(value):
                report.add_error(
                    f"{field} must be a finite number."
"
            )
            elif value <= 0:
                report.add_error(
                    f"{field} must be greater than zero."
"
            )
            else:
                report.add_pass()

        return report

    def validate_trades(self, trades):
        report = ValidationReport()

        if not isinstance(trades, (list, tuple)):
            report.add_error(
                "Trades must be a list or tuple."
"
            )
            return report

        report.add_pass()
        seen_ids = set()

        for index, trade in enumerate(trades):
            if trade is None:
                report.add_error(
                    f"Trade at index {index} is None."
"
            )
                continue

            trade_id = self._get(trade, "trade_id")

            if trade_id is not None:
                if trade_id in seen_ids:
                    report.add_error(
                        f"Duplicate trade_id: {trade_id}"
                    )
                else:
                    seen_ids.add(trade_id)
                    report.add_pass()

            self.validate_trade(trade, report)

        return report

    def validate_metrics(self, metrics):
        report = ValidationReport()

        if not isinstance(metrics, dict):
            report.add_error(
                "Metrics must be a dictionary."
"
            )
            return report

        for field in self.REQUIRED_METRICS:
            if field not in metrics:
                report.add_error(
                    f"Missing metric: {field}"
                )
            else:
                report.add_pass()

        total_trades = metrics.get("total_trades")
        win_rate = metrics.get("win_rate")
        total_pnl = metrics.get("total_pnl")

        if total_trades is not None:
            if (
                not isinstance(total_trades, int)
                or isinstance(total_trades, bool)
                or total_trades < 0
            ):
                report.add_error(
                    "total_trades must be a non-negative integer."
"
            )
            else:
                report.add_pass()

        if win_rate is not None:
            if not self._is_number(win_rate):
                report.add_error(
                    "win_rate must be a finite number."
"
            )
            elif not 0 <= win_rate <= 100:
                report.add_error(
                    "win_rate must be between 0 and 100."
"
            )
            else:
                report.add_pass()

        if total_pnl is not None:
            if not self._is_number(total_pnl):
                report.add_error(
                    "total_pnl must be a finite number."
"
            )
            else:
                report.add_pass()

        for field in (
            "max_drawdown",
            "profit_factor",
            "average_win",
            "average_loss",
        ):
            value = metrics.get(field)

            if value is not None:
                if not self._is_number(value):
                    report.add_error(
                        f"{field} must be a finite number."
"
                )
                else:
                    report.add_pass()

        max_drawdown = metrics.get("max_drawdown")

        if self._is_number(max_drawdown):
            if max_drawdown < 0:
                report.add_warning(
                    "max_drawdown is negative; check its convention."
"
            )

        return report

    def validate_result(self, result):
        report = ValidationReport()

        if not isinstance(result, dict):
            report.add_error(
                "Backtest result must be a dictionary."
"
            )
            return report

        if "trades" not in result:
            report.add_error(
                "Backtest result is missing trades."
"
            )
        else:
            trade_report = self.validate_trades(
                result["trades"]
            )
            report.errors.extend(trade_report.errors)
            report.warnings.extend(trade_report.warnings)
            report.checks_passed += trade_report.checks_passed
            report.checks_failed += trade_report.checks_failed

        if "metrics" not in result:
            report.add_error(
                "Backtest result is missing metrics."
"
            )
        else:
            metric_report = self.validate_metrics(
                result["metrics"]
            )
            report.errors.extend(metric_report.errors)
            report.warnings.extend(metric_report.warnings)
            report.checks_passed += metric_report.checks_passed
            report.checks_failed += metric_report.checks_failed

        trades = result.get("trades")
        metrics = result.get("metrics")

        if isinstance(trades, (list, tuple)) and isinstance(
            metrics, dict
        ):
            reported_count = metrics.get("total_trades")

            if reported_count is not None:
                if reported_count != len(trades):
                    report.add_error(
                        "Reported trade count does not match "
                        "the actual trades list."
"
                )
                else:
                    report.add_pass()

        return report

    def validate_and_raise(self, result):
        report = self.validate_result(result)

        if not report.is_valid:
            raise ValueError(
                "Backtest validation failed: "
                + "; ".join(report.errors)
            )

        return report
        
