
import ast
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "tests/full_system_test.py",
    "tests/test_dashboard_integration.py",
    "tests/test_paper_backtest_adapter.py",
    "tests/test_execution_engine.py",
    "tests/test_portfolio_manager.py",
    "paper_trading/execution_engine.py",
    "paper_trading/portfolio_manager.py",
    "paper_trading/risk_simulator.py",
    "backtesting/paper_backtest_adapter.py",
    "integration/dashboard_integration.py",
    "integration/dashboard_adapter.py",
]

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
}

REVIEW_MARKERS = [
    "TODO",
    "FIXME",
    "PLACEHOLDER",
    "NOT IMPLEMENTED",
]


class FinalProjectAudit:
    """
    Final static audit for the research/paper-trading project.

    Checks file presence, Python syntax and review markers.
    Does not execute strategies or place trades.
    """

    def __init__(self, project_root=None):
        self.root = Path(project_root or ROOT).resolve()
        self.results = []

    def record(self, category, item, status, details=""):
        self.results.append({
            "category": category,
            "item": str(item),
            "status": status,
            "details": str(details),
        })

    def check_required_files(self):
        for relative in REQUIRED_FILES:
            path = self.root / relative

            if path.is_file():
                self.record(
                    "REQUIRED_FILE",
                    relative,
                    "PASS",
                    "File exists",
                )
            else:
                self.record(
                    "REQUIRED_FILE",
                    relative,
                    "FAIL",
                    "Missing file",
                )

    def get_python_files(self):
        found = []

        for path in self.root.rglob("*.py"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            found.append(path)

        return sorted(found)

    def check_syntax(self):
        python_files = self.get_python_files()

        if not python_files:
            self.record(
                "SYNTAX",
                "Python file scan",
                "FAIL",
                "No Python files found",
            )
            return

        for path in python_files:
            relative = path.relative_to(self.root)

            try:
                source = path.read_text(encoding="utf-8")
                ast.parse(source, filename=str(relative))

                self.record(
                    "SYNTAX",
                    relative,
                    "PASS",
                    "Syntax is valid",
                )

            except Exception as exc:
                self.record(
                    "SYNTAX",
                    relative,
                    "FAIL",
                    f"{type(exc).__name__}: {exc}",
                )

    def check_review_markers(self):
        python_files = self.get_python_files()

        for path in python_files:
            relative = path.relative_to(self.root)

            try:
                lines = path.read_text(
                    encoding="utf-8"
                ).splitlines()

            except Exception as exc:
                self.record(
                    "REVIEW_MARKER",
                    relative,
                    "ERROR",
                    f"Could not read file: {exc}",
                )
                continue

            matches = []

            for line_number, line in enumerate(lines, start=1):
                upper_line = line.upper()

                for marker in REVIEW_MARKERS:
                    if marker in upper_line:
                        matches.append(
                            f"Line {line_number}: {line.strip()}"
                        )

            if matches:
                self.record(
                    "REVIEW_MARKER",
                    relative,
                    "REVIEW",
                    " | ".join(matches),
                )

    def build_report(self):
        passed = sum(
            item["status"] == "PASS"
            for item in self.results
        )

        failed = sum(
            item["status"] == "FAIL"
            for item in self.results
        )

        review = sum(
            item["status"] == "REVIEW"
            for item in self.results
        )

        errors = sum(
            item["status"] == "ERROR"
            for item in self.results
        )

        if failed > 0 or errors > 0:
            status = "FAIL"
        elif review > 0:
            status = "REVIEW_REQUIRED"
        else:
            status = "STATIC_CHECKS_PASS"

        return {
            "project": "India Arbitrage Lab",
            "audit_type": "FINAL_STATIC_AUDIT",
            "paper_only": True,
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "overall_status": status,
            "total_checks": len(self.results),
            "passed": passed,
            "failed": failed,
            "review_required": review,
            "errors": errors,
            "results": list(self.results),
        }

    def run(self):
        self.results = []

        if not self.root.exists():
            self.record(
                "PROJECT",
                self.root,
                "FAIL",
                "Project root does not exist",
            )
            return self.build_report()

        self.record(
            "PROJECT",
            self.root,
            "PASS",
            "Project directory found",
        )

        self.check_required_files()
        self.check_syntax()
        self.check_review_markers()

        return self.build_report()

    def save_report(self, filename="final_audit_report.json"):
        report = self.build_report()
        output = self.root / filename

        output.write_text(
            json.dumps(report, indent=4),
            encoding="utf-8",
        )

        return str(output)

    def print_report(self):
        report = self.build_report()

        print("=" * 60)
        print("INDIA ARBITRAGE LAB - FINAL AUDIT")
        print("=" * 60)
        print(f"Status : {report['overall_status']}")
        print(f"Checks : {report['total_checks']}")
        print(f"Passed : {report['passed']}")
        print(f"Failed : {report['failed']}")
        print(f"Review : {report['review_required']}")
        print("-" * 60)

        for result in report["results"]:
            print(
                f"[{result['status']}] "
                f"{result['category']} - "
                f"{result['item']} - "
                f"{result['details']}"
            )

        print("=" * 60)

        return report


if __name__ == "__main__":
    audit = FinalProjectAudit()

    audit.run()
    report = audit.print_report()
    saved_file = audit.save_report()

    print(f"\nAudit report saved: {saved_file}")
  
