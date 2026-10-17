from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request

from app.config.settings import get_settings


ROLE_ADMIN = "admin"


def roles_from_request(request: Request) -> set[str]:
    settings = get_settings()
    claims = getattr(request.state, "auth_claims", {}) or {}
    role_claim: Any = claims.get("roles")
    if not role_claim:
        role_claim = claims.get("groups")

    if isinstance(role_claim, str):
        role_values = [role_claim]
    elif isinstance(role_claim, list) and all(isinstance(role, str) for role in role_claim):
        # Work on a copy; never mutate claims provided by the auth middleware.
        role_values = list(role_claim)
    else:
        # Malformed or nested role claims grant no roles.
        role_values = []

    roles = {role.strip() for role in role_values if role.strip()}

    # Header role simulation is only for unauthenticated local development and
    # test workflows. Once API authentication is enabled, roles must come from
    # the validated token claims; an API key authenticates but grants no role.
    local_unauthenticated_mode = (
        not settings.api_auth_required
        and settings.app_env.strip().lower() in {"development", "dev", "test", "local"}
    )
    if local_unauthenticated_mode:
        header_roles = request.headers.get("X-Actor-Roles", "")
        roles.update(role.strip() for role in header_roles.split(",") if role.strip())

    return roles


def require_roles(request: Request, allowed_roles: set[str], action: str) -> None:
    settings = get_settings()
    if not settings.rbac_enforced:
        return
    roles = roles_from_request(request)
    if ROLE_ADMIN in roles or roles.intersection(allowed_roles):
        return
    raise HTTPException(
        status_code=403,
        detail=f"Role not permitted for action '{action}'. Required roles: {', '.join(sorted(allowed_roles))}.",
    )

