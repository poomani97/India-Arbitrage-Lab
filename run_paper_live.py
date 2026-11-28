"""
Live Fyers prices, PAPER orders only. Run from the project folder:

    set FYERS_APP_ID and FYERS_ACCESS_TOKEN first (environment variables)
    python run_paper_live.py --config config/live_feed.example.json --mode AUTO

Ctrl+C stops it and prints the paper account summary.
Nothing here can send a real order: the broker is the paper broker.
"""

import argparse
import json
import time

from brokers.paper_adapter import PaperBrokerAdapter
from execution.paper_broker import PaperBroker
from execution.strategy_controls import StrategyControls
from execution.trading_controller import TradingController
from feeds.fyers_feed import FyersFeed
from feeds.live import run_live_step
from risk.risk_gate import RiskGate


def build(config: dict, mode: str):
    feed = FyersFeed(
        config["columns"],
        constants=config.get("constants"),
        volume_columns=config.get("volume_columns"),
    )
    broker = PaperBrokerAdapter(PaperBroker(float(config.get("paper_cash", 10_000_000)), allow_short=True))
    gate = RiskGate(
        max_capital_per_trade=float(config.get("max_capital_per_trade", 5_000_000)),
        max_margin_per_trade=float(config.get("max_margin_per_trade", 5_000_000)),
    )
    controller = TradingController(broker, risk_gate=gate, mode=mode,
                                   controls=StrategyControls("state/strategy_controls.json"))
    return feed, controller


def main() -> None:
    parser = argparse.ArgumentParser(description="Live Fyers prices, paper orders.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--mode", choices=["MANUAL", "AUTO"], default="MANUAL",
                        help="MANUAL only watches; AUTO places paper orders.")
    parser.add_argument("--interval", type=float, default=5.0, help="seconds between polls")
    parser.add_argument("--ignore-hours", action="store_true")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as handle:
        config = json.load(handle)

    feed, controller = build(config, args.mode)
    lot_size = int(config.get("lot_size", 1))
    print(f"Paper trading on live Fyers prices. Mode={args.mode}. Ctrl+C to stop.")

    try:
        while True:
            result = run_live_step(controller, feed, lot_size, ignore_hours=args.ignore_hours)
            status = result["status"]
            if status == "OK":
                outcomes = ", ".join(f"{r['strategy']}:{r['status']}" for r in result["results"]) or "none"
                print(f"{result['datetime']} ready={result['ready']} opportunities={result['opportunities']} -> {outcomes}")
            else:
                print(f"{status}: {result.get('reason', '')}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped. Paper account:", controller.broker.broker.get_summary())


if __name__ == "__main__":
    main()
