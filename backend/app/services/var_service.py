from __future__ import annotations

import numpy as np
from statsmodels.tsa.api import VAR

from app.models.schemas import VarRequest, VarResult
from app.services.dataset_service import filter_model_frame
from app.services.model_governance_service import assert_model_use_allowed


def run_var(request: VarRequest) -> VarResult:
    model_governance = assert_model_use_allowed("var", request.intended_use, request.model_id)
    if len(request.variables) < 2:
        raise ValueError("VAR needs at least two variables.")
    metadata, df = filter_model_frame(request.dataset_id, request.country, request.date_start, request.date_end, request.variables)
    df = df.dropna(subset=request.variables).sort_values(metadata.date_column).copy()
    min_obs = max(12, len(request.variables) * request.lag_order * 3)
    if len(df) < min_obs:
        raise ValueError("The VAR model could not be estimated reliably. Try fewer variables, a shorter lag length, or a longer time series.")

    try:
        fit = VAR(df[request.variables].astype(float)).fit(request.lag_order)
        forecast_values = fit.forecast(df[request.variables].astype(float).values[-request.lag_order :], steps=request.forecast_horizon)
        irf = fit.irf(min(request.forecast_horizon, 8)).irfs
    except Exception as exc:
        raise ValueError("The VAR model could not be estimated reliably. Try fewer variables, a shorter lag length, or a longer time series.") from exc

    forecast = []
    for step, values in enumerate(forecast_values, start=1):
        row = {"period": f"t+{step}"}
        row.update({variable: float(values[i]) for i, variable in enumerate(request.variables)})
        forecast.append(row)

    impulse_response = []
    for horizon in range(irf.shape[0]):
        for impulse_idx, impulse in enumerate(request.variables):
            for response_idx, response in enumerate(request.variables):
                impulse_response.append(
                    {
                        "horizon": horizon,
                        "impulse": impulse,
                        "response": response,
                        "value": float(np.nan_to_num(irf[horizon, response_idx, impulse_idx])),
                    }
                )

    python_code = "\n".join(
        [
            "from statsmodels.tsa.api import VAR",
            f"variables = {request.variables!r}",
            "model = VAR(df[variables])",
            f"fit = model.fit({request.lag_order})",
            f"forecast = fit.forecast(df[variables].values[-{request.lag_order}:], steps={request.forecast_horizon})",
        ]
    )
    weaknesses = [
        "VAR results can be unstable when the sample is short or variables are highly persistent.",
        "Impulse responses are educational approximations and require economic judgement.",
    ]
    if metadata.frequency == "annual":
        weaknesses.append("Annual data may not provide enough observations for rich VAR specifications.")

    return VarResult(
        variables=request.variables,
        lag_order=request.lag_order,
        aic=float(fit.aic),
        bic=float(fit.bic),
        forecast=forecast,
        impulse_response=impulse_response,
        strengths=[
            "VAR allows several macro-financial variables to interact over time.",
            "The model helps analysts learn lagged relationships and impulse responses.",
        ],
        weaknesses=weaknesses,
        suggested_modifications=[
            "Try fewer variables or a lower lag length if the model is unstable.",
            "Compare results across countries and sub-periods.",
            "Future phase: stationarity tests, Johansen cointegration test, and VECM estimation.",
        ],
        python_code=python_code,
        dataset=metadata,
        model_governance=model_governance,
    )
