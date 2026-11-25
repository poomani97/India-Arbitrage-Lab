
from integration.system_check import check_imports


def test_all_required_modules_import():
    results = check_imports()

    failures = [
        item for item in results
        if item["status"] != "PASS"
    ]

    assert failures == [], (
        f"Module import failures: {failures}"
    )


def test_import_results_are_not_empty():
    results = check_imports()

    assert len(results) > 0


def test_import_results_have_status():
    results = check_imports()

    for item in results:
        assert "module" in item
        assert "status" in item
        assert item["status"] in ["PASS", "FAIL"]
      
