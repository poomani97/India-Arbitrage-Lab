
"""
India Arbitrage Lab - Backtest Engine

Historical strategy simulation for research purposes.
No live trading.
"""

from dataclasses import dataclass, asdict
from typing import Optional, List

import pandas as pd


@dataclass
class BacktestTrade:
    entry_time: object
    exit_time: object
    direction: str
    entry_price: float
    exit_price: float
    quantity: float
    gross_pnl: float
    costs: float
    net_pnl: float
    bars_held: int


class BacktestEngine:
    """
    Basic single-position backtesting engine.

    Signals:
        1  = Long
       -1  = Short
        0  = Flat

    Signal is read on one candle and execution is simulated
    on the next candle's open to reduce look-ahead bias.

    This is a simplified research simulator, not an exchange-
    accurate execution model.
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

        self.trades: List[BacktestTrade] = []
        self.equity_curve = pd.DataFrame()
        self.metrics = {}

    def run(
        self,
        data: pd.DataFrame,
        signal_column: str = "signal",
        price_column: str = "close",
        open_column: Optional[str] = "open",
    ) -> dict:
        """
        Run a backtest on historical data.

        Signal execution:
        - Signal is generated at candle close.
        - Execution occurs at next candle open (if available).
        - Position reversals close the old position and open the new.
        - Only one position is held at a time.

        Required columns:
            signal_column
            price_column
            open_column (optional)

        Signals must be -1, 0, or 1.
        """

        if data is None or data.empty:
            raise ValueError("Historical data is empty.")

        if signal_column not in data.columns:
            raise ValueError(
                f"Missing signal column: {signal_column}"
            )

        if price_column not in data.columns:
            raise ValueError(
                f"Missing price column: {price_column}"
            )

        df = data.copy()

        if open_column and open_column in df.columns:
            execution_prices = df[open_column].astype(float)
        else:
            execution_prices = df[price_column].astype(float)

        df["_execution_price"] = execution_prices
        df["_signal"] = df[signal_column]

        if not df.index.is_monotonic_increasing:
            df = df.sort_index()

        df["_signal"] = pd.to_numeric(
            df["_signal"], errors="coerce"
        ).fillna(0)

        if not df["_signal"].isin([-1, 0, 1]).all():
            raise ValueError(
                "Signals must only contain -1, 0, or 1."
            )

        if not pd.api.types.is_numeric_dtype(
            df["_execution_price"]
        ):
            raise ValueError("Execution prices must be numeric.")

        if (
            df["_execution_price"].isna().any()
            or (df["_execution_price"] <= 0).any()
        ):
            raise ValueError(
                "Execution prices must be valid and positive."
            )

        df = df.reset_index(drop=False)
        time_column = df.columns[0]

        self.trades = []
        position = 0
        entry_price = 0.0
        entry_time = None
        entry_bar = 0
        equity = self.initial_capital

        equity_rows = []

        # Signals on bar i execute on bar i+1.
        for i in range(len(df) - 1):
            current_signal = int(df.loc[i, "_signal"])
            next_price = float(df.loc[i + 1, "_execution_price"])
            next_time = df.loc[i + 1, time_column]

            # Close position if signal changes.
            if current_signal != position:
                if position != 0:
                    gross_pnl = (
                        (next_price - entry_price)
                        * position
                        * self.position_size
                    )

                    costs = self.cost_per_trade * 2

                    net_pnl = gross_pnl - costs
                    equity += net_pnl

                    self.trades.append(
                        BacktestTrade(
                            entry_time=entry_time,
                            exit_time=next_time,
                            direction=(
                                "LONG" if position > 0 else "SHORT"
                            ),
                            entry_price=entry_price,
                            exit_price=next_price,
                            quantity=self.position_size,
                            gross_pnl=gross_pnl,
                            costs=costs,
                            net_pnl=net_pnl,
                            bars_held=i - entry_bar + 1,
                        )
                    )

                    position = 0
                    entry_price = 0.0
                    entry_time = None

                # Open new position if the new signal is non-zero.
                if current_signal != 0:
                    position = current_signal
                    entry_price = next_price
                    entry_time = next_time
                    entry_bar = i + 1

            equity_rows.append(
                {
                    "time": df.loc[i, time_column],
                    "equity": equity,
                    "position": position,
                }
            )

        # Close any remaining position at the final candle close.
        if position != 0:
            final_price = float(df.iloc[-1][price_column])
            final_time = df.iloc[-1][time_column]

            gross_pnl = (
                (final_price - entry_price)
                * position
                * self.position_size
            )

            costs = self.cost_per_trade * 2
            net_pnl = gross_pnl - costs
            equity += net_pnl

            self.trades.append(
                BacktestTrade(
                    entry_time=entry_time,
                    exit_time=final_time,
                    direction=(
                        "LONG" if position > 0 else "SHORT"
                    ),
                    entry_price=entry_price,
                    exit_price=final_price,
                    quantity=self.position_size,
                    gross_pnl=gross_pnl,
                    costs=costs,
                    net_pnl=net_pnl,
                    bars_held=len(df) - entry_bar,
                )
            )

        # Add final equity point.
        equity_rows.append(
            {
                "time": df.iloc[-1][time_column],
                "equity": equity,
                "position": 0,
            }
        )

        self.equity_curve = pd.DataFrame(equity_rows)

        self.metrics = self._calculate_metrics()

        return {
            "trades": [
                asdict(trade) for trade in self.trades
            ],
            "equity_curve": self.equity_curve.copy(),
            "metrics": self.metrics.copy(),
        }

    def _calculate_metrics(self) -> dict:
        total_trades = len(self.trades)

        wins = [
            trade for trade in self.trades
            if trade.net_pnl > 0
        ]

        losses = [
            trade for trade in self.trades
            if trade.net_pnl < 0
        ]

        total_profit = sum(
            trade.net_pnl for trade in wins
        )

        total_loss = abs(sum(
            trade.net_pnl for trade in losses
        ))

        net_pnl = sum(
            trade.net_pnl for trade in self.trades
        )

        win_rate = (
            len(wins) / total_trades * 100
            if total_trades else 0.0
        )

        profit_factor = (
            total_profit / total_loss
            if total_loss > 0
            else float("inf") if total_profit > 0
            else 0.0
        )

        if not self.equity_curve.empty:
            equity = self.equity_curve["equity"]
            running_peak = equity.cummax()
            drawdown = running_peak - equity

            max_drawdown = (
                float(drawdown.max())
                if not drawdown.empty
                else 0.0
            )

            max_drawdown_pct = (
                float(
                    (drawdown / running_peak.replace(0, float("nan")))
                    .max() * 100
                )
                if not drawdown.empty
                else 0.0
            )
        else:
            max_drawdown = 0.0
            max_drawdown_pct = 0.0

        average_trade = (
            net_pnl / total_trades
            if total_trades else 0.0
        )

        return {
            "initial_capital": self.initial_capital,
            "final_equity": self.initial_capital + net_pnl,
            "net_pnl": net_pnl,
            "return_pct": (
                net_pnl / self.initial_capital * 100
            ),
            "total_trades": total_trades,
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate_pct": win_rate,
            "profit_factor": profit_factor,
            "average_trade_pnl": average_trade,
            "max_drawdown": max_drawdown,
            "max_drawdown_pct": max_drawdown_pct,
        }
      
