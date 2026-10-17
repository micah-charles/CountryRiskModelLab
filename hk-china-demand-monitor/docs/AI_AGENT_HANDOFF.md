# AI agent handoff

The production population implements all pipeline stages, static-data React UI, tests, state schema, scheduling, official HKEX catalogue/title-search discovery, Playwright fallback, Firecrawl capture, and manual fallback. The current dataset contains 26 companies × three financial years = 78 canonical reports and passes `scripts/11_production_audit.py`. Begin with `README.md` and `docs/PRODUCTION_DATASET_AUDIT.md`. Source-of-truth files are configs, raw PDFs, document inventory, metric evidence, and SQLite state. Do not manually edit generated reports or web exports.

To add a company, edit `config/universe_seed.yaml` and rerun stage 01. To debug downloads, inspect `logs/screenshots`, failure HTML, candidate JSON, and inventory status; supply an official URL manually if HKEX blocks automation. For OCR, inspect quality CSV plus preserved embedded/OCR text. To add a metric, update extraction schema, add focused parser tests, rerun stages 04–06, and verify evidence rows. Update weights only in scoring YAML.

Validate the no-source/no-data invariant with `src.qa.validation.validate_all()` and tests. Any value without a page and snippet is a defect, not an invitation to infer.

## Agent Safety Rules

1. Do not invent company data.
2. Do not fill missing metrics from memory.
3. Do not update score inputs unless metric evidence exists.
4. Do not overwrite raw PDFs.
5. Do not delete previous run state unless explicitly asked.
6. Prefer incremental reruns over full regeneration.
7. Keep all changes reproducible and documented.
