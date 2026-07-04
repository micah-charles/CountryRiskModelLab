#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import os
import sqlite3
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE = ROOT / "backend/app/data_registry/registry.sqlite3"


def main() -> int:
    sqlite_path = Path(os.getenv("DATASET_REGISTRY_SQLITE_PATH", str(DEFAULT_SQLITE)))
    if not sqlite_path.exists():
        print(f"SQLite registry not found: {sqlite_path}")
        return 1

    failures: list[str] = []
    with sqlite3.connect(sqlite_path) as connection:
        rows = connection.execute("SELECT dataset_id, payload FROM datasets ORDER BY dataset_id").fetchall()

    if not rows:
        failures.append("SQLite registry has no datasets.")

    for dataset_id, payload in rows:
        try:
            item = json.loads(payload)
        except json.JSONDecodeError as exc:
            failures.append(f"{dataset_id}: invalid JSON payload: {exc}")
            continue
        if item.get("dataset_id") != dataset_id:
            failures.append(f"{dataset_id}: payload dataset_id mismatch")
        file_path = Path(item.get("file_path", ""))
        if not file_path.is_absolute():
            file_path = ROOT / file_path
        if not file_path.exists():
            failures.append(f"{dataset_id}: file_path does not exist: {file_path}")

    if failures:
        print("SQLite registry check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"SQLite registry check passed for {len(rows)} datasets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

