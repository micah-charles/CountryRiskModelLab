from __future__ import annotations

import csv, hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p

def ensure_parent(path: str | Path) -> Path:
    p = resolve(path); p.parent.mkdir(parents=True, exist_ok=True); return p

def read_json(path: str | Path, default: Any = None) -> Any:
    p = resolve(path)
    return json.loads(p.read_text()) if p.exists() else default

def write_json(path: str | Path, value: Any) -> Path:
    p = ensure_parent(path); p.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n"); return p

def read_csv(path: str | Path) -> list[dict[str, str]]:
    p = resolve(path)
    if not p.exists() or p.stat().st_size == 0: return []
    with p.open(newline="", encoding="utf-8-sig") as f: return list(csv.DictReader(f))

def write_csv(path: str | Path, rows: Iterable[dict[str, Any]], fields: list[str] | None = None) -> Path:
    rows = list(rows); p = ensure_parent(path)
    fields = fields or list(dict.fromkeys(k for row in rows for k in row))
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    return p

def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with resolve(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()

def sha256_text(text: str) -> str: return hashlib.sha256(text.encode()).hexdigest()

def relative(path: str | Path) -> str:
    try: return str(resolve(path).relative_to(ROOT))
    except ValueError: return str(path)

def atomic_write(path: str | Path, content: str) -> Path:
    p = ensure_parent(path); tmp = p.with_suffix(p.suffix + ".tmp"); tmp.write_text(content); os.replace(tmp, p); return p

