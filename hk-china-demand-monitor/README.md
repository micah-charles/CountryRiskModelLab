# HK China Demand Monitor

An evidence-first research pipeline for assessing Mainland China domestic demand from Hong Kong-listed companies' annual reports. It builds a configurable company universe, discovers or accepts official annual-report links, preserves PDFs, extracts page-bounded Markdown with OCR fallback, records every supported and missing metric, calculates transparent 0–5 pressure scores, and publishes an auditable local dashboard.

The system never fills a missing value from memory. A metric is usable only when it has a source document, PDF page, exact snippet, extraction method, confidence, and validation status. Otherwise it is stored as `null` with `missing_reason`.

## Quick start

```bash
cd /Volumes/ExtremePro/AIWorkspace/Econ/hk-china-demand-monitor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install
cd web && npm install && cd ..
npx playwright install chromium
python scripts/07_run_all.py --years 3 --max-companies 3
python -m pytest tests
```

For OCR on macOS, install `brew install tesseract tesseract-lang poppler`; on Ubuntu/Debian install `tesseract-ocr poppler-utils tesseract-ocr-chi-sim tesseract-ocr-chi-tra`.

HKEX automation is courteous and cache-first. The primary deterministic adapter resolves issuer IDs from HKEX's active-security catalogue, then submits the official title-search form by issuer, date range, and `Annual Report`. Playwright remains the browser fallback. If search is unavailable, add official links to `config/manual_report_links.csv`; all downstream stages are source-agnostic. Automated discovery never bypasses captchas or access controls.

## Commands

```bash
python scripts/01_build_universe.py
python scripts/02_hkex_search_download.py --years 3
python scripts/03_pdf_to_markdown.py
python scripts/04_extract_metrics.py --no-llm
python scripts/05_score_domestic_demand.py
python scripts/06_generate_report.py --export-web-data
python scripts/08_incremental_update.py --years 3 --export-web-data
python scripts/08_incremental_update.py --stock-code 02020 --force
python scripts/09_schedule_weekly.py --target launchd --weekday monday --time 08:00
python scripts/10_generate_architecture_docs.py
```

Start the dashboard with `cd web && npm run dev`, then open `http://127.0.0.1:5173/`. Pages include dashboard, companies, industries, company detail, evidence explorer, sources, and quality warnings. Exported data is static JSON under `web/public/data/`.

## Data sources and fallback order

Source priority is configured in `config/update_policy.yaml`: HKEX Playwright, optional browser-use, optional Firecrawl, then analyst-supplied manual links. HKEXnews remains preferred whenever duplicate official sources exist. Firecrawl is available at `/Volumes/ExtremePro/AIWorkspace/firecrawl`; the workspace is a runnable monorepo whose documented local API port is 3002. Enable it only after starting that service and setting `.env` values.

Add or remove companies in `config/universe_seed.yaml`. The universe builder validates five-digit codes and rejects duplicates. Verify issuer metadata against HKEX before production research.

## Outputs

- `data/processed/document_inventory.csv`: discovery and download source of truth.
- `data/interim/markdown/{stock}/{year}/annual_report.md`: YAML metadata and explicit page markers.
- `data/processed/company_year_metrics.{csv,json}`: wide analytical values.
- `data/processed/metric_evidence.{csv,jsonl}`: long evidence contract, including explicit missing records.
- `data/processed/source_documents.csv` and `source_page_index.csv`: document/page lineage.
- `data/processed/demand_pressure_scores.csv`: company-year 0–5 scores and component JSON.
- `data/processed/industry_summary.csv`: equal-company industry rollups.
- `data/reports/china_domestic_demand_summary.{md,html}`: cautious deterministic summary.
- `state/document_state.sqlite`: incremental document, run, cache, and lineage state.

Scores are reweighted across supported components only. Coverage controls score confidence, so a numerically extreme low-confidence score is not equivalent to a broad evidence base. Review `config/scoring_weights.yaml` to change weights.

## QA and limitations

Run `python -m pytest tests`, `npm run qa:browser`, and `cd web && npm run build`. External HKEX UI tests may fail when its structure, availability, or anti-automation controls change; failure snapshots are saved in `logs/`. Deterministic regex extraction intentionally favours precision and traceability over recall. Complex financial tables, inconsistent units, multi-column year alignment, and OCR-heavy pages require manual review. This is research software, not investment advice.

Run the strict full-population gate with `python scripts/11_production_audit.py`. Its human-readable evidence is stored in `docs/PRODUCTION_DATASET_AUDIT.md`. The current production population contains 26 companies, three annual reports per company, 78 PDFs, 22,246 indexed pages, and 2,730 evidence/missing records.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Data flow](docs/DATA_FLOW.md)
- [AI agent handoff](docs/AI_AGENT_HANDOFF.md)
- [Incremental updates](docs/INCREMENTAL_UPDATE.md)
- [Runbook](docs/RUNBOOK.md)
- [Production dataset audit](docs/PRODUCTION_DATASET_AUDIT.md)

Raw PDFs are immutable inputs. Do not delete state or overwrite raw reports. Token-consuming enhancements must key their cache on source content, schema version, and prompt version; deterministic extraction remains the default.
