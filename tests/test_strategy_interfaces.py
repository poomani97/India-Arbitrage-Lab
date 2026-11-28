
from importlib import import_module


STRATEGY_MODULES = [
    "strategies.s01_cash_futures_carry",
    "strategies.s02_futures_fair_value",
    "strategies.s03_futures_calendar_spread",
    "strategies.s04_put_call_parity",
    "strategies.s05_synthetic_vs_actual_futures",
    "strategies.s06_box_spread",
    "strategies.s07_index_etf_futures_fair_value",
    "strategies.s08_index_relative_value",
    "strategies.s09_cross_exchange_arbitrage",
    "strategies.s10_event_implied_vs_realized_move",
]


def test_strategy_modules_import():
    failures = []

    for module_name in STRATEGY_MODULES:
        try:
            import_module(module_name)
        except Exception as exc:
            failures.append(
                f"{module_name}: {type(exc).__name__}: {exc}"
            )

    assert failures == [], (
        "Strategy import failures:\n" + "\n".join(failures)
    )


def test_all_ten_strategy_modules_are_listed():
    assert len(STRATEGY_MODULES) == 10


def test_strategy_names_are_unique():
    assert len(STRATEGY_MODULES) == len(set(STRATEGY_MODULES))
  
