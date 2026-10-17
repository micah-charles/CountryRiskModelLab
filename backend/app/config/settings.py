from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


APP_DIR = Path(__file__).resolve().parents[1]


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _list_env(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = "Risk Research Lab"
    app_version: str = "0.1.0"
    app_env: str = "development"
    log_level: str = "INFO"
    cors_allowed_origins: list[str] = None  # type: ignore[assignment]
    api_auth_required: bool = False
    auth_mode: str = "api_key"
    api_key: str | None = None
    jwt_hs256_secret: str | None = None
    jwt_jwks_url: str | None = None
    jwt_jwks_path: Path | None = None
    jwt_issuer: str | None = None
    jwt_audience: str | None = None
    audit_log_path: Path = None  # type: ignore[assignment]
    audit_sinks: list[str] = None  # type: ignore[assignment]
    audit_http_endpoint: str | None = None
    audit_http_token: str | None = None
    audit_http_fail_closed: bool = False
    model_approvals_path: Path = None  # type: ignore[assignment]
    max_upload_bytes: int = 10 * 1024 * 1024
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    rbac_enforced: bool = False
    dataset_registry_backend: str = "json"
    dataset_registry_sqlite_path: Path = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        object.__setattr__(self, "app_name", os.getenv("APP_NAME", self.app_name))
        object.__setattr__(self, "app_version", os.getenv("APP_VERSION", self.app_version))
        object.__setattr__(self, "app_env", os.getenv("APP_ENV", self.app_env))
        object.__setattr__(self, "log_level", os.getenv("LOG_LEVEL", self.log_level))
        object.__setattr__(
            self,
            "cors_allowed_origins",
            _list_env("CORS_ALLOWED_ORIGINS", ["http://localhost:5173", "http://127.0.0.1:5173"]),
        )
        auth_default = self.app_env.lower() in {"production", "prod"}
        object.__setattr__(self, "api_auth_required", _bool_env("API_AUTH_REQUIRED", auth_default))
        object.__setattr__(self, "auth_mode", os.getenv("AUTH_MODE", self.auth_mode).strip().lower())
        object.__setattr__(self, "api_key", os.getenv("API_KEY"))
        object.__setattr__(self, "jwt_hs256_secret", os.getenv("JWT_HS256_SECRET"))
        object.__setattr__(self, "jwt_jwks_url", os.getenv("JWT_JWKS_URL"))
        jwks_path = os.getenv("JWT_JWKS_PATH")
        object.__setattr__(self, "jwt_jwks_path", Path(jwks_path) if jwks_path else None)
        object.__setattr__(self, "jwt_issuer", os.getenv("JWT_ISSUER"))
        object.__setattr__(self, "jwt_audience", os.getenv("JWT_AUDIENCE"))
        object.__setattr__(
            self,
            "audit_log_path",
            Path(os.getenv("AUDIT_LOG_PATH", str(APP_DIR / "data_registry" / "audit" / "audit_events.jsonl"))),
        )
        object.__setattr__(self, "audit_sinks", _list_env("AUDIT_SINKS", ["local"]))
        object.__setattr__(self, "audit_http_endpoint", os.getenv("AUDIT_HTTP_ENDPOINT"))
        object.__setattr__(self, "audit_http_token", os.getenv("AUDIT_HTTP_TOKEN"))
        object.__setattr__(self, "audit_http_fail_closed", _bool_env("AUDIT_HTTP_FAIL_CLOSED", False))
        object.__setattr__(
            self,
            "model_approvals_path",
            Path(os.getenv("MODEL_APPROVALS_PATH", str(APP_DIR / "data_registry" / "model_approvals.json"))),
        )
        object.__setattr__(self, "max_upload_bytes", int(os.getenv("MAX_UPLOAD_BYTES", str(self.max_upload_bytes))))
        object.__setattr__(self, "rate_limit_enabled", _bool_env("RATE_LIMIT_ENABLED", self.rate_limit_enabled))
        object.__setattr__(self, "rate_limit_requests", int(os.getenv("RATE_LIMIT_REQUESTS", str(self.rate_limit_requests))))
        object.__setattr__(self, "rate_limit_window_seconds", int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", str(self.rate_limit_window_seconds))))
        object.__setattr__(self, "rbac_enforced", _bool_env("RBAC_ENFORCED", self.api_auth_required))
        object.__setattr__(
            self,
            "dataset_registry_backend",
            os.getenv("DATASET_REGISTRY_BACKEND", self.dataset_registry_backend).strip().lower(),
        )
        object.__setattr__(
            self,
            "dataset_registry_sqlite_path",
            Path(os.getenv("DATASET_REGISTRY_SQLITE_PATH", str(APP_DIR / "data_registry" / "registry.sqlite3"))),
        )


def get_settings() -> Settings:
    return Settings()
