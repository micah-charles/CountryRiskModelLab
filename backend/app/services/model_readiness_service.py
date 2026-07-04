from __future__ import annotations

from app.models.schemas import ModelReadinessRequest, ModelReadinessResponse, VariableCoverage
from app.services.dataset_registry_service import load_dataset, model_numeric_columns


MARKET_VARIABLES = {
    "bond_yield_10y",
    "policy_rate",
    "global_risk_index",
    "fx_depreciation_yoy",
    "fx_index",
    "reserves_months_imports",
}


def _unique(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _selected_variables(request: ModelReadinessRequest) -> list[str]:
    if request.lab_type == "regression":
        return _unique([request.dependent_variable, *request.independent_variables])
    if request.lab_type == "forecast":
        variables = [request.target_variable]
        if request.model_type == "SARIMAX":
            variables += request.external_variables
        return _unique(variables)
    return _unique(request.variables)


def _required_observations(request: ModelReadinessRequest) -> int:
    if request.lab_type == "regression":
        return len(request.independent_variables) + 3
    if request.lab_type == "forecast":
        return 12
    variable_count = max(len(request.variables), 1)
    lag_order = max(request.lag_order, 1)
    return max(12, variable_count * lag_order * 3)


def _format_list(values: list[str]) -> str:
    if len(values) == 1:
        return values[0]
    return ", ".join(values[:-1]) + f", and {values[-1]}"


def assess_model_readiness(request: ModelReadinessRequest) -> ModelReadinessResponse:
    metadata, df = load_dataset(request.dataset_id)
    model_columns = model_numeric_columns(df, metadata.country_column, metadata.date_column)
    selected = _selected_variables(request)
    selected_set = set(selected)

    country_df = df.copy()
    if request.country and metadata.country_column in country_df.columns:
        country_df = country_df[country_df[metadata.country_column].astype(str) == request.country]

    range_df = country_df.copy()
    if request.date_start and metadata.date_column in range_df.columns:
        range_df = range_df[range_df[metadata.date_column].astype(str) >= request.date_start]
    if request.date_end and metadata.date_column in range_df.columns:
        range_df = range_df[range_df[metadata.date_column].astype(str) <= request.date_end]

    coverage_variables = _unique([*model_columns, *selected])
    coverage: list[VariableCoverage] = []
    for variable in coverage_variables:
        if variable not in df.columns:
            coverage.append(VariableCoverage(variable=variable, exists=False, selected=variable in selected_set, all_missing=True))
            continue
        non_null = country_df[country_df[variable].notna()] if variable in country_df.columns else country_df.iloc[0:0]
        first_date = None
        last_date = None
        if not non_null.empty and metadata.date_column in non_null.columns:
            dates = non_null[metadata.date_column].dropna().astype(str).sort_values()
            if not dates.empty:
                first_date = str(dates.iloc[0])
                last_date = str(dates.iloc[-1])
        coverage.append(
            VariableCoverage(
                variable=variable,
                exists=True,
                selected=variable in selected_set,
                non_null_count=int(len(non_null)),
                first_date=first_date,
                last_date=last_date,
                all_missing=len(non_null) == 0,
            )
        )

    existing_selected = [variable for variable in selected if variable in df.columns]
    missing_columns = [variable for variable in selected if variable not in df.columns]
    complete_case_count = 0
    suggested_date_start = None
    suggested_date_end = None
    if existing_selected:
        complete_cases = country_df.dropna(subset=existing_selected)
        ranged_complete_cases = range_df.dropna(subset=existing_selected)
        complete_case_count = int(len(ranged_complete_cases))
        if not complete_cases.empty and metadata.date_column in complete_cases.columns:
            dates = complete_cases[metadata.date_column].dropna().astype(str).sort_values()
            if not dates.empty:
                suggested_date_start = str(dates.iloc[0])
                suggested_date_end = str(dates.iloc[-1])

    required = _required_observations(request)
    blocking_issues: list[str] = []
    recommendations: list[str] = []

    if request.country and country_df.empty:
        blocking_issues.append(f"No rows found for {request.country} in this dataset.")
        recommendations.append("Choose a country that appears in the selected dataset.")

    if request.lab_type == "regression":
        if not request.dependent_variable:
            blocking_issues.append("Select a dependent variable.")
        if not request.independent_variables:
            blocking_issues.append("Select at least one independent variable.")
    elif request.lab_type == "forecast":
        if not request.target_variable:
            blocking_issues.append("Select a target variable.")
    elif len(request.variables) < 2:
        blocking_issues.append("VAR needs at least two variables.")

    if missing_columns:
        blocking_issues.append(f"This dataset does not contain: {_format_list(missing_columns)}.")
        if metadata.source_type == "imf_api" and any(variable in MARKET_VARIABLES for variable in missing_columns):
            available = [column for column in model_columns if column not in missing_columns]
            if available:
                recommendations.append(
                    "The IMF annual dataset currently contains macro variables such as "
                    f"{_format_list(available[:5])}. Use those variables, choose a sample market dataset, "
                    "or add a real market-data source for bond yields, policy rates, and risk indexes."
                )
            else:
                recommendations.append("Choose a dataset that contains the missing market variables.")

    empty_selected = [
        item.variable
        for item in coverage
        if item.selected and item.exists and item.all_missing
    ]
    if empty_selected:
        blocking_issues.append(f"Selected variables have no observations for {request.country or 'the selected country'}: {_format_list(empty_selected)}.")
        recommendations.append("Remove those variables or choose a country with observations for them.")

    if selected and not missing_columns and not empty_selected and complete_case_count < required:
        blocking_issues.append(f"Only {complete_case_count} complete observations are available; this model needs at least {required}.")
        if suggested_date_start and suggested_date_end:
            recommendations.append(f"Use the complete-data window {suggested_date_start} to {suggested_date_end}, reduce variables, or choose another country.")
        else:
            recommendations.append("Use a longer date range, reduce variables, or choose another country.")

    if suggested_date_start and suggested_date_end:
        outside_suggested = (
            (request.date_start and request.date_start < suggested_date_start)
            or (request.date_end and request.date_end > suggested_date_end)
        )
        if outside_suggested:
            recommendations.append(f"The selected variables have complete data from {suggested_date_start} to {suggested_date_end}.")

    if metadata.frequency == "annual" and request.lab_type in {"forecast", "var"}:
        recommendations.append("This is annual data. Forecasting and VAR are usually stronger with longer monthly or quarterly series.")

    status = "blocked" if blocking_issues else "warning" if recommendations else "ready"
    return ModelReadinessResponse(
        dataset_id=metadata.dataset_id,
        lab_type=request.lab_type,
        status=status,
        run_enabled=not blocking_issues,
        country=request.country,
        frequency=metadata.frequency,
        date_range=metadata.date_range,
        model_numeric_columns=model_columns,
        selected_variables=selected,
        missing_columns=missing_columns,
        variable_coverage=coverage,
        complete_case_count=complete_case_count,
        required_observations=required,
        suggested_date_start=suggested_date_start,
        suggested_date_end=suggested_date_end,
        blocking_issues=blocking_issues,
        recommendations=recommendations,
    )
