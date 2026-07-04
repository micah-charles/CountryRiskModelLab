# Production Readiness

## Current Verified Status

The repository now contains a verified MVP plus production-control baseline:

- FastAPI backend
- React/Vite frontend
- Unified dataset registry
- IMF connector
- Regression, forecasting, and VAR services
- Memo generation
- Lesson packs
- Security headers
- Request IDs
- Optional production API key enforcement
- Configurable auth mode: API key, JWT, or API key/JWT migration mode
- OIDC/JWKS RS256 token validation for bank-managed identity integration
- Role-based access control for sensitive API operations
- Tamper-evident audit ledger with hash-chain verification
- Optional audit forwarding to SIEM or central logging
- Model catalog with intended-use enforcement
- Model-risk approval workflow for exceptional intended uses
- Registry integrity check
- SQLite registry backend and migration check
- Dependency and simple secret checks
- Prometheus-style metrics endpoint
- Configurable service-level rate limiting
- Backup/restore disaster-recovery drill
- Readiness endpoint
- Backend tests
- Frontend build
- Deployment files
- QA checklist
- OpenAPI contract export
- Release evidence pack generator

## Release Gates

| Gate | Evidence | Status |
| --- | --- | --- |
| Backend unit and API tests | `PYTHONPATH=backend backend/.venv/bin/pytest backend/app/tests -q` | Required |
| Frontend production build | `npm run build` | Required |
| Production readiness check | `python3 scripts/production_readiness_check.py` | Required |
| Registry integrity check | `python3 scripts/registry_integrity_check.py` | Required |
| SQLite registry migration check | `python3 scripts/migrate_registry_to_sqlite.py` and `python3 scripts/sqlite_registry_check.py` | Required |
| Security check | `python3 scripts/security_check.py` | Required |
| Disaster recovery check | `python3 scripts/disaster_recovery_check.py` | Required |
| OpenAPI export | `python3 scripts/export_openapi.py` | Required |
| Release evidence pack | `python3 scripts/generate_release_evidence.py` | Required |
| Manual QA | `qa/manual-test-checklist.md` | Required before release |
| Security configuration | `.env.example`, `API_AUTH_REQUIRED=true` in production | Required |
| RBAC configuration | `RBAC_ENFORCED=true` in production | Required |
| Audit evidence | `audit_events.jsonl` or enterprise log sink | Required |

## Known Residual Risks

- API key auth is an MVP control. OIDC/JWKS mode should be integrated with bank-owned identity/gateway controls for enterprise release.
- File-based JSON registry is acceptable for controlled MVP/UAT; SQLite mode is available for transactional storage but large-scale production should use a managed database.
- Audit JSONL is tamper-evident locally but should still be shipped to immutable enterprise logging for regulated production.
- Local backup/restore is verified; production backup retention and offsite storage must be configured by bank operations.
- IMF API availability is external and should be monitored separately.
- Statistical services are educational and require formal model validation before decision use.
