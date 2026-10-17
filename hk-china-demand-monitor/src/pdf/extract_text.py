from __future__ import annotations
import re
from pathlib import Path
from src.common import resolve

def _garble_ratio(text: str) -> float:
    if not text: return 1.0
    bad = sum(ch == "\ufffd" or (ord(ch) < 32 and ch not in "\n\t\r") for ch in text)
    return bad / max(1, len(text))

def extract_pages(path: str | Path) -> tuple[list[str], dict]:
    import fitz
    doc = fitz.open(resolve(path)); pages = [p.get_text("text") for p in doc]
    counts = [len(p.strip()) for p in pages]; total = len(pages)
    with_text = sum(c >= 50 for c in counts); sparse = sum(c < 50 for c in counts)
    avg = sum(counts) / max(1, total); garble = _garble_ratio("".join(pages))
    coverage = with_text / max(1, total)
    quality = max(0.0, min(1.0, coverage * .7 + min(avg / 1000, 1) * .25 + (1 - min(garble * 20, 1)) * .05))
    return pages, {"total_pages":total,"pages_with_text":with_text,"average_characters_per_page":round(avg,2),"low_text_page_percentage":round(sparse/max(1,total),4),"garbled_character_ratio":round(garble,6),"quality_score":round(quality,4)}

