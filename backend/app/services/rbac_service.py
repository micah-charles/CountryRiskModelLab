from __future__ import annotations

from fastapi import HTTPException, Request

from app.config.settings import get_settings


ROLE_ADMIN = "admin"


def roles_from_request(request: Request) -> set[str]:
    claims = getattr(request.state, "auth_claims", {}) or {}
    roles = claims.get("roles") or claims.get("groups") or []
    if isinstance(roles, str):
        roles = [roles]
    header_roles = request.headers.get("X-Actor-Roles", "")
    roles.extend([role.strip() for role in header_roles.split(",") if role.strip()])
    return {role for role in roles if role}


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

