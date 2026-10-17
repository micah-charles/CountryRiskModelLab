# Theory and Calculation Integration

## Current architecture

Research Cases are validated and normalized by `research_case_service.py`, served by FastAPI, and rendered by `HistoricalEventLabPage.tsx`. Formula metadata and calculation are already separated: `formula_engine.py` exposes a registry of definitions and maps approved formula IDs to trusted Python implementations. The Formula Playground consumes that same API.

## Reused components

- Existing Case Pack validation, source references, consequence graph and progressive Event Lab stages.
- Existing Formula Registry and trusted calculator map; imported packs never execute formula strings.
- Existing session storage for learner answers, extended to preserve Event Lab stage when the learner visits the Formula Playground.
- Existing provenance fields on case indicators and portfolio warning metadata.

## Schema changes

`predictions.json` questions now support `directional`, `binary`, `numeric`, `categorical`, `ranking` and `free_text` types. A question can reference an `analytical_support` object with one of `formula`, `statistical_model`, `transmission`, `identity`, `rule_of_thumb` or `none`.

Definitions are kept in reusable registries. Formula support resolves through the Formula Registry; transmission, statistical-model, identity and rule-of-thumb support resolve through `analytical_support_service.py`. Before-reveal support is checked for actual or post-reveal fields. This validation and the UI's staged reveal are pedagogical safeguards only: the Event Lab currently loads the complete case payload into the browser before prediction, so its actual values are not confidential from a learner using developer tools.

Legacy questions without a `type` remain directional by default. New Case Packs should declare the type and include explicit options for binary or categorical questions.

## UI changes

The Predict stage renders only controls that match the question semantic. Analytical support is expandable inline so the learner can inspect intuition, symbols, units, assumptions and limitations without leaving the prediction. Formula support includes a link into the existing Playground with the case attached and the formula preselected.

The Reveal stage labels observed, synthetic, derived, calculated and user-input values. The LDI teaching portfolio now includes a visible DV01 substitution, units, first-order P&L result and limitations. The canonical case values remain immutable; Playground edits are session-only.

## Testing strategy

Backend tests cover semantic question normalization, formula and transmission reference resolution, broken-reference rejection, before-reveal protection, and the existing known-answer formula suite. The full frontend build remains the type-check and bundle smoke test. Manual acceptance follows Context -> Predict -> optional theory/formula -> Submit -> Reveal -> calculation -> Decide using the UK 2022 Mini-Budget / LDI case.
