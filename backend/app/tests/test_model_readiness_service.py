from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import ModelReadinessRequest
from app.services.dataset_registry_service import metadata_from_csv, read_registry, upsert_dataset, write_registry
from app.services.model_readiness_service import assess_model_readiness


def _register_imf_readiness_fixture(tmp_path: Path) -> str:
    rows = []
    for country, code in [("Afghanistan", "AFG"), ("Japan", "JPN"), ("Thailand", "THA")]:
        for year in range(2010, 2027):
            rows.append(
                {
                    "country": country,
                    "country_code": code,
                    "date": year,
                    "gdp_growth_yoy": 2.0,
                    "inflation_yoy": 3.0,
                    "debt_gdp": 60.0,
                    "current_account_gdp": -1.0,
                    "fiscal_balance_gdp": -3.0,
                    "unemployment_rate": None if country == "Afghanistan" else 4.0,
                }
            )
    path = tmp_path / "imf_readiness_fixture.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    metadata = metadata_from_csv(
        "imf_readiness_fixture",
        "IMF Readiness Fixture",
        "imf_api",
        "Test IMF data",
        path,
        notes=["IMF_ALL_COUNTRIES_PREFETCH"],
    )
    upsert_dataset(metadata)
    return metadata.dataset_id


def test_readiness_blocks_missing_market_columns_for_imf_dataset(tmp_path):
    original_registry = read_registry()
    try:
        dataset_id = _register_imf_readiness_fixture(tmp_path)
        response = assess_model_readiness(
            ModelReadinessRequest(
                dataset_id=dataset_id,
                lab_type="regression",
                country="Afghanistan",
                dependent_variable="bond_yield_10y",
                independent_variables=["policy_rate", "global_risk_index"],
            )
        )

        assert response.run_enabled is False
        assert response.status == "blocked"
        assert response.missing_columns == ["bond_yield_10y", "policy_rate", "global_risk_index"]
        assert any("real market-data source" in item for item in response.recommendations)
    finally:
        write_registry(original_registry)


def test_readiness_reports_present_but_empty_country_variable(tmp_path):
    original_registry = read_registry()
    try:
        dataset_id = _register_imf_readiness_fixture(tmp_path)
        response = assess_model_readiness(
            ModelReadinessRequest(
                dataset_id=dataset_id,
                lab_type="var",
                country="Afghanistan",
                variables=["gdp_growth_yoy", "unemployment_rate"],
                lag_order=1,
            )
        )

        unemployment = next(item for item in response.variable_coverage if item.variable == "unemployment_rate")
        assert unemployment.exists is True
        assert unemployment.non_null_count == 0
        assert unemployment.first_date is None
        assert response.run_enabled is False
        assert any("unemployment_rate" in issue for issue in response.blocking_issues)
    finally:
        write_registry(original_registry)


def test_readiness_reports_japan_imf_macro_window_as_usable(tmp_path):
    original_registry = read_registry()
    try:
        dataset_id = _register_imf_readiness_fixture(tmp_path)
        response = assess_model_readiness(
            ModelReadinessRequest(
                dataset_id=dataset_id,
                lab_type="regression",
                country="Japan",
                dependent_variable="gdp_growth_yoy",
                independent_variables=["inflation_yoy", "debt_gdp", "current_account_gdp"],
            )
        )

        assert response.run_enabled is True
        assert response.complete_case_count == 17
        assert response.required_observations == 6
        assert response.suggested_date_start == "2010"
        assert response.suggested_date_end == "2026"
    finally:
        write_registry(original_registry)


def test_readiness_blocks_var_when_lag_and_variable_count_need_more_rows(tmp_path):
    original_registry = read_registry()
    try:
        dataset_id = _register_imf_readiness_fixture(tmp_path)
        response = assess_model_readiness(
            ModelReadinessRequest(
                dataset_id=dataset_id,
                lab_type="var",
                country="Thailand",
                variables=["gdp_growth_yoy", "inflation_yoy", "debt_gdp", "current_account_gdp", "fiscal_balance_gdp"],
                lag_order=2,
            )
        )

        assert response.run_enabled is False
        assert response.complete_case_count == 17
        assert response.required_observations == 30
        assert any("complete observations" in issue for issue in response.blocking_issues)
    finally:
        write_registry(original_registry)


def test_model_readiness_endpoint_is_available(tmp_path):
    original_registry = read_registry()
    try:
        dataset_id = _register_imf_readiness_fixture(tmp_path)
        client = TestClient(app)
        response = client.post(
            "/api/models/readiness",
            json={
                "dataset_id": dataset_id,
                "lab_type": "forecast",
                "country": "Thailand",
                "target_variable": "gdp_growth_yoy",
                "model_type": "ARIMA",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["run_enabled"] is True
        assert payload["status"] == "warning"
        assert payload["suggested_date_start"] == "2010"
        assert payload["suggested_date_end"] == "2026"
    finally:
        write_registry(original_registry)
