
from integration.system_check import check_project_structure


def test_required_project_folders_exist():
    missing_dirs = check_project_structure()

    assert missing_dirs == [], (
        f"Missing project folders: {missing_dirs}"
    )
  
