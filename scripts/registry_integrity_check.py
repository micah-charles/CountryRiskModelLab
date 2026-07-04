#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import csv
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "backend/app/data_registry/registry.json"
REQUIRED_FIELDS = {
    "dataset_id",
    "name",
    "source_type",
    "source_name",
    "created_at",
    "frequency",
    "country_column",
    "date_column",
    "columns",
    "file_path",
}


def main() -> int:
    items = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    failures: list[str] = []
    seen: set[str] = set()

    for item in items:
        dataset_id = item.get("dataset_id", "<missing>")
        missing = REQUIRED_FIELDS - set(item)
        if missing:
            failures.append(f"{dataset_id}: missing fields {sorted(missing)}")
        if dataset_id in seen:
            failures.append(f"{dataset_id}: duplicate dataset_id")
        seen.add(dataset_id)

        path = Path(item.get("file_path", ""))
        if not path.is_absolute():
            path = ROOT / path
        if not path.exists():
            failures.append(f"{dataset_id}: file_path does not exist: {path}")
            continue

        try:
            with path.open(newline="", encoding="utf-8") as handle:
                reader = csv.reader(handle)
                columns = next(reader)
        except Exception as exc:
            failures.append(f"{dataset_id}: CSV cannot be read: {exc}")
            continue

        expected_columns = item.get("columns", [])
        if columns != expected_columns:
            failures.append(f"{dataset_id}: registry columns do not match CSV columns")
        for required_column in [item.get("country_column"), item.get("date_column")]:
            if required_column and required_column not in columns:
                failures.append(f"{dataset_id}: required column missing from CSV: {required_column}")

    if failures:
        print("Registry integrity check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"Registry integrity check passed for {len(items)} datasets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
