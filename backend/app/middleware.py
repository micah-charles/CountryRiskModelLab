from __future__ import annotations

from time import perf_counter
from collections import defaultdict, deque
import logging
import uuid

from fastapi import HTTPException, Request
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.settings import get_settings
from app.services.auth_service import AuthError, validate_request_auth
from app.services.metrics_service import record_request


logger = logging.getLogger("country_risk_model_lab")
_rate_limit_buckets = defaultdict(deque)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        start = perf_counter()
        response = await call_next(request)
        duration_seconds = perf_counter() - start
        duration_ms = round(duration_seconds * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Cache-Control"] = "no-store"
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        record_request(request.method, request.url.path, response.status_code, duration_seconds)
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return await call_next(request)

        key = request.headers.get("X-Actor-ID") or request.headers.get("X-User-ID")
        if not key:
            key = request.client.host if request.client else "unknown"
        now = perf_counter()
        bucket = _rate_limit_buckets[key]
        while bucket and now - bucket[0] > settings.rate_limit_window_seconds:
            bucket.popleft()
        if len(bucket) >= settings.rate_limit_requests:
            return JSONResponse(
                {"detail": "Rate limit exceeded. Please retry later."},
                status_code=429,
                headers={"Retry-After": str(settings.rate_limit_window_seconds)},
            )
        bucket.append(now)
        return await call_next(request)


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        public_paths = {
            "/api/health",
            "/api/ready",
            "/api/version",
            "/api/metrics",
            "/docs",
            "/openapi.json",
            "/redoc",
        }
        if settings.api_auth_required and request.url.path not in public_paths:
            try:
                claims = validate_request_auth({key.lower(): value for key, value in request.headers.items()}, settings)
                request.state.actor = claims.get("sub") or claims.get("preferred_username") or claims.get("email") or "authenticated"
                request.state.auth_claims = claims
            except AuthError as exc:
                return JSONResponse(
                    {"detail": str(exc)},
                    status_code=401,
                )
        return await call_next(request)


def actor_from_request(request: Request) -> str:
    if getattr(request.state, "actor", None):
        return request.state.actor
    return request.headers.get("X-Actor-ID") or request.headers.get("X-User-ID") or "anonymous"


def require_api_key(request: Request) -> None:
    settings = get_settings()
    if not settings.api_auth_required:
        return
    supplied = request.headers.get("X-API-Key")
    if not settings.api_key or supplied != settings.api_key:
        raise HTTPException(status_code=401, detail="Authentication is required for this environment.")
