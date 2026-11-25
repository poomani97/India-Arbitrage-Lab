
from strategies.strategy_registry import StrategyRegistry
from strategies.strategy_batch import StrategyBatchExecutor


def test_batch_runs_enabled_strategies():
    registry = StrategyRegistry()

    registry.register("S01", lambda data: ["A", "B"])
    registry.register("S02", lambda data: ["C"])
    registry.register("S03", lambda data: ["D"], enabled=False)

    executor = StrategyBatchExecutor(registry)
    result = executor.run_all([1, 2, 3])

    assert result["strategies_tested"] == 2
    assert result["successful"] == 2
    assert result["failed"] == 0
    assert result["combined_output_count"] == 3


def test_batch_captures_errors():
    registry = StrategyRegistry()

    def broken_strategy(data):
        raise ValueError("broken")

    registry.register("S01", broken_strategy)
    registry.register("S02", lambda data: [123])

    executor = StrategyBatchExecutor(registry)
    result = executor.run_all([])

    assert result["failed"] == 1
    assert result["successful"] == 1


def test_batch_does_not_execute_strategy_twice():
    calls = {"count": 0}

    def strategy(data):
        calls["count"] += 1
        return ["signal"]

    registry = StrategyRegistry()
    registry.register("S01", strategy)

    executor = StrategyBatchExecutor(registry)
    result = executor.run_all([])

    assert calls["count"] == 1
    assert result["combined_output_count"] == 1


def test_batch_empty_registry():
    registry = StrategyRegistry()

    executor = StrategyBatchExecutor(registry)
    result = executor.run_all([])

    assert result["strategies_tested"] == 0
    assert result["successful"] == 0
    assert result["failed"] == 0
  
