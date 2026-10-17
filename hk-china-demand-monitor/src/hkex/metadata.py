from __future__ import annotations
import re
from urllib.parse import urlsplit, urlunsplit

ANNUAL_PATTERNS = ("annual report", "年報", "年度報告", "financial statements/esg information - [annual report]")
def is_annual_report(title: str) -> bool:
    t = " ".join(title.lower().split())
    return any(p in t for p in ANNUAL_PATTERNS) and not ("esg" in t and "annual report" not in t)
def canonical_url(url: str) -> str:
    if not url: return ""
    p = urlsplit(url); return urlunsplit((p.scheme.lower(), p.netloc.lower(), re.sub(r"/+", "/", p.path), p.query, ""))
def normalize_title(title: str) -> str: return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")

