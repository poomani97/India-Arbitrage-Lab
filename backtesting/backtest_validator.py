
from math import isfinite


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

    def _get_value(self, item, key, default=None):
        if isinstance(item, dict):
            return item.get(key, default)

        return getattr(item, key, default)

    def _is_number(self, value):
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and isfinite(value)
        )

    def validate_trade(self, trade, report=None):
        if report is None:
            report = ValidationReport()

        # Required fields
        for field in self.REQUIRED_TRADE_FIELDS:
            value = self._get_value(trade, field)

            if value is None:
                report.add_error(
                    f"Trade missing required field: {field}"
                )
            else:
                report.add_pass()

        # Validate entry price
        entry_price = self._get_value(trade, "entry_price")

        if entry_price is not None:
            if not self._is_number(entry_price):
                report.add_error(
                    "Entry price must be a finite number."
                )
            elif entry_price <= 0:
                report.add_error(
                    "Entry price must be greater than zero."
 
            else:
                report.add_pass()

        # Validate exit price
        exit_price = self._get_value(trade, "exit_price")

        if exit_price is not None:
            if not self._is_number(exit_price):
                report.add_error(
                    "Exit price must be a finite number."
                )
            elif exit_price <= 0:
                report.add_error(
                    "Exit price must be greater than zero."
                )
            else:
                report.add_pass()

        # Validate PnL
        pnl = self._get_value(trade, "pnl")

        if pnl is not None:
            if not self._is_number(pnl):
                report.add_error(
                    "Trade PnL must be a finite number."
"
                )
            else:
                report.add_pass()

        # Validate side
        side = self._get_value(trade, "side")

        if side is not None:
            normalized_side = str(side).upper()

            if normalized_side not in (
                "BUY",
                "SELL",
                "LONG",
                "SHORT",
            ):
                report.add_error(
                    f"Invalid trade side: {side}"
                )
            else:
                report.add_pass()

        # Validate timestamps when present
        entry_time = self._get_value(trade, "entry_time")
        exit_time = self._get_value(trade, "exit_time")

        if entry_time is not None and exit_time is not None:
            if exit_time < entry_time:
                report.add_error(
                    "Exit time occurs before entry time."
"
                )
            else:
                report.add_pass()

        # Validate stop loss
        stop_loss = self._get_value(trade, "stop_loss")

        if stop_loss is not None:
            if not self._is_number(stop_loss):
                report.add_error(
                    "Stop loss must be a finite number."
"
                )
            elif stop_loss <= 0:
                report.add_error(
                    "Stop loss must be greater than zero."
"
                )
            else:
                report.add_pass()

        # Validate take profit
        take_profit = self._get_value(trade, "take_profit")

        if take_profit is not None:
            if not self._is_number(take_profit):
                report.add_error(
                    "Take profit must be a finite number."
"
                )
            elif take_profit <= 0:
                report.add_error(
                    "Take profit must be greater than zero."
"
            )
            else:
                report.add_pass()

        return report

    def validate_trades(self, trades):
        report = ValidationReport()

        if not isinstance(trades, (list, tuple)):
            report.add_error(
                "Trades must be supplied as a list or tuple."
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

            trade_id = self._get_value(trade, "trade_id")

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
                "Metrics must be supplied as a dictionary."
"
            )
            return report

        for field in self.REQUIRED_METRICS:
            if field not in metrics:
                report.add_error(
                    f"Metrics missing required field: {field}"
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

        # Optional metric checks
        for field in (
            "max_drawdown",
            "profit_factor",
            "average_win",
            "average_loss",
        ):
            value = metrics.get(field)

            if value is not None and not self._is_number(value):
                report.add_error(
                    f"{field} must be a finite number."
"
            )

        max_drawdown = metrics.get("max_drawdown")

        if max_drawdown is not None:
            if self._is_number(max_drawdown):
                if max_drawdown < 0:
                    report.add_warning(
                        "max_drawdown is negative. "
                        "Check the metric convention."
"
                )
                else:
                    report.add_pass()

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
            metrics_report = self.validate_metrics(
                result["metrics"]
            )
            report.errors.extend(metrics_report.errors)
            report.warnings.extend(metrics_report.warnings)
            report.checks_passed += metrics_report.checks_passed
            report.checks_failed += metrics_report.checks_failed

        # Cross-check trade count against metrics
        trades = result.get("trades")
        metrics = result.get("metrics")

        if isinstance(trades, (list, tuple)) and isinstance(
            metrics, dict
        ):
            metric_trade_count = metrics.get("total_trades")

            if metric_trade_count is not None:
                if metric_trade_count != len(trades):
                    report.add_error(
                        "Metrics total_trades does not match "
                        "the actual trade list length."
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
          
