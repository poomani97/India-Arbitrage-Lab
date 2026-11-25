
from integration.system_check import (
    check_project_structure,
    check_imports,
)


def test_structure_check_returns_list():
    result = check_project_structure()

    assert isinstance(result, list)


def test_import_check_returns_list():
    result = check_imports()

    assert isinstance(result, list)


def test_import_check_has_module_names():
    result = check_imports()

    for item in result:
        assert isinstance(item["module"], str)
        assert len(item["module"]) > 0


def test_system_check_status_format():
    result = check_imports()

    for item in result:
        assert item["status"] in ("PASS", "FAIL")
      
