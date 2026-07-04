#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    sys.path.insert(0, str(ROOT / "backend"))

    from app.services.imf_service import COUNTRY_CATALOG_PATH, refresh_country_catalog

    try:
        catalog = refresh_country_catalog()
    except Exception as exc:
        print(f"FAIL: could not refresh IMF country catalogue: {exc}")
        return 1

    print(f"Refreshed IMF country catalogue: {catalog.country_count} countries")
    print(f"Last modified UTC: {catalog.last_modified_utc}")
    print(f"Wrote: {COUNTRY_CATALOG_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
