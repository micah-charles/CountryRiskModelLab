from src.analysis.metrics_schema import Evidence
def test_missing_metric_contract():
    e=Evidence(stock_code="02020",company_name="ANTA",industry="sportswear",financial_year=2024,metric="gmv",confidence=0,validation_status="missing",missing_reason="not found")
    assert e.value is None and e.missing_reason

