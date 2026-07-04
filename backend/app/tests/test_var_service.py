import pytest

from app.models.schemas import VarRequest
from app.services.var_service import run_var


def test_var_runs_with_three_to_four_variables():
    result = run_var(
        VarRequest(
            dataset_id="sample_country_risk_quarterly",
            country="Indonesia",
            variables=["inflation_yoy", "policy_rate", "bond_yield_10y", "fx_depreciation_yoy"],
            lag_order=1,
            forecast_horizon=4,
        )
    )
    assert len(result.forecast) == 4
    assert result.impulse_response


def test_short_var_data_produces_clear_error():
    with pytest.raises(ValueError, match="VAR model could not be estimated reliably"):
        run_var(
            VarRequest(
                dataset_id="sample_country_risk_quarterly",
                country="Indonesia",
                date_start="2025-Q1",
                variables=["inflation_yoy", "policy_rate", "bond_yield_10y", "fx_depreciation_yoy"],
                lag_order=4,
                forecast_horizon=4,
            )
        )

