from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dataset_preview_endpoint():
    client = TestClient(app)
    response = client.get("/api/datasets/samples/sample_country_risk_quarterly/preview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["dataset_id"] == "sample_country_risk_quarterly"
    assert "bond_yield_10y" in payload["numeric_columns"]
    assert "date" not in payload["numeric_columns"]
    assert payload["row_count"] > len(payload["rows"])


def test_dataset_preview_limit_can_return_more_rows():
    client = TestClient(app)
    response = client.get("/api/datasets/samples/sample_country_risk_quarterly/preview?limit=50")
    assert response.status_code == 200
    payload = response.json()
    assert payload["row_count"] == 264
    assert len(payload["rows"]) == 50


def test_research_case_indicator_and_formula_endpoints():
    client = TestClient(app)

    cases = client.get("/api/research-cases")
    assert cases.status_code == 200
    assert cases.json()[0]["case_id"] == "uk_2022_mini_budget_ldi"

    case = client.get("/api/research-cases/uk_2022_mini_budget_ldi")
    assert case.status_code == 200
    assert case.json()["metadata"]["origin"] == "built_in"

    indicators = client.get("/api/indicators")
    assert indicators.status_code == 200
    assert any(item["indicator_id"] == "GOVT_YIELD_30Y" for item in indicators.json())

    formulas = client.get("/api/formulas")
    assert formulas.status_code == 200
    assert len(formulas.json()) >= 20

    calculation = client.post(
        "/api/formulas/calculate",
        json={
            "formula_id": "RATE_DV01",
            "parameters": {"position_value": 100000000, "modified_duration": 18, "yield_shock_bp": 50},
            "input_origin": "case_values",
        },
    )
    assert calculation.status_code == 200
    assert calculation.json()["outputs"]["estimated_pnl"] == -9000000
