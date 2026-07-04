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
