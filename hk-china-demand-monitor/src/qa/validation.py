from __future__ import annotations
import json, re
from pathlib import Path
from src.common import read_csv, resolve

def validate_all():
    errors=[]; inventory=read_csv("data/processed/document_inventory.csv")
    for d in inventory:
        for key in ("stock_code","financial_year","document_title","local_pdf_path"):
            if not d.get(key): errors.append(f"document missing {key}: {d}")
        if d.get("download_status") in ("downloaded","cached") and not resolve(d["local_pdf_path"]).exists(): errors.append(f"PDF absent: {d['local_pdf_path']}")
        md=resolve(f"data/interim/markdown/{d['stock_code']}/{d['financial_year']}/annual_report.md")
        if md.exists() and (not md.read_text().startswith("---") or "<!-- page:" not in md.read_text()): errors.append(f"invalid markdown contract: {md}")
    for e in read_csv("data/processed/metric_evidence.csv"):
        if not e.get("evidence_text") and not e.get("missing_reason"): errors.append(f"metric lacks evidence or missing_reason: {e.get('stock_code')} {e.get('metric')}")
        if e.get("value") and not e.get("pdf_page"): errors.append(f"metric value lacks page: {e.get('metric')}")
    for s in read_csv("data/processed/demand_pressure_scores.csv"):
        if s.get("demand_pressure_score") not in (None,"") and not 0<=float(s["demand_pressure_score"])<=5: errors.append(f"score out of range: {s}")
    return errors

