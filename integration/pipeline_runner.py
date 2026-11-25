
"""
India Arbitrage Lab
STEP 20 - Integrated Pipeline Runner

Connects adapters to the MainApplicationEngine.

Research and simulation only.
No live order execution.
"""

from typing import Any, Callable

from integration.adapters import AdapterBundle, AdapterError
from integration.main_engine import MainApplicationEngine, PipelineReport


class PipelineConfigurationError(Exception):
    """Raised when required pipeline components are missing."""


class IntegratedPipelineRunner:
    """
    Connects all pipeline adapters to the central engine.

    All six callbacks are required. Missing stages fail closed,
    instead of silently passing data through.
    """

    def __init__(
        self,
        data_loader: Callable,
        scanner: Callable,
        validator: Callable,
        qualification: Callable,
        ranking: Callable,
        risk_check: Callable,
    ):
        callbacks = {
            "data_loader": data_loader,
            "scanner": scanner,
            "validator": validator,
            "qualification": qualification,
            "ranking": ranking,
            "risk_check": risk_check,
        }

        missing = [
            name for name, callback in callbacks.items()
            if callback is None or not callable(callback)
        ]

        if missing:
            raise PipelineConfigurationError(
                "Missing or invalid callbacks: "
                + ", ".join(missing)
            )

        self.adapters = AdapterBundle(
            data_loader=data_loader,
            scanner=scanner,
            validator=validator,
            qualification=qualification,
            ranking=ranking,
            risk_check=risk_check,
        )

        self.engine = MainApplicationEngine(
            load_data=self.adapters.data.load,
            scan=self.adapters.scanner.scan,
            validate=self.adapters.validation.validate,
            qualify=self.adapters.qualification.qualify,
            rank=self.adapters.ranking.rank,
            risk_check=self.adapters.risk.check,
        )

    def run(self, source: Any = None) -> PipelineReport:
        """
        Run the complete pipeline.

        When source is None, data_loader() is called.
        Otherwise data_loader(source) is called.
        """

        try:
            if source is None:
                market_data = self.adapters.data.load()
            else:
                market_data = self.adapters.data.load(source)

            return self.engine.run(market_data=market_data)

        except AdapterError as exc:
            raise PipelineConfigurationError(
                f"Pipeline adapter error: {exc}"
            ) from exc

    def describe(self):
        return {
            "pipeline": "India Arbitrage Lab",
            "mode": "Research / Paper",
            "live_trading": False,
            "stages": [
                "Data Load",
                "Scanner",
                "Validation",
                "Qualification",
                "Ranking",
                "Risk Check",
            ],
            "adapters": self.adapters.describe(),
        }
      
