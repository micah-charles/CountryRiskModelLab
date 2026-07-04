from __future__ import annotations

import pandas as pd
import statsmodels.api as sm

from app.models.schemas import CoefficientResult, RegressionRequest, RegressionResult
from app.services.dataset_service import filter_model_frame
from app.services.diagnostics_service import regression_diagnostics, strength_weakness_suggestions
from app.services.model_governance_service import assert_model_use_allowed


def _apply_transformations(df: pd.DataFrame, date_column: str, transformations: dict[str, list[str]]) -> pd.DataFrame:
    df = df.sort_values(date_column).copy()
    for column in transformations.get("lag_1", []):
        if column in df.columns:
            df[f"{column}_lag1"] = df[column].shift(1)
    for column in transformations.get("z_score", []):
        if column in df.columns:
            std = df[column].std()
            if std:
                df[f"{column}_z"] = (df[column] - df[column].mean()) / std
    return df


def _model_columns(independent_variables: list[str], transformations: dict[str, list[str]]) -> list[str]:
    lagged = set(transformations.get("lag_1", []))
    z_scored = set(transformations.get("z_score", []))
    columns: list[str] = []
    for column in independent_variables:
        if column in lagged:
            columns.append(f"{column}_lag1")
        elif column in z_scored:
            columns.append(f"{column}_z")
        else:
            columns.append(column)
    return columns


def run_regression(request: RegressionRequest) -> RegressionResult:
    model_governance = assert_model_use_allowed("regression", request.intended_use, request.model_id)
    required = [request.dependent_variable] + request.independent_variables
    metadata, df = filter_model_frame(
        request.dataset_id,
        request.country,
        request.date_start,
        request.date_end,
        required,
    )
    date_column = metadata.date_column
    df = _apply_transformations(df, date_column, request.transformations)
    model_columns = [column for column in _model_columns(request.independent_variables, request.transformations) if column in df.columns]
    if not model_columns:
        raise ValueError("Select at least one valid independent variable.")

    model_df = df[[date_column, request.dependent_variable] + model_columns].dropna().copy()
    if len(model_df) < len(model_columns) + 3:
        raise ValueError("Not enough observations for this model. Try a longer date range or fewer variables.")

    y = model_df[request.dependent_variable].astype(float)
    X = sm.add_constant(model_df[model_columns].astype(float), has_constant="add")
    fit = sm.OLS(y, X).fit()

    model_df["_actual"] = y
    model_df["_fitted"] = fit.fittedvalues
    model_df["_residual"] = fit.resid
    diagnostics = regression_diagnostics(model_df, model_columns, model_df["_residual"])
    strengths, weaknesses, suggestions = strength_weakness_suggestions(diagnostics, "regression")

    coefficients: list[CoefficientResult] = []
    for variable in ["const"] + model_columns:
        coefficient = float(fit.params.get(variable, 0.0))
        label = "intercept" if variable == "const" else variable
        if variable == "const":
            interpretation = "The intercept is the fitted baseline when all explanatory variables equal zero."
        else:
            interpretation = (
                f"A one-unit increase in {variable} is associated with a {coefficient:.3f} change in "
                f"{request.dependent_variable}, holding other selected variables constant."
            )
        coefficients.append(
            CoefficientResult(
                variable=label,
                coefficient=coefficient,
                p_value=float(fit.pvalues.get(variable)) if variable in fit.pvalues else None,
                std_error=float(fit.bse.get(variable)) if variable in fit.bse else None,
                interpretation=interpretation,
            )
        )

    python_code = "\n".join(
        [
            "import pandas as pd",
            "import statsmodels.api as sm",
            f'X = df[{model_columns!r}]',
            f'y = df["{request.dependent_variable}"]',
            "X = sm.add_constant(X)",
            "model = sm.OLS(y, X).fit()",
            "print(model.summary())",
        ]
    )

    return RegressionResult(
        n_observations=len(model_df),
        dependent_variable=request.dependent_variable,
        independent_variables=model_columns,
        r_squared=float(fit.rsquared),
        adjusted_r_squared=float(fit.rsquared_adj),
        coefficients=coefficients,
        diagnostics=diagnostics,
        charts={
            "actual_vs_fitted": [
                {"date": row[date_column], "actual": row["_actual"], "fitted": row["_fitted"]}
                for row in model_df.to_dict(orient="records")
            ],
            "residuals": [
                {"date": row[date_column], "residual": row["_residual"]}
                for row in model_df.to_dict(orient="records")
            ],
        },
        strengths=strengths,
        weaknesses=weaknesses,
        suggested_modifications=suggestions,
        python_code=python_code,
        dataset=metadata,
        model_governance=model_governance,
    )
