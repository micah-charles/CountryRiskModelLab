#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        backup_dir = ROOT / "backups"
        before = set(backup_dir.glob("data_registry_*.manifest.json")) if backup_dir.exists() else set()
        backup = run([sys.executable, "scripts/backup_data_registry.py"])
        if backup.returncode != 0:
            print(backup.stdout)
            return backup.returncode

        after = set(backup_dir.glob("data_registry_*.manifest.json"))
        new_manifests = sorted(after - before)
        if not new_manifests:
            print("Backup manifest was not created.")
            return 1
        manifest = new_manifests[-1]
        target = temp_path / "restored_data_registry"
        restore = run([sys.executable, "scripts/restore_data_registry.py", str(manifest), "--target", str(target)])
        if restore.returncode != 0:
            print(restore.stdout)
            return restore.returncode

        registry = target / "registry.json"
        if not registry.exists():
            print("Restored registry.json is missing.")
            return 1
        items = json.loads(registry.read_text(encoding="utf-8"))
        ids = {item["dataset_id"] for item in items}
        if {"sample_country_risk_quarterly", "sample_country_risk_monthly"} - ids:
            print("Restored registry is missing required sample datasets.")
            return 1

        manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
        archive = Path(manifest_payload["archive"])
        archive.unlink(missing_ok=True)
        manifest.unlink(missing_ok=True)
        if backup_dir.exists() and not any(backup_dir.iterdir()):
            shutil.rmtree(backup_dir)

    print("Disaster recovery check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

