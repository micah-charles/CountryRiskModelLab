from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


AnalyticalSupportType = Literal["formula", "statistical_model", "transmission", "identity", "rule_of_thumb", "none"]
PredictionQuestionType = Literal["directional", "binary", "numeric", "categorical", "ranking", "free_text"]


class HealthResponse(BaseModel):
    status: str = "ok"


class DatasetMetadata(BaseModel):
    dataset_id: str
    name: str
    source_type: Literal["sample", "upload", "imf_api"]
    source_name: str
    created_at: str
    frequency: Literal["monthly", "quarterly", "annual", "unknown"]
    country_column: str = "country"
    date_column: str = "date"
    columns: list[str]
    file_path: str
    metadata_path: str | None = None
    countries: list[str] = Field(default_factory=list)
    date_range: str | None = None
    notes: list[str] = Field(default_factory=list)


class DatasetPreview(BaseModel):
    dataset_id: str
    name: str
    source_type: str
    source_name: str
    frequency: str
    columns: list[str]
    row_count: int
    column_count: int
    rows: list[dict[str, Any]]
    numeric_columns: list[str]
    date_column: str
    country_column: str
    missing_values: dict[str, int]
    countries: list[str]
    date_range: str | None = None
    notes: list[str] = Field(default_factory=list)


class ImfCountry(BaseModel):
    code: str
    name: str


class ImfCountryCatalog(BaseModel):
    source_url: str
    last_modified_utc: str | None = None
    country_count: int
    countries: list[ImfCountry]


class ImfIndicator(BaseModel):
    code: str
    platform_variable: str
    label: str
    category: str
    frequency: str
    description: str
    typical_country_risk_interpretation: str
    expected_relationship_to_bond_yield: str


class ImfFetchRequest(BaseModel):
    countries: list[str]
    indicators: list[str]
    start_year: int = 2010
    end_year: int = 2026


class ImfPrefetchAllRequest(BaseModel):
    indicators: list[str] = Field(default_factory=list)
    start_year: int = 2010
    end_year: int = 2026


class ImfPrefetchedSessionRequest(BaseModel):
    source_dataset_id: str
    countries: list[str]
    indicators: list[str] = Field(default_factory=list)
    start_year: int | None = None
    end_year: int | None = None


class ImfFetchResponse(BaseModel):
    dataset: DatasetMetadata
    preview: DatasetPreview
    progress_states: list[str]


class RegressionValidation(BaseModel):
    train_test_split: bool = False
    test_size: float = 0.2


class RegressionRequest(BaseModel):
    dataset_id: str
    model_id: str | None = None
    intended_use: str = "learning"
    country: str | None = None
    date_start: str | None = None
    date_end: str | None = None
    dependent_variable: str
    independent_variables: list[str]
    transformations: dict[str, list[str]] = Field(default_factory=dict)
    validation: RegressionValidation = Field(default_factory=RegressionValidation)


class CoefficientResult(BaseModel):
    variable: str
    coefficient: float
    p_value: float | None = None
    std_error: float | None = None
    interpretation: str


class RegressionResult(BaseModel):
    model_type: str = "OLS Regression"
    n_observations: int
    dependent_variable: str
    independent_variables: list[str]
    r_squared: float
    adjusted_r_squared: float
    coefficients: list[CoefficientResult]
    diagnostics: dict[str, Any]
    charts: dict[str, list[dict[str, Any]]]
    strengths: list[str]
    weaknesses: list[str]
    suggested_modifications: list[str]
    python_code: str
    dataset: DatasetMetadata | None = None
    model_governance: dict[str, Any] = Field(default_factory=dict)


class ForecastValidation(BaseModel):
    train_test_split: bool = True
    test_size: float = 0.2


class ForecastRequest(BaseModel):
    dataset_id: str
    model_id: str | None = None
    intended_use: str = "learning"
    country: str | None = None
    date_start: str | None = None
    date_end: str | None = None
    target_variable: str
    model_type: Literal["ARIMA", "SARIMA", "SARIMAX", "AUTO_ARIMA"] = "ARIMA"
    order: list[int] = Field(default_factory=lambda: [1, 1, 1])
    seasonal_order: list[int] = Field(default_factory=lambda: [0, 0, 0, 0])
    external_variables: list[str] = Field(default_factory=list)
    forecast_horizon: int = 8
    validation: ForecastValidation = Field(default_factory=ForecastValidation)


class ForecastResult(BaseModel):
    model_type: str
    target_variable: str
    order: list[int]
    seasonal_order: list[int]
    aic: float | None = None
    bic: float | None = None
    mae: float | None = None
    rmse: float | None = None
    forecast: list[dict[str, Any]]
    fitted_values: list[dict[str, Any]]
    residuals: list[dict[str, Any]]
    model_candidates: list[dict[str, Any]] = Field(default_factory=list)
    strengths: list[str]
    weaknesses: list[str]
    suggested_modifications: list[str]
    python_code: str
    dataset: DatasetMetadata | None = None
    model_governance: dict[str, Any] = Field(default_factory=dict)


class VarRequest(BaseModel):
    dataset_id: str
    model_id: str | None = None
    intended_use: str = "learning"
    country: str | None = None
    date_start: str | None = None
    date_end: str | None = None
    variables: list[str]
    lag_order: int = 1
    forecast_horizon: int = 8


class VarResult(BaseModel):
    model_type: str = "VAR"
    variables: list[str]
    lag_order: int
    aic: float | None = None
    bic: float | None = None
    forecast: list[dict[str, Any]]
    impulse_response: list[dict[str, Any]]
    strengths: list[str]
    weaknesses: list[str]
    suggested_modifications: list[str]
    python_code: str
    dataset: DatasetMetadata | None = None
    model_governance: dict[str, Any] = Field(default_factory=dict)


class ModelReadinessRequest(BaseModel):
    dataset_id: str
    lab_type: Literal["regression", "forecast", "var"]
    country: str | None = None
    date_start: str | None = None
    date_end: str | None = None
    dependent_variable: str | None = None
    independent_variables: list[str] = Field(default_factory=list)
    target_variable: str | None = None
    external_variables: list[str] = Field(default_factory=list)
    variables: list[str] = Field(default_factory=list)
    model_type: str | None = None
    lag_order: int = 1


class VariableCoverage(BaseModel):
    variable: str
    exists: bool
    selected: bool = False
    non_null_count: int = 0
    first_date: str | None = None
    last_date: str | None = None
    all_missing: bool = False


class ModelReadinessResponse(BaseModel):
    dataset_id: str
    lab_type: str
    status: Literal["ready", "warning", "blocked"]
    run_enabled: bool
    country: str | None = None
    frequency: str
    date_range: str | None = None
    model_numeric_columns: list[str]
    selected_variables: list[str]
    missing_columns: list[str]
    variable_coverage: list[VariableCoverage]
    complete_case_count: int
    required_observations: int
    suggested_date_start: str | None = None
    suggested_date_end: str | None = None
    blocking_issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class CasePackValidation(BaseModel):
    valid: bool
    case_id: str | None = None
    schema_version: str | None = None
    imported: bool = False
    files: list[str] = Field(default_factory=list)
    file_hashes: dict[str, str] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    case: dict[str, Any] | None = None


class ResearchCaseSummary(BaseModel):
    case_id: str
    schema_version: str
    title: str
    short_title: str
    summary: str
    countries: list[str] = Field(default_factory=list)
    start_date: str | None = None
    end_date: str | None = None
    anchor_event_date: str | None = None
    themes: list[str] = Field(default_factory=list)
    difficulty: str = "intermediate"
    source_count: int = 0
    indicator_count: int = 0
    prediction_count: int = 0
    formula_refs: list[str] = Field(default_factory=list)
    has_report: bool = False
    origin: Literal["built_in", "imported"] = "built_in"


class AnalyticalSupport(BaseModel):
    """A safe reference to a reusable learning explanation."""

    type: AnalyticalSupportType = "none"
    reference_id: str | None = None
    title: str = ""
    summary: str = ""
    available_before_reveal: bool = True


class PredictionQuestion(BaseModel):
    """A prediction prompt with an explicit answer semantic."""

    model_config = ConfigDict(extra="allow")

    prediction_id: str
    prompt: str
    type: PredictionQuestionType = "directional"
    options: list[str] = Field(default_factory=list)
    expected_answer: Any = None
    actual_direction: str | None = None
    actual_answer: Any = None
    assessment: str | None = None
    explanation: str = ""
    source_ids: list[str] = Field(default_factory=list)
    analytical_support: AnalyticalSupport | None = None
    confidence_required: bool = True
    magnitude_label: str = "Expected magnitude / range"
    magnitude_placeholder: str = "e.g. +25 to +50bp"


class ResearchCase(BaseModel):
    case_id: str
    schema_version: str
    title: str
    short_title: str
    summary: str
    countries: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    start_date: str | None = None
    end_date: str | None = None
    anchor_event_date: str | None = None
    themes: list[str] = Field(default_factory=list)
    difficulty: str = "intermediate"
    trigger: dict[str, Any] = Field(default_factory=dict)
    background: str = ""
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    expected_transmission: list[dict[str, Any]] = Field(default_factory=list)
    actual_market_moves: list[dict[str, Any]] = Field(default_factory=list)
    market_series: list[dict[str, Any]] = Field(default_factory=list)
    predictions: list[PredictionQuestion] = Field(default_factory=list)
    consequences: dict[str, Any] = Field(default_factory=dict)
    portfolio_impacts: list[dict[str, Any]] = Field(default_factory=list)
    formula_refs: list[str] = Field(default_factory=list)
    lessons: list[Any] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    datasets: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(default_factory=dict)
    evidence_policy: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IndicatorDefinition(BaseModel):
    indicator_id: str
    name: str
    family: str
    description: str
    unit: str
    direction_semantics: str
    frequency: str
    source: str
    source_series_id: str | None = None
    transformation: str = "none"
    display_format: str = "value"


class FormulaVariable(BaseModel):
    name: str
    symbol: str
    label: str
    type: Literal["number", "array", "matrix", "text"] = "number"
    unit: str = ""
    default: Any = None
    min: float | None = None
    max: float | None = None
    step: float | None = None


class FormulaWorkedExample(BaseModel):
    name: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    expected_outputs: dict[str, Any] = Field(default_factory=dict)


class FormulaDefinition(BaseModel):
    formula_id: str
    name: str
    family: str
    business_question: str
    support_type: Literal["formula"] = "formula"
    difficulty: str
    latex: str
    plain_english: str
    variables: list[FormulaVariable] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    calculation_method: str
    worked_examples: list[FormulaWorkedExample] = Field(default_factory=list)
    related_formula_ids: list[str] = Field(default_factory=list)
    relevant_indicator_ids: list[str] = Field(default_factory=list)


class FormulaCalculationRequest(BaseModel):
    formula_id: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    input_origin: Literal["formula_example", "case_values", "user_modified"] = "user_modified"


class FormulaStep(BaseModel):
    label: str
    expression: str
    result: Any


class FormulaCalculationResponse(BaseModel):
    formula_id: str
    input_origin: str
    parameters: dict[str, Any]
    outputs: dict[str, Any]
    headline: str
    steps: list[FormulaStep]
    assumptions: list[str]
    limitations: list[str]


class ResearchCaseImportResponse(CasePackValidation):
    case_summary: ResearchCaseSummary | None = None


class MemoRequest(BaseModel):
    model_result: dict[str, Any]
    user_notes: str = ""
    analytical_question: str = "What does this model teach us about country risk?"
    final_analyst_judgement: str = "Use this model as a learning aid and validate conclusions with economic judgement."


class MemoResponse(BaseModel):
    markdown: str


class ModelApprovalCreateRequest(BaseModel):
    model_id: str
    intended_use: str
    requester: str
    justification: str
    evidence_uri: str | None = None


class ModelApprovalDecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    approver: str
    conditions: list[str] = Field(default_factory=list)
    expires_at: str | None = None


class LessonConcept(BaseModel):
    name: str
    plain_english: str


class Lesson(BaseModel):
    lesson_id: str
    title: str
    level: str
    module: str
    analytical_question: str
    default_dataset_id: str
    default_country: str
    target_variable: str | None = None
    candidate_variables: list[str]
    learning_objectives: list[str]
    concepts: list[LessonConcept]
    review_questions: list[str]
    required_outputs: list[str]
