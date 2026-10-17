import json
import urllib.request

from fastapi.testclient import TestClient
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from app.main import app
from app.services.audit_service import verify_audit_chain, write_audit_event
from app.services.auth_service import make_hs256_jwt
from app.services.model_governance_service import assert_model_use_allowed
from app.services.rbac_service import roles_from_request
from starlette.requests import Request


def test_security_headers_and_request_id_are_set():
    client = TestClient(app)
    response = client.get("/api/health", headers={"X-Request-ID": "test-request-001"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-001"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"


def test_readiness_endpoint_reports_required_dependencies():
    client = TestClient(app)
    response = client.get("/api/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["checks"]["sample_datasets"]["status"] == "ok"
    assert payload["checks"]["imf_indicator_mapping"]["status"] == "ok"


def test_model_run_writes_audit_event(monkeypatch, tmp_path):
    audit_path = tmp_path / "audit_events.jsonl"
    monkeypatch.setenv("AUDIT_LOG_PATH", str(audit_path))
    client = TestClient(app)
    response = client.post(
        "/api/models/regression/run",
        headers={"X-Actor-ID": "test-economist"},
        json={
            "dataset_id": "sample_country_risk_quarterly",
            "country": "Indonesia",
            "dependent_variable": "bond_yield_10y",
            "independent_variables": ["inflation_yoy", "policy_rate"],
        },
    )
    assert response.status_code == 200
    events = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert events[-1]["event_type"] == "model.regression_run"
    assert events[-1]["actor"] == "test-economist"
    assert events[-1]["metadata"]["dataset_id"] == "sample_country_risk_quarterly"
    assert events[-1]["event_hash"]
    assert "previous_hash" in events[-1]


def test_api_key_auth_can_be_required(monkeypatch):
    monkeypatch.setenv("API_AUTH_REQUIRED", "true")
    monkeypatch.setenv("RBAC_ENFORCED", "false")
    monkeypatch.setenv("API_KEY", "expected-key")
    client = TestClient(app)

    blocked = client.get("/api/datasets")
    assert blocked.status_code == 401

    allowed = client.get("/api/datasets", headers={"X-API-Key": "expected-key"})
    assert allowed.status_code == 200


def test_jwt_auth_mode_accepts_valid_enterprise_token(monkeypatch):
    monkeypatch.setenv("API_AUTH_REQUIRED", "true")
    monkeypatch.setenv("RBAC_ENFORCED", "false")
    monkeypatch.setenv("AUTH_MODE", "jwt")
    monkeypatch.setenv("JWT_HS256_SECRET", "test-shared-secret")
    monkeypatch.setenv("JWT_ISSUER", "https://issuer.example.test")
    monkeypatch.setenv("JWT_AUDIENCE", "country-risk-model-lab")
    token = make_hs256_jwt(
        {
            "sub": "economist-001",
            "iss": "https://issuer.example.test",
            "aud": "country-risk-model-lab",
            "exp": 4102444800,
        },
        "test-shared-secret",
    )
    client = TestClient(app)
    response = client.get("/api/datasets", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_jwt_auth_mode_rejects_wrong_audience(monkeypatch):
    monkeypatch.setenv("API_AUTH_REQUIRED", "true")
    monkeypatch.setenv("RBAC_ENFORCED", "false")
    monkeypatch.setenv("AUTH_MODE", "jwt")
    monkeypatch.setenv("JWT_HS256_SECRET", "test-shared-secret")
    monkeypatch.setenv("JWT_AUDIENCE", "country-risk-model-lab")
    token = make_hs256_jwt({"sub": "economist-001", "aud": "other-app", "exp": 4102444800}, "test-shared-secret")
    client = TestClient(app)
    response = client.get("/api/datasets", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_oidc_jwks_auth_mode_accepts_rs256_token(monkeypatch, tmp_path):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk["kid"] = "test-rsa-key"
    jwks_path = tmp_path / "jwks.json"
    jwks_path.write_text(json.dumps({"keys": [public_jwk]}), encoding="utf-8")
    token = jwt.encode(
        {
            "sub": "economist-rs256",
            "roles": ["economist"],
            "iss": "https://issuer.example.test",
            "aud": "country-risk-model-lab",
            "exp": 4102444800,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-rsa-key"},
    )

    monkeypatch.setenv("API_AUTH_REQUIRED", "true")
    monkeypatch.setenv("RBAC_ENFORCED", "false")
    monkeypatch.setenv("AUTH_MODE", "oidc_jwks")
    monkeypatch.setenv("JWT_JWKS_PATH", str(jwks_path))
    monkeypatch.setenv("JWT_ISSUER", "https://issuer.example.test")
    monkeypatch.setenv("JWT_AUDIENCE", "country-risk-model-lab")
    client = TestClient(app)
    response = client.get("/api/datasets", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_audit_chain_detects_tampering(monkeypatch, tmp_path):
    audit_path = tmp_path / "audit_events.jsonl"
    monkeypatch.setenv("AUDIT_LOG_PATH", str(audit_path))
    write_audit_event("test.first", "tester")
    write_audit_event("test.second", "tester")
    assert verify_audit_chain()["status"] == "ok"

    lines = audit_path.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[0])
    tampered["metadata"] = {"tampered": True}
    lines[0] = json.dumps(tampered, sort_keys=True)
    audit_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert verify_audit_chain()["status"] == "fail"


def test_audit_http_sink_forwards_event(monkeypatch, tmp_path):
    audit_path = tmp_path / "audit_events.jsonl"
    captured = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("AUDIT_LOG_PATH", str(audit_path))
    monkeypatch.setenv("AUDIT_SINKS", "local,http")
    monkeypatch.setenv("AUDIT_HTTP_ENDPOINT", "https://siem.example.test/audit")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    event = write_audit_event("test.forwarded", "tester")
    assert captured["url"] == "https://siem.example.test/audit"
    assert captured["body"]["event_id"] == event["event_id"]
    assert captured["body"]["event_hash"] == event["event_hash"]
    assert captured["timeout"] == 3


def test_model_governance_blocks_unapproved_intended_use():
    try:
        assert_model_use_allowed("regression", "trading")
    except ValueError as exc:
        assert "not approved" in str(exc)
    else:
        raise AssertionError("Trading use should be blocked for learning model.")


def test_model_approval_can_authorize_exception_use(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("API_AUTH_REQUIRED", "false")
    monkeypatch.setenv("RBAC_ENFORCED", "true")
    monkeypatch.setenv("MODEL_APPROVALS_PATH", str(tmp_path / "model_approvals.json"))
    monkeypatch.setenv("AUDIT_LOG_PATH", str(tmp_path / "audit_events.jsonl"))
    client = TestClient(app)
    submitted = client.post(
        "/api/model-governance/approvals",
        headers={"X-Actor-Roles": "economist"},
        json={
            "model_id": "ols_country_risk_learning_v1",
            "intended_use": "external_publication",
            "requester": "senior-economist",
            "justification": "Approved publication dry run with evidence pack.",
            "evidence_uri": "ticket://MRM-123",
        },
    )
    assert submitted.status_code == 200
    approval_id = submitted.json()["approval_id"]

    forbidden = client.post(
        f"/api/model-governance/approvals/{approval_id}/decision",
        json={"decision": "approved", "approver": "validator"},
    )
    assert forbidden.status_code == 403

    decided = client.post(
        f"/api/model-governance/approvals/{approval_id}/decision",
        headers={"X-Actor-Roles": "model_risk"},
        json={"decision": "approved", "approver": "validator", "conditions": ["UAT only"]},
    )
    assert decided.status_code == 200

    metadata = assert_model_use_allowed("regression", "external_publication", "ols_country_risk_learning_v1")
    assert metadata["approved_by_exception"] is True


def test_rbac_ignores_forged_role_header_for_authenticated_jwt(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("API_AUTH_REQUIRED", "true")
    monkeypatch.setenv("RBAC_ENFORCED", "true")
    monkeypatch.setenv("AUTH_MODE", "jwt")
    monkeypatch.setenv("JWT_HS256_SECRET", "test-shared-secret")
    monkeypatch.setenv("AUDIT_LOG_PATH", str(tmp_path / "audit_events.jsonl"))
    token = make_hs256_jwt({"sub": "viewer-001", "roles": ["viewer"], "exp": 4102444800}, "test-shared-secret")
    client = TestClient(app)
    response = client.post(
        "/api/model-governance/approvals",
        headers={"Authorization": f"Bearer {token}", "X-Actor-Roles": "economist"},
        json={
            "model_id": "ols_country_risk_learning_v1",
            "intended_use": "external_publication",
            "requester": "viewer-001",
            "justification": "Forged-header regression test.",
            "evidence_uri": "ticket://RBAC-TEST",
        },
    )
    assert response.status_code == 403


def test_api_key_authentication_does_not_grant_rbac_roles(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("API_AUTH_REQUIRED", "true")
    monkeypatch.setenv("RBAC_ENFORCED", "true")
    monkeypatch.setenv("AUTH_MODE", "api_key")
    monkeypatch.setenv("API_KEY", "test-api-key")
    monkeypatch.setenv("AUDIT_LOG_PATH", str(tmp_path / "audit_events.jsonl"))
    response = TestClient(app).post(
        "/api/model-governance/approvals",
        headers={"X-API-Key": "test-api-key", "X-Actor-Roles": "economist"},
        json={
            "model_id": "ols_country_risk_learning_v1",
            "intended_use": "external_publication",
            "requester": "api-key-client",
            "justification": "An API key is authentication only.",
            "evidence_uri": "ticket://RBAC-TEST",
        },
    )
    assert response.status_code == 403


def test_role_claims_are_copied_and_malformed_values_grant_nothing(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("API_AUTH_REQUIRED", "true")
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [(b"x-actor-roles", b"admin")],
        "scheme": "http",
        "server": ("test", 80),
        "client": ("127.0.0.1", 12345),
    }
    request = Request(scope)
    claims = {"roles": ["viewer", " economist "]}
    request.state.auth_claims = claims
    assert roles_from_request(request) == {"viewer", "economist"}
    assert claims["roles"] == ["viewer", " economist "]

    for invalid_claim in ({"admin": True}, 7, ["admin", 7]):
        request.state.auth_claims = {"roles": invalid_claim}
        assert roles_from_request(request) == set()


def test_role_header_is_ignored_outside_development_even_if_auth_is_disabled(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("API_AUTH_REQUIRED", "false")
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [(b"x-actor-roles", b"admin")],
        "scheme": "http",
        "server": ("test", 80),
        "client": ("127.0.0.1", 12345),
    }
    request = Request(scope)
    request.state.auth_claims = {}
    assert roles_from_request(request) == set()


def test_rbac_blocks_dataset_upload_without_data_role(monkeypatch, tmp_path):
    monkeypatch.setenv("API_AUTH_REQUIRED", "true")
    monkeypatch.setenv("RBAC_ENFORCED", "true")
    monkeypatch.setenv("AUTH_MODE", "jwt")
    monkeypatch.setenv("JWT_HS256_SECRET", "test-shared-secret")
    token = make_hs256_jwt({"sub": "viewer-001", "roles": ["viewer"], "exp": 4102444800}, "test-shared-secret")
    client = TestClient(app)
    csv_path = tmp_path / "upload.csv"
    csv_path.write_text("country,date,value\nIndonesia,2020,1\n", encoding="utf-8")
    with csv_path.open("rb") as handle:
        response = client.post(
            "/api/datasets/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("upload.csv", handle, "text/csv")},
        )
    assert response.status_code == 403


def test_rbac_allows_economist_model_run(monkeypatch, tmp_path):
    monkeypatch.setenv("API_AUTH_REQUIRED", "true")
    monkeypatch.setenv("RBAC_ENFORCED", "true")
    monkeypatch.setenv("AUTH_MODE", "jwt")
    monkeypatch.setenv("JWT_HS256_SECRET", "test-shared-secret")
    monkeypatch.setenv("AUDIT_LOG_PATH", str(tmp_path / "audit_events.jsonl"))
    token = make_hs256_jwt({"sub": "economist-001", "roles": ["economist"], "exp": 4102444800}, "test-shared-secret")
    client = TestClient(app)
    response = client.post(
        "/api/models/regression/run",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "dataset_id": "sample_country_risk_quarterly",
            "country": "Indonesia",
            "dependent_variable": "bond_yield_10y",
            "independent_variables": ["inflation_yoy", "policy_rate"],
        },
    )
    assert response.status_code == 200


def test_rbac_blocks_audit_events_without_auditor_role(monkeypatch):
    monkeypatch.setenv("API_AUTH_REQUIRED", "true")
    monkeypatch.setenv("RBAC_ENFORCED", "true")
    monkeypatch.setenv("AUTH_MODE", "jwt")
    monkeypatch.setenv("JWT_HS256_SECRET", "test-shared-secret")
    token = make_hs256_jwt({"sub": "economist-001", "roles": ["economist"], "exp": 4102444800}, "test-shared-secret")
    client = TestClient(app)
    response = client.get("/api/audit/events", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_model_governance_catalog_endpoint():
    client = TestClient(app)
    response = client.get("/api/model-governance/catalog")
    assert response.status_code == 200
    assert "ols_country_risk_learning_v1" in response.json()


def test_metrics_endpoint_exposes_request_counters():
    client = TestClient(app)
    client.get("/api/health")
    response = client.get("/api/metrics")
    assert response.status_code == 200
    assert "country_risk_http_requests_total" in response.text
    assert "country_risk_app_uptime_seconds" in response.text


def test_rate_limit_can_block_requests(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "1")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    client = TestClient(app)
    headers = {"X-Actor-ID": "rate-limit-test-actor"}
    first = client.get("/api/health", headers=headers)
    second = client.get("/api/health", headers=headers)
    assert first.status_code == 200
    assert second.status_code == 429
