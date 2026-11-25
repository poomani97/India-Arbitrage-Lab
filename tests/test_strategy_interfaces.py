
from importlib import import_module


STRATEGY_MODULES = [
    "strategies.s01",
    "strategies.s02",
    "strategies.s03",
    "strategies.s04",
    "strategies.s05",
    "strategies.s06",
    "strategies.s07",
    "strategies.s08",
    "strategies.s09",
    "strategies.s10",
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
  
