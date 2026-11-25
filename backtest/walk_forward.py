
"""
India Arbitrage Lab - Walk Forward Analysis

Chronological rolling-window backtesting.
Research only.
"""

from typing import Optional, List

import pandas as pd

from .backtest_engine import BacktestEngine


class WalkForwardAnalyzer:
    """
    Runs a strategy signal column over chronological windows.

    This is a simple rolling-window evaluation tool.
    It does NOT train or optimize a strategy automatically.

    Window sizes are measured in rows/bars, not calendar days.
    """

    def __init__(
        self,
        initial_capital: float = 100000.0,
        position_size: float = 1.0,
        cost_per_trade: float = 0.0,
    ):
        if initial_capital <= 0:
            raise ValueError("Initial capital must be positive.")

        if position_size <= 0:
            raise ValueError("Position size must be positive.")

        if cost_per_trade < 0:
            raise ValueError("Cost cannot be negative.")

        self.initial_capital = float(initial_capital)
        self.position_size = float(position_size)
        self.cost_per_trade = float(cost_per_trade)

        self.results: List[dict] = []

    def run(
        self,
        data: pd.DataFrame,
        train_bars: int,
        test_bars: int,
        signal_column: str = "signal",
        price_column: str = "close",
        open_column: Optional[str] = "open",
        step_bars: Optional[int] = None,
    ) -> dict:
        """
        Run sequential test windows.

        Parameters
        ----------
        data:
            Historical DataFrame with price and signal columns.

        train_bars:
            Initial historical warm-up period in bars.

        test_bars:
            Number of bars in each test window.

        step_bars:
            Distance between window starts.
            Defaults to test_bars (non-overlapping test windows).

        Notes
        -----
        train_bars is currently used only as a warm-up offset.
        No strategy training occurs in this module.
        """

        if data is None or data.empty:
            raise ValueError("Historical data is empty.")

        if train_bars <= 0 or test_bars <= 0:
            raise ValueError(
                "train_bars and test_bars must be positive."
            )

        if signal_column not in data.columns:
            raise ValueError(
                f"Missing signal column: {signal_column}"
            )

        if price_column not in data.columns:
            raise ValueError(
                f"Missing price column: {price_column}"
            )

        if step_bars is None:
            step_bars = test_bars

        if step_bars <= 0:
            raise ValueError("step_bars must be positive.")

        df = data.copy()

        if not df.index.is_monotonic_increasing:
            df = df.sort_index()

        df = df.reset_index(drop=False)

        time_column = df.columns[0]

        start = train_bars
        window_number = 1

        self.results = []

        while start < len(df):
            end = min(start + test_bars, len(df))

            test_data = df.iloc[start:end].copy()

            if len(test_data) < 2:
                break

            engine = BacktestEngine(
                initial_capital=self.initial_capital,
                position_size=self.position_size,
                cost_per_trade=self.cost_per_trade,
            )

            result = engine.run(
                data=test_data,
                signal_column=signal_column,
                price_column=price_column,
                open_column=open_column,
            )

            self.results.append(
                {
                    "window": window_number,
                    "start_time": test_data.iloc[0][time_column],
                    "end_time": test_data.iloc[-1][time_column],
                    "bars": len(test_data),
                    "metrics": result["metrics"],
                }
            )

            window_number += 1
            start += step_bars

        summary = self._build_summary()

        return {
            "windows": self.results.copy(),
            "summary": summary,
        }

    def _build_summary(self) -> dict:
        if not self.results:
            return {
                "total_windows": 0,
                "average_return_pct": 0.0,
                "average_win_rate_pct": 0.0,
                "total_net_pnl": 0.0,
                "positive_windows": 0,
                "negative_windows": 0,
            }

        returns = [
            result["metrics"]["return_pct"]
            for result in self.results
        ]

        win_rates = [
            result["metrics"]["win_rate_pct"]
            for result in self.results
        ]

        pnls = [
            result["metrics"]["net_pnl"]
            for result in self.results
        ]

        return {
            "total_windows": len(self.results),
            "average_return_pct": sum(returns) / len(returns),
            "average_win_rate_pct": (
                sum(win_rates) / len(win_rates)
            ),
            "total_net_pnl": sum(pnls),
            "positive_windows": sum(
                1 for pnl in pnls if pnl > 0
            ),
            "negative_windows": sum(
                1 for pnl in pnls if pnl < 0
            ),
        }

    def get_results_dataframe(self) -> pd.DataFrame:
        rows = []

        for result in self.results:
            row = {
                "window": result["window"],
                "start_time": result["start_time"],
                "end_time": result["end_time"],
                "bars": result["bars"],
            }

            row.update(result["metrics"])
            rows.append(row)

        return pd.DataFrame(rows)
      
