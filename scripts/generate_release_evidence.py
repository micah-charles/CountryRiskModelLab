#!/usr/bin/env python3
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import argparse
import hashlib
import json
import platform
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_JSON = ROOT / "release_evidence/current_release_evidence.json"
OUTPUT_MD = ROOT / "release_evidence/current_release_evidence.md"

GATES = [
    {
        "name": "backend_tests",
        "command": ["backend/.venv/bin/pytest", "backend/app/tests", "-q"],
        "env": {"PYTHONPATH": "backend"},
    },
    {"name": "frontend_build", "command": ["npm", "run", "build"]},
    {"name": "registry_integrity", "command": [sys.executable, "scripts/registry_integrity_check.py"]},
    {"name": "security_check", "command": [sys.executable, "scripts/security_check.py"]},
    {"name": "disaster_recovery", "command": [sys.executable, "scripts/disaster_recovery_check.py"]},
    {"name": "production_readiness", "command": [sys.executable, "scripts/production_readiness_check.py"]},
    {
        "name": "openapi_export",
        "command": ["backend/.venv/bin/python", "scripts/export_openapi.py"],
        "env": {"PYTHONPATH": "backend"},
    },
]

KEY_FILES = [
    "README.md",
    ".env.example",
    "backend/app/main.py",
    "backend/app/config/settings.py",
    "backend/app/middleware.py",
    "backend/app/services/rbac_service.py",
    "backend/app/config/model_catalog.json",
    "backend/app/data/imf_all_countries_2010_2026.csv",
    "backend/app/data_registry/registry.json",
    "docs/ARCHITECTURE.md",
    "docs/CONTROLS_MATRIX.md",
    "docs/DATA_AND_MODEL_GOVERNANCE.md",
    "docs/DEPLOYMENT.md",
    "docs/PRODUCTION_READINESS.md",
    "docs/RUNBOOK.md",
    "qa/manual-test-checklist.md",
    "package.json",
    "backend/app/requirements.txt",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_gate(gate: dict) -> dict:
    env = None
    if gate.get("env"):
        import os

        env = os.environ.copy()
        env.update(gate["env"])
    result = subprocess.run(
        gate["command"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    output_tail = result.stdout.strip().splitlines()[-20:]
    return {
        "name": gate["name"],
        "command": " ".join(gate["command"]),
        "exit_code": result.returncode,
        "passed": result.returncode == 0,
        "output_tail": output_tail,
    }


def collect_metadata() -> dict:
    node_version = subprocess.run(["node", "--version"], cwd=ROOT, stdout=subprocess.PIPE, text=True, check=False).stdout.strip()
    npm_version = subprocess.run(["npm", "--version"], cwd=ROOT, stdout=subprocess.PIPE, text=True, check=False).stdout.strip()
    python_version = subprocess.run([sys.executable, "--version"], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False).stdout.strip()
    return {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "platform": platform.platform(),
        "python": python_version,
        "node": node_version,
        "npm": npm_version,
    }


def file_manifest() -> list[dict]:
    rows = []
    for relative in KEY_FILES:
        path = ROOT / relative
        if path.exists():
            rows.append({"path": relative, "sha256": sha256(path), "bytes": path.stat().st_size})
        else:
            rows.append({"path": relative, "missing": True})
    return rows


def write_markdown(payload: dict) -> None:
    lines = [
        "# Release Evidence Pack",
        "",
        f"Generated at: `{payload['metadata']['generated_at']}`",
        "",
        "## Gate Results",
        "",
        "| Gate | Result | Command |",
        "| --- | --- | --- |",
    ]
    for gate in payload["gates"]:
        result = "PASS" if gate["passed"] else "FAIL"
        lines.append(f"| {gate['name']} | {result} | `{gate['command']}` |")
    lines.extend(["", "## File Manifest", "", "| File | SHA-256 | Bytes |", "| --- | --- | --- |"])
    for row in payload["file_manifest"]:
        if row.get("missing"):
            lines.append(f"| {row['path']} | MISSING |  |")
        else:
            lines.append(f"| {row['path']} | `{row['sha256']}` | {row['bytes']} |")
    lines.extend(["", "## Residual Enterprise Dependencies", ""])
    for item in payload["residual_enterprise_dependencies"]:
        lines.append(f"- {item}")
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a production release evidence pack.")
    parser.add_argument("--skip-gates", action="store_true", help="Collect metadata without executing release gates.")
    args = parser.parse_args()

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    gates = []
    if args.skip_gates:
        gates = [{"name": gate["name"], "command": " ".join(gate["command"]), "exit_code": None, "passed": None, "output_tail": []} for gate in GATES]
    else:
        gates = [run_gate(gate) for gate in GATES]

    payload = {
        "metadata": collect_metadata(),
        "gates": gates,
        "all_gates_passed": all(gate["passed"] is True for gate in gates) if not args.skip_gates else None,
        "file_manifest": file_manifest(),
        "residual_enterprise_dependencies": [
            "Configure bank-owned OIDC/JWKS issuer and audience.",
            "Configure SIEM or immutable enterprise audit sink.",
            "Configure managed production database or approved durable registry storage.",
            "Complete institution-owned model-risk approval and signoff records.",
            "Run bank vulnerability scanning and change-management approval before live release.",
        ],
    }
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(payload)
    print(f"Wrote release evidence JSON to {OUTPUT_JSON}")
    print(f"Wrote release evidence Markdown to {OUTPUT_MD}")
    return 0 if args.skip_gates or payload["all_gates_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
