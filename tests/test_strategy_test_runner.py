
import pytest

from strategies.strategy_registry import StrategyRegistry
from strategies.strategy_test_runner import StrategyTestRunner


def build_registry():
    registry = StrategyRegistry()

    registry.register(
        "S01",
        lambda data: [{"signal": "BUY"}],
    )

    registry.register(
        "S02",
        lambda data: [],
    )

    registry.register(
        "S03",
        lambda data: 1 / 0,
    )

    registry.register(
        "S04",
        lambda data: data,
        enabled=False,
    )

    return registry


def test_runner_success():
    registry = build_registry()
    runner = StrategyTestRunner(registry)

    result = runner.test_one("S01", [1, 2, 3])

    assert result.status == "PASS"
    assert result.output_count == 1


def test_runner_empty_output():
    registry = build_registry()
    runner = StrategyTestRunner(registry)

    result = runner.test_one("S02", [])

    assert result.status == "PASS"
    assert result.output_count == 0


def test_runner_captures_strategy_error():
    registry = build_registry()
    runner = StrategyTestRunner(registry)

    result = runner.test_one("S03", [])

    assert result.status == "FAIL"
    assert "ZeroDivisionError" in result.error


def test_runner_skips_disabled_strategy():
    registry = build_registry()
    runner = StrategyTestRunner(registry)

    result = runner.test_one("S04", [])

    assert result.status == "SKIPPED"


def test_runner_all_strategies():
    registry = build_registry()
    runner = StrategyTestRunner(registry)

    results = runner.test_all([1, 2, 3])

    assert len(results) == 4


def test_report_counts():
    registry = build_registry()
    runner = StrategyTestRunner(registry)

    results = runner.test_all([])

    report = runner.report(results)

    assert report["total"] == 4
    assert report["passed"] == 2
    assert report["failed"] == 1
    assert report["skipped"] == 1


def test_strategy_method_interface():
    class ExampleStrategy:
        def generate_signals(self, data):
            return ["signal-1", "signal-2"]

    registry = StrategyRegistry()
    registry.register("S05", ExampleStrategy())

    runner = StrategyTestRunner(registry)
    result = runner.test_one("S05", [])

    assert result.status == "PASS"
    assert result.output_count == 2
  
