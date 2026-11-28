from pathlib import Path

from streamlit.testing.v1 import AppTest

from tests.helpers import goto

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def test_app_loads_without_error():
    at = goto(AppTest.from_file(APP).run(timeout=30), "Paper Trading")
    assert not at.exception


def test_manual_order_button_and_demo_flow():
    at = goto(AppTest.from_file(APP).run(timeout=30), "Paper Trading")
    at.button[[b.label for b in at.button].index("Send TEST opportunity (demo data)")].click().run()
    assert not at.exception          # manual mode: ignored, no crash
    at.radio(key="mode_radio").set_value("AUTO").run(timeout=30)
    at.button[[b.label for b in at.button].index("Send TEST opportunity (demo data)")].click().run()
    assert not at.exception
    assert at.session_state.controller.broker.get_summary()["active_positions"] == 2
