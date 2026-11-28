# Review fixes (Nov 27, 2026)

Before: 17 of 140 tests failed. After: 145 pass (5 regression tests added).

## Fixed
- data/historical_catalog.py: `register()` was missing `self` (8 tests).
- integration/main_engine.py: `load_data()` was called with an argument although it takes none;
  failures outside a stage (no data, no loader) left `errors` empty.
- strategies/strategy_batch.py: ran each strategy twice. Replaced with the single-run version;
  removed the duplicate root-level strategy_batch.py.
- integration/system_check.py, tests/test_strategy_interfaces.py: expected module names that do not
  exist (data.csv_loader -> data_engine.csv_loader, strategies.s01 -> strategies.s01_cash_futures_carry,
  dashboard.* not built yet).
- validation/qualification.py, ranking/opportunity_score.py, risk/risk_gate.py: read `confidence`,
  `liquidity`, `capital`, `margin`, `score` while the Opportunity model uses `confidence_score`,
  `liquidity_score`, `capital_required`, `estimated_margin`, `opportunity_score`. New
  models/field_access.py reads either name. Real Opportunity objects could never pass the risk gate.
- RiskGate.filter_approved now sets `risk_approved=True` (ExecutionRouter requires it).
- models/opportunity.py: confidence_score bound 0-100 -> 0-1 (all consumers use 0-1).
- .github/workflows/project-audit.yml: CI never ran pytest; added.

## Open (needs a decision)
1. Shipped Nifty data is spot-only OHLC; S01-S10 need futures/options/ETF/BSE/event columns.
2. Costs default to 0 in every strategy; ChargesCalculator/NetEdgeCalculator are not connected;
   all charge rates are 0 and unverified.
3. ExecutionRouter needs `leg["symbol"]`; strategies emit `leg["instrument"]` -> INVALID_LEGS.
4. liquidity_score is 0-100 in the model but the scorer divides by a rupee target (100000).
5. estimated_margin is never computed (0 -> risk gate rejects, correctly); default_lot_size = 1.
6. app.py is a static page, not wired to the engine; dashboard/ package does not exist.
7. Duplicate packages: execution/ vs paper_trading/, backtest/ vs backtesting/, portfolio/ vs paper_trading/portfolio_manager.
8. No tests for strategies, scanner, ranking, risk (this is why the above was not caught).

Run: `pip install -r requirements.txt`, `streamlit run app.py`, `python -m pytest -q`, `python -m integration.system_check`
(use `-m`; running the script by path breaks imports).

## Step 1 - costs (added)
- pricing/cost_model.py: CostModel + add_cost_column(df, lot_size) fills estimated_costs_per_unit.
  Use it before scanning. Rates: STT/stamp/SEBI/GST per Apr 2026 figures; exchange fee and flat
  broker fee are placeholders to CONFIRM (profiles remain verified=False).
- tests/test_cost_model.py (3 tests). Total now 148 passing.

## Step 2 - refillable paper account (added)
- execution/paper_broker.py: deposit(amount), withdraw(amount), reset(new_cash=None),
  get_pnl(mark_prices), funds_history. P&L is measured against all money put in,
  so top-ups never look like profit.
- tests/test_paper_funds.py (6 tests). Total now 154 passing.

## Step 3 - trading modes (added)
- execution/trading_controller.py: TradingController with MANUAL / SEMI_AUTO / AUTO.
  manual_order() always works; submit_opportunity() is ignored in MANUAL, queued for
  approve()/reject() in SEMI_AUTO, executed at once in AUTO. Every automated trade
  passes OpportunityScorer + RiskGate. halt()/resume() = emergency stop.
  If any leg fails, earlier legs are unwound (no one-legged positions).
- execution/paper_broker.py: optional allow_short=True (no margin simulated).
- tests/test_trading_controller.py (11 tests). Total now 165 passing.
- Not yet: dashboard buttons (app.py), real-broker adapters, live switch.

## Step 4 - dashboard + broker interface (added)
- dashboard/trading_page.py (shown at the bottom of app.py): mode switch, STOP/Resume,
  add money/withdraw/reset, manual buy/sell form, approve/reject queue, positions, log.
  "Send TEST opportunity" uses clearly labelled demo data.
- brokers/: BrokerAdapter interface, PaperBrokerAdapter, registry (register_broker /
  create_broker), GuardedBroker (live needs settings flag + confirm phrase + order-value
  and daily-count limits; Stop button disarms), not-connected stubs for Dhan, Fyers,
  Angel One, Groww, Forex (they raise NotImplementedError, nothing is sent).
- TradingController works with any BrokerAdapter.
- tests: test_trading_page.py (2), test_brokers.py (7). Total 174 passing.
- Still to do: real API code per broker (needs your keys + tiny-quantity test),
  live price feed, margin model, forex cost model, data schema for strategies.

## Step 5 - data schema (added)
- data_engine/schema.py: prepare_spot_frame(), merge_derivatives() (nearest earlier quote,
  stale quotes stay NaN), check_data_coverage()/format_coverage() per strategy.
- DATA_SCHEMA.md: columns each of S01-S10 needs.
- tests/test_data_schema.py (5 tests). Total 179 passing.
- The shipped Nifty files are spot-only, so no strategy is ready on them alone.
  You need a futures/options (etc.) file or feed; nothing is invented.

## Step 6 - live data feed interface (added)
- feeds/: DataFeed interface, ReplayFeed (plays any prepared DataFrame back one row per step,
  like live), registry (register_feed/create_feed), not-connected stubs for Dhan, Fyers,
  Angel One (raise NotImplementedError; nothing is fetched).
- feeds/runner.py FeedRunner: each step() pulls one snapshot, skips stale rows, runs only
  strategies whose columns are complete, sends opportunities to TradingController
  (mode, risk gate and halt all apply). Missing columns are reported, never invented.
- tests/test_feeds.py (8 tests). Total 187 passing.
- Finding: real S01-S10 set confidence_score = 0, so the risk gate rejects them in AUTO and
  SEMI_AUTO. They need confidence / fill-probability / liquidity / margin models first.
- Cost model covers futures/options strategies only (not S08-S10).
- Not wired into the dashboard yet. Real broker websocket code still to write.

## Step 7 - estimators for margin / confidence / fill / liquidity (added)
- risk/estimators.py: MarginModel (flat % of leg value, NOT SPAN; fallback to capital_required),
  estimate_confidence, estimate_fill_probability, estimate_liquidity, OpportunityEnricher.
  Only fills fields still at 0; never overwrites supplied values; notes in
  opportunity.metadata["estimates"]. Liquidity stays 0 unless the row has a volume column.
- FeedRunner enriches every opportunity before it reaches the controller (enricher=None to disable).
- tests/test_estimators.py (8). Total 195 passing.
- These are uncalibrated heuristics. Replace margin with the broker margin API; calibrate
  confidence/fill on paper results.
- Finding: with default RiskGate limits (1 lakh) a full Nifty lot (about 19.5 lakh cash leg) is
  always rejected. Set max_capital_per_trade / max_margin_per_trade to match your real capital,
  and verify the current Nifty lot size.
- Finding: only S01, S02, S03 emit executable legs (side + price + quantity). S05-S09 use
  `action` and no price/quantity; S06 is research_only and S09 has execution_enabled flags.
  Leg format must be standardized before those strategies can trade.

## Step 8 - standard legs (added)
- models/legs.py: normalize_leg() reads side/action and price/market_price into one shape and builds a
  unique contract_key (strike, expiry, exchange). Before this, the two calls of a box spread both
  mapped to "NIFTY:CALL" and cancelled each other in positions.
- executable_problems(): paper-blocking reasons (no side, observation-only legs, execution_enabled=False,
  unverified hedge, single-leg unless allow_single_leg=True).
- live_problems(): research_only / live_trading_allowed=False block LIVE brokers only; paper may trade them.
- TradingController refuses non-executable opportunities up front (nothing is queued for approval).
- Enricher fills capital_required from gross leg notional when a strategy left it 0.
- tests/test_leg_standard.py (11). Total 206 passing.
- Strategy flags are respected, not overridden: S05 (RESEARCH_ONLY, no sides) and S09 (observation, no
  execution) stay non-tradable; S07 is one-legged (unhedged).

## Step 9 - per-strategy Paper/Live switches + dashboard panel (added)
- execution/strategy_controls.py: Paper (default ON) and Live (default OFF) per strategy, saved to
  state/strategy_controls.json (git-ignored). Live ON needs an explicit acknowledgement and at least
  `min_paper_trades` (default 10, can be 0) executed paper trades for that strategy. Switching OFF always works.
- Switching a strategy Live is the only thing that lifts its research_only / live_trading_allowed=False
  flag for a live broker. Missing side, unverified hedge, single-leg and risk-gate checks still apply, and
  the global LIVE_TRADING_ENABLED flag + GuardedBroker arming + order limits are still required.
- TradingController(controls=...) returns STRATEGY_OFF when the switch for the connected broker type is off.
- dashboard: strategy switch panel (tap Paper/Live per strategy) and a "Run demo feed" button. The demo uses
  made-up prices with a deliberately large 3% futures premium so a trade fires; at a realistic 1% premium and
  1 unit, S01 is rejected (score 47.9 < 60) because flat per-order fees dominate. Rejection reasons are shown.
- tests: test_strategy_controls.py (12), test_dashboard_controls.py (6). Total 223 passing.
- Still not done: real broker API adapters (Live switches do nothing until one exists), live feed code,
  S02/S07 are single-leg (blocked unless allow_single_leg=True), your futures/options data.
- Real-size note: one Nifty lot at a 1% premium scores 62.8 (passes), but its ~19.5 lakh cash leg exceeds the
  default RiskGate limit (1 lakh) and the default paper cash; set limits and deposit to match your capital.

## Step 10 - Fyers connection (added)
- brokers/fyers_adapter.py: real Fyers v3 adapter (place/cancel order, positions, funds). Credentials only from
  env vars FYERS_APP_ID and FYERS_ACCESS_TOKEN (token expires daily). create_broker("FYERS") returns it wrapped in
  GuardedBroker. Fail closed: an order goes out only if its contract_key is in symbol_map
  (e.g. "NIFTY:FUTURES:2026-12-29" -> "NSE:NIFTY26DECFUT"). product_type default INTRADAY; choose MARGIN/CNC deliberately.
- feeds/fyers_feed.py: polls Fyers quotes into one row (columns -> symbols map). Any missing price = no row.
- Controller: when a broker accepts an order but does not confirm the fill (real brokers), it now halts all
  automation, disarms the live broker and reports UNCONFIRMED_FILL instead of assuming a fill.
- requirements-live.txt: fyers-apiv3 (install only when connecting).
- tests/test_fyers.py (11, fake client). Total 233 passing, 1 skipped (needs the SDK).
- NOT tested against the real Fyers API. First real test: tiny quantity, product type chosen by you.
- Still open: websocket streaming, order-status polling to confirm fills, Dhan/Angel One/Groww/Delta/MT5 adapters.

## Step 11 - live prices with paper orders, and history download (added)
- feeds/live.py: run_live_step() = one live snapshot -> strategies -> controller. Skips outside
  09:15-15:30 IST Mon-Fri (exchange holidays are NOT checked; use ignore_hours=True to override).
- run_paper_live.py + config/live_feed.example.json: loop that reads live Fyers prices and trades on the PAPER
  broker only (MANUAL = watch, AUTO = paper orders). Edit symbols/expiry in the config first.
  Run: python run_paper_live.py --config config/live_feed.example.json --mode AUTO
- feeds/fyers_feed.py: optional volume columns; live rows now carry open/high/low/close = last spot price
  (placeholder, not a candle). Bug found by test: without them S01/S03/S04... silently skipped every live row.
- data_engine/history_download.py: Fyers history -> CSV in the same format as the shipped Nifty files
  (chunked, de-duplicated, India-time stamps, errors raise instead of writing a short file).
  Run: python -m data_engine.history_download --symbol NSE:NIFTY50-INDEX --start 2026-01-01 --end 2026-11-27 --out data/historical/nifty/NIFTY50_1min_new.csv
- tests: test_live_paper.py (6), test_history_download.py (5). Total 244 passing, 1 skipped.
- NOT tested against real Fyers. Expired futures/options often have little history; futures and option
  history for backtests may need another source.

## Step 12 - one app with a sidebar menu, charts (added)
- app.py is now the single entry point: `streamlit run app.py`, sidebar menu with Home, Paper Trading,
  Live Trading, Charts, Strategies, Live Prices, Data & Replay, Download History, Brokers.
- Live Trading page (separate, real-money area): connect Fyers (sends nothing), arm with the confirm phrase,
  per-strategy Live switches, live mode (manual/semi-auto/auto), STOP, live manual order, approval queue.
  The global flag LIVE_TRADING_ENABLED stays a code setting on purpose (not a button).
- Live Prices page can target the paper account (default) or the live controller.
- Strategies page: S01-S10 table, per-strategy paper/live state, scan any strategy on a data file.
- Data & Replay: coverage per strategy and a replay test on its own practice account (counts outcomes, no profit).
- Charts: candlesticks from your own data (resample, SMA/EMA, pattern markers) via Plotly, plus a view-only
  TradingView widget tab (internet needed, no orders, NSE data usually delayed).
- analytics/candle_patterns.py: doji, hammer, shooting star, bullish/bearish engulfing, morning/evening star.
  Shapes only, not signals, not tested for profitability.
- Existing dashboard tests updated for the menu. Total 270 passing, 2 skipped (need the Fyers SDK).
- Not done: SMC / risk-first / trend-first folders (not provided); Dhan, Angel One, Groww, Delta, MT5 adapters;
  live-candle chart from Fyers; the live controller has not been tried against a real account.
