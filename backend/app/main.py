from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from app.models.schemas import (
    DatasetMetadata,
    DatasetPreview,
    ForecastRequest,
    ForecastResult,
    HealthResponse,
    ImfCountry,
    ImfCountryCatalog,
    ImfFetchRequest,
    ImfFetchResponse,
    ImfIndicator,
    ImfPrefetchAllRequest,
    ImfPrefetchedSessionRequest,
    FormulaCalculationRequest,
    FormulaCalculationResponse,
    FormulaDefinition,
    IndicatorDefinition,
    Lesson,
    MemoRequest,
    MemoResponse,
    ModelReadinessRequest,
    ModelReadinessResponse,
    ResearchCase,
    ResearchCaseImportResponse,
    ResearchCaseSummary,
    ModelApprovalCreateRequest,
    ModelApprovalDecisionRequest,
    RegressionRequest,
    RegressionResult,
    VarRequest,
    VarResult,
)
from app.config.settings import get_settings
from app.middleware import ApiKeyAuthMiddleware, RateLimitMiddleware, RequestContextMiddleware, actor_from_request
from app.services.audit_service import read_audit_events, verify_audit_chain, write_audit_event
from app.services.dataset_service import get_preview, list_all_datasets, list_sample_datasets, save_uploaded_dataset
from app.services.dataset_registry_service import load_dataset
from app.services.imf_service import (
    country_catalog,
    create_prefetched_test_session,
    fetch_imf_dataset,
    prefetch_all_countries_dataset,
    refresh_country_catalog,
    supported_countries,
)
from app.services.indicator_mapping_service import list_indicators
from app.services.indicator_registry_service import get_indicator_definition, list_indicator_definitions
from app.services.lesson_service import get_lesson, list_lessons
from app.services.memo_service import generate_memo
from app.services.metrics_service import metrics_text
from app.services.model_readiness_service import assess_model_readiness
from app.services.model_approval_service import decide_model_approval, list_model_approvals, submit_model_approval
from app.services.model_governance_service import load_model_catalog
from app.services.formula_engine import calculate_formula, get_formula_definition, list_formula_definitions
from app.services.analytical_support_service import AnalyticalSupportDefinition, get_analytical_support
from app.services.research_case_service import case_artifact_path, get_research_case, import_case_pack, list_research_cases
from app.services.rbac_service import require_roles
from app.services.readiness_service import readiness_report
from app.services.regression_service import run_regression
from app.services.forecasting_service import run_forecast
from app.services.var_service import run_var


settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(ApiKeyAuthMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def friendly_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


def ensure_model_ready(payload: RegressionRequest | ForecastRequest | VarRequest) -> None:
    if isinstance(payload, RegressionRequest):
        request = ModelReadinessRequest(
            dataset_id=payload.dataset_id,
            lab_type="regression",
            country=payload.country,
            date_start=payload.date_start,
            date_end=payload.date_end,
            dependent_variable=payload.dependent_variable,
            independent_variables=payload.independent_variables,
        )
    elif isinstance(payload, ForecastRequest):
        request = ModelReadinessRequest(
            dataset_id=payload.dataset_id,
            lab_type="forecast",
            country=payload.country,
            date_start=payload.date_start,
            date_end=payload.date_end,
            target_variable=payload.target_variable,
            model_type=payload.model_type,
            external_variables=payload.external_variables,
        )
    else:
        request = ModelReadinessRequest(
            dataset_id=payload.dataset_id,
            lab_type="var",
            country=payload.country,
            date_start=payload.date_start,
            date_end=payload.date_end,
            variables=payload.variables,
            lag_order=payload.lag_order,
        )
    result = assess_model_readiness(request)
    if not result.run_enabled:
        raise ValueError("Model readiness check failed: " + " ".join(result.blocking_issues))


def request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.get("/api/ready")
def ready() -> dict:
    return readiness_report()


@app.get("/api/version")
def version() -> dict:
    return {"name": settings.app_name, "version": settings.app_version, "environment": settings.app_env}


@app.get("/api/metrics")
def metrics() -> Response:
    return Response(metrics_text(), media_type="text/plain; version=0.0.4")


@app.get("/api/research-cases", response_model=list[ResearchCaseSummary])
def research_cases() -> list[ResearchCaseSummary]:
    return list_research_cases()


@app.get("/api/research-cases/{case_id}", response_model=ResearchCase)
def research_case(case_id: str) -> ResearchCase:
    try:
        return get_research_case(case_id)
    except Exception as exc:
        raise friendly_error(exc) from exc


@app.post("/api/research-cases/import", response_model=ResearchCaseImportResponse)
async def research_case_import(request: Request, file: UploadFile = File(...)) -> ResearchCaseImportResponse:
    require_roles(request, {"economist", "data_steward", "operator"}, "research_cases.import")
    try:
        max_upload_bytes = 100 * 1024 * 1024
        content = await file.read(max_upload_bytes + 1)
        if len(content) > max_upload_bytes:
            raise HTTPException(status_code=413, detail="Case Pack exceeds the 100 MiB upload limit.")
        result = await asyncio.to_thread(import_case_pack, content)
        if not result.valid:
            raise HTTPException(status_code=400, detail={"message": "Case Pack validation failed.", "validation": result.model_dump()})
        write_audit_event(
            "research_case.imported",
            actor_from_request(request),
            request_id(request),
            metadata={"case_id": result.case_id, "filename": file.filename, "warnings": result.warnings},
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        write_audit_event(
            "research_case.imported",
            actor_from_request(request),
            request_id(request),
            status="failed",
            metadata={"filename": file.filename, "error": str(exc)},
        )
        raise friendly_error(exc) from exc


@app.get("/api/research-cases/{case_id}/artifact/{artifact_path:path}")
def research_case_artifact(case_id: str, artifact_path: str) -> FileResponse:
    try:
        path = case_artifact_path(case_id, artifact_path)
        return FileResponse(path)
    except Exception as exc:
        raise friendly_error(exc) from exc


@app.get("/api/indicators", response_model=list[IndicatorDefinition])
def indicators() -> list[IndicatorDefinition]:
    return list_indicator_definitions()


@app.get("/api/indicators/{indicator_id}", response_model=IndicatorDefinition)
def indicator(indicator_id: str) -> IndicatorDefinition:
    try:
        return get_indicator_definition(indicator_id)
    except Exception as exc:
        raise friendly_error(exc) from exc


@app.get("/api/formulas", response_model=list[FormulaDefinition])
def formulas() -> list[FormulaDefinition]:
    return list_formula_definitions()


@app.get("/api/formulas/{formula_id}", response_model=FormulaDefinition)
def formula(formula_id: str) -> FormulaDefinition:
    try:
        return get_formula_definition(formula_id)
    except Exception as exc:
        raise friendly_error(exc) from exc


@app.get("/api/analytical-support/{support_type}/{reference_id}", response_model=AnalyticalSupportDefinition)
def analytical_support(support_type: str, reference_id: str) -> AnalyticalSupportDefinition:
    try:
        return get_analytical_support(support_type, reference_id)
    except Exception as exc:
        raise friendly_error(exc) from exc


@app.post("/api/formulas/calculate", response_model=FormulaCalculationResponse)
def formula_calculate(payload: FormulaCalculationRequest, request: Request) -> FormulaCalculationResponse:
    require_roles(request, {"viewer", "economist", "model_risk"}, "formulas.calculate")
    try:
        result = calculate_formula(payload)
        write_audit_event(
            "formula.calculated",
            actor_from_request(request),
            request_id(request),
            metadata={"formula_id": payload.formula_id, "input_origin": payload.input_origin},
        )
        return result
    except Exception as exc:
        write_audit_event(
            "formula.calculated",
            actor_from_request(request),
            request_id(request),
            status="failed",
            metadata={"formula_id": payload.formula_id, "error": str(exc)},
        )
        raise friendly_error(exc) from exc


@app.get("/api/datasets", response_model=list[DatasetMetadata])
def datasets(request: Request) -> list[DatasetMetadata]:
    require_roles(request, {"viewer", "economist", "data_steward", "auditor", "operator"}, "datasets.list")
    return list_all_datasets()


@app.get("/api/datasets/samples", response_model=list[DatasetMetadata])
def samples() -> list[DatasetMetadata]:
    return list_sample_datasets()


@app.get("/api/datasets/{dataset_id}/preview", response_model=DatasetPreview)
def dataset_preview(dataset_id: str, limit: int = Query(20, ge=1)) -> DatasetPreview:
    try:
        return get_preview(dataset_id, limit=limit)
    except Exception as exc:
        raise friendly_error(exc) from exc


@app.get("/api/datasets/{dataset_id}/csv")
def dataset_csv(dataset_id: str, request: Request) -> FileResponse:
    require_roles(request, {"economist", "data_steward", "auditor"}, "datasets.download_csv")
    try:
        metadata, _ = load_dataset(dataset_id)
        path = Path(metadata.file_path)
        write_audit_event(
            "dataset.csv_downloaded",
            actor_from_request(request),
            request_id(request),
            metadata={"dataset_id": dataset_id, "source_type": metadata.source_type},
        )
        return FileResponse(path, media_type="text/csv", filename=f"{dataset_id}.csv")
    except Exception as exc:
        raise friendly_error(exc) from exc


@app.get("/api/datasets/samples/{dataset_id}/preview", response_model=DatasetPreview)
def sample_dataset_preview(dataset_id: str, limit: int = Query(20, ge=1)) -> DatasetPreview:
    try:
        return get_preview(dataset_id, limit=limit)
    except Exception as exc:
        raise friendly_error(exc) from exc


@app.post("/api/datasets/upload", response_model=DatasetPreview)
async def upload_dataset(request: Request, file: UploadFile = File(...)) -> DatasetPreview:
    require_roles(request, {"economist", "data_steward"}, "datasets.upload")
    try:
        preview = await save_uploaded_dataset(file)
        write_audit_event(
            "dataset.uploaded",
            actor_from_request(request),
            request_id(request),
            metadata={"dataset_id": preview.dataset_id, "filename": file.filename},
        )
        return preview
    except Exception as exc:
        write_audit_event(
            "dataset.uploaded",
            actor_from_request(request),
            request_id(request),
            status="failed",
            metadata={"filename": file.filename, "error": str(exc)},
        )
        raise friendly_error(exc) from exc


@app.get("/api/imf/countries", response_model=list[ImfCountry])
def imf_countries() -> list[ImfCountry]:
    return supported_countries()


@app.get("/api/imf/country-catalog", response_model=ImfCountryCatalog)
def imf_country_catalog() -> ImfCountryCatalog:
    return country_catalog()


@app.post("/api/imf/countries/refresh", response_model=ImfCountryCatalog)
def imf_countries_refresh(request: Request) -> ImfCountryCatalog:
    require_roles(request, {"economist", "data_steward", "operator"}, "imf.countries.refresh")
    try:
        catalog = refresh_country_catalog()
        write_audit_event(
            "imf.country_catalog_refreshed",
            actor_from_request(request),
            request_id(request),
            metadata={"country_count": catalog.country_count, "last_modified_utc": catalog.last_modified_utc},
        )
        return catalog
    except Exception as exc:
        write_audit_event(
            "imf.country_catalog_refreshed",
            actor_from_request(request),
            request_id(request),
            status="failed",
            metadata={"error": str(exc)},
        )
        raise friendly_error(exc) from exc


@app.get("/api/imf/indicators", response_model=list[ImfIndicator])
def imf_indicators() -> list[ImfIndicator]:
    return list_indicators()


@app.post("/api/imf/fetch", response_model=ImfFetchResponse)
async def imf_fetch(payload: ImfFetchRequest, request: Request) -> ImfFetchResponse:
    require_roles(request, {"economist", "data_steward"}, "imf.fetch")
    try:
        response = await fetch_imf_dataset(payload)
        write_audit_event(
            "imf.dataset_fetched",
            actor_from_request(request),
            request_id(request),
            metadata={
                "dataset_id": response.dataset.dataset_id,
                "countries": payload.countries,
                "indicators": payload.indicators,
                "date_range": f"{payload.start_year}-{payload.end_year}",
            },
        )
        return response
    except Exception as exc:
        write_audit_event(
            "imf.dataset_fetched",
            actor_from_request(request),
            request_id(request),
            status="failed",
            metadata={"countries": payload.countries, "indicators": payload.indicators, "error": str(exc)},
        )
        raise friendly_error(exc) from exc


@app.post("/api/imf/prefetch-all-countries", response_model=ImfFetchResponse)
async def imf_prefetch_all_countries(payload: ImfPrefetchAllRequest, request: Request) -> ImfFetchResponse:
    require_roles(request, {"economist", "data_steward", "operator"}, "imf.prefetch_all_countries")
    try:
        response = await prefetch_all_countries_dataset(payload)
        write_audit_event(
            "imf.all_countries_prefetched",
            actor_from_request(request),
            request_id(request),
            metadata={
                "dataset_id": response.dataset.dataset_id,
                "country_count": len(response.dataset.countries),
                "indicators": payload.indicators,
                "date_range": f"{payload.start_year}-{payload.end_year}",
            },
        )
        return response
    except Exception as exc:
        write_audit_event(
            "imf.all_countries_prefetched",
            actor_from_request(request),
            request_id(request),
            status="failed",
            metadata={"indicators": payload.indicators, "error": str(exc)},
        )
        raise friendly_error(exc) from exc


@app.post("/api/imf/prefetched-session", response_model=ImfFetchResponse)
def imf_prefetched_session(payload: ImfPrefetchedSessionRequest, request: Request) -> ImfFetchResponse:
    require_roles(request, {"economist", "data_steward"}, "imf.prefetched_session")
    try:
        response = create_prefetched_test_session(payload)
        write_audit_event(
            "imf.prefetched_session_created",
            actor_from_request(request),
            request_id(request),
            metadata={
                "dataset_id": response.dataset.dataset_id,
                "source_dataset_id": payload.source_dataset_id,
                "countries": payload.countries,
                "indicators": payload.indicators,
            },
        )
        return response
    except Exception as exc:
        write_audit_event(
            "imf.prefetched_session_created",
            actor_from_request(request),
            request_id(request),
            status="failed",
            metadata={"source_dataset_id": payload.source_dataset_id, "error": str(exc)},
        )
        raise friendly_error(exc) from exc


@app.post("/api/models/regression/run", response_model=RegressionResult)
def regression(payload: RegressionRequest, request: Request) -> RegressionResult:
    require_roles(request, {"economist", "model_risk"}, "models.regression.run")
    try:
        ensure_model_ready(payload)
        result = run_regression(payload)
        write_audit_event(
            "model.regression_run",
            actor_from_request(request),
            request_id(request),
            metadata={
                "dataset_id": payload.dataset_id,
                "country": payload.country,
                "dependent_variable": payload.dependent_variable,
                "independent_variables": payload.independent_variables,
                "n_observations": result.n_observations,
                "model_governance": result.model_governance,
            },
        )
        return result
    except Exception as exc:
        write_audit_event(
            "model.regression_run",
            actor_from_request(request),
            request_id(request),
            status="failed",
            metadata={"dataset_id": payload.dataset_id, "error": str(exc)},
        )
        raise friendly_error(exc) from exc


@app.post("/api/models/readiness", response_model=ModelReadinessResponse)
def model_readiness(payload: ModelReadinessRequest, request: Request) -> ModelReadinessResponse:
    require_roles(request, {"economist", "model_risk"}, "models.readiness")
    try:
        result = assess_model_readiness(payload)
        write_audit_event(
            "model.readiness_checked",
            actor_from_request(request),
            request_id(request),
            status="success" if result.run_enabled else "blocked",
            metadata={
                "dataset_id": payload.dataset_id,
                "lab_type": payload.lab_type,
                "country": payload.country,
                "status": result.status,
                "complete_case_count": result.complete_case_count,
                "required_observations": result.required_observations,
                "missing_columns": result.missing_columns,
            },
        )
        return result
    except Exception as exc:
        write_audit_event(
            "model.readiness_checked",
            actor_from_request(request),
            request_id(request),
            status="failed",
            metadata={"dataset_id": payload.dataset_id, "lab_type": payload.lab_type, "error": str(exc)},
        )
        raise friendly_error(exc) from exc


@app.post("/api/models/forecast/run", response_model=ForecastResult)
def forecast(payload: ForecastRequest, request: Request) -> ForecastResult:
    require_roles(request, {"economist", "model_risk"}, "models.forecast.run")
    try:
        ensure_model_ready(payload)
        result = run_forecast(payload)
        write_audit_event(
            "model.forecast_run",
            actor_from_request(request),
            request_id(request),
            metadata={
                "dataset_id": payload.dataset_id,
                "country": payload.country,
                "target_variable": payload.target_variable,
                "model_type": payload.model_type,
                "forecast_horizon": payload.forecast_horizon,
                "model_governance": result.model_governance,
            },
        )
        return result
    except Exception as exc:
        write_audit_event(
            "model.forecast_run",
            actor_from_request(request),
            request_id(request),
            status="failed",
            metadata={"dataset_id": payload.dataset_id, "model_type": payload.model_type, "error": str(exc)},
        )
        raise friendly_error(exc) from exc


@app.post("/api/models/var/run", response_model=VarResult)
def var_model(payload: VarRequest, request: Request) -> VarResult:
    require_roles(request, {"economist", "model_risk"}, "models.var.run")
    try:
        ensure_model_ready(payload)
        result = run_var(payload)
        write_audit_event(
            "model.var_run",
            actor_from_request(request),
            request_id(request),
            metadata={
                "dataset_id": payload.dataset_id,
                "country": payload.country,
                "variables": payload.variables,
                "lag_order": payload.lag_order,
                "model_governance": result.model_governance,
            },
        )
        return result
    except Exception as exc:
        write_audit_event(
            "model.var_run",
            actor_from_request(request),
            request_id(request),
            status="failed",
            metadata={"dataset_id": payload.dataset_id, "error": str(exc)},
        )
        raise friendly_error(exc) from exc


@app.post("/api/memo/generate", response_model=MemoResponse)
def memo(payload: MemoRequest, request: Request) -> MemoResponse:
    require_roles(request, {"economist", "model_risk"}, "memo.generate")
    try:
        response = generate_memo(payload)
        write_audit_event(
            "memo.generated",
            actor_from_request(request),
            request_id(request),
            metadata={
                "model_type": payload.model_result.get("model_type"),
                "analytical_question": payload.analytical_question,
            },
        )
        return response
    except Exception as exc:
        write_audit_event(
            "memo.generated",
            actor_from_request(request),
            request_id(request),
            status="failed",
            metadata={"error": str(exc)},
        )
        raise friendly_error(exc) from exc


@app.get("/api/audit/events")
def audit_events(request: Request, limit: int = 100) -> list[dict]:
    require_roles(request, {"auditor", "operator"}, "audit.events")
    return read_audit_events(limit)


@app.get("/api/audit/verify")
def audit_verify(request: Request) -> dict:
    require_roles(request, {"auditor", "operator"}, "audit.verify")
    return verify_audit_chain()


@app.get("/api/model-governance/catalog")
def model_governance_catalog(request: Request) -> dict:
    require_roles(request, {"economist", "model_risk", "auditor"}, "model_governance.catalog")
    return load_model_catalog()


@app.get("/api/model-governance/approvals")
def model_governance_approvals(request: Request) -> list[dict]:
    require_roles(request, {"model_risk", "auditor"}, "model_governance.approvals.list")
    return list_model_approvals()


@app.post("/api/model-governance/approvals")
def model_governance_submit_approval(payload: ModelApprovalCreateRequest, request: Request) -> dict:
    require_roles(request, {"economist", "model_risk"}, "model_governance.approvals.submit")
    approval = submit_model_approval(
        payload.model_id,
        payload.intended_use,
        payload.requester,
        payload.justification,
        payload.evidence_uri,
    )
    write_audit_event(
        "model.approval_submitted",
        actor_from_request(request),
        request_id(request),
        metadata={"approval_id": approval["approval_id"], "model_id": payload.model_id, "intended_use": payload.intended_use},
    )
    return approval


@app.post("/api/model-governance/approvals/{approval_id}/decision")
def model_governance_decide_approval(approval_id: str, payload: ModelApprovalDecisionRequest, request: Request) -> dict:
    require_roles(request, {"model_risk"}, "model_governance.approvals.decide")
    approval = decide_model_approval(
        approval_id,
        payload.decision,
        payload.approver,
        payload.conditions,
        payload.expires_at,
    )
    write_audit_event(
        "model.approval_decided",
        actor_from_request(request),
        request_id(request),
        metadata={
            "approval_id": approval_id,
            "model_id": approval["model_id"],
            "intended_use": approval["intended_use"],
            "decision": payload.decision,
        },
    )
    return approval


@app.get("/api/lessons", response_model=list[Lesson])
def lessons() -> list[Lesson]:
    return list_lessons()


@app.get("/api/lessons/{lesson_id}", response_model=Lesson)
def lesson(lesson_id: str) -> Lesson:
    try:
        return get_lesson(lesson_id)
    except Exception as exc:
        raise friendly_error(exc) from exc
