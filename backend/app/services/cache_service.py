from __future__ import annotations

from pathlib import Path
import hashlib
import json

from app.services.dataset_registry_service import REGISTRY_DIR


CACHE_DIR = REGISTRY_DIR / "imf_cache"


def cache_key(parts: list[str]) -> str:
    joined = "|".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:24]


def read_cache(key: str) -> dict | None:
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_cache(key: str, payload: dict) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{key}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path

