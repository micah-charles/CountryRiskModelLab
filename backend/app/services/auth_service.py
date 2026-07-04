from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import base64
import hashlib
import hmac
import json

import jwt
from jwt import PyJWKClient

from app.config.settings import Settings


class AuthError(ValueError):
    pass


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _json_part(value: str) -> dict[str, Any]:
    try:
        return json.loads(_b64url_decode(value))
    except Exception as exc:
        raise AuthError("Bearer token is not a valid JWT.") from exc


def validate_api_key(supplied: str | None, settings: Settings) -> dict[str, Any]:
    if settings.api_key and supplied == settings.api_key:
        return {"sub": "api-key-client", "auth_mode": "api_key"}
    raise AuthError("Authentication is required for this environment.")


def validate_hs256_jwt(token: str | None, settings: Settings) -> dict[str, Any]:
    if not token:
        raise AuthError("Bearer token is required.")
    if not settings.jwt_hs256_secret:
        raise AuthError("JWT validation is not configured.")

    parts = token.split(".")
    if len(parts) != 3:
        raise AuthError("Bearer token is not a valid JWT.")

    header = _json_part(parts[0])
    payload = _json_part(parts[1])
    if header.get("alg") != "HS256":
        raise AuthError("Only HS256 JWT validation is configured for this deployment mode.")

    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    expected = _b64url_encode(hmac.new(settings.jwt_hs256_secret.encode("utf-8"), signing_input, hashlib.sha256).digest())
    if not hmac.compare_digest(parts[2], expected):
        raise AuthError("Bearer token signature is invalid.")

    now = int(datetime.now(UTC).timestamp())
    if "exp" in payload and int(payload["exp"]) <= now:
        raise AuthError("Bearer token has expired.")
    if "nbf" in payload and int(payload["nbf"]) > now:
        raise AuthError("Bearer token is not valid yet.")
    if settings.jwt_issuer and payload.get("iss") != settings.jwt_issuer:
        raise AuthError("Bearer token issuer is not trusted.")
    if settings.jwt_audience:
        audience = payload.get("aud")
        if isinstance(audience, str):
            valid_audience = audience == settings.jwt_audience
        else:
            valid_audience = settings.jwt_audience in (audience or [])
        if not valid_audience:
            raise AuthError("Bearer token audience is not allowed.")

    payload["auth_mode"] = "jwt"
    return payload


def _jwt_decode_options(settings: Settings) -> dict[str, Any]:
    options: dict[str, Any] = {"require": ["exp"]}
    if settings.jwt_issuer:
        options["require"].append("iss")
    if settings.jwt_audience:
        options["require"].append("aud")
    return options


def validate_jwks_jwt(token: str | None, settings: Settings) -> dict[str, Any]:
    if not token:
        raise AuthError("Bearer token is required.")
    try:
        if settings.jwt_jwks_path:
            jwks = json.loads(settings.jwt_jwks_path.read_text(encoding="utf-8"))
            header = jwt.get_unverified_header(token)
            key_payload = next((item for item in jwks.get("keys", []) if item.get("kid") == header.get("kid")), None)
            if not key_payload:
                raise AuthError("Bearer token key ID is not in trusted JWKS.")
            signing_key = jwt.PyJWK.from_dict(key_payload).key
        elif settings.jwt_jwks_url:
            signing_key = PyJWKClient(settings.jwt_jwks_url).get_signing_key_from_jwt(token).key
        else:
            raise AuthError("JWKS validation is not configured.")

        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options=_jwt_decode_options(settings),
        )
    except AuthError:
        raise
    except Exception as exc:
        raise AuthError("Bearer token failed JWKS validation.") from exc

    payload["auth_mode"] = "oidc_jwks"
    return payload


def validate_request_auth(headers: dict[str, str], settings: Settings) -> dict[str, Any]:
    mode = settings.auth_mode
    supplied_api_key = headers.get("x-api-key")
    authorization = headers.get("authorization", "")
    bearer = authorization.removeprefix("Bearer ").strip() if authorization.startswith("Bearer ") else None

    if mode == "api_key":
        return validate_api_key(supplied_api_key, settings)
    if mode == "jwt":
        return validate_hs256_jwt(bearer, settings)
    if mode == "oidc_jwks":
        return validate_jwks_jwt(bearer, settings)
    if mode == "api_key_or_jwt":
        try:
            if settings.jwt_jwks_path or settings.jwt_jwks_url:
                return validate_jwks_jwt(bearer, settings)
            return validate_hs256_jwt(bearer, settings)
        except AuthError:
            return validate_api_key(supplied_api_key, settings)
    raise AuthError(f"Unsupported AUTH_MODE: {mode}")


def make_hs256_jwt(payload: dict[str, Any], secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    encoded_payload = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = _b64url_encode(hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest())
    return f"{encoded_header}.{encoded_payload}.{signature}"
