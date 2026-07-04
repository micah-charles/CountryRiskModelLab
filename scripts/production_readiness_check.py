#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    ".env.example",
    "README.md",
    "docs/ARCHITECTURE.md",
    "docs/CONTROLS_MATRIX.md",
    "docs/DATA_AND_MODEL_GOVERNANCE.md",
    "docs/DEPLOYMENT.md",
    "docs/PRODUCTION_READINESS.md",
    "docs/RELEASE_CHECKLIST.md",
    "docs/RUNBOOK.md",
    "qa/manual-test-checklist.md",
    "backend/app/config/settings.py",
    "backend/app/config/imf_country_catalog.json",
    "backend/app/middleware.py",
    "backend/app/services/audit_service.py",
    "backend/app/services/auth_service.py",
    "backend/app/services/model_approval_service.py",
    "backend/app/services/model_governance_service.py",
    "backend/app/services/rbac_service.py",
    "backend/app/services/readiness_service.py",
    "backend/Dockerfile",
    "Dockerfile.frontend",
    "docker-compose.yml",
    "scripts/production_readiness_check.py",
    "scripts/registry_integrity_check.py",
    "scripts/security_check.py",
    "scripts/export_openapi.py",
    "scripts/generate_release_evidence.py",
    "scripts/refresh_imf_country_catalog.py",
    "scripts/prefetch_imf_all_countries_dataset.py",
    "scripts/migrate_registry_to_sqlite.py",
    "scripts/sqlite_registry_check.py",
    "scripts/backup_data_registry.py",
    "scripts/restore_data_registry.py",
    "scripts/disaster_recovery_check.py",
]


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def check_files() -> list[str]:
    return [path for path in REQUIRED_FILES if not (ROOT / path).exists()]


def check_registry() -> list[str]:
    registry = ROOT / "backend/app/data_registry/registry.json"
    items = json.loads(registry.read_text(encoding="utf-8"))
    ids = {item["dataset_id"] for item in items}
    missing = []
    for required in ["sample_country_risk_quarterly", "sample_country_risk_monthly"]:
        if required not in ids:
            missing.append(required)
    return missing


def check_backend_ready() -> int:
    code = (
        "from fastapi.testclient import TestClient\n"
        "from app.main import app\n"
        "client=TestClient(app)\n"
        "r=client.get('/api/ready')\n"
        "assert r.status_code == 200, r.text\n"
        "assert r.json()['status'] == 'ok', r.text\n"
    )
    return subprocess.run(
        [str(ROOT / "backend/.venv/bin/python"), "-c", code],
        cwd=ROOT,
        env={"PYTHONPATH": "backend"},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    ).returncode


def run_script(relative_path: str) -> int:
    return subprocess.run(
        [sys.executable, str(ROOT / relative_path)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    ).returncode


def main() -> int:
    missing_files = check_files()
    if missing_files:
        return fail("missing required files: " + ", ".join(missing_files))

    missing_datasets = check_registry()
    if missing_datasets:
        return fail("registry missing datasets: " + ", ".join(missing_datasets))

    if not (ROOT / "backend/.venv/bin/python").exists():
        return fail("backend virtualenv not found; run backend dependency installation first")

    if check_backend_ready() != 0:
        return fail("backend readiness endpoint did not pass")

    if run_script("scripts/registry_integrity_check.py") != 0:
        return fail("registry integrity check did not pass")

    print("Production readiness check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
