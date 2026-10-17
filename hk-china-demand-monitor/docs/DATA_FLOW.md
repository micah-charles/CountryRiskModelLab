# Data flow

| Stage | Script | Input | Output | Primary key | Safe rerun | Incremental behaviour |
|---|---|---|---|---|---|---|
| Universe | `01_build_universe.py` | seed YAML | company universe CSV | stock code | Yes | deterministic rebuild |
| Discovery | `02_hkex_search_download.py` | universe, HKEX, manual links | inventory, PDFs | document ID | Yes | cache and URL dedupe |
| Extraction | `03_pdf_to_markdown.py` | PDF | raw text, OCR, Markdown, pages, quality | stock/year/page | Yes | selected stock only |
| Metrics | `04_extract_metrics.py` | Markdown, schema | metrics and evidence | stock/year/metric | Yes | selected records merged |
| Scores | `05_score_domestic_demand.py` | evidence-backed metrics, weights | company and industry scores | stock/year | Yes | selected company then rollup |
| Reporting | `06_generate_report.py` | processed records | Markdown, HTML, web JSON | output name | Yes | cheap deterministic refresh |
| State | `08_incremental_update.py` | inventory, hashes, SQLite | change log and manifests | run/document ID | Yes | skips identical hashes |

Failures are recorded and processing continues where possible. A missing PDF does not become a metric. OCR errors preserve embedded text. A missing label creates an explicit null evidence row. Atomic/cached acquisition prevents partial PDFs from being accepted.

