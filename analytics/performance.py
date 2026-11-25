
"""
India Arbitrage Lab - Performance Analytics

Performance metrics for backtests and paper-trading records.
Research only. No live trading.
"""

from typing import Iterable, Optional

import pandas as pd


class PerformanceAnalyzer:
    """Analyze closed trade records and equity curves."""

    def __init__(self, initial_capital: float = 100000.0):
        if initial_capital <= 0:
            raise ValueError("Initial capital must be positive.")

        self.initial_capital = float(initial_capital)

    @staticmethod
    def _to_dataframe(trades) -> pd.DataFrame:
        if trades is None:
            return pd.DataFrame()

        if isinstance(trades, pd.DataFrame):
            return trades.copy()

        records = []

        for trade in trades:
            if isinstance(trade, dict):
                records.append(trade)
            elif hasattr(trade, "__dict__"):
                records.append(trade.__dict__.copy())
            else:
                raise TypeError(
                    "Trades must be dictionaries or objects."
                )

        return pd.DataFrame(records)

    def analyze(self, trades) -> dict:
        df = self._to_dataframe(trades)

        if df.empty:
            return self._empty_result()

        if "status" in df.columns:
            df = df[
                df["status"].astype(str).str.upper() == "CLOSED"
            ].copy()

        if "net_pnl" not in df.columns:
            raise ValueError(
                "Trade records must contain net_pnl."
            )

        df["net_pnl"] = pd.to_numeric(
            df["net_pnl"], errors="coerce"
        )

        df = df.dropna(subset=["net_pnl"]).copy()

        if df.empty:
            return self._empty_result()

        pnl = df["net_pnl"]
        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]

        total_trades = len(df)
        winning_trades = len(wins)
        losing_trades = len(losses)
        breakeven_trades = int((pnl == 0).sum())

        gross_profit = float(wins.sum())
        gross_loss = float(abs(losses.sum()))
        net_pnl = float(pnl.sum())

        win_rate = (
            winning_trades / total_trades * 100
            if total_trades else 0.0
        )

        profit_factor = (
            gross_profit / gross_loss
            if gross_loss > 0
            else float("inf") if gross_profit > 0
            else 0.0
        )

        average_win = (
            float(wins.mean()) if not wins.empty else 0.0
        )

        average_loss = (
            float(losses.mean()) if not losses.empty else 0.0
        )

        expectancy = (
            float(pnl.mean()) if total_trades else 0.0
        )

        payoff_ratio = (
            average_win / abs(average_loss)
            if average_loss != 0
            else float("inf") if average_win > 0
            else 0.0
        )

        equity = self.initial_capital + pnl.cumsum()
        peak = equity.cummax()
        drawdown = peak - equity

        max_drawdown = (
            float(drawdown.max()) if not drawdown.empty else 0.0
        )

        max_drawdown_pct = (
            float(
                (drawdown / peak.replace(0, float("nan")) * 100)
                .max()
            )
            if not drawdown.empty
            else 0.0
        )

        return {
            "initial_capital": self.initial_capital,
            "final_equity": self.initial_capital + net_pnl,
            "total_net_pnl": net_pnl,
            "return_pct": net_pnl / self.initial_capital * 100,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "breakeven_trades": breakeven_trades,
            "win_rate_pct": win_rate,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "profit_factor": profit_factor,
            "average_win": average_win,
            "average_loss": average_loss,
            "payoff_ratio": payoff_ratio,
            "expectancy_per_trade": expectancy,
            "max_drawdown": max_drawdown,
            "max_drawdown_pct": max_drawdown_pct,
            "equity_curve": equity.tolist(),
        }

    def _empty_result(self) -> dict:
        return {
            "initial_capital": self.initial_capital,
            "final_equity": self.initial_capital,
            "total_net_pnl": 0.0,
            "return_pct": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "breakeven_trades": 0,
            "win_rate_pct": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "profit_factor": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "payoff_ratio": 0.0,
            "expectancy_per_trade": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_pct": 0.0,
            "equity_curve": [],
        }

    def analyze_by_strategy(self, trades) -> dict:
        df = self._to_dataframe(trades)

        if df.empty or "strategy_id" not in df.columns:
            return {}

        if "status" in df.columns:
            df = df[
                df["status"].astype(str).str.upper() == "CLOSED"
            ]

        if "net_pnl" not in df.columns:
            raise ValueError(
                "Trade records must contain net_pnl."
            )

        results = {}

        for strategy_id, group in df.groupby("strategy_id"):
            results[str(strategy_id)] = self.analyze(group)

        return results

    def analyze_by_direction(self, trades) -> dict:
        df = self._to_dataframe(trades)

        if df.empty or "direction" not in df.columns:
            return {}

        if "status" in df.columns:
            df = df[
                df["status"].astype(str).str.upper() == "CLOSED"
            ]

        if "net_pnl" not in df.columns:
            raise ValueError(
                "Trade records must contain net_pnl."
            )

        results = {}

        for direction, group in df.groupby("direction"):
            results[str(direction).upper()] = self.analyze(group)

        return results

    def get_equity_curve(self, trades) -> pd.DataFrame:
        df = self._to_dataframe(trades)

        if df.empty:
            return pd.DataFrame(
                columns=["trade_number", "net_pnl", "equity"]
            )

        if "status" in df.columns:
            df = df[
                df["status"].astype(str).str.upper() == "CLOSED"
            ]

        if "net_pnl" not in df.columns:
            raise ValueError(
                "Trade records must contain net_pnl."
            )

        df["net_pnl"] = pd.to_numeric(
            df["net_pnl"], errors="coerce"
        )

        df = df.dropna(subset=["net_pnl"]).copy()

        df["trade_number"] = range(1, len(df) + 1)
        df["equity"] = (
            self.initial_capital + df["net_pnl"].cumsum()
        )

        return df[["trade_number", "net_pnl", "equity"]]

    def get_monthly_pnl(self, trades) -> pd.DataFrame:
        df = self._to_dataframe(trades)

        if df.empty or "exit_time" not in df.columns:
            return pd.DataFrame(
                columns=["month", "net_pnl", "trade_count"]
            )

        if "status" in df.columns:
            df = df[
                df["status"].astype(str).str.upper() == "CLOSED"
            ].copy()

        if "net_pnl" not in df.columns:
            raise ValueError(
                "Trade records must contain net_pnl."
            )

        df["exit_time"] = pd.to_datetime(
            df["exit_time"], errors="coerce"
        )

        df["net_pnl"] = pd.to_numeric(
            df["net_pnl"], errors="coerce"
        )

        df = df.dropna(subset=["exit_time", "net_pnl"])

        df["month"] = df["exit_time"].dt.to_period("M")

        monthly = (
            df.groupby("month")
            .agg(
                net_pnl=("net_pnl", "sum"),
                trade_count=("net_pnl", "count"),
            )
            .reset_index()
        )

        monthly["month"] = monthly["month"].astype(str)

        return monthly
      
