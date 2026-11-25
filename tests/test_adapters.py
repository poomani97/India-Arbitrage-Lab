
import pytest

from integration.adapters import (
    AdapterError,
    normalize_list,
    DataAdapter,
    ScannerAdapter,
    ValidationAdapter,
    QualificationAdapter,
    RankingAdapter,
    RiskAdapter,
    AdapterBundle,
)


def test_normalize_list():
    assert normalize_list(None) == []
    assert normalize_list([1, 2]) == [1, 2]
    assert normalize_list((1, 2)) == [1, 2]
    assert normalize_list(5) == [5]


def test_data_adapter():
    adapter = DataAdapter(lambda: [10, 20, 30])
    assert adapter.load() == [10, 20, 30]


def test_data_adapter_with_source():
    adapter = DataAdapter(lambda source: {"source": source})
    assert adapter.load("test.csv") == {"source": "test.csv"}


def test_data_adapter_error():
    adapter = DataAdapter(lambda: None)

    with pytest.raises(AdapterError):
        adapter.load()


def test_scanner_adapter():
    adapter = ScannerAdapter(
        lambda data: [{"symbol": "TEST"}]
    )

    result = adapter.scan([1, 2, 3])

    assert isinstance(result, list)
    assert result[0]["symbol"] == "TEST"


def test_validation_adapter():
    adapter = ValidationAdapter(lambda items: items[:1])

    result = adapter.validate([1, 2, 3])

    assert result == [1]


def test_qualification_adapter():
    adapter = QualificationAdapter(
        lambda items: [item for item in items if item > 10]
    )

    assert adapter.qualify([5, 15, 25]) == [15, 25]


def test_ranking_adapter():
    adapter = RankingAdapter(
        lambda items: sorted(items, reverse=True)
    )

    assert adapter.rank([1, 3, 2]) == [3, 2, 1]


def test_risk_adapter():
    adapter = RiskAdapter(
        lambda items: [item for item in items if item["approved"]]
    )

    result = adapter.check([
        {"approved": True},
        {"approved": False},
    ])

    assert len(result) == 1
    assert result[0]["approved"] is True


def test_adapter_bundle():
    bundle = AdapterBundle(
        data_loader=lambda: [],
        scanner=lambda data: [],
        validator=lambda items: items,
        qualification=lambda items: items,
        ranking=lambda items: items,
        risk_check=lambda items: items,
    )

    description = bundle.describe()

    assert "data" in description
    assert "scanner" in description
    assert "risk" in description


def test_adapter_rejects_non_callable():
    with pytest.raises(AdapterError):
        ScannerAdapter(None)


def test_scanner_errors_are_wrapped():
    def broken_scanner(data):
        raise RuntimeError("scanner crash")

    adapter = ScannerAdapter(broken_scanner)

    with pytest.raises(AdapterError):
        adapter.scan([])
      
