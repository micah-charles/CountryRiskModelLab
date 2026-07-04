from __future__ import annotations

from pathlib import Path

from app.config.settings import get_settings
from app.services.audit_service import verify_audit_chain
from app.services.dataset_registry_service import list_datasets
from app.services.imf_service import country_catalog
from app.services.indicator_mapping_service import load_indicator_mapping
from app.services.model_governance_service import load_model_catalog


def readiness_report() -> dict:
    settings = get_settings()
    checks: dict[str, dict] = {}

    datasets = list_datasets("sample")
    sample_ids = {dataset.dataset_id for dataset in datasets}
    checks["sample_datasets"] = {
        "status": "ok" if {"sample_country_risk_quarterly", "sample_country_risk_monthly"}.issubset(sample_ids) else "fail",
        "details": sorted(sample_ids),
    }

    missing_files = [dataset.dataset_id for dataset in datasets if not Path(dataset.file_path).exists()]
    checks["dataset_files"] = {
        "status": "ok" if not missing_files else "fail",
        "details": missing_files,
    }

    indicators = load_indicator_mapping()
    checks["imf_indicator_mapping"] = {
        "status": "ok" if {"NGDP_RPCH", "PCPIPCH", "GGXWDG_NGDP", "BCA_NGDPD"}.issubset(indicators) else "fail",
        "details": sorted(indicators),
    }

    imf_countries = country_catalog()
    checks["imf_country_catalog"] = {
        "status": "ok" if imf_countries.country_count >= 50 and bool(imf_countries.last_modified_utc) else "fail",
        "details": {
            "country_count": imf_countries.country_count,
            "last_modified_utc": imf_countries.last_modified_utc,
            "source_url": imf_countries.source_url,
        },
    }

    checks["audit_log_writable"] = {
        "status": "ok" if settings.audit_log_path.parent.exists() or settings.audit_log_path.parent.parent.exists() else "fail",
        "details": str(settings.audit_log_path),
    }

    checks["audit_sinks"] = {
        "status": "ok" if "http" not in settings.audit_sinks or bool(settings.audit_http_endpoint) else "fail",
        "details": {"sinks": settings.audit_sinks, "http_configured": bool(settings.audit_http_endpoint)},
    }

    audit_chain = verify_audit_chain()
    checks["audit_hash_chain"] = {
        "status": "ok" if audit_chain["status"] == "ok" else "fail",
        "details": audit_chain,
    }

    catalog = load_model_catalog()
    required_models = {
        "ols_country_risk_learning_v1",
        "sarimax_country_risk_learning_v1",
        "var_country_risk_learning_v1",
    }
    checks["model_governance_catalog"] = {
        "status": "ok" if required_models.issubset(catalog) else "fail",
        "details": sorted(catalog),
    }

    auth_ok = True
    if settings.api_auth_required:
        if settings.auth_mode == "api_key":
            auth_ok = bool(settings.api_key)
        elif settings.auth_mode == "jwt":
            auth_ok = bool(settings.jwt_hs256_secret)
        elif settings.auth_mode == "oidc_jwks":
            auth_ok = bool(settings.jwt_jwks_url or settings.jwt_jwks_path)
        elif settings.auth_mode == "api_key_or_jwt":
            auth_ok = bool(settings.api_key or settings.jwt_hs256_secret or settings.jwt_jwks_url or settings.jwt_jwks_path)
        else:
            auth_ok = False
    checks["auth_configuration"] = {
        "status": "ok" if auth_ok else "fail",
        "details": {"required": settings.api_auth_required, "mode": settings.auth_mode, "rbac_enforced": settings.rbac_enforced},
    }

    checks["model_approval_store"] = {
        "status": "ok" if settings.model_approvals_path.parent.exists() or settings.model_approvals_path.parent.parent.exists() else "fail",
        "details": str(settings.model_approvals_path),
    }

    checks["rate_limit_configuration"] = {
        "status": "ok" if settings.rate_limit_requests > 0 and settings.rate_limit_window_seconds > 0 else "fail",
        "details": {
            "enabled": settings.rate_limit_enabled,
            "requests": settings.rate_limit_requests,
            "window_seconds": settings.rate_limit_window_seconds,
        },
    }

    overall = "ok" if all(check["status"] == "ok" for check in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}
