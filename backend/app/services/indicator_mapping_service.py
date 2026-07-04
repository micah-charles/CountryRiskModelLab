from __future__ import annotations

from pathlib import Path
import json

from app.models.schemas import ImfIndicator


MAPPING_PATH = Path(__file__).resolve().parents[1] / "config" / "imf_indicator_mapping.json"


def load_indicator_mapping() -> dict[str, ImfIndicator]:
    raw = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    return {code: ImfIndicator(code=code, **payload) for code, payload in raw.items()}


def list_indicators() -> list[ImfIndicator]:
    return list(load_indicator_mapping().values())

