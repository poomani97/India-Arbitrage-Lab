
"""
India Arbitrage Lab
System Structure and Module Import Check
"""

from importlib import import_module
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent


REQUIRED_DIRS = [
    "config",
    "models",
    "data",
    "contracts",
    "pricing",
    "strategies",
    "scanner",
    "validation",
    "ranking",
    "risk",
    "execution",
    "portfolio",
    "backtest",
    "journal",
    "analytics",
    "ai",
    "dashboard",
    "tests",
    "integration",
]


REQUIRED_MODULES = [
    "config.settings",
    "config.charges_config",
    "models.opportunity",
    "models.trade",
    "data.csv_loader",
    "data.data_validator",
    "data.market_data",
    "contracts.contract_master",
    "pricing.charges",
    "pricing.fair_value",
    "pricing.net_edge",
    "strategies.base_strategy",
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
    "scanner.detector",
    "scanner.opportunity_scanner",
    "validation.validator",
    "validation.qualification",
    "ranking.opportunity_score",
    "ranking.capital_efficiency",
    "risk.risk_gate",
    "risk.margin_manager",
    "execution.paper_broker",
    "execution.fill_simulator",
    "execution.router",
    "portfolio.portfolio_manager",
    "portfolio.pnl",
    "backtest.backtest_engine",
    "backtest.walk_forward",
    "journal.trade_journal",
    "analytics.performance",
    "analytics.failure_analysis",
    "ai.research_assistant",
    "ai.improvement_proposals",
    "dashboard.overview",
    "dashboard.scanner_page",
    "dashboard.backtest_page",
    "dashboard.portfolio_page",
    "dashboard.settings_page",
    "integration.main_engine",
    "integration.adapters",
    "integration.pipeline_runner",
]


def check_project_structure():
    missing = []

    for folder in REQUIRED_DIRS:
        if not (ROOT_DIR / folder).exists():
            missing.append(folder)

    return missing


def check_imports():
    results = []

    for module_name in REQUIRED_MODULES:
        try:
            import_module(module_name)

            results.append({
                "module": module_name,
                "status": "PASS",
                "error": None,
            })

        except Exception as exc:
            results.append({
                "module": module_name,
                "status": "FAIL",
                "error": f"{type(exc).__name__}: {exc}",
            })

    return results


def run_system_check():
    print("=" * 60)
    print("INDIA ARBITRAGE LAB - SYSTEM CHECK")
    print("=" * 60)

    missing_dirs = check_project_structure()

    print("\nDIRECTORY CHECK")

    if not missing_dirs:
        print("PASS: All required directories exist.")
    else:
        for directory in missing_dirs:
            print("MISSING:", directory)

    print("\nMODULE IMPORT CHECK")

    results = check_imports()

    passed = 0
    failed = 0

    for result in results:
        if result["status"] == "PASS":
            passed += 1
            print("[PASS]", result["module"])
        else:
            failed += 1
            print("[FAIL]", result["module"])
            print("       ", result["error"])

    print("\nSUMMARY")
    print("Modules passed:", passed)
    print("Modules failed:", failed)
    print("Missing folders:", len(missing_dirs))

    success = failed == 0 and len(missing_dirs) == 0

    print(
        "\nSYSTEM CHECK PASSED"
        if success
        else "\nSYSTEM CHECK FAILED"
    )

    return success


if __name__ == "__main__":
    if not run_system_check():
        raise SystemExit(1)
        
