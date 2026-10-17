import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { IndicatorDefinition } from "../types/research";

export function IndicatorRegistryPage() {
  const [indicators, setIndicators] = useState<IndicatorDefinition[]>([]);
  const [family, setFamily] = useState("all");
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.indicators().then(setIndicators).catch((err) => setError(err instanceof Error ? err.message : "Could not load the indicator registry."));
  }, []);

  const families = useMemo(() => ["all", ...Array.from(new Set(indicators.map((item) => item.family))).sort()], [indicators]);
  const visible = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return indicators.filter((item) => {
      const matchesFamily = family === "all" || item.family === family;
      const matchesQuery = !normalized || [item.indicator_id, item.name, item.description, item.source].join(" ").toLowerCase().includes(normalized);
      return matchesFamily && matchesQuery;
    });
  }, [family, indicators, query]);

  return (
    <div className="page">
      <header className="page-header">
        <span className="eyebrow">Shared Data Layer</span>
        <h1>Indicator Registry</h1>
        <p>Stable indicator definitions used by Case Packs, market evidence, formulas, and country-risk datasets.</p>
      </header>
      {error && <p className="error">{error}</p>}
      <section className="panel">
        <div className="two-column registry-filters">
          <label className="field"><span>Search indicators</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="ID, name, source..." /></label>
          <label className="field"><span>Family</span><select value={family} onChange={(event) => setFamily(event.target.value)}>{families.map((item) => <option key={item} value={item}>{item === "all" ? "All families" : item}</option>)}</select></label>
        </div>
        <p className="muted">Showing {visible.length} of {indicators.length} registered indicators. IDs are the stable references used in imported Case Packs.</p>
      </section>
      <section className="panel table-wrap">
        <table>
          <thead><tr><th>Indicator</th><th>Family</th><th>Unit</th><th>Frequency</th><th>Source / transformation</th><th>Direction semantics</th></tr></thead>
          <tbody>{visible.map((item) => <tr key={item.indicator_id}><td><strong>{item.name}</strong><br /><code>{item.indicator_id}</code><p className="muted">{item.description}</p></td><td>{item.family}</td><td>{item.unit}</td><td>{item.frequency}</td><td>{item.source}<br /><span className="muted">{item.transformation}</span></td><td>{item.direction_semantics}</td></tr>)}</tbody>
        </table>
        {!visible.length && <p className="empty">No indicators match this filter.</p>}
      </section>
    </div>
  );
}
