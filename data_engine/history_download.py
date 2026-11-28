"""
India Arbitrage Lab
Download historical candles from Fyers into CSV files for backtesting.

Output matches the shipped Nifty files:
    Epoch,Timestamp,Open,High,Low,Close,Volume     (Timestamp is India time)
so data_engine.CSVDataLoader reads them directly.

Fyers limits how many days one request may cover, so the range is cut into
chunks (default 90 days for minute data). Chunks are joined, de-duplicated
and sorted. A failed chunk raises, so you never get a silently short file.

Written from the Fyers v3 history call (symbol, resolution, range_from,
range_to, date_format, cont_flag). Tested only with a fake client; run a
small range first. Expired futures contracts may have little or no history.
"""

import csv
from datetime import date, timedelta
from pathlib import Path
from typing import Any, List, Optional

import pandas as pd

from brokers.base import BrokerError

HEADER = ["Epoch", "Timestamp", "Open", "High", "Low", "Close", "Volume"]


def _chunks(start: date, end: date, days: int):
    current = start
    while current <= end:
        stop = min(current + timedelta(days=days - 1), end)
        yield current, stop
        current = stop + timedelta(days=1)


def fetch_candles(client: Any, symbol: str, start: date, end: date,
                  resolution: str = "1", chunk_days: int = 90) -> List[list]:
    if end < start:
        raise ValueError("end date is before start date.")
    rows = {}
    for chunk_start, chunk_end in _chunks(start, end, chunk_days):
        response = client.history(data={
            "symbol": symbol,
            "resolution": resolution,
            "date_format": "1",
            "range_from": chunk_start.isoformat(),
            "range_to": chunk_end.isoformat(),
            "cont_flag": "1",
        })
        if not isinstance(response, dict) or response.get("s") != "ok":
            raise BrokerError(
                f"Fyers history failed for {symbol} {chunk_start}..{chunk_end}: {response}"
            )
        for candle in response.get("candles", []):
            rows[int(candle[0])] = candle
    return [rows[key] for key in sorted(rows)]


def save_candles_csv(candles: List[list], path: str) -> int:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        for epoch, open_, high, low, close, volume in candles:
            stamp = (pd.Timestamp(int(epoch), unit="s", tz="UTC")
                     .tz_convert("Asia/Kolkata").tz_localize(None).isoformat())
            writer.writerow([int(epoch), stamp, open_, high, low, close, volume])
    return len(candles)


def download_to_csv(client: Any, symbol: str, start: date, end: date, path: str,
                    resolution: str = "1", chunk_days: int = 90) -> int:
    candles = fetch_candles(client, symbol, start, end, resolution, chunk_days)
    if not candles:
        raise BrokerError(f"Fyers returned no candles for {symbol} in that range.")
    return save_candles_csv(candles, path)


def main(argv: Optional[list] = None) -> None:
    import argparse
    from brokers.fyers_adapter import _client_from_env

    parser = argparse.ArgumentParser(description="Download Fyers candles to CSV.")
    parser.add_argument("--symbol", required=True, help="e.g. NSE:NIFTY50-INDEX")
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--out", required=True, help="CSV path")
    parser.add_argument("--resolution", default="1", help="minutes, or D for daily")
    args = parser.parse_args(argv)

    count = download_to_csv(
        _client_from_env(), args.symbol,
        date.fromisoformat(args.start), date.fromisoformat(args.end),
        args.out, args.resolution,
    )
    print(f"Saved {count} candles to {args.out}")


if __name__ == "__main__":
    main()
