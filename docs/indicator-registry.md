# Indicator Registry

Indicators have stable IDs shared by cases and datasets. A case supplies observations and provenance; the registry supplies reusable display and interpretation metadata.

The first registry includes rates, FX, equity, credit, volatility, macro, policy, and market-risk families. Each definition carries `indicator_id`, `name`, `family`, `description`, `unit`, `direction_semantics`, `frequency`, `source`, `source_series_id`, `transformation`, and `display_format`.

Case-specific observations are never silently converted into a new indicator definition. If a new case needs a new indicator, add a reviewed registry definition and then reference it from the pack.

