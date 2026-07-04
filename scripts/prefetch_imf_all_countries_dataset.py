#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


def parse_indicator_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Prefetch IMF DataMapper macro data for every country in the static IMF country catalogue.")
    parser.add_argument("--start-year", type=int, default=2010)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument(
        "--indicators",
        default="",
        help="Comma-separated IMF indicator codes. Defaults to all indicators configured in imf_indicator_mapping.json.",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT / "backend"))

    from app.models.schemas import ImfPrefetchAllRequest
    from app.services.imf_service import prefetch_all_countries_dataset

    request = ImfPrefetchAllRequest(
        indicators=parse_indicator_list(args.indicators),
        start_year=args.start_year,
        end_year=args.end_year,
    )

    try:
        response = asyncio.run(prefetch_all_countries_dataset(request))
    except Exception as exc:
        print(f"FAIL: could not prefetch all-country IMF dataset: {exc}")
        return 1

    print(f"Created dataset: {response.dataset.dataset_id}")
    print(f"Name: {response.dataset.name}")
    print(f"Countries: {len(response.dataset.countries)}")
    print(f"Rows: {response.preview.row_count}")
    print(f"Columns: {response.preview.column_count}")
    print(f"CSV: {response.dataset.file_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
