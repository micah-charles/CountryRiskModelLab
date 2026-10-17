# Case Pack Schema v1

Case Packs are ZIP files with `schema_version` `1.0`. The importer accepts a legacy v1 pack without `formula_refs.json` with a warning so the supplied UK LDI Golden Case remains importable; new packs should include it. It also accepts the common ChatGPT export aliases `case_pack_schema_version`, `question`, `question_type`, and object-shaped formula references, and generates the required `indicators.csv` from wide `market_series/*.csv` files. The extracted copy is normalized before validation; the uploaded ZIP is never modified.

## Required files

`manifest.json`, `case.json`, `timeline.json`, `indicators.csv`, `predictions.json`, `consequence_graph.json`, `sources.json`, `portfolio_learning.json`, `report.pdf`, and `README.md` are required. `market_series/` and `calculations/` are optional directories. `formula_refs.json` is recommended and becomes required for new packs that declare formula connections.

## Core fields

`case.json` contains `case_id`, `schema_version`, title/summary metadata, countries, date boundaries, trigger, themes, and references to its artifacts. The normalized runtime domain also exposes `short_title`, `start_date`, `end_date`, `anchor_event_date`, `timeline`, `actual_market_moves`, `predictions`, `consequences`, `portfolio_impacts`, `formula_refs`, `lessons`, `sources`, `datasets`, and `artifacts`.

Each prediction question may declare:

```json
{
  "prediction_id": "p2",
  "prompt": "What happens to long-duration bond prices when yields rise?",
  "type": "directional",
  "analytical_support": {
    "type": "formula",
    "reference_id": "RATE_BOND_PRICE_SENSITIVITY",
    "available_before_reveal": true
  }
}
```

Supported question types are `directional`, `binary`, `numeric`, `categorical`, `ranking` and `free_text`. Analytical support types are `formula`, `statistical_model`, `transmission`, `identity`, `rule_of_thumb` and `none`. These are references to common registries, not executable content or duplicated formula definitions.

## Integrity rules

- ZIP paths must be relative, unique, regular files without `..` traversal.
- The manifest and case schema versions must match and be supported.
- Manifest file entries must exist; optional `bytes` and `sha256` values are checked.
- JSON artifacts must parse.
- Every `source_id`, `source_ids`, and `source_refs` reference must resolve in `sources.json`.
- Case indicator IDs must appear in `indicators.csv` and the common Indicator Registry.
- Formula IDs must resolve in the common Formula Registry.
- Consequence graph edges must reference declared nodes.
- Validation errors prevent import and no partial pack is registered.

## Adding a case

Research -> assemble evidence -> create the pack -> run the importer -> inspect warnings -> open the new case from the library. No application code changes are needed for a new valid pack.
