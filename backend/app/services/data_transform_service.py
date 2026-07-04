from __future__ import annotations

from typing import Any

import pandas as pd

from app.models.schemas import ImfIndicator


COUNTRY_CODES = {
    "Indonesia": "IDN",
    "Brazil": "BRA",
    "South Africa": "ZAF",
    "Turkey": "TUR",
    "Mexico": "MEX",
    "India": "IND",
}


COUNTRY_NAMES = {code: country for country, code in COUNTRY_CODES.items()}


def resolve_country_code(selection: str, country_codes_by_name: dict[str, str] | None = None) -> str:
    if selection in COUNTRY_NAMES:
        return selection
    if selection in COUNTRY_CODES:
        return COUNTRY_CODES[selection]
    if country_codes_by_name and selection in country_codes_by_name:
        return country_codes_by_name[selection]
    return selection


def _coerce_float(value: Any) -> float | None:
    try:
        if value in ("", None):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_values(payload: dict[str, Any], indicator_code: str) -> dict[str, dict[str, Any]]:
    values = payload.get("values", payload)
    if isinstance(values, dict) and indicator_code in values:
        values = values[indicator_code]
    if not isinstance(values, dict):
        return {}
    return values


def transform_datamapper_payloads(
    payloads_by_indicator: dict[str, dict[str, Any]],
    indicators: dict[str, ImfIndicator],
    country_names: list[str],
    years: list[int],
    country_names_by_code: dict[str, str] | None = None,
    country_codes_by_name: dict[str, str] | None = None,
) -> pd.DataFrame:
    country_codes = [resolve_country_code(country, country_codes_by_name) for country in country_names]
    rows: dict[tuple[str, str], dict[str, Any]] = {}

    for country, country_code in zip(country_names, country_codes):
        display_name = (
            country_names_by_code.get(country_code)
            if country_names_by_code
            else COUNTRY_NAMES.get(country_code, country)
        )
        for year in years:
            rows[(country_code, str(year))] = {
                "country": display_name or country,
                "country_code": country_code,
                "date": str(year),
            }

    for indicator_code, payload in payloads_by_indicator.items():
        indicator = indicators[indicator_code]
        values = _extract_values(payload, indicator_code)
        for country_code in country_codes:
            country_label = (
                country_names_by_code.get(country_code)
                if country_names_by_code
                else COUNTRY_NAMES.get(country_code, "")
            )
            country_payload = values.get(country_code) or values.get(country_label)
            if not isinstance(country_payload, dict):
                continue
            for year in years:
                row = rows.setdefault(
                    (country_code, str(year)),
                    {
                        "country": country_label or COUNTRY_NAMES.get(country_code, country_code),
                        "country_code": country_code,
                        "date": str(year),
                    },
                )
                row[indicator.platform_variable] = _coerce_float(country_payload.get(str(year)))

    df = pd.DataFrame(rows.values())
    ordered_columns = ["country", "country_code", "date"] + [
        indicators[code].platform_variable for code in payloads_by_indicator
    ]
    for column in ordered_columns:
        if column not in df.columns:
            df[column] = None
    return df[ordered_columns].sort_values(["country", "date"]).reset_index(drop=True)


def missing_value_summary(df: pd.DataFrame) -> dict[str, int]:
    return {column: int(value) for column, value in df.isna().sum().items()}


def imf_learning_notes() -> list[str]:
    return [
        "This dataset uses annual IMF macroeconomic indicators. Annual data is suitable for medium-term country-risk analysis and cross-country comparison, but it is less suitable for short-term market forecasting.",
        "For regression, use this dataset to explore whether inflation, government debt, current account balance, and GDP growth are associated with sovereign risk indicators.",
        "For forecasting, annual data has fewer observations than monthly or quarterly data. ARIMA may be less reliable if the sample is short.",
        "For VAR models, annual data may not provide enough observations unless the time range is long and the number of variables is limited.",
    ]
