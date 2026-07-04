# Deployment

## Environment Variables

Use `.env.example` as the contract. In production:

- `APP_ENV=production`
- `API_AUTH_REQUIRED=true`
- `AUTH_MODE=api_key`, `jwt`, `oidc_jwks`, or `api_key_or_jwt`
- `API_KEY` must be provided through a secret manager when API-key mode is used
- `JWT_HS256_SECRET`, `JWT_ISSUER`, and `JWT_AUDIENCE` must be set when JWT mode is used behind an enterprise gateway
- `JWT_JWKS_URL` or `JWT_JWKS_PATH` must be set when OIDC/JWKS mode is used
- `CORS_ALLOWED_ORIGINS` must list approved frontend origins only
- `AUDIT_LOG_PATH` must point to durable storage or a mounted log path
- `AUDIT_SINKS=local,http` and `AUDIT_HTTP_ENDPOINT` can forward tamper-evident audit events to SIEM or central logging
- `MODEL_APPROVALS_PATH` controls the model-risk approval store
- `RATE_LIMIT_ENABLED=true`, `RATE_LIMIT_REQUESTS`, and `RATE_LIMIT_WINDOW_SECONDS` enable service-level throttling
- `RBAC_ENFORCED=true` enables service-level role enforcement for sensitive endpoints
- `DATASET_REGISTRY_BACKEND=json` for local MVP or `sqlite` for transactional registry storage

## Backend Container

```bash
docker build -f backend/Dockerfile -t country-risk-model-lab-api .
docker run --rm -p 8000:8000 --env-file .env country-risk-model-lab-api
```

## Frontend Container

```bash
docker build -f Dockerfile.frontend -t country-risk-model-lab-web .
docker run --rm -p 5173:80 country-risk-model-lab-web
```

## CI Gates

Required gates:

1. Backend tests pass.
2. Frontend TypeScript build passes.
3. Production readiness checker passes.
4. Registry integrity checker passes.
5. SQLite registry migration checker passes.
6. Security checker passes.
7. Disaster recovery checker passes.
8. Manual QA checklist is completed before release.

## SQLite Registry Migration

```bash
python3 scripts/migrate_registry_to_sqlite.py
DATASET_REGISTRY_BACKEND=sqlite python3 scripts/sqlite_registry_check.py
```

Then run the backend with:

```bash
DATASET_REGISTRY_BACKEND=sqlite DATASET_REGISTRY_SQLITE_PATH=backend/app/data_registry/registry.sqlite3 uvicorn app.main:app --reload --port 8000
```

## JWT Auth Mode

For bank gateway or identity-provider integration:

```bash
APP_ENV=production \
API_AUTH_REQUIRED=true \
AUTH_MODE=jwt \
JWT_HS256_SECRET=$JWT_SECRET_FROM_SECRET_MANAGER \
JWT_ISSUER="https://identity.example-bank.internal" \
JWT_AUDIENCE="country-risk-model-lab" \
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The service validates token signature, issuer, audience, expiry, and not-before claims. In an enterprise deployment, prefer bank-managed OIDC at the gateway and pass only trusted tokens to the service.

## OIDC/JWKS Auth Mode

For bank-managed identity provider or API gateway tokens:

```bash
APP_ENV=production \
API_AUTH_REQUIRED=true \
AUTH_MODE=oidc_jwks \
JWT_JWKS_URL="https://identity.example-bank.internal/.well-known/jwks.json" \
JWT_ISSUER="https://identity.example-bank.internal" \
JWT_AUDIENCE="country-risk-model-lab" \
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

This mode validates RS256 bearer tokens against the trusted JWKS, issuer, audience, expiry, and not-before claims.

## Audit Forwarding

```bash
AUDIT_SINKS=local,http \
AUDIT_HTTP_ENDPOINT="https://siem.example-bank.internal/ingest/country-risk-model-lab" \
AUDIT_HTTP_TOKEN=$AUDIT_HTTP_TOKEN_FROM_SECRET_MANAGER \
AUDIT_HTTP_FAIL_CLOSED=true
```

Keep `local` enabled unless enterprise logging has a stronger immutable store. Use fail-closed for production workflows where audit evidence is mandatory.

## Metrics and Rate Limiting

`GET /api/metrics` exposes Prometheus-style request counters and duration metrics for internal scraping.

Enable service-level rate limiting:

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60
```

Use gateway/WAF throttling as the primary enterprise control; the service-level limiter is a defense-in-depth control.

## RBAC Roles

Set `RBAC_ENFORCED=true` for production. Supported service roles:

- `viewer`: list and preview datasets.
- `economist`: fetch IMF data, upload datasets, run models, generate memos, submit model approvals.
- `data_steward`: upload datasets and fetch IMF data.
- `model_risk`: review model catalog, run validation workflows, decide model approvals.
- `auditor`: inspect audit and governance evidence.
- `operator`: inspect audit/readiness evidence.
- `admin`: all service actions.

## Backup and Restore

```bash
python3 scripts/backup_data_registry.py
python3 scripts/restore_data_registry.py backups/<manifest>.manifest.json --force
python3 scripts/disaster_recovery_check.py
```

## Banking Production Notes

For a bank-managed deployment, run the containers behind approved ingress, WAF, TLS termination, centralized logging, vulnerability scanning, secrets management, and enterprise identity controls.
