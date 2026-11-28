from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from dashboard.charts_page import RULES, build_figure, resample_ohlc
from analytics.candle_patterns import detect_patterns
from tests.helpers import goto

APP = str(Path(__file__).resolve().parent.parent / "app.py")
PAGES = ["Home", "Paper Trading", "Live Trading", "Charts", "Strategies", "Live Prices",
         "Data & Replay", "Download History", "Brokers"]


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return AppTest.from_file(APP).run(timeout=60)


def click(at, label_start):
    for b in at.button:
        if b.label.startswith(label_start):
            b.click()
            return at.run(timeout=90)
    raise AssertionError(f"button {label_start!r} not found")


def test_sidebar_menu_lists_every_page(app):
    assert list(app.sidebar.radio(key="menu").options) == PAGES


@pytest.mark.parametrize("page", PAGES)
def test_every_page_opens_without_error(app, page):
    goto(app, page)
    assert not app.exception


def test_strategies_table_lists_all_ten(app):
    goto(app, "Strategies")
    assert len(app.dataframe[0].value) == 10


def test_strategy_scan_on_spot_only_data_names_missing_columns(app):
    goto(app, "Strategies")
    click(app, "Scan this strategy")
    assert any("futures_price" in w.value for w in app.warning)


def test_data_page_shows_no_strategy_ready_on_spot_only_file(app):
    goto(app, "Data & Replay")
    table = [d.value for d in app.dataframe if "Ready" in d.value.columns][0]
    assert len(table) == 10 and not table["Ready"].any()


def test_replay_runs_on_data_page(app):
    goto(app, "Data & Replay")
    click(app, "Run replay test")
    assert not app.exception


def test_live_trading_page_cannot_be_armed_while_global_flag_is_off(app, monkeypatch):
    monkeypatch.setenv("FYERS_APP_ID", "X-100")
    monkeypatch.setenv("FYERS_ACCESS_TOKEN", "t")
    pytest.importorskip("fyers_apiv3")
    goto(app, "Live Trading")
    click(app, "Connect Fyers live broker")
    app.text_input(key="lt_phrase").set_value("I UNDERSTAND LIVE ORDERS USE REAL MONEY").run(timeout=60)
    click(app, "Arm live broker")
    assert any("flag" in e.value.lower() for e in app.error)
    assert not app.session_state["live_controller"].broker.armed


def test_live_trading_without_credentials_shows_error_not_crash(app, monkeypatch):
    monkeypatch.delenv("FYERS_APP_ID", raising=False)
    monkeypatch.delenv("FYERS_ACCESS_TOKEN", raising=False)
    goto(app, "Live Trading")
    click(app, "Connect Fyers live broker")
    assert not app.exception and any("FYERS" in e.value or "Install" in e.value for e in app.error)


def test_download_history_without_credentials_shows_error(app, monkeypatch):
    monkeypatch.delenv("FYERS_APP_ID", raising=False)
    monkeypatch.delenv("FYERS_ACCESS_TOKEN", raising=False)
    goto(app, "Download History")
    click(app, "Download")
    assert not app.exception and len(app.error) == 1


class FakeFeed:
    finished = False

    def __init__(self, premium=1.03):
        self.premium = premium

    def poll(self):
        now = pd.Timestamp.now()
        expiry = (date.today() + timedelta(days=30)).isoformat()
        return {"datetime": now, "symbol": "NIFTY", "expiry_date": expiry, "spot_price": 26000.0,
                "futures_price": 26000.0 * self.premium, "futures_volume": 900000.0,
                "open": 26000.0, "high": 26000.0, "low": 26000.0, "close": 26000.0}


def test_live_prices_trade_on_paper_from_the_menu(app):
    goto(app, "Paper Trading")
    app.radio(key="mode_radio").set_value("AUTO").run(timeout=60)
    app.session_state["feed_override"] = FakeFeed()
    goto(app, "Live Prices")
    app.checkbox(key="lv_ignore").set_value(True).run(timeout=60)
    click(app, "Fetch live prices once")
    assert not app.exception
    assert app.session_state["controller"].broker.get_summary()["active_positions"] == 2


def test_resample_and_figure_build():
    frame = pd.DataFrame({"datetime": pd.date_range("2026-01-05 09:15", periods=30, freq="1min"),
                          "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 10})
    five = resample_ohlc(frame, RULES["5 minutes"])
    assert len(five) == 6 and five["volume"].iloc[0] == 50
    fig = build_figure(five, detect_patterns(five), ["doji"], 3, 0)
    assert len(fig.data) >= 1
