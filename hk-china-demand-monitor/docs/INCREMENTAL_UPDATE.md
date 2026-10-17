# Incremental update

The updater loads inventory and SQLite state, courteously discovers candidates, computes PDF SHA-256 and Markdown content hashes, and classifies each document as new, changed, or unchanged. Identical URL metadata with identical PDF bytes is unchanged; changed bytes re-run PDF extraction. A Markdown-only change re-runs metrics and downstream scores without clobbering the source text. Partial scripts merge selected-stock records into full datasets.

State tables track documents, pipeline runs, processing cache, and metric lineage. JSON manifests make the latest run inspectable without SQLite. The change log records steps reprocessed and skipped. Run `--dry-run` to inspect local state without file changes; `--force` reprocesses selected documents while preserving raw PDFs.

LLM use is disabled by default. Any future LLM operation must use a stable hash of stock, year, section/metric, source page text, prompt version, and schema version. Cache hits are reusable only for exact input hashes, and outputs remain candidate extractions until page-grounded.

```bash
python scripts/08_incremental_update.py --years 3 --export-web-data
python scripts/08_incremental_update.py --stock-code 02020 --force
python scripts/08_incremental_update.py --dry-run
```

