#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/api/openapi.json"


def main() -> int:
    sys.path.insert(0, str(ROOT / "backend"))
    from app.main import app

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Exported OpenAPI contract to {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

