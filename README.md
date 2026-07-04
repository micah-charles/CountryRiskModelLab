# Country Risk Statistical Model Lab

## What This Is

A Python-powered learning lab for country-risk statistical modelling.

The platform helps country-risk analysts learn how to import macroeconomic data, run regression and time-series models, inspect diagnostics, understand the statistical logic in plain English, and document findings in a model review memo.

## What It Teaches

- Importing real IMF macroeconomic data
- CSV and synthetic sample dataset handling
- OLS regression
- ARIMA forecasting
- SARIMA/SARIMAX forecasting
- Simplified Auto ARIMA model comparison
- VAR basics
- Model diagnostics
- Model strengths and weaknesses
- Model review documentation

## Dataset Sources

Supported dataset sources:

1. Synthetic sample datasets
2. CSV upload
3. IMF API import

All datasets flow through the same local registry using `dataset_id`, `source_type`, `source_name`, `frequency`, `country_column`, `date_column`, `columns`, `file_path`, and metadata.

## IMF API Connector

The platform can import macroeconomic data from the IMF API.

The IMF connector allows users to:

- Select countries
- Select macroeconomic indicators
- Fetch data from the IMF API
- Transform the response into a modelling-ready country-year panel
- Review missing values and data limitations
- Save the fetched data into the local dataset registry
- Use the dataset in Regression Lab, Forecasting Lab, VAR Lab, and Model Review

The connector is designed for learning and transparency. It shows indicator descriptions, country-risk interpretation, expected relationship to sovereign risk, missing values, and transformation notes.

The IMF country catalogue is stored locally at `backend/app/config/imf_country_catalog.json` with a `last_modified_utc` timestamp. Analysts can refresh it from the IMF Data Connector UI, and operators can refresh it from the command line:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/refresh_imf_country_catalog.py
```

Operators can also prefetch macro data for every country in the static IMF catalogue:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/prefetch_imf_all_countries_dataset.py --start-year 2010 --end-year 2026
```

If the IMF API is unavailable, users can continue with sample datasets or CSV upload.

## What It Is Not

This is not a full replacement for EViews, Stata, R, or a production banking model platform. It is a focused learning platform for practical country-risk statistical modelling.

## How To Run Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
uvicorn app.main:app --reload --port 8000
```

## How To Run Frontend

```bash
npm install
npm run dev
```

The frontend expects the backend at `http://localhost:8000`.

## QA

Run backend tests:

```bash
cd backend
pytest
```

Manual QA checklist:

- [qa/manual-test-checklist.md](qa/manual-test-checklist.md)

## Production Controls

This repo includes a production-control baseline for controlled banking UAT or internal learning deployment:

- Environment-driven settings in `backend/app/config/settings.py`
- Optional production API key, JWT, or OIDC/JWKS enforcement with `API_AUTH_REQUIRED=true`
- Role-based authorization for sensitive API operations with `RBAC_ENFORCED=true`
- Request IDs and security headers on API responses
- JSONL audit ledger for dataset downloads, uploads, IMF fetches, model runs, and memo generation
- Tamper-evident audit hash chain with `/api/audit/verify`
- Optional audit forwarding to SIEM or central logging
- Model-governance catalog and intended-use enforcement
- Model-risk approval workflow for exceptional intended uses
- Readiness endpoint at `GET /api/ready`
- Registry integrity and security check scripts
- SQLite registry migration and check scripts
- Metrics endpoint, configurable rate limiting, and DR backup/restore scripts
- OpenAPI export and release evidence pack generator
- Dockerfiles and `docker-compose.yml`
- CI workflow in `.github/workflows/ci.yml`
- Production evidence docs in `docs/`

Run the readiness checker:

```bash
python3 scripts/production_readiness_check.py
```

Run the additional release gates:

```bash
python3 scripts/registry_integrity_check.py
python3 scripts/migrate_registry_to_sqlite.py
python3 scripts/sqlite_registry_check.py
python3 scripts/security_check.py
python3 scripts/disaster_recovery_check.py
python3 scripts/export_openapi.py
python3 scripts/generate_release_evidence.py
```

For production-style local backend startup:

```bash
cd backend
source .venv/bin/activate
APP_ENV=production API_AUTH_REQUIRED=true API_KEY="<secret>" uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For enterprise banking release, replace the MVP API-key control with enterprise SSO/OIDC, ship audit logs to immutable centralized logging, and move the file registry to approved durable storage.
