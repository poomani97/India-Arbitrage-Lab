
from importlib import import_module
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent

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
]


def check_project_structure():
    required_dirs = [
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

    missing = []

    for folder in required_dirs:
        path = ROOT_DIR / folder

        if not path.exists():
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
                "error": str(exc),
            })

    return results


def run_system_check():
    print("=" * 50)
    print("INDIA ARBITRAGE LAB - SYSTEM CHECK")
    print("=" * 50)

    missing_dirs = check_project_structure()

    print("\n[1] DIRECTORY CHECK")

    if not missing_dirs:
        print("PASS: All required folders found.")
    else:
        print("FAIL: Missing folders:")
        for folder in missing_dirs:
            print(" -", folder)

    print("\n[2] MODULE IMPORT CHECK")

    results = check_imports()

    passed = 0
    failed = 0

    for item in results:
        if item["status"] == "PASS":
            passed += 1
            print("[PASS]", item["module"])
        else:
            failed += 1
            print("[FAIL]", item["module"])
            print("       Error:", item["error"])

    print("\n[3] SUMMARY")
    print("Modules passed:", passed)
    print("Modules failed:", failed)
    print("Folders missing:", len(missing_dirs))

    if failed == 0 and len(missing_dirs) == 0:
        print("\nSYSTEM CHECK PASSED")
        return True

    print("\nSYSTEM CHECK FAILED")
    return False


if __name__ == "__main__":
    success = run_system_check()

    if not success:
        raise SystemExit(1)
      
