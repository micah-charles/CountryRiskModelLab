from app.main import app


def test_openapi_contract_contains_core_production_endpoints():
    schema = app.openapi()
    paths = schema["paths"]
    required_paths = {
        "/api/ready",
        "/api/metrics",
        "/api/models/regression/run",
        "/api/models/readiness",
        "/api/models/forecast/run",
        "/api/models/var/run",
        "/api/model-governance/catalog",
        "/api/model-governance/approvals",
        "/api/audit/verify",
        "/api/research-cases",
        "/api/research-cases/import",
        "/api/indicators",
        "/api/formulas",
        "/api/formulas/calculate",
    }
    assert required_paths.issubset(paths)
