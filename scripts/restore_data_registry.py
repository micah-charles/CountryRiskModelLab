#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys
import tarfile


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore a data_registry backup archive.")
    parser.add_argument("manifest", help="Path to data_registry backup manifest JSON")
    parser.add_argument("--target", default=str(ROOT / "backend/app/data_registry"), help="Restore target directory")
    parser.add_argument("--force", action="store_true", help="Allow replacing an existing target directory")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    archive = Path(manifest["archive"])
    target = Path(args.target)
    if sha256(archive) != manifest["sha256"]:
        print("Backup archive checksum does not match manifest.")
        return 1
    if target.exists():
        if not args.force:
            print(f"Target exists; pass --force to replace: {target}")
            return 1
        shutil.rmtree(target)

    target.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(target.parent)
    restored = target.parent / "data_registry"
    if restored != target:
        restored.rename(target)
    print(f"Restored data registry to {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

