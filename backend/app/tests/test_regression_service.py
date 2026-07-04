from app.models.schemas import MemoRequest, RegressionRequest
from app.services.memo_service import generate_memo
from app.services.regression_service import run_regression


def test_ols_model_runs_and_returns_diagnostics():
    result = run_regression(
        RegressionRequest(
            dataset_id="sample_country_risk_quarterly",
            country="Indonesia",
            dependent_variable="bond_yield_10y",
            independent_variables=["inflation_yoy", "policy_rate", "debt_gdp", "current_account_gdp", "global_risk_index"],
        )
    )
    assert result.n_observations > 30
    assert result.coefficients
    assert result.r_squared >= 0
    assert "rmse" in result.diagnostics
    assert result.charts["residuals"]


def test_memo_can_be_generated_from_regression_result():
    result = run_regression(
        RegressionRequest(
            dataset_id="sample_country_risk_quarterly",
            country="Indonesia",
            dependent_variable="bond_yield_10y",
            independent_variables=["inflation_yoy", "policy_rate"],
        )
    )
    memo = generate_memo(MemoRequest(model_result=result.model_dump()))
    assert "# Model Review Memo" in memo.markdown
    assert "Python Code Appendix" in memo.markdown

