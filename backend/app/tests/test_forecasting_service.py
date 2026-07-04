from app.models.schemas import ForecastRequest
from app.services.forecasting_service import run_forecast


def test_arima_model_runs_on_sample_monthly_data():
    result = run_forecast(
        ForecastRequest(
            dataset_id="sample_country_risk_monthly",
            country="Indonesia",
            target_variable="bond_yield_10y",
            model_type="ARIMA",
            order=[1, 1, 1],
            forecast_horizon=4,
        )
    )
    assert len(result.forecast) == 4
    assert result.aic is not None
    assert result.residuals


def test_sarimax_model_runs_with_external_variables():
    result = run_forecast(
        ForecastRequest(
            dataset_id="sample_country_risk_monthly",
            country="Indonesia",
            target_variable="bond_yield_10y",
            model_type="SARIMAX",
            order=[1, 1, 1],
            seasonal_order=[1, 0, 1, 12],
            external_variables=["policy_rate", "inflation_yoy", "global_risk_index"],
            forecast_horizon=4,
        )
    )
    assert len(result.forecast) == 4
    assert result.rmse is not None


def test_auto_arima_returns_ranked_model_candidates():
    result = run_forecast(
        ForecastRequest(
            dataset_id="sample_country_risk_monthly",
            country="Indonesia",
            target_variable="bond_yield_10y",
            model_type="AUTO_ARIMA",
            forecast_horizon=4,
        )
    )
    assert result.model_candidates

