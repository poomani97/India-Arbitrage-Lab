from datetime import date

import pytest

from brokers.base import BrokerError
from data_engine import CSVDataLoader
from data_engine.history_download import download_to_csv, fetch_candles


class FakeHistory:
    def __init__(self, fail_on_call=None):
        self.calls, self.fail_on_call = [], fail_on_call

    def history(self, data):
        self.calls.append(data)
        if self.fail_on_call == len(self.calls):
            return {"s": "error", "message": "limit"}
        base = 1767239100 + (len(self.calls) - 1) * 600
        return {"s": "ok", "candles": [[base + i * 60, 100.0 + i, 101.0 + i, 99.0 + i, 100.5 + i, 1000 + i]
                                        for i in range(3)]}


def test_range_is_split_into_chunks():
    client = FakeHistory()
    fetch_candles(client, "NSE:NIFTY50-INDEX", date(2026, 1, 1), date(2026, 6, 30), chunk_days=90)
    assert len(client.calls) == 3
    assert client.calls[0]["range_from"] == "2026-01-01"
    assert client.calls[-1]["range_to"] == "2026-06-30"


def test_csv_matches_project_format_and_loads(tmp_path):
    out = tmp_path / "nifty.csv"
    count = download_to_csv(FakeHistory(), "NSE:NIFTY50-INDEX", date(2026, 1, 1), date(2026, 1, 31), str(out))
    assert count == 3
    assert out.read_text().splitlines()[0] == "Epoch,Timestamp,Open,High,Low,Close,Volume"
    frame = CSVDataLoader().load(str(out))
    assert len(frame) == 3 and {"datetime", "open", "high", "low", "close"} <= set(frame.columns)


def test_timestamps_are_india_time(tmp_path):
    out = tmp_path / "t.csv"
    download_to_csv(FakeHistory(), "X", date(2026, 1, 1), date(2026, 1, 2), str(out))
    assert out.read_text().splitlines()[1].split(",")[1] == "2026-01-01T09:15:00"


def test_failed_chunk_raises_instead_of_writing_a_short_file(tmp_path):
    out = tmp_path / "bad.csv"
    with pytest.raises(BrokerError):
        download_to_csv(FakeHistory(fail_on_call=2), "X", date(2026, 1, 1), date(2026, 6, 30), str(out))
    assert not out.exists()


def test_bad_range_rejected():
    with pytest.raises(ValueError):
        fetch_candles(FakeHistory(), "X", date(2026, 2, 1), date(2026, 1, 1))
