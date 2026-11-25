
"""
India Arbitrage Lab
STEP 21 - Strategy Test Runner

Tests strategies individually using injected test data.
No live orders are placed.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List

from strategies.strategy_registry import StrategyRegistry


@dataclass
class StrategyTestResult:
    strategy_name: str
    status: str
    output_count: int = 0
    duration_seconds: float = 0.0
    error: str = ""

    def to_dict(self):
        return asdict(self)


class StrategyTestRunner:
    def __init__(self, registry: StrategyRegistry):
        self.registry = registry

    @staticmethod
    def _execute(strategy: Any, test_data: Any):
        """
        Supported test interfaces:

        1. strategy.scan(test_data)
        2. strategy.generate_signals(test_data)
        3. strategy.run(test_data)
        4. callable strategy(test_data)

        This is a testing interface, not proof that every
        production strategy uses the same interface.
        """

        if hasattr(strategy, "scan") and callable(strategy.scan):
            return strategy.scan(test_data)

        if hasattr(strategy, "generate_signals") and callable(
            strategy.generate_signals
        ):
            return strategy.generate_signals(test_data)

        if hasattr(strategy, "run") and callable(strategy.run):
            return strategy.run(test_data)

        if callable(strategy):
            return strategy(test_data)

        raise TypeError(
            "Strategy has no supported test interface."
        )

    @staticmethod
    def _count_output(output: Any) -> int:
        if output is None:
            return 0

        if isinstance(output, (list, tuple, set, dict)):
            return len(output)

        return 1

    def test_one(self, name: str, test_data: Any):
        import time

        start = time.perf_counter()

        try:
            strategy = self.registry.get(name)

            if not self.registry.is_enabled(name):
                return StrategyTestResult(
                    strategy_name=name,
                    status="SKIPPED",
                    error="Strategy is disabled.",
                )

            output = self._execute(strategy, test_data)

            elapsed = time.perf_counter() - start

            return StrategyTestResult(
                strategy_name=name,
                status="PASS",
                output_count=self._count_output(output),
                duration_seconds=round(elapsed, 6),
            )

        except Exception as exc:
            elapsed = time.perf_counter() - start

            return StrategyTestResult(
                strategy_name=name,
                status="FAIL",
                duration_seconds=round(elapsed, 6),
                error=f"{type(exc).__name__}: {exc}",
            )

    def test_all(self, test_data: Any):
        results = []

        for name in self.registry.all_names():
            result = self.test_one(name, test_data)
            results.append(result)

        return results

    @staticmethod
    def report(results: List[StrategyTestResult]):
        passed = sum(
            1 for result in results
            if result.status == "PASS"
        )

        failed = sum(
            1 for result in results
            if result.status == "FAIL"
        )

        skipped = sum(
            1 for result in results
            if result.status == "SKIPPED"
        )

        return {
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "results": [
                result.to_dict()
                for result in results
            ],
        }

    @staticmethod
    def print_report(report: Dict[str, Any]):
        print("=" * 60)
        print("STRATEGY TEST REPORT")
        print("=" * 60)

        print("Total:", report["total"])
        print("Passed:", report["passed"])
        print("Failed:", report["failed"])
        print("Skipped:", report["skipped"])

        print("-" * 60)

        for item in report["results"]:
            print(
                f'{item["strategy_name"]:<12} '
                f'{item["status"]:<8} '
                f'outputs={item["output_count"]:<5} '
                f'time={item["duration_seconds"]:.4f}s'
            )

            if item["error"]:
                print("  Error:", item["error"])

        print("=" * 60)
      
