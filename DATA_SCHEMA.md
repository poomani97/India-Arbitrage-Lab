# Data needed by each strategy

Your Nifty files are spot OHLC only. `prepare_spot_frame()` adds `symbol` and `spot_price`.
Everything else must come from a real feed or file you supply, then `merge_derivatives()`.
All files need a `datetime` column. Optional on every strategy: `lot_size`,
`estimated_costs_per_unit` (fill with `pricing.cost_model.add_cost_column`),
`estimated_margin`, `liquidity_score` (0-100), `fill_probability` (0-1).

| Strategy | Extra columns required |
|---|---|
| S01 cash-futures carry, S02 futures fair value | futures_price, expiry_date |
| S03 calendar spread | near_futures_price, far_futures_price, near_expiry_date, far_expiry_date |
| S04 put-call parity | strike_price, call_price, put_price, expiry_date |
| S05 synthetic vs futures | strike_price, call_price, put_price, futures_price, expiry_date |
| S06 box spread | lower_strike, higher_strike, call_lower_price, call_higher_price, put_lower_price, put_higher_price, expiry_date |
| S07 index/ETF vs futures | index_price, etf_price, etf_conversion_factor, futures_price, expiry_date |
| S08 index relative value | symbol_a, symbol_b, price_a, price_b, historical_spread_mean, historical_spread_std |
| S09 NSE vs BSE | nse_price, bse_price |
| S10 event move | event_name, implied_move_percent, underlying_price_before_event, underlying_price_after_event |

Check any frame: `from data_engine.schema import check_data_coverage, format_coverage`.
