import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from tests.helpers import goto

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def fresh(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)   # state/strategy_controls.json lands in the temp dir
    return goto(AppTest.from_file(APP).run(timeout=30), "Paper Trading")


def click(at, label_start):
    for b in at.button:
        if b.label.startswith(label_start):
            b.click()
            return at.run(timeout=30)
    raise AssertionError(f"button {label_start!r} not found")


def test_panel_lists_all_ten_strategies_paper_on_live_off(tmp_path, monkeypatch):
    at = fresh(tmp_path, monkeypatch)
    assert not at.exception
    labels = [b.label for b in at.button]
    assert sum(l.startswith("Paper: ON") for l in labels) == 10
    assert sum(l.startswith("Live: OFF") for l in labels) == 10


def test_live_on_without_acknowledgement_is_refused(tmp_path, monkeypatch):
    at = fresh(tmp_path, monkeypatch)
    at = click(at, "Live: OFF")
    assert not at.exception
    assert any("Confirm" in e.value for e in at.error)
    assert sum(b.label.startswith("Live: ON") for b in at.button) == 0


def test_paper_switch_toggles_and_is_saved(tmp_path, monkeypatch):
    at = fresh(tmp_path, monkeypatch)
    at = click(at, "Paper: ON")
    assert sum(b.label.startswith("Paper: OFF") for b in at.button) == 1
    saved = json.loads((tmp_path / "state" / "strategy_controls.json").read_text())
    assert any(v["paper"] is False for v in saved["strategies"].values())


def test_demo_feed_in_manual_mode_trades_nothing(tmp_path, monkeypatch):
    at = fresh(tmp_path, monkeypatch)
    at = click(at, "Run demo feed")
    assert not at.exception
    assert at.session_state.controller.broker.get_summary()["active_positions"] == 0


def test_demo_feed_in_auto_mode_trades_on_paper(tmp_path, monkeypatch):
    at = fresh(tmp_path, monkeypatch)
    at.radio(key="mode_radio").set_value("AUTO").run(timeout=30)
    at = click(at, "Run demo feed")
    assert not at.exception
    controller = at.session_state.controller
    assert controller.broker.get_summary()["active_positions"] == 2   # S01 cash + futures legs
    assert controller.controls.paper_trades("S01") == 3               # default slider = 3 steps


def test_demo_feed_in_semi_auto_queues_for_approval(tmp_path, monkeypatch):
    at = fresh(tmp_path, monkeypatch)
    at.radio(key="mode_radio").set_value("SEMI_AUTO").run(timeout=30)
    at = click(at, "Run demo feed")
    controller = at.session_state.controller
    assert len(controller.list_pending()) >= 1
    assert controller.broker.get_summary()["active_positions"] == 0
