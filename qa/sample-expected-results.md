# Sample Expected Results

The synthetic datasets are deterministic, so sample model outputs should be stable in broad shape even if dependency versions change exact coefficients.

## Regression

Use:

- Dataset: `sample_country_risk_quarterly`
- Country: Indonesia
- Dependent variable: `bond_yield_10y`
- Independent variables: `inflation_yoy`, `policy_rate`, `debt_gdp`, `current_account_gdp`, `global_risk_index`

Expected:

- OLS result returns coefficients.
- R-squared is present.
- Actual vs fitted and residual charts are populated.
- Diagnostics include RMSE, MAE, Durbin-Watson, and warning flags.
- Python code preview uses `statsmodels.api.OLS`.

## Forecasting

Use:

- Dataset: `sample_country_risk_monthly`
- Country: Indonesia
- Target variable: `bond_yield_10y`
- Model type: `ARIMA` or `SARIMAX`
- Forecast horizon: 12

Expected:

- Forecast has 12 rows.
- AIC and BIC are present.
- Residual chart is populated.
- Auto ARIMA returns ranked candidate models when enough observations are available.

## VAR

Use:

- Dataset: `sample_country_risk_quarterly`
- Country: Indonesia
- Variables: `inflation_yoy`, `policy_rate`, `bond_yield_10y`, `fx_depreciation_yoy`
- Lag order: 1
- Forecast horizon: 8

Expected:

- Forecast has 8 rows.
- Impulse response data is populated.
- Response includes strengths, weaknesses, suggestions, and Python code.

