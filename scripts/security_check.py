#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)(api[_-]?key|secret|password)\s*=\s*['\"][^'\"]{12,}['\"]"),
]
SCAN_SUFFIXES = {".py", ".ts", ".tsx", ".json", ".yml", ".yaml", ".md", ".env", ".example"}
SKIP_PARTS = {"node_modules", ".venv", "dist", ".git"}


def run(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
    return result.returncode, result.stdout


def scan_for_secrets() -> list[str]:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.suffix not in SCAN_SUFFIXES and path.name not in {".env.example"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                findings.append(str(path.relative_to(ROOT)))
                break
    return findings


def main() -> int:
    failures: list[str] = []

    pip = ROOT / "backend/.venv/bin/pip"
    if pip.exists():
        code, output = run([str(pip), "check"])
        if code != 0:
            failures.append("pip check failed:\n" + output)
    else:
        failures.append("backend virtualenv is missing; cannot run pip check")

    if (ROOT / "package-lock.json").exists():
        code, output = run(["npm", "audit", "--audit-level=high"])
        if code != 0:
            failures.append("npm audit found high severity issues:\n" + output)

    secret_findings = scan_for_secrets()
    if secret_findings:
        failures.append("possible secrets found in: " + ", ".join(secret_findings))

    if failures:
        print("Security check failed.")
        for failure in failures:
            print(failure)
        return 1

    print("Security check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

