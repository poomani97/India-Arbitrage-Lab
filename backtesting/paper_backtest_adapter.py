
from datetime import datetime, timezone
import math


class PaperBacktestAdapter:
    """
    Connects historical candle data to the paper execution engine.

    This adapter is for research/backtesting only.
    It does not place real broker orders.
    """

    def __init__(self, execution_engine, strategy_callback,
                 exit_callback=None):
        if not callable(strategy_callback):
            raise ValueError("strategy_callback must be callable.")

        if exit_callback is not None and not callable(exit_callback):
            raise ValueError("exit_callback must be callable.")

        self.execution_engine = execution_engine
        self.strategy_callback = strategy_callback
        self.exit_callback = exit_callback

        self.results = []
        self.errors = []

    @staticmethod
    def _number(value, field):
        if isinstance(value, bool):
            raise ValueError(f"{field} must be numeric.")

        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{field} must be numeric.")

        if not math.isfinite(number):
            raise ValueError(f"{field} must be finite.")

        return number

    @classmethod
    def _validate_bar(cls, bar):
        if not isinstance(bar, dict):
            raise ValueError("Each candle must be a dictionary.")

        required = ("timestamp", "open", "high", "low", "close")

        for field in required:
            if field not in bar:
                raise ValueError(f"Missing candle field: {field}")

        open_price = cls._number(bar["open"], "open")
        high_price = cls._number(bar["high"], "high")
        low_price = cls._number(bar["low"], "low")
        close_price = cls._number(bar["close"], "close")

        if min(open_price, high_price, low_price, close_price) <= 0:
            raise ValueError("OHLC prices must be positive.")

        if high_price < max(open_price, low_price, close_price):
            raise ValueError("Candle high is inconsistent.")

        if low_price > min(open_price, high_price, close_price):
            raise ValueError("Candle low is inconsistent.")

        return {
            **bar,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
        }

    def run(self, candles, symbol):
        if not isinstance(candles, (list, tuple)) or not candles:
            raise ValueError("candles must be a non-empty list.")

        symbol = str(symbol).strip().upper()

        if not symbol:
            raise ValueError("symbol is required.")

        self.results = []
        self.errors = []

        history = []
        active_position_id = None

        for index, raw_bar in enumerate(candles):
            bar = self._validate_bar(raw_bar)
            history.append(bar)

            # Update the active paper position using this candle's close.
            if active_position_id is not None:
                self.execution_engine.update_trade_price(
                    active_position_id,
                    bar["close"],
                )

                active_trade = self.execution_engine.active_trades.get(
                    active_position_id
                )

                should_exit = False

                if self.exit_callback is not None and active_trade is not None:
                    should_exit = bool(
                        self.exit_callback(bar, active_trade)
                    )

                if should_exit:
                    close_result = self.execution_engine.close_trade(
                        active_position_id,
                        bar["close"],
                    )

                    self.results.append({
                        "event": "CLOSE",
                        "timestamp": bar["timestamp"],
                        "result": close_result,
                    })

                    active_position_id = None

            # Only look for a new entry when no position is open.
            if active_position_id is None:
                signal = self.strategy_callback(bar, list(history))

                if signal is not None:
                    if not isinstance(signal, dict):
                        raise ValueError(
                            "Strategy callback must return a dictionary or None."
                        )

                    signal = dict(signal)
                    signal["symbol"] = symbol

                    open_result = self.execution_engine.execute_signal(signal)

                    self.results.append({
                        "event": "OPEN_ATTEMPT",
                        "timestamp": bar["timestamp"],
                        "result": open_result,
                    })

                    if open_result.get("status") == "EXECUTED_PAPER":
                        active_position_id = open_result["position_id"]

        # Close any remaining open position at the final candle close.
        if active_position_id is not None:
            final_bar = history[-1]

            close_result = self.execution_engine.close_trade(
                active_position_id,
                final_bar["close"],
            )

            self.results.append({
                "event": "FORCED_FINAL_CLOSE",
                "timestamp": final_bar["timestamp"],
                "result": close_result,
            })

        return self.get_report()

    def get_report(self):
        open_events = sum(
            1 for item in self.results
            if item["event"] == "OPEN_ATTEMPT"
            and item["result"].get("status") == "EXECUTED_PAPER"
        )

        close_events = sum(
            1 for item in self.results
            if item["event"] in ("CLOSE", "FORCED_FINAL_CLOSE")
        )

        rejected_events = sum(
            1 for item in self.results
            if item["event"] == "OPEN_ATTEMPT"
            and item["result"].get("status") == "REJECTED"
        )

        return {
            "mode": "HISTORICAL_PAPER_BACKTEST",
            "paper_only": True,
            "opened_trades": open_events,
            "closed_trades": close_events,
            "rejected_signals": rejected_events,
            "events": list(self.results),
            "errors": list(self.errors),
        }

    def reset(self):
        self.results.clear()
        self.errors.clear()
      
