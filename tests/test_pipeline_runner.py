
import pytest

from integration.pipeline_runner import (
    IntegratedPipelineRunner,
    PipelineConfigurationError,
)


def create_test_runner():
    return IntegratedPipelineRunner(
        data_loader=lambda: [
            {"symbol": "TEST", "price": 100},
            {"symbol": "TEST2", "price": 200},
        ],
        scanner=lambda data: [
            {"symbol": row["symbol"], "price": row["price"]}
            for row in data
        ],
        validator=lambda items: items,
        qualification=lambda items: items,
        ranking=lambda items: sorted(
            items, key=lambda item: item["price"], reverse=True
        ),
        risk_check=lambda items: [
            item for item in items if item["price"] <= 200
        ],
    )


def test_runner_initializes():
    runner = create_test_runner()

    assert runner is not None
    assert runner.engine is not None


def test_runner_completes_pipeline():
    runner = create_test_runner()

    report = runner.run()

    assert report.status == "SUCCESS"
    assert len(report.scanned_opportunities) == 2
    assert len(report.validated_opportunities) == 2
    assert len(report.qualified_opportunities) == 2
    assert len(report.ranked_opportunities) == 2
    assert len(report.risk_approved_opportunities) == 2


def test_runner_ranking_order():
    runner = create_test_runner()

    report = runner.run()

    ranked = report.ranked_opportunities

    assert ranked[0]["price"] >= ranked[-1]["price"]


def test_runner_accepts_data_source():
    runner = IntegratedPipelineRunner(
        data_loader=lambda source: source,
        scanner=lambda data: data,
        validator=lambda items: items,
        qualification=lambda items: items,
        ranking=lambda items: items,
        risk_check=lambda items: items,
    )

    report = runner.run(
        source=[{"symbol": "ABC", "price": 50}]
    )

    assert report.status == "SUCCESS"
    assert report.scanned_opportunities[0]["symbol"] == "ABC"


def test_missing_callback_is_rejected():
    with pytest.raises(PipelineConfigurationError):
        IntegratedPipelineRunner(
            data_loader=lambda: [],
            scanner=None,
            validator=lambda items: items,
            qualification=lambda items: items,
            ranking=lambda items: items,
            risk_check=lambda items: items,
        )


def test_runner_description():
    runner = create_test_runner()

    info = runner.describe()

    assert info["live_trading"] is False
    assert info["mode"] == "Research / Paper"
    assert len(info["stages"]) == 6


def test_risk_callback_filters_opportunities():
    runner = IntegratedPipelineRunner(
        data_loader=lambda: [10, 20, 30],
        scanner=lambda data: data,
        validator=lambda items: items,
        qualification=lambda items: items,
        ranking=lambda items: items,
        risk_check=lambda items: [
            item for item in items if item <= 20
        ],
    )

    report = runner.run()

    assert report.status == "SUCCESS"
    assert report.risk_approved_opportunities == [10, 20]
  
