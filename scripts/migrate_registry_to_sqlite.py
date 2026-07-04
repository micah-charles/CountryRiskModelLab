#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import os
import sqlite3
import sys


ROOT = Path(__file__).resolve().parents[1]
JSON_REGISTRY = ROOT / "backend/app/data_registry/registry.json"
DEFAULT_SQLITE = ROOT / "backend/app/data_registry/registry.sqlite3"


def main() -> int:
    sqlite_path = Path(os.getenv("DATASET_REGISTRY_SQLITE_PATH", str(DEFAULT_SQLITE)))
    items = json.loads(JSON_REGISTRY.read_text(encoding="utf-8"))
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(sqlite_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS datasets (
                dataset_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute("DELETE FROM datasets")
        connection.executemany(
            "INSERT INTO datasets(dataset_id, payload, updated_at) VALUES (?, ?, datetime('now'))",
            [(item["dataset_id"], json.dumps(item, sort_keys=True)) for item in items],
        )
        connection.commit()

    print(f"Migrated {len(items)} datasets to {sqlite_path}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

