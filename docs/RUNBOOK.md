# Production Runbook

## Start Backend

```bash
cd backend
source .venv/bin/activate
APP_ENV=production API_AUTH_REQUIRED=true AUTH_MODE=jwt JWT_HS256_SECRET="<secret>" JWT_ISSUER="<issuer>" JWT_AUDIENCE="country-risk-model-lab" uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Start Frontend

```bash
npm run build
npm run preview
```

## Health Checks

- `GET /api/health` returns basic liveness.
- `GET /api/ready` validates sample datasets, dataset files, IMF indicator mapping, and audit path.
- `GET /api/version` returns app version and environment.
- `GET /api/audit/verify` validates the local audit hash chain.
- `GET /api/model-governance/catalog` returns registered model policies.
- `GET /api/model-governance/approvals` returns model-risk approval records.
- `GET /api/metrics` exposes Prometheus-style metrics for internal monitoring.
- Production authorization requires mapped roles when `RBAC_ENFORCED=true`.

## Start-of-Day Checks

1. Confirm `/api/ready` returns `status: ok`.
2. Confirm sample datasets are visible in `/api/datasets/samples`.
3. Confirm IMF indicator mapping is visible in `/api/imf/indicators`.
4. Run one regression smoke test on the quarterly sample dataset.
5. Confirm audit events are being written.
6. Confirm `python3 scripts/registry_integrity_check.py` passes.
7. Confirm `python3 scripts/migrate_registry_to_sqlite.py` and `python3 scripts/sqlite_registry_check.py` pass before switching to SQLite registry mode.
8. Confirm `python3 scripts/security_check.py` passes before release.
9. Confirm `python3 scripts/disaster_recovery_check.py` passes before release.

## Incident Handling

| Scenario | Response |
| --- | --- |
| IMF API unavailable | Tell users to continue with sample or CSV data; confirm user-friendly error appears |
| Uploaded CSV fails | Validate required `country` and `date` columns and file size |
| Model run fails | Review service error and suggest longer sample, fewer variables, or simpler model |
| Audit ledger not writable | Treat as production-impacting; material actions should not be trusted without audit evidence |
| Audit hash chain fails | Treat as potential tampering or file corruption; preserve the file, restrict access, and investigate by request ID and timestamp |
| Audit HTTP sink fails in fail-closed mode | Treat as production-impacting because material events cannot be centrally retained |
| Model intended use blocked | Confirm the requested purpose; use learning/UAT or route through formal model-risk approval |
| Approval decision rejected with 403 | Confirm actor has `model_risk` role or equivalent bank entitlement |
| Sensitive endpoint returns 403 | Confirm identity token contains the required role or group mapping |
| Unexpected API errors | Capture request ID, endpoint, timestamp, actor header, and server logs |
| Rate limit exceeded | Confirm client identity, request volume, and gateway/WAF policy before increasing limits |
| Restore required | Run restore from a verified manifest and complete post-restore readiness checks |

## Rollback

Rollback requires:

- Previous application artifact or image
- Previous frontend build
- Registry backup if schema changed
- Environment variable snapshot
- Smoke test after rollback
