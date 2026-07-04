from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import hashlib
import json
import urllib.request
import uuid

from app.config.settings import get_settings


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canonical_event(event: dict[str, Any]) -> str:
    payload = {key: value for key, value in event.items() if key != "event_hash"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _hash_event(event: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_event(event).encode("utf-8")).hexdigest()


def _last_event_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return None
    return json.loads(lines[-1]).get("event_hash")


def write_audit_event(
    event_type: str,
    actor: str,
    request_id: str | None = None,
    status: str = "succeeded",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    path: Path = settings.audit_log_path
    path.parent.mkdir(parents=True, exist_ok=True)
    previous_hash = _last_event_hash(path)
    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "actor": actor,
        "request_id": request_id,
        "status": status,
        "occurred_at": now_utc(),
        "previous_hash": previous_hash,
        "metadata": metadata or {},
    }
    event["event_hash"] = _hash_event(event)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    _forward_audit_event(event, settings)
    return event


def _forward_audit_event(event: dict[str, Any], settings) -> None:
    if "http" not in settings.audit_sinks:
        return
    if not settings.audit_http_endpoint:
        if settings.audit_http_fail_closed:
            raise RuntimeError("AUDIT_HTTP_ENDPOINT is required when HTTP audit sink is fail-closed.")
        return
    payload = json.dumps(event, sort_keys=True).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if settings.audit_http_token:
        headers["Authorization"] = f"Bearer {settings.audit_http_token}"
    request = urllib.request.Request(settings.audit_http_endpoint, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            if response.status >= 400:
                raise RuntimeError(f"HTTP audit sink returned status {response.status}")
    except Exception:
        if settings.audit_http_fail_closed:
            raise


def read_audit_events(limit: int = 100) -> list[dict[str, Any]]:
    path = get_settings().audit_log_path
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines[-limit:]]


def verify_audit_chain() -> dict[str, Any]:
    path = get_settings().audit_log_path
    if not path.exists():
        return {"status": "ok", "events_checked": 0, "message": "No audit events found."}

    previous_hash = None
    events_checked = 0
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        event = json.loads(line)
        expected_hash = _hash_event(event)
        if event.get("event_hash") != expected_hash:
            return {
                "status": "fail",
                "events_checked": events_checked,
                "line_number": line_number,
                "message": "Audit event hash mismatch.",
            }
        if event.get("previous_hash") != previous_hash:
            return {
                "status": "fail",
                "events_checked": events_checked,
                "line_number": line_number,
                "message": "Audit previous_hash chain mismatch.",
            }
        previous_hash = event["event_hash"]
        events_checked += 1

    return {"status": "ok", "events_checked": events_checked, "message": "Audit hash chain is valid."}
