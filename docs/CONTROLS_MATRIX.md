# Controls Matrix

| Control ID | Control | Implementation Evidence | Production Owner | Status |
| --- | --- | --- | --- | --- |
| CTL-001 | Environment-specific configuration | `backend/app/config/settings.py`, `.env.example` | Platform Engineering | Implemented |
| CTL-002 | Authentication can be required in production | `API_AUTH_REQUIRED`, `API_KEY`, `ApiKeyAuthMiddleware` | Security | Implemented MVP control |
| CTL-002A | JWT bearer authentication supports issuer, audience, and expiry checks | `AUTH_MODE=jwt`, `auth_service.py` | Security | Implemented gateway-compatible control |
| CTL-002B | OIDC/JWKS authentication supports bank-managed RS256 tokens | `AUTH_MODE=oidc_jwks`, `JWT_JWKS_URL` or `JWT_JWKS_PATH` | Security | Implemented |
| CTL-002C | Role-based access control protects sensitive operations | `RBAC_ENFORCED`, `rbac_service.py`, endpoint role checks | Security | Implemented |
| CTL-003 | Security headers on API responses | `RequestContextMiddleware` | Security | Implemented |
| CTL-004 | Request traceability | `X-Request-ID` request/response header | Platform Engineering | Implemented |
| CTL-005 | Material activity audit ledger | `audit_events.jsonl`, audit tests | Platform Engineering | Implemented MVP control |
| CTL-005A | Audit ledger is tamper-evident through hash chaining | `event_hash`, `previous_hash`, `/api/audit/verify` | Platform Engineering | Implemented |
| CTL-005B | Audit events can be forwarded to external SIEM/log collector | `AUDIT_SINKS=local,http`, `AUDIT_HTTP_ENDPOINT` | Security Operations | Implemented |
| CTL-006 | Dataset registry unifies sample, upload, and IMF datasets | `dataset_registry_service.py` | Data Owner | Implemented |
| CTL-006A | Dataset registry integrity is verified against CSV files | `scripts/registry_integrity_check.py` | Data Owner | Implemented |
| CTL-006B | Dataset registry can run on SQLite backend for transactional storage | `DATASET_REGISTRY_BACKEND=sqlite`, migration/check scripts | Data Owner | Implemented |
| CTL-007 | User-friendly error responses | Endpoint exception mapping, service errors | Platform Engineering | Implemented |
| CTL-008 | IMF API failure does not block learning flow | IMF service graceful error message | Data Owner | Implemented |
| CTL-009 | Model diagnostics and limitations are returned | Regression, forecasting, VAR services | Model Owner | Implemented |
| CTL-009A | Model intended use is checked against a model catalog | `model_catalog.json`, `model_governance_service.py` | Model Risk | Implemented learning/UAT control |
| CTL-009B | Model-risk approval workflow can approve exceptional intended uses | `/api/model-governance/approvals`, `model_approval_service.py` | Model Risk | Implemented |
| CTL-010 | Model review memo includes methodology and limitations | `memo_service.py` | Model Owner | Implemented |
| CTL-011 | Readiness endpoint validates critical dependencies | `readiness_service.py`, `/api/ready` | Operations | Implemented |
| CTL-012 | Automated regression tests cover critical workflows | `backend/app/tests` | Engineering | Implemented |
| CTL-013 | Frontend production build gate | `npm run build` | Engineering | Implemented |
| CTL-014 | Manual QA checklist exists | `qa/manual-test-checklist.md` | QA | Implemented |
| CTL-015 | Deployment instructions and container files exist | `docs/DEPLOYMENT.md`, Dockerfiles | Operations | Implemented |
| CTL-016 | Dependency and simple secret checks are executable | `scripts/security_check.py` | Security | Implemented |
| CTL-017 | HTTP request metrics are exposed for internal scraping | `/api/metrics`, `metrics_service.py` | Operations | Implemented |
| CTL-018 | Service-level rate limiting can be enabled by environment | `RATE_LIMIT_ENABLED`, `RateLimitMiddleware` | Security Operations | Implemented |
| CTL-019 | Backup and restore drill is executable | `backup_data_registry.py`, `restore_data_registry.py`, `disaster_recovery_check.py` | Operations | Implemented |

## Required Before Enterprise-Wide Release

- Front JWT mode with enterprise identity provider or API gateway using bank-managed keys.
- Store audit events in immutable enterprise logging infrastructure.
- Add vulnerability scanning and dependency review to CI.
- Add formal model validation sign-off for any output used outside learning.
- Move file-based registry to approved durable storage or managed database.
