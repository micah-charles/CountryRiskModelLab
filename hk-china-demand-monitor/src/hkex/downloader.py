from __future__ import annotations
import hashlib, time
from pathlib import Path
import requests
from src.common import resolve, sha256_file

def download_pdf(url: str, destination: str | Path, retries: int = 3, delay: float = 2) -> dict:
    dest = resolve(destination); dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 4 and dest.read_bytes()[:4] == b"%PDF":
        return {"status":"cached","file_size":dest.stat().st_size,"sha256":sha256_file(dest)}
    error = ""
    for attempt in range(retries):
        try:
            with requests.get(url, timeout=45, stream=True, headers={"User-Agent":"hk-china-demand-monitor/0.1 research; cache-first"}) as r:
                r.raise_for_status(); tmp = dest.with_suffix(".part")
                with tmp.open("wb") as f:
                    for chunk in r.iter_content(1024 * 128): f.write(chunk)
                if tmp.read_bytes()[:4] != b"%PDF": raise ValueError("response is not a PDF")
                tmp.replace(dest)
            return {"status":"downloaded","file_size":dest.stat().st_size,"sha256":sha256_file(dest)}
        except Exception as exc:
            error = str(exc); time.sleep(delay * (2 ** attempt))
    return {"status":"failed","file_size":0,"sha256":"","error_message":error}

