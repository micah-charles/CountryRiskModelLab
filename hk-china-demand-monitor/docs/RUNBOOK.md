# Runbook

```bash
# first sample
python scripts/07_run_all.py --years 3 --max-companies 3
# full universe
python scripts/07_run_all.py --years 3
# incremental / one company / force
python scripts/08_incremental_update.py --years 3
python scripts/08_incremental_update.py --stock-code 02020 --years 3
python scripts/08_incremental_update.py --stock-code 02020 --years 3 --force
# web
python scripts/06_generate_report.py --export-web-data
cd web && npm run dev
# QA
python -m pytest tests
npm run qa:browser
cd web && npm run build
python scripts/11_production_audit.py
```

If discovery fails, inspect screenshots and add official links to `config/manual_report_links.csv`. If a document is corrupt, keep it, mark the inventory failure, and acquire a verified replacement under a distinct document identity. If quality is below 0.65, inspect raw and OCR text and cite the original PDF during manual review. Generate a launchd definition using script 09; review it before loading.
