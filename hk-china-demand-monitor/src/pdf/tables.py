from __future__ import annotations
from pathlib import Path
from src.common import resolve

def extract_tables(pdf_path, output_dir):
    """Best-effort table extraction; failures never suppress page text."""
    import pdfplumber, csv
    out=resolve(output_dir); out.mkdir(parents=True, exist_ok=True); paths=[]; number=0
    with pdfplumber.open(resolve(pdf_path)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                number += 1; path=out/f"table_{number:03d}.csv"
                with path.open("w", newline="", encoding="utf-8") as f: csv.writer(f).writerows(table)
                paths.append(path)
    return paths

