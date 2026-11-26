
import ast
import importlib
import json
import sys
from pathlib import Path
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
    
EXPECTED_MODULES = [
    "data.historical_quality",
    "data.historical_catalog",
    "strategies.strategy_registry",
    "strategies.strategy_test_runner",
    "strategies.strategy_batch",
    "integration.dashboard_adapter",
    "integration.dashboard_integration",
    "paper_trading.risk_simulator",
    "paper_trading.portfolio_manager",
    "paper_trading.execution_engine",
    "backtesting.backtest_validator",
    "backtesting.paper_backtest_adapter",
]

EXPECTED_FILES = [
    "data/historical_quality.py",
    "data/historical_catalog.py",
    "strategies/strategy_registry.py",
    "strategies/strategy_test_runner.py",
    "strategies/strategy_batch.py",
    "integration/dashboard_adapter.py",
    "integration/dashboard_integration.py",
    "paper_trading/risk_simulator.py",
    "paper_trading/portfolio_manager.py",
    "paper_trading/execution_engine.py",
    "backtesting/backtest_validator.py",
    "backtesting/paper_backtest_adapter.py",
]


class FullSystemTester:
    """
    Research system smoke-test runner.

    Checks:
    1. Expected project files
    2. Python syntax
    3. Core module imports
    4. Basic report generation

    Does not place real trades or connect to a broker.
    """

    def __init__(self, project_root=None):
        self.root = Path(project_root or ROOT).resolve()
        self.results = []
        self.started_at = None
        self.finished_at = None

    def _record(self, name, status, details=""):
        self.results.append({
            "test": name,
            "status": status,
            "details": str(details),
        })

    def check_expected_files(self):
        for relative_path in EXPECTED_FILES:
            path = self.root / relative_path

            if path.is_file():
                self._record(
                    f"FILE: {relative_path}",
                    "PASS",
                    "File exists",
                )
            else:
                self._record(
                    f"FILE: {relative_path}",
                    "FAIL",
                    "Expected file is missing",
                )

    def check_python_syntax(self):
        python_files = list(self.root.rglob("*.py"))

        if not python_files:
            self._record(
                "Python syntax scan",
                "FAIL",
                "No Python files found",
            )
            return

        for path in python_files:
            # Skip virtual environments and cache folders.
            if any(
                part in {
                    ".git",
                    "__pycache__",
                }
                for part in path.parts
            ):
                continue

            try:
                source = path.read_text(encoding="utf-8")
                ast.parse(source, filename=str(path))

                self._record(
                    f"SYNTAX: {path.relative_to(self.root)}",
                    "PASS",
                    "Syntax parsed successfully",
                )

            except Exception as exc:
                self._record(
                    f"SYNTAX: {path.relative_to(self.root)}",
                    "FAIL",
                    exc,
                )

    def check_imports(self):
        for module_name in EXPECTED_MODULES:
            try:
                importlib.import_module(module_name)

                self._record(
                    f"IMPORT: {module_name}",
                    "PASS",
                    "Module imported successfully",
                )

            except Exception as exc:
                self._record(
                    f"IMPORT: {module_name}",
                    "FAIL",
                    f"{type(exc).__name__}: {exc}",
                )

    def run(self):
        self.results = []
        self.started_at = datetime.now(timezone.utc).isoformat()

        self._record(
            "PROJECT ROOT",
            "INFO",
            self.root,
        )

        if not self.root.exists():
            self._record(
                "PROJECT ROOT CHECK",
                "FAIL",
                "Project root does not exist",
            )

            self.finished_at = datetime.now(timezone.utc).isoformat()
            return self.get_report()

        self.check_expected_files()
        self.check_python_syntax()
        self.check_imports()

        self.finished_at = datetime.now(timezone.utc).isoformat()
        return self.get_report()

    def get_report(self):
        passed = sum(
            item["status"] == "PASS"
            for item in self.results
        )

        failed = sum(
            item["status"] == "FAIL"
            for item in self.results
        )

        info = sum(
            item["status"] == "INFO"
            for item in self.results
        )

        if failed == 0:
            overall_status = "PASS"
        else:
            overall_status = "FAIL"

        return {
            "project": "India Arbitrage Lab",
            "test_type": "FULL_SYSTEM_SMOKE_TEST",
            "paper_only": True,
            "overall_status": overall_status,
            "total_checks": len(self.results),
            "passed": passed,
            "failed": failed,
            "info": info,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "results": list(self.results),
        }

    def print_report(self):
        report = self.get_report()

        print("\n" + "=" * 60)
        print("       INDIA ARBITRAGE LAB - SYSTEM TEST")
        print("=" * 60)

        print(f"Overall Status : {report['overall_status']}")
        print(f"Total Checks  : {report['total_checks']}")
        print(f"Passed        : {report['passed']}")
        print(f"Failed        : {report['failed']}")
        print("-" * 60)

        for item in report["results"]:
            print(
                f"[{item['status']}] "
                f"{item['test']} - {item['details']}"
            )

        print("=" * 60)

        return report

    def save_report(self, filename="system_test_report.json"):
        report = self.get_report()
        output_path = self.root / filename

        output_path.write_text(
            json.dumps(report, indent=4),
            encoding="utf-8",
        )

        return str(output_path)


if __name__ == "__main__":
    tester = FullSystemTester()

    tester.run()
    report = tester.print_report()

    report_path = tester.save_report()

    print(f"\nReport saved: {report_path}")

    if report["failed"] > 0:
        sys.exit(1)

    sys.exit(0)
  
