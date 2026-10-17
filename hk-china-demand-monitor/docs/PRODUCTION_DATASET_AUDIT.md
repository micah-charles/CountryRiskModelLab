# Production Dataset Audit

Status: **PASS**
Audited: `2026-07-11T23:35:56.611633+00:00`

| Check | Status | Evidence |
|---|---|---|
| seed_universe | pass | 26 unique companies |
| three_year_document_coverage | pass | coverage distribution {3: 26} |
| pdf_integrity | pass | 78/78 PDFs pass status, header, size, and SHA-256; bad=[] |
| source_document_lineage | pass | 78 source rows |
| page_index | pass | 22246 indexed pages; expected 22246 |
| markdown_contract | pass | 78/78 Markdown reports have front matter and page markers |
| company_year_metrics | pass | 78 company-year rows |
| evidence_contract | pass | 2730/2730 rows; invalid=0 |
| score_bounds | pass | 78 score rows; out of range=0 |
| quality_log | pass | 78 quality rows; 9 flagged |
| incremental_state | pass | 78 state documents |
| web_exports | pass | missing=[] |
