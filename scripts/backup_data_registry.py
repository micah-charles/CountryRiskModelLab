#!/usr/bin/env python3
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import hashlib
import json
import sys
import tarfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "backend/app/data_registry"
BACKUP_DIR = ROOT / "backups"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    if not SOURCE.exists():
        print(f"Data registry does not exist: {SOURCE}")
        return 1
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    archive = BACKUP_DIR / f"data_registry_{timestamp}.tar.gz"
    manifest = BACKUP_DIR / f"data_registry_{timestamp}.manifest.json"

    with tarfile.open(archive, "w:gz") as tar:
        tar.add(SOURCE, arcname="data_registry")

    payload = {
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": str(SOURCE),
        "archive": str(archive),
        "sha256": sha256(archive),
    }
    manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

