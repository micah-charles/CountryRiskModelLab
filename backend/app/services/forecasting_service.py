from __future__ import annotations

import itertools
import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.statespace.sarimax import SARIMAX

from app.models.schemas import ForecastRequest, ForecastResult
from app.services.dataset_service import filter_model_frame
from app.services.diagnostics_service import strength_weakness_suggestions
from app.services.model_governance_service import assert_model_use_allowed


def _fit_sarimax(y: pd.Series, order: list[int], seasonal_order: list[int], exog: pd.DataFrame | None):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = SARIMAX(
            y,
            order=tuple(order),
            seasonal_order=tuple(seasonal_order),
            exog=exog,
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        return model.fit(disp=False)


def _next_dates(last_date: str, horizon: int, frequency: str) -> list[str]:
    if frequency == "monthly":
        start = pd.Period(last_date, freq="M") + 1
        return [str(start + i) for i in range(horizon)]
    if frequency == "quarterly":
        start = pd.Period(last_date.replace("-Q", "Q"), freq="Q") + 1
        return [str(start + i).replace("Q", "-Q") for i in range(horizon)]
    if last_date.isdigit():
        return [str(int(last_date) + i + 1) for i in range(horizon)]
    return [f"t+{i + 1}" for i in range(horizon)]


def _candidate_metrics(fit, y: pd.Series) -> tuple[float | None, float | None]:
    fitted = pd.Series(fit.fittedvalues, index=y.index).dropna()
    aligned = y.loc[fitted.index]
    if fitted.empty:
        return None, None
    mae = float(mean_absolute_error(aligned, fitted))
    rmse = float(np.sqrt(mean_squared_error(aligned, fitted)))
    return mae, rmse


def _auto_grid_search(y: pd.Series, frequency: str) -> list[dict]:
    candidates = []
    seasonal_m = 12 if frequency == "monthly" else 4 if frequency == "quarterly" else 0
    for order in itertools.product([0, 1, 2], [0, 1], [0, 1, 2]):
        seasonal_orders = [(0, 0, 0, 0)]
        if seasonal_m:
            seasonal_orders += list(itertools.product([0, 1], [0, 1], [0, 1], [seasonal_m]))
        for seasonal_order in seasonal_orders:
            try:
                fit = _fit_sarimax(y, list(order), list(seasonal_order), None)
                mae, rmse = _candidate_metrics(fit, y)
                candidates.append(
                    {
                        "order": list(order),
                        "seasonal_order": list(seasonal_order),
                        "aic": float(fit.aic),
                        "bic": float(fit.bic),
                        "mae": mae,
                        "rmse": rmse,
                        "converged": bool(fit.mle_retvals.get("converged", True)),
                    }
                )
            except Exception:
                continue
    return sorted(candidates, key=lambda item: (item.get("aic") or float("inf"), item.get("rmse") or float("inf")))[:10]


def run_forecast(request: ForecastRequest) -> ForecastResult:
    model_governance = assert_model_use_allowed("forecast", request.intended_use, request.model_id)
    required = [request.target_variable] + request.external_variables
    metadata, df = filter_model_frame(request.dataset_id, request.country, request.date_start, request.date_end, required)
    df = df.dropna(subset=[request.target_variable]).sort_values(metadata.date_column).copy()
    if len(df) < 12:
        raise ValueError("Not enough observations for this model. Try a longer date range or a simpler model order.")

    y = df[request.target_variable].astype(float)
    exog = df[request.external_variables].astype(float).ffill().bfill() if request.external_variables else None
    order = request.order
    seasonal_order = request.seasonal_order
    candidates: list[dict] = []

    if request.model_type == "AUTO_ARIMA":
        candidates = _auto_grid_search(y, metadata.frequency)
        if not candidates:
            raise ValueError("The model failed to converge. Try a simpler model order, such as ARIMA(1,1,1).")
        best = candidates[0]
        order = best["order"]
        seasonal_order = best["seasonal_order"]
        exog = None
    elif request.model_type == "ARIMA":
        seasonal_order = [0, 0, 0, 0]
        exog = None
    elif request.model_type == "SARIMA":
        exog = None

    try:
        fit = _fit_sarimax(y, order, seasonal_order, exog)
    except Exception as exc:
        raise ValueError("The model failed to converge. Try a simpler model order, such as ARIMA(1,1,1).") from exc

    future_exog = None
    if exog is not None:
        last = exog.tail(1)
        future_exog = pd.concat([last] * request.forecast_horizon, ignore_index=True)

    forecast_obj = fit.get_forecast(steps=request.forecast_horizon, exog=future_exog)
    forecast_mean = forecast_obj.predicted_mean
    conf = forecast_obj.conf_int()
    future_dates = _next_dates(str(df[metadata.date_column].iloc[-1]), request.forecast_horizon, metadata.frequency)

    fitted = pd.Series(fit.fittedvalues, index=df.index)
    fitted_clean = fitted.bfill().fillna(0.0)
    residuals = y - fitted
    mae, rmse = _candidate_metrics(fit, y)
    diagnostics = {"small_sample_warning": len(df) < 30}
    strengths, weaknesses, suggestions = strength_weakness_suggestions(diagnostics, "forecast")
    if request.model_type == "AUTO_ARIMA":
        weaknesses.append("The model with the lowest AIC is not always best for country-risk analysis.")
        suggestions.append("Use analyst judgement to review crisis periods, policy changes, and structural breaks.")
    if metadata.frequency == "annual":
        weaknesses.append("Annual data may have limited observations for ARIMA/SARIMAX models.")

    python_code = "\n".join(
        [
            "from statsmodels.tsa.statespace.sarimax import SARIMAX",
            f'y = df["{request.target_variable}"]',
            f"model = SARIMAX(y, order={order}, seasonal_order={seasonal_order})",
            "fit = model.fit(disp=False)",
            f"forecast = fit.get_forecast(steps={request.forecast_horizon})",
        ]
    )

    return ForecastResult(
        model_type=request.model_type,
        target_variable=request.target_variable,
        order=order,
        seasonal_order=seasonal_order,
        aic=float(fit.aic),
        bic=float(fit.bic),
        mae=mae,
        rmse=rmse,
        forecast=[
            {
                "date": future_dates[i],
                "forecast": float(forecast_mean.iloc[i]),
                "lower_ci": float(conf.iloc[i, 0]),
                "upper_ci": float(conf.iloc[i, 1]),
            }
            for i in range(request.forecast_horizon)
        ],
        fitted_values=[
            {"date": str(df[metadata.date_column].iloc[i]), "fitted": float(value)}
            for i, value in enumerate(fitted_clean)
        ],
        residuals=[
            {"date": str(df[metadata.date_column].iloc[i]), "residual": float(value)}
            for i, value in enumerate(residuals.fillna(0.0))
        ],
        model_candidates=candidates,
        strengths=strengths,
        weaknesses=weaknesses,
        suggested_modifications=suggestions,
        python_code=python_code,
        dataset=metadata,
        model_governance=model_governance,
    )
