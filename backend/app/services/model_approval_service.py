from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import json
import uuid

from app.config.settings import get_settings


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _path() -> Path:
    return get_settings().model_approvals_path


def _read() -> list[dict[str, Any]]:
    path = _path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _write(items: list[dict[str, Any]]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def list_model_approvals() -> list[dict[str, Any]]:
    return _read()


def submit_model_approval(
    model_id: str,
    intended_use: str,
    requester: str,
    justification: str,
    evidence_uri: str | None = None,
) -> dict[str, Any]:
    approval = {
        "approval_id": str(uuid.uuid4()),
        "model_id": model_id,
        "intended_use": intended_use,
        "requester": requester,
        "justification": justification,
        "evidence_uri": evidence_uri,
        "status": "pending",
        "submitted_at": _now(),
        "decided_at": None,
        "approver": None,
        "conditions": [],
        "expires_at": None,
    }
    items = _read()
    items.append(approval)
    _write(items)
    return approval


def decide_model_approval(
    approval_id: str,
    decision: str,
    approver: str,
    conditions: list[str] | None = None,
    expires_at: str | None = None,
) -> dict[str, Any]:
    items = _read()
    for item in items:
        if item["approval_id"] == approval_id:
            item["status"] = decision
            item["approver"] = approver
            item["conditions"] = conditions or []
            item["expires_at"] = expires_at
            item["decided_at"] = _now()
            _write(items)
            return item
    raise ValueError(f"Model approval request not found: {approval_id}")


def has_active_model_approval(model_id: str, intended_use: str) -> bool:
    now = datetime.now(UTC)
    for item in _read():
        if item.get("model_id") != model_id or item.get("intended_use") != intended_use:
            continue
        if item.get("status") != "approved":
            continue
        expires_at = item.get("expires_at")
        if expires_at:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if expiry <= now:
                continue
        return True
    return False

