
"""
India Arbitrage Lab - Failure Analysis

Analyzes losing trades and identifies recorded loss patterns.
Research only. Does not infer proven causes.
"""

from typing import Optional

import pandas as pd


class FailureAnalyzer:
    """Analyze losing trades and their recorded characteristics."""

    def __init__(self, minimum_samples: int = 1):
        if minimum_samples < 1:
            raise ValueError(
                "minimum_samples must be at least 1."
            )

        self.minimum_samples = int(minimum_samples)

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

    def _prepare(self, trades) -> pd.DataFrame:
        df = self._to_dataframe(trades)

        if df.empty:
            return df

        if "net_pnl" not in df.columns:
            raise ValueError(
                "Trade records must contain net_pnl."
            )

        df["net_pnl"] = pd.to_numeric(
            df["net_pnl"], errors="coerce"
        )

        df = df.dropna(subset=["net_pnl"]).copy()

        if "status" in df.columns:
            df = df[
                df["status"].astype(str).str.upper() == "CLOSED"
            ].copy()

        return df

    def get_losing_trades(self, trades) -> pd.DataFrame:
        df = self._prepare(trades)

        if df.empty:
            return df

        return df[df["net_pnl"] < 0].copy()

    def analyze_overall(self, trades) -> dict:
        df = self._prepare(trades)

        if df.empty:
            return {
                "total_trades": 0,
                "losing_trades": 0,
                "loss_rate_pct": 0.0,
                "total_loss": 0.0,
                "average_loss": 0.0,
                "largest_loss": 0.0,
                "largest_loss_trade": None,
            }

        losing = df[df["net_pnl"] < 0]

        largest_loss_trade = None

        if not losing.empty:
            idx = losing["net_pnl"].idxmin()
            largest_loss_trade = losing.loc[idx].to_dict()

        total_trades = len(df)
        losing_count = len(losing)

        return {
            "total_trades": totalal_trades if False else total_trades,
            "losing_trades": losing_count,
            "loss_rate_pct": (
                losing_count / total_trades * 100
                if total_trades else 0.0
            ),
            "total_loss": float(losing["net_pnl"].sum()),
            "average_loss": (
                float(losing["net_pnl"].mean())
                if not losing.empty else 0.0
            ),
            "largest_loss": (
                float(losing["net_pnl"].min())
                if not losing.empty else 0.0
            ),
            "largest_loss_trade": largest_loss_trade,
        }

    def analyze_by_strategy(self, trades) -> pd.DataFrame:
        df = self._prepare(trades)

        if df.empty or "strategy_id" not in df.columns:
            return pd.DataFrame()

        rows = []

        for strategy_id, group in df.groupby("strategy_id"):
            losing = group[group["net_pnl"] < 0]

            if len(group) < self.minimum_samples:
                continue

            rows.append({
                "strategy_id": strategy_id,
                "total_trades": len(group),
                "losing_trades": len(losing),
                "loss_rate_pct": (
                    len(losing) / len(group) * 100
                ),
                "net_pnl": float(group["net_pnl"].sum()),
                "total_loss": float(losing["net_pnl"].sum()),
                "average_loss": (
                    float(losing["net_pnl"].mean())
                    if not losing.empty else 0.0
                ),
                "largest_loss": (
                    float(losing["net_pnl"].min())
                    if not losing.empty else 0.0
                ),
            })

        if not rows:
            return pd.DataFrame()

        return (
            pd.DataFrame(rows)
            .sort_values("total_loss")
            .reset_index(drop=True)
        )

    def analyze_by_symbol(self, trades) -> pd.DataFrame:
        df = self._prepare(trades)

        if df.empty or "symbol" not in df.columns:
            return pd.DataFrame()

        rows = []

        for symbol, group in df.groupby("symbol"):
            losing = group[group["net_pnl"] < 0]

            if len(group) < self.minimum_samples:
                continue

            rows.append({
                "symbol": symbol,
                "total_trades": len(group),
                "losing_trades": len(losing),
                "loss_rate_pct": (
                    len(losing) / len(group) * 100
                ),
                "net_pnl": float(group["net_pnl"].sum()),
                "total_loss": float(losing["net_pnl"].sum()),
                "average_loss": (
                    float(losing["net_pnl"].mean())
                    if not losing.empty else 0.0
                ),
            })

        if not rows:
            return pd.DataFrame()

        return (
            pd.DataFrame(rows)
            .sort_values("total_loss")
            .reset_index(drop=True)
        )

    def analyze_by_direction(self, trades) -> pd.DataFrame:
        df = self._prepare(trades)

        if df.empty or "direction" not in df.columns:
            return pd.DataFrame()

        rows = []

        for direction, group in df.groupby("direction"):
            losing = group[group["net_pnl"] < 0]

            if len(group) < self.minimum_samples:
                continue

            rows.append({
                "direction": direction,
                "total_trades": len(group),
                "losing_trades": len(losing),
                "loss_rate_pct": (
                    len(losing) / len(group) * 100
                ),
                "net_pnl": float(group["net_pnl"].sum()),
                "total_loss": float(losing["net_pnl"].sum()),
            })

        return pd.DataFrame(rows)

    def analyze_loss_tags(self, trades) -> pd.DataFrame:
        """
        Counts tags attached to losing trades.

        Tags represent recorded observations, not proven causes.
        """

        losing = self.get_losing_trades(trades)

        if losing.empty or "tags" not in losing.columns:
            return pd.DataFrame(
                columns=["tag", "occurrences", "total_loss"]
            )

        tag_stats = {}

        for _, trade in losing.iterrows():
            tags = trade.get("tags", [])

            if tags is None:
                continue

            if isinstance(tags, str):
                tags = [
                    item.strip()
                    for item in tags.split(",")
                    if item.strip()
                ]

            if not isinstance(tags, (list, tuple, set)):
                continue

            for tag in tags:
                clean_tag = str(tag).strip()

                if not clean_tag:
                    continue

                if clean_tag not in tag_stats:
                    tag_stats[clean_tag] = {
                        "occurrences": 0,
                        "total_loss": 0.0,
                    }

                tag_stats[clean_tag]["occurrences"] += 1
                tag_stats[clean_tag]["total_loss"] += float(
                    trade["net_pnl"]
                )

        rows = []

        for tag, stats in tag_stats.items():
            rows.append({
                "tag": tag,
                "occurrences": stats["occurrences"],
                "total_loss": stats["total_loss"],
            })

        if not rows:
            return pd.DataFrame(
                columns=["tag", "occurrences", "total_loss"]
            )

        return (
            pd.DataFrame(rows)
            .sort_values(
                "total_loss",
                ascending=True,
            )
            .reset_index(drop=True)
        )

    def get_largest_losses(
        self,
        trades,
        top_n: int = 10,
    ) -> pd.DataFrame:
        if top_n <= 0:
            raise ValueError("top_n must be positive.")

        losing = self.get_losing_trades(trades)

        if losing.empty:
            return losing

        return (
            losing.sort_values("net_pnl", ascending=True)
            .head(top_n)
            .reset_index(drop=True)
      )
      
