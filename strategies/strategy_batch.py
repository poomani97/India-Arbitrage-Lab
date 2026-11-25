
"""
India Arbitrage Lab
STEP 21 - Strategy Batch Executor

Runs registered enabled strategies on the same input data
and collects their outputs independently.

Observation/testing only.
"""

from typing import Any, Dict, List

from strategies.strategy_registry import StrategyRegistry
from strategies.strategy_test_runner import StrategyTestRunner


class StrategyBatchExecutor:
    def __init__(self, registry: StrategyRegistry):
        self.registry = registry
        self.runner = StrategyTestRunner(registry)

    def run_all(self, market_data: Any) -> Dict[str, Any]:
        results = []
        combined_outputs = []
        strategy_outputs = {}

        for name in self.registry.enabled_names():
            result = self.runner.test_one(name, market_data)

            results.append(result.to_dict())

            if result.status != "PASS":
                strategy_outputs[name] = []
                continue

            try:
                strategy = self.registry.get(name)
                output = self.runner._execute(
                    strategy,
                    market_data,
                )

                if output is None:
                    output_items = []
                elif isinstance(output, list):
                    output_items = output
                elif isinstance(output, tuple):
                    output_items = list(output)
                else:
                    output_items = [output]

                strategy_outputs[name] = output_items

                for item in output_items:
                    combined_outputs.append({
                        "strategy": name,
                        "output": item,
                    })

            except Exception as exc:
                strategy_outputs[name] = []
                results[-1]["status"] = "FAIL"
                results[-1]["error"] = (
                    f"{type(exc).__name__}: {exc}"
                )

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
      
