
"""
India Arbitrage Lab
STEP 21 - Strategy Batch Executor

Executes each enabled strategy once and collects outputs.
Testing and observation only.
"""

import time
from typing import Any, Dict

from strategies.strategy_test_runner import (
    StrategyTestRunner,
    StrategyTestResult,
)


class StrategyBatchExecutor:
    def __init__(self, registry):
        self.registry = registry
        self.runner = StrategyTestRunner(registry)

    def run_all(self, market_data: Any) -> Dict[str, Any]:
        results = []
        combined_outputs = []
        strategy_outputs = {}

        for name in self.registry.enabled_names():
            start = time.perf_counter()

            try:
                strategy = self.registry.get(name)

                # Execute only once per strategy
                output = self.runner._execute(
                    strategy, market_data
                )

                if output is None:
                    items = []
                elif isinstance(output, list):
                    items = output
                elif isinstance(output, tuple):
                    items = list(output)
                else:
                    items = [output]

                elapsed = time.perf_counter() - start

                result = StrategyTestResult(
                    strategy_name=name,
                    status="PASS",
                    output_count=len(items),
                    duration_seconds=round(elapsed, 6),
                )

                strategy_outputs[name] = items

                for item in items:
                    combined_outputs.append({
                        "strategy": name,
                        "output": item,
                    })

            except Exception as exc:
                elapsed = time.perf_counter() - start

                result = StrategyTestResult(
                    strategy_name=name,
                    status="FAIL",
                    duration_seconds=round(elapsed, 6),
                    error=f"{type(exc).__name__}: {exc}",
                )

                strategy_outputs[name] = []

            results.append(result.to_dict())

        return {
            "strategies_tested": len(results),
            "successful": sum(
                1 for item in results
                if item["status"] == "PASS"
            ),
            "failed": sum(
                1 for item in results
                if item["status"] == "FAIL"
            ),
            "combined_output_count": len(combined_outputs),
            "strategy_results": results,
            "strategy_outputs": strategy_outputs,
            "combined_outputs": combined_outputs,
        }
      
