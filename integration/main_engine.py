
"""
India Arbitrage Lab
STEP 18 - Main Application Engine

Central orchestration engine for:
Data -> Scan -> Validate -> Qualify -> Rank -> Risk -> Paper candidates

This engine does NOT place live orders.
All modules are injected as callables to avoid hardcoded assumptions
about the interfaces of individual project modules.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


PipelineFunction = Callable[..., Any]


@dataclass
class StageResult:
    name: str
    status: str
    message: str = ""
    item_count: int = 0
    duration_seconds: float = 0.0


@dataclass
class PipelineReport:
    run_id: str
    started_at: str
    completed_at: Optional[str] = None

    status: str = "RUNNING"

    raw_data: Any = None
    scanned_opportunities: List[Any] = field(default_factory=list)
    validated_opportunities: List[Any] = field(default_factory=list)
    qualified_opportunities: List[Any] = field(default_factory=list)
    ranked_opportunities: List[Any] = field(default_factory=list)
    risk_approved_opportunities: List[Any] = field(default_factory=list)

    stages: List[StageResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "scanned": len(self.scanned_opportunities),
            "validated": len(self.validated_opportunities),
            "qualified": len(self.qualified_opportunities),
            "ranked": len(self.ranked_opportunities),
            "risk_approved": len(self.risk_approved_opportunities),
            "stage_count": len(self.stages),
            "error_count": len(self.errors),
            "errors": list(self.errors),
        }


class MainApplicationEngine:
    """
    Runs the arbitrage research pipeline.

    Callback contracts:

    load_data():
        Returns market data.

    scan(data):
        Returns opportunities.

    validate(opportunities):
        Returns validated opportunities.

    qualify(opportunities):
        Returns qualified opportunities.

    rank(opportunities):
        Returns ranked opportunities.

    risk_check(opportunities):
        Returns approved opportunities.

    Optional callbacks may be omitted. If omitted, the engine
    passes the previous stage's output forward unchanged.
    """

    def __init__(
        self,
        load_data: Optional[PipelineFunction] = None,
        scan: Optional[PipelineFunction] = None,
        validate: Optional[PipelineFunction] = None,
        qualify: Optional[PipelineFunction] = None,
        rank: Optional[PipelineFunction] = None,
        risk_check: Optional[PipelineFunction] = None,
    ):
        self.load_data_fn = load_data
        self.scan_fn = scan
        self.validate_fn = validate
        self.qualify_fn = qualify
        self.rank_fn = rank
        self.risk_check_fn = risk_check

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _to_list(value: Any) -> List[Any]:
        if value is None:
            return []

        if isinstance(value, list):
            return value

        if isinstance(value, tuple):
            return list(value)

        return [value]

    @staticmethod
    def _run_stage(
        report: PipelineReport,
        stage_name: str,
        function: Optional[PipelineFunction],
        input_data: Any,
    ) -> Any:
        import time

        start = time.perf_counter()

        try:
            if function is None:
                output = input_data
                message = "No callback supplied; input passed through."
            else:
                output = function(input_data)
                message = "Stage completed successfully."

            duration = time.perf_counter() - start

            result_count = (
                len(output)
                if isinstance(output, (list, tuple, dict))
                else (0 if output is None else 1)
            )

            report.stages.append(
                StageResult(
                    name=stage_name,
                    status="PASS",
                    message=message,
                    item_count=result_count,
                    duration_seconds=round(duration, 6),
                )
            )

            return output

        except Exception as exc:
            duration = time.perf_counter() - start

            report.stages.append(
                StageResult(
                    name=stage_name,
                    status="FAIL",
                    message=str(exc),
                    item_count=0,
                    duration_seconds=round(duration, 6),
                )
            )

            report.errors.append(
                f"{stage_name}: {type(exc).__name__}: {exc}"
            )

            raise

    def run(self, market_data: Any = None) -> PipelineReport:
        """
        Execute one pipeline run.

        If market_data is supplied, the data-loading callback is skipped.
        Otherwise load_data() is used when available.
        """

        run_id = datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%S%fZ"
        )

        report = PipelineReport(
            run_id=run_id,
            started_at=self._utc_now(),
        )

        try:
            # STAGE 1 - LOAD DATA
            if market_data is not None:
                data = market_data

                report.stages.append(
                    StageResult(
                        name="data_load",
                        status="PASS",
                        message="Market data supplied directly.",
                        item_count=(
                            len(data)
                            if hasattr(data, "__len__")
                            else 1
                        ),
                    )
                )

            elif self.load_data_fn is not None:
                # load_data() takes no arguments (see class docstring)
                data = self._run_stage(
                    report,
                    "data_load",
                    lambda _unused: self.load_data_fn(),
                    None,
                )

            else:
                raise ValueError(
                    "No market data supplied and no load_data "
                    "callback configured."
                )

            report.raw_data = data

            # STAGE 2 - SCAN
            scanned = self._run_stage(
                report,
                "scan",
                self.scan_fn,
                data,
            )

            report.scanned_opportunities = self._to_list(scanned)

            # STAGE 3 - VALIDATION
            validated = self._run_stage(
                report,
                "validation",
                self.validate_fn,
                report.scanned_opportunities,
            )

            report.validated_opportunities = self._to_list(
                validated
            )

            # STAGE 4 - QUALIFICATION
            qualified = self._run_stage(
                report,
                "qualification",
                self.qualify_fn,
                report.validated_opportunities,
            )

            report.qualified_opportunities = self._to_list(
                qualified
            )

            # STAGE 5 - RANKING
            ranked = self._run_stage(
                report,
                "ranking",
                self.rank_fn,
                report.qualified_opportunities,
            )

            report.ranked_opportunities = self._to_list(
                ranked
            )

            # STAGE 6 - RISK CHECK
            approved = self._run_stage(
                report,
                "risk_check",
                self.risk_check_fn,
                report.ranked_opportunities,
            )

            report.risk_approved_opportunities = self._to_list(
                approved
            )

            report.status = "SUCCESS"

        except Exception as exc:
            report.status = "FAILED"

            # Stage failures are already recorded by _run_stage. Anything
            # raised elsewhere (e.g. no data and no loader) must be recorded
            # here, otherwise the run fails with an empty error list.
            message = f"{type(exc).__name__}: {exc}"
            if not any(message in err for err in report.errors):
                report.errors.append(message)

        finally:
            report.completed_at = self._utc_now()

        return report

    @staticmethod
    def print_report(report: PipelineReport) -> None:
        print("=" * 60)
        print("INDIA ARBITRAGE LAB - PIPELINE REPORT")
        print("=" * 60)

        print("Run ID:", report.run_id)
        print("Status:", report.status)
        print("Started:", report.started_at)
        print("Completed:", report.completed_at)

        print("\nOPPORTUNITY SUMMARY")
        print("-" * 40)

        print(
            "Scanned:",
            len(report.scanned_opportunities),
        )
        print(
            "Validated:",
            len(report.validated_opportunities),
        )
        print(
            "Qualified:",
            len(report.qualified_opportunities),
        )
        print(
            "Ranked:",
            len(report.ranked_opportunities),
        )
        print(
            "Risk approved:",
            len(report.risk_approved_opportunities),
        )

        print("\nSTAGE DETAILS")
        print("-" * 40)

        for stage in report.stages:
            print(
                f"{stage.name:<16} "
                f"{stage.status:<8} "
                f"items={stage.item_count:<5} "
                f"time={stage.duration_seconds:.4f}s"
            )

            if stage.message:
                print("  ", stage.message)

        if report.errors:
            print("\nERRORS")
            print("-" * 40)

            for error in report.errors:
                print("-", error)

        print("=" * 60)
      
