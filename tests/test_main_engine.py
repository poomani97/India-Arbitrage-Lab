
from integration.main_engine import MainApplicationEngine


def test_pipeline_runs_successfully():
    engine = MainApplicationEngine(
        load_data=lambda: [100, 101, 102],
        scan=lambda data: [{"symbol": "TEST", "price": data[-1]}],
        validate=lambda items: items,
        qualify=lambda items: items,
        rank=lambda items: items,
        risk_check=lambda items: items,
    )

    report = engine.run()

    assert report.status == "SUCCESS"
    assert len(report.scanned_opportunities) == 1
    assert len(report.risk_approved_opportunities) == 1


def test_pipeline_passes_data_between_stages():
    engine = MainApplicationEngine(
        load_data=lambda: [10, 20, 30],
        scan=lambda data: [{"value": sum(data)}],
        validate=lambda items: items,
        qualify=lambda items: items,
        rank=lambda items: items,
        risk_check=lambda items: items,
    )

    report = engine.run()

    assert report.status == "SUCCESS"
    assert report.scanned_opportunities[0]["value"] == 60


def test_pipeline_accepts_direct_market_data():
    engine = MainApplicationEngine(
        scan=lambda data: [{"data_count": len(data)}],
    )

    report = engine.run(market_data=[1, 2, 3, 4])

    assert report.status == "SUCCESS"
    assert report.scanned_opportunities[0]["data_count"] == 4


def test_pipeline_records_stage_results():
    engine = MainApplicationEngine(
        load_data=lambda: [1, 2, 3],
        scan=lambda data: data,
        validate=lambda items: items,
        qualify=lambda items: items,
        rank=lambda items: items,
        risk_check=lambda items: items,
    )

    report = engine.run()

    assert len(report.stages) == 6

    for stage in report.stages:
        assert stage.status == "PASS"


def test_pipeline_handles_errors():
    def broken_scan(data):
        raise RuntimeError("Test scanner failure")

    engine = MainApplicationEngine(
        load_data=lambda: [1, 2, 3],
        scan=broken_scan,
    )

    report = engine.run()

    assert report.status == "FAILED"
    assert len(report.errors) > 0


def test_pipeline_report_summary():
    engine = MainApplicationEngine(
        load_data=lambda: [1, 2],
        scan=lambda data: [{"symbol": "TEST"}],
        validate=lambda items: items,
        qualify=lambda items: items,
        rank=lambda items: items,
        risk_check=lambda items: items,
    )

    report = engine.run()
    summary = report.summary()

    assert summary["status"] == "SUCCESS"
    assert summary["scanned"] == 1
    assert summary["risk_approved"] == 1
    assert summary["error_count"] == 0


def test_pipeline_without_loader_requires_data():
    engine = MainApplicationEngine()

    report = engine.run()

    assert report.status == "FAILED"
    assert len(report.errors) > 0
  
