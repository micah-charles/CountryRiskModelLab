from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from app.services.model_approval_service import has_active_model_approval


CATALOG_PATH = Path(__file__).resolve().parents[1] / "config" / "model_catalog.json"

DEFAULT_MODEL_BY_KIND = {
    "regression": "ols_country_risk_learning_v1",
    "forecast": "sarimax_country_risk_learning_v1",
    "var": "var_country_risk_learning_v1",
}


def load_model_catalog() -> dict[str, dict[str, Any]]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def resolve_model_policy(model_kind: str, model_id: str | None = None) -> tuple[str, dict[str, Any]]:
    catalog = load_model_catalog()
    resolved_id = model_id or DEFAULT_MODEL_BY_KIND[model_kind]
    if resolved_id not in catalog:
        raise ValueError(f"Model is not registered in the model catalog: {resolved_id}")
    return resolved_id, catalog[resolved_id]


def assert_model_use_allowed(model_kind: str, intended_use: str, model_id: str | None = None) -> dict[str, Any]:
    resolved_id, policy = resolve_model_policy(model_kind, model_id)
    allowed_uses = set(policy.get("allowed_uses", []))
    approved_by_exception = intended_use not in allowed_uses and has_active_model_approval(resolved_id, intended_use)
    if intended_use not in allowed_uses and not approved_by_exception:
        raise ValueError(
            f"Model {resolved_id} is not approved for intended use '{intended_use}'. "
            "Use a learning/uat purpose or complete formal model-risk approval."
        )
    return governance_metadata(resolved_id, policy, intended_use, approved_by_exception)


def governance_metadata(model_id: str, policy: dict[str, Any], intended_use: str, approved_by_exception: bool = False) -> dict[str, Any]:
    return {
        "model_id": model_id,
        "model_type": policy.get("model_type"),
        "status": policy.get("status"),
        "owner": policy.get("owner"),
        "validator": policy.get("validator"),
        "intended_use": intended_use,
        "approved_by_exception": approved_by_exception,
        "allowed_uses": policy.get("allowed_uses", []),
        "prohibited_uses": policy.get("prohibited_uses", []),
        "limitations": policy.get("limitations", []),
    }
