#!/usr/bin/env python3
"""Build private, source-linked Site snapshots and optionally publish them.

The payload directory is ignored and mode 0600. No source excerpts, reports,
raw market CSVs, or credentials are written into the public source tree.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import getpass
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
import urllib.parse


SCRIPT = Path(__file__).resolve()
SITE_ROOT = SCRIPT.parents[1]
WORKSPACE = SCRIPT.parents[2]
PRIVATE_ROOT = SITE_ROOT / "private-data"
PAYLOAD_ROOT = PRIVATE_ROOT / "payloads"
READBACK_ROOT = PRIVATE_ROOT / "readbacks"
SITE_REQUEST = SCRIPT.with_name("private_site_request.py")

HK_NUMERIC_FIELDS = (
    "revenue_total", "revenue_china_or_mainland", "revenue_china_share", "revenue_yoy",
    "gross_profit", "gross_margin", "operating_profit", "operating_margin", "net_profit",
    "net_margin", "capex", "free_cash_flow", "same_store_sales_growth",
    "customer_traffic_growth", "table_turnover_rate", "average_spending_per_customer",
    "average_selling_price", "sales_volume", "delivery_volume", "gmv", "order_volume",
    "active_customers", "monthly_transacting_users", "store_count", "net_store_openings",
    "store_closures", "mall_occupancy_rate", "tenant_sales_growth", "rental_income_growth",
    "inventory", "inventory_yoy", "inventory_days", "trade_receivables", "receivable_days",
    "management_tone_negative",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_json(path: Path, fallback: Any = None) -> Any:
    if not path.exists():
        return fallback
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def write_private_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(encoded)


def number_or_none(raw: Any) -> int | float | None:
    if raw is None or raw == "":
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return int(value) if value.is_integer() else value


def build_country_risk(retrieved_at: str) -> dict[str, Any]:
    path = WORKSPACE / "backend/app/data/imf_all_countries_2010_2026.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Country-risk source panel not found: {path}")
    indicators = ["gdp_growth_yoy", "inflation_yoy", "debt_gdp", "current_account_gdp", "fiscal_balance_gdp", "unemployment_rate"]
    observations = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            country = row.get("country", "").strip()
            country_code = row.get("country_code", "").strip()
            date = row.get("date", "").strip()
            if not country or not country_code or not date:
                continue
            observations.append({
                "countryCode": country_code,
                "country": country,
                "indicatorId": "macro_panel",
                "date": date,
                "values": {indicator: number_or_none(row.get(indicator)) for indicator in indicators},
            })
    observations.sort(key=lambda row: (row["countryCode"], row["date"]))
    if not observations:
        raise RuntimeError("Country-risk panel is empty; refusing to publish an empty snapshot")
    return {
        "schemaVersion": 1,
        "datasetKey": "country-risk",
        "retrievedAt": retrieved_at,
        "periodStart": min(row["date"] for row in observations),
        "periodEnd": max(row["date"] for row in observations),
        "historyComplete": True,
        "missingValuePolicy": "Source blanks remain null; no fill or interpolation.",
        "observations": observations,
        "indicators": [{"indicator_id": key, "name": key.replace("_", " ").title(), "source": "IMF country macro panel", "unit": "Source panel units", "frequency": "annual"} for key in indicators],
        "sources": [{"publisher": "International Monetary Fund", "title": "Country macroeconomic indicator panel", "sourceUrl": "https://www.imf.org/en/Data", "sourceFile": path.name, "reuse": "Private research snapshot; retain IMF attribution and source terms."}],
        "sourceStatus": {"country-risk": {"status": "current", "lastSuccessAt": retrieved_at, "recordCount": len(observations)}},
    }


def build_cases(retrieved_at: str) -> dict[str, Any]:
    root = WORKSPACE / "backend/app/research_cases"
    cases = []
    for folder in sorted(path for path in root.iterdir() if path.is_dir()):
        case = read_json(folder / "case.json")
        if not isinstance(case, dict) or not case.get("case_id"):
            continue
        item = {key: case[key] for key in (
            "case_id", "case_type", "status", "research_cutoff", "title", "short_title", "summary",
            "countries", "regions", "start_date", "end_date", "event_start", "event_end",
            "anchor_event_date", "themes", "difficulty", "trigger", "background", "learning_objectives",
            "formula_refs", "indicator_ids", "evidence_policy",
        ) if key in case}
        item["timeline"] = read_json(folder / "timeline.json", [])
        item["predictions"] = read_json(folder / "predictions.json", [])
        item["consequenceGraph"] = read_json(folder / "consequence_graph.json", {})
        item["sources"] = read_json(folder / "sources.json", [])
        calculations = {}
        calculation_dir = folder / "calculations"
        if calculation_dir.is_dir():
            for calculation in sorted(calculation_dir.glob("*.json")):
                calculations[calculation.stem] = read_json(calculation)
        item["calculations"] = calculations
        cases.append(item)
    if not cases:
        raise RuntimeError("No curated case manifests were found")
    return {
        "schemaVersion": 1,
        "datasetKey": "research-cases",
        "retrievedAt": retrieved_at,
        "cases": cases,
        "sourceStatus": {"research-cases": {"status": "current", "lastSuccessAt": retrieved_at, "caseCount": len(cases)}},
        "contentPolicy": "Curated metadata and source references only; no reports, raw market series, or full document text included.",
    }


def build_hk_demand(retrieved_at: str) -> dict[str, Any]:
    root = WORKSPACE / "hk-china-demand-monitor/data/processed"
    company_path = root / "company_year_metrics.json"
    if not company_path.is_file():
        raise FileNotFoundError(f"HK company metrics not found: {company_path}")
    companies = []
    for row in read_json(company_path, []):
        if not isinstance(row, dict):
            continue
        item = {key: row.get(key) for key in ("stock_code", "company_name", "industry", "financial_year")}
        for field in HK_NUMERIC_FIELDS:
            item[field] = number_or_none(row.get(field))
        companies.append(item)

    industry_path = root / "industry_summary.csv"
    industries = []
    with industry_path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            industries.append({
                "industry": row.get("industry", ""),
                "financial_year": number_or_none(row.get("financial_year")),
                "demand_pressure_score": number_or_none(row.get("demand_pressure_score")),
                "company_count": number_or_none(row.get("company_count")),
            })

    evidence_path = root / "metric_evidence.csv"
    evidence = []
    if evidence_path.is_file():
        with evidence_path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                evidence.append({
                    "stock_code": row.get("stock_code", ""),
                    "financial_year": number_or_none(row.get("financial_year")),
                    "metric": row.get("metric", ""),
                    "value": number_or_none(row.get("value")),
                    "unit": row.get("unit", ""),
                    "report_title": row.get("report_title", ""),
                    "source_document_url": row.get("source_document_url", ""),
                    "hkex_result_page_url": row.get("hkex_result_page_url", ""),
                    "pdf_page": number_or_none(row.get("pdf_page")),
                    "extraction_method": row.get("extraction_method", ""),
                    "confidence": number_or_none(row.get("confidence")),
                    "validation_status": row.get("validation_status", ""),
                    "missing_reason": row.get("missing_reason", ""),
                })

    sources = []
    inventory = root / "document_inventory.csv"
    if inventory.is_file():
        with inventory.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                sources.append({key: row.get(source, "") for key, source in {
                    "stock_code": "stock_code", "company_name": "company_name", "financial_year": "financial_year",
                    "report_title": "document_title", "release_date": "release_date", "hkex_url": "hkex_url",
                    "source_page_url": "source_page_url", "source_method": "source_method", "sha256": "sha256",
                    "download_status": "download_status",
                }.items()})

    if not companies:
        raise RuntimeError("HK company metrics are empty; refusing to publish an empty snapshot")
    return {
        "schemaVersion": 1,
        "datasetKey": "hk-demand",
        "retrievedAt": retrieved_at,
        "companies": companies,
        "industrySummary": industries,
        "evidence": evidence,
        "sources": sources,
        "companyCount": len(companies),
        "evidenceCount": len(evidence),
        "sourceStatus": {"hk-demand": {"status": "current", "lastSuccessAt": retrieved_at, "companyYears": len(companies), "evidenceRows": len(evidence)}},
        "contentPolicy": "Metric values, page citations, extraction confidence and missing reasons only. No report PDF, local file path, OCR page text, or source excerpt is included.",
    }


def load_catalog() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    backend = WORKSPACE / "backend"
    interpreter = backend / ".venv/bin/python"
    if not interpreter.exists():
        interpreter = Path(sys.executable)
    code = """
import json, sys
sys.path.insert(0, '.')
from app.services.formula_engine import list_formula_definitions
from app.services.indicator_registry_service import list_indicator_definitions
formulas = [item.model_dump(mode='json') for item in list_formula_definitions()]
indicators = [item.model_dump(mode='json') for item in list_indicator_definitions()]
print(json.dumps({'formulas': formulas, 'indicators': indicators}, ensure_ascii=False, allow_nan=False))
"""
    result = subprocess.run([str(interpreter), "-c", code], cwd=backend, check=True, capture_output=True, text=True)
    loaded = json.loads(result.stdout)
    return loaded["indicators"], loaded["formulas"]


def build_catalog(retrieved_at: str) -> dict[str, Any]:
    indicators, formulas = load_catalog()
    return {
        "schemaVersion": 1,
        "datasetKey": "catalog",
        "retrievedAt": retrieved_at,
        "indicators": indicators,
        "formulas": formulas,
        "sourceStatus": {"catalog": {"status": "current", "lastSuccessAt": retrieved_at, "indicatorCount": len(indicators), "formulaCount": len(formulas)}},
    }


def build_all() -> dict[str, dict[str, Any]]:
    retrieved_at = utc_now()
    return {
        "country-risk": build_country_risk(retrieved_at),
        "research-cases": build_cases(retrieved_at),
        "hk-demand": build_hk_demand(retrieved_at),
        "catalog": build_catalog(retrieved_at),
    }


def run_private_site_request(token: str, site_origin: str, url: str, method: str, *, response_file: Path | None = None, payload_file: Path | None = None) -> tuple[int, dict[str, Any]]:
    config: dict[str, Any] = {"url": url, "site_origin": site_origin, "token": token, "method": method}
    if response_file:
        config["response_file"] = str(response_file)
    if payload_file:
        config["payload_file"] = str(payload_file)
    completed = subprocess.run([sys.executable, str(SITE_REQUEST)], input=json.dumps(config), capture_output=True, text=True, check=False)
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    summary = json.loads(lines[-1]) if lines else {"status": 0, "error": completed.stderr.strip() or "Private Site request failed"}
    return int(summary.get("status", 0)), summary


def publish(payloads: dict[str, dict[str, Any]], site_origin: str, token: str) -> list[dict[str, Any]]:
    site_origin = site_origin.rstrip("/")
    results = []
    PAYLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    READBACK_ROOT.mkdir(parents=True, exist_ok=True)
    for dataset, snapshot in payloads.items():
        safe_key = urllib.parse.quote(dataset, safe="")
        current_path = READBACK_ROOT / f"{dataset}-before.json"
        current_status, current_summary = run_private_site_request(token, site_origin, f"{site_origin}/api/snapshots/{safe_key}", "GET", response_file=current_path)
        current_version = None
        if current_status == 200:
            current = read_json(current_path, {})
            current_version = current.get("version")
            if not isinstance(current_version, int):
                raise RuntimeError(f"Current {dataset} response did not contain an integer version")
        elif current_status != 404:
            raise RuntimeError(f"Could not read current {dataset} snapshot: {current_summary}")

        payload_path = PAYLOAD_ROOT / f"{dataset}.json"
        write_private_json(payload_path, snapshot)
        ingest_path = PAYLOAD_ROOT / f"{dataset}-ingest.json"
        write_private_json(ingest_path, {"expectedVersion": current_version, "snapshot": snapshot})
        post_status, post_summary = run_private_site_request(token, site_origin, f"{site_origin}/api/admin/snapshots/{safe_key}/ingest", "POST", payload_file=ingest_path)
        if post_status != 201:
            raise RuntimeError(f"Could not publish {dataset} snapshot: {post_summary}")

        verified_path = READBACK_ROOT / f"{dataset}-after-v{post_summary.get('version')}.json"
        verify_status, verify_summary = run_private_site_request(token, site_origin, f"{site_origin}/api/snapshots/{safe_key}", "GET", response_file=verified_path)
        if verify_status != 200:
            raise RuntimeError(f"Readback failed for {dataset}: {verify_summary}")
        verified = read_json(verified_path, {})
        if verified.get("version") != post_summary.get("version") or verified.get("snapshot") != snapshot:
            raise RuntimeError(f"Readback content or version mismatch for {dataset}")
        if verified.get("manifest", {}).get("snapshotSha256") != post_summary.get("snapshotSha256"):
            raise RuntimeError(f"Readback SHA-256 mismatch for {dataset}")
        results.append({"datasetKey": dataset, "version": post_summary["version"], "snapshotSha256": post_summary["snapshotSha256"], "changeCount": post_summary.get("changeCount"), "readbackVerified": True})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true", help="Read the current cloud version and publish, then verify the full readback.")
    parser.add_argument("--dataset", action="append", choices=["country-risk", "research-cases", "hk-demand", "catalog"], help="Limit the run to selected datasets; repeat for more than one.")
    parser.add_argument("--site-origin", default=os.environ.get("ECON_SITE_ORIGIN", "https://econ-research-hub.ckstks246335.chatgpt.site"))
    args = parser.parse_args()
    payloads = build_all()
    if args.dataset:
        payloads = {key: value for key, value in payloads.items() if key in args.dataset}
    for dataset, value in payloads.items():
        size = len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        if size > 3 * 1024 * 1024:
            raise RuntimeError(f"{dataset} snapshot is {size:,} bytes, larger than the Site 3 MiB limit")
        write_private_json(PAYLOAD_ROOT / f"{dataset}.json", value)
    if not args.publish:
        print(json.dumps({"built": {key: {"bytes": (PAYLOAD_ROOT / f"{key}.json").stat().st_size, "counts": {name: len(value) for name, value in snapshot.items() if isinstance(value, list)}} for key, snapshot in payloads.items()}, "directory": str(PAYLOAD_ROOT), "network": "not used"}, indent=2))
        return 0
    token = os.environ.get("OAI_SITES_BYPASS_TOKEN")
    if not token:
        if not sys.stdin.isatty():
            raise RuntimeError("Provide the ephemeral Site service credential via OAI_SITES_BYPASS_TOKEN at runtime; never pass it as an argument or write it to a file.")
        token = getpass.getpass("Private Site service credential: ")
    results = publish(payloads, args.site_origin, token)
    print(json.dumps({"published": results}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"Snapshot sync stopped safely: {error}", file=sys.stderr)
        raise SystemExit(1)
