# Risk Research Lab Architecture

## Purpose

CountryRiskModelLab is being extended into a case-driven Risk Research Lab. The existing Country Risk workspace remains the primary macroeconomic and statistical learning surface. Market Risk is added as a connected research workflow rather than a separate application.

The shared learning chain is:

`Historical event -> market data -> prediction review -> consequence -> risk mathematics -> risk decision`

## Current repository audit

| Area | Classification | Decision |
| --- | --- | --- |
| React/Vite/TypeScript shell | REUSE | Keep the existing component and route conventions. |
| FastAPI backend | REUSE | Add domain services and endpoints beside the current services. |
| Dataset Registry and CSV preview | REUSE/EXTEND | Continue to own country-risk datasets and add case packs as a separate registry. |
| IMF connector and static seed data | REUSE | Keep static data as a dataset option; live refresh remains an operator action. |
| Regression, Forecasting, and VAR services | REUSE | Keep existing model APIs and readiness checks. |
| Model Review, governance, RBAC, audit | REUSE/EXTEND | Audit case imports and formula calculations without weakening controls. |
| Frontend sidebar and home | REFACTOR | Re-label the product and group Country Risk, Market Risk, and shared learning surfaces. |
| Research Case domain | NEW | Versioned, data-driven case-pack loader and validator. |
| Indicator Registry | NEW | Shared stable IDs and provenance metadata for case indicators. |
| Formula Registry and trusted engine | NEW | Approved calculation implementations; imported packs cannot execute code. |
| Historical Event Lab | NEW | Generic staged UI rendered from a Research Case. |
| Scenario, Portfolio, VaR, ES, Case Builder | EXTENSION POINT | Keep APIs and registries open for later milestones; do not fake unavailable historical data. |
| Old user-facing `VAR Lab` label | REFACTOR | Rename to `Vector Autoregression Lab` to reserve VaR for Value at Risk. |

## Runtime boundaries

```text
Frontend routes
  -> typed API client
    -> FastAPI endpoint
      -> domain service
        -> validated registry/data file
```

Case packs contain facts, references, parameters, and content. They never contain executable Python or JavaScript. Formula IDs map to trusted implementations in `formula_engine.py`.

The case registry is separate from the dataset registry:

- `backend/app/data_registry/` stores mutable datasets and audit state.
- `backend/app/research_cases/` can store optional built-in case packs supplied separately for a private/local deployment. The public source checkout excludes private research packs and does not ship built-in case data.
- `backend/app/data_registry/cases/` stores successfully imported packs.

The public checkout starts with an empty Case Library until a valid pack is imported through the UI or supplied separately in a private/local deployment. An import validates into a staging directory and publishes the complete directory only after validation succeeds. Duplicate IDs are rejected so an existing import is preserved.

## Research Case flow

1. Research is assembled into a canonical report and structured Case Pack.
2. The importer validates paths, required artifacts, schema version, JSON, source references, indicator references, formula references, and optional manifest hashes.
3. The Case Library displays the validated case.
4. The Historical Event Lab presents context, prediction, visual reveal, explanation, consequence graph, calculation, and decision stages. The reveal is a pedagogical UI step, not a data-security boundary: the current API sends the full case payload, including actual observations and expected answers, to the browser before prediction.
5. A future case adds content and data, not a custom React page.

## Provenance model

Every observation or claim is labelled where relevant as `OBSERVED`, `CALCULATED`, `DERIVED`, `INTERPOLATED`, `SYNTHETIC`, or `USER_INPUT`. Historical sources are links in the source registry. Synthetic portfolios are visually separated and never presented as historical positions.

## Milestone status

| ID | Milestone | Status | Evidence target |
| --- | --- | --- | --- |
| M00 | Repository audit | PASS | This document and inspected existing services/tests |
| M01 | Architecture and navigation | PASS | Updated shell, routes, and docs |
| M02 | Shared indicator registry | PASS | `/api/indicators`, registry UI, and registry tests |
| M03 | Formula engine | PASS | 21 trusted formulas, API, known-answer tests |
| M04 | Case Pack schema/importer | PASS | ZIP validation and atomic import tests |
| M05 | Historical Event Lab | PASS | Generic staged case UI |
| M06 | UK LDI Golden Case | PASS (private/local fixture) | Private workspace fixture and public import/render flow; no case data is included in the public checkout |
| M07 | Portfolio/risk integration | PASS | Synthetic portfolio to DV01 flow |
| M08 | Learning interactions | PASS (visual staging) | Prediction and visual reveal/decision flow; pre-reveal payload confidentiality is not implemented |
| M09 | QA/regression | PASS | Backend pytest, frontend build, browser smoke |
| M10 | Documentation/release | PASS | Schema, formula, provenance, testing docs |
