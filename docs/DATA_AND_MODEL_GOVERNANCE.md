# Data and Model Governance

## Data Governance

Supported data sources are synthetic sample data, user CSV upload, and IMF DataMapper import.

Every registered dataset records:

- Dataset ID
- Source type and source name
- Created timestamp
- Frequency
- Country and date columns
- Column list
- File path
- Countries
- Date range
- Learning notes and limitations

The registry can run in two modes:

- `json`: local MVP file-based registry.
- `sqlite`: transactional registry mode using `DATASET_REGISTRY_BACKEND=sqlite`.

Use `scripts/migrate_registry_to_sqlite.py` to migrate JSON metadata into SQLite and `scripts/sqlite_registry_check.py` to verify the migrated registry.

## IMF Data Controls

The IMF connector uses a curated indicator mapping in `backend/app/config/imf_indicator_mapping.json`. Each indicator includes a platform variable name, description, category, frequency, country-risk interpretation, and expected relationship to bond yields.

IMF datasets include learning notes warning that annual data is suitable for medium-term analysis and cross-country comparison but may be weak for short-horizon forecasting or dense VAR models.

## Model Governance

The platform is educational. It does not certify models for capital, trading, credit, or regulatory decisioning.

Model governance metadata lives in `backend/app/config/model_catalog.json`. Each registered model has:

- Model ID
- Model type
- Status
- Owner
- Validator
- Allowed uses
- Prohibited uses
- Methodology
- Limitations

The backend enforces intended-use checks through `backend/app/services/model_governance_service.py`. Current MVP models are approved only for `learning` and `uat`. Requests with prohibited purposes such as `trading`, `credit_decisioning`, `regulatory_capital`, or `external_publication` are blocked unless the model catalog is updated after formal model-risk approval.

Exceptional use approvals are managed through `backend/app/services/model_approval_service.py` and the `/api/model-governance/approvals` endpoints. Approval decisions require a `model_risk` role and are audit logged.

Each model run must provide:

- Method type
- Dataset metadata
- Variables
- Fit or forecast metrics
- Diagnostics or warnings
- Strengths
- Weaknesses
- Suggested modifications
- Python code preview

## Model Risk Limitations

- OLS results are associational, not causal proof.
- ARIMA/SARIMAX forecasts can fail under structural breaks.
- Auto ARIMA is educational grid search, not a full professional model-selection engine.
- VAR results are sensitive to variable choice, lag length, stationarity, and sample size.
- IMF annual data can be too sparse for high-frequency forecasting workflows.

## Production Rule

Any use beyond learning must pass formal model inventory, independent validation, data lineage review, intended-use approval, monitoring definition, and retirement criteria.
