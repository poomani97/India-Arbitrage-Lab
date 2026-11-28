# India Arbitrage Lab

Research, paper trading and (locked by default) live trading in ONE app.

    pip install -r requirements.txt
    streamlit run app.py

Everything is in the menu on the left (tap the arrow at the top left on a phone):
Home, Paper Trading, Live Trading, Charts, Strategies, Live Prices, Data & Replay,
Download History, Brokers.

Fyers: set FYERS_APP_ID and FYERS_ACCESS_TOKEN as environment variables and
`pip install -r requirements-live.txt`. Live orders also need LIVE_TRADING_ENABLED = True in
config/settings.py, an armed broker, and that strategy's Live switch. See CHANGES.md.

Tests: `python -m pytest -q`   System check: `python -m integration.system_check`
