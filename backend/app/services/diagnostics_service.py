from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.stats.stattools import durbin_watson


def regression_diagnostics(df: pd.DataFrame, independent_variables: list[str], residuals: pd.Series) -> dict:
    n_obs = len(df)
    multicollinearity_warning = False
    if len(independent_variables) > 1:
        corr = df[independent_variables].corr(numeric_only=True).abs()
        upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
        multicollinearity_warning = bool((upper > 0.8).any().any())

    dw = float(durbin_watson(residuals)) if len(residuals) > 2 else None
    residual_autocorrelation_warning = bool(dw is not None and (dw < 1.5 or dw > 2.5))
    overfitting_warning = bool(n_obs < max(10, len(independent_variables) * 10))

    return {
        "rmse": float(np.sqrt(mean_squared_error(df["_actual"], df["_fitted"]))),
        "mae": float(mean_absolute_error(df["_actual"], df["_fitted"])),
        "durbin_watson": dw,
        "residual_autocorrelation_warning": residual_autocorrelation_warning,
        "multicollinearity_warning": multicollinearity_warning,
        "small_sample_warning": n_obs < 30,
        "overfitting_warning": overfitting_warning,
    }


def strength_weakness_suggestions(diagnostics: dict, model_type: str = "regression") -> tuple[list[str], list[str], list[str]]:
    strengths = [
        "The model uses variables with a clear macroeconomic rationale.",
        "The model is interpretable and suitable for analyst communication.",
    ]
    weaknesses = [
        "The model may omit political, institutional, and event-risk factors.",
        "Statistical fit does not guarantee forecasting performance or causal interpretation.",
    ]
    suggestions = [
        "Compare the result with a simpler model and a richer model.",
        "Test whether results are stable before and after crisis periods.",
    ]

    if model_type == "regression":
        if not diagnostics.get("small_sample_warning"):
            strengths.append("The sample size is adequate for a basic regression learning exercise.")
        if diagnostics.get("multicollinearity_warning"):
            weaknesses.append("Some explanatory variables may be highly correlated with each other.")
            suggestions.append("Reduce correlated variables or test them in separate specifications.")
        if diagnostics.get("small_sample_warning"):
            weaknesses.append("The sample size may be too small for reliable inference.")
            suggestions.append("Use a longer date range or fewer explanatory variables.")
        if diagnostics.get("residual_autocorrelation_warning"):
            weaknesses.append("Residual autocorrelation suggests the model may miss time-series dynamics.")
            suggestions.append("Test lagged explanatory variables or compare with a time-series model.")
        suggestions.append("Add or compare a global risk sentiment variable where available.")
    else:
        strengths.append("The model provides a transparent baseline for time-series learning.")
        weaknesses.append("Country-risk series may have structural breaks that reduce forecast stability.")
        suggestions.append("Compare statistical fit with economic plausibility before using the forecast.")

    return strengths, weaknesses, suggestions

