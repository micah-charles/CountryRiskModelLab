import type { ImfIndicator } from "../types/dataset";

export function ImfIndicatorSelector({ indicators, selected, setSelected }: { indicators: ImfIndicator[]; selected: string[]; setSelected: (value: string[]) => void }) {
  function toggle(code: string) {
    setSelected(selected.includes(code) ? selected.filter((item) => item !== code) : [...selected, code]);
  }
  return (
    <section className="panel">
      <h3>Indicators</h3>
      <div className="indicator-grid">
        {indicators.map((indicator) => (
          <button key={indicator.code} className={selected.includes(indicator.code) ? "indicator selected" : "indicator"} onClick={() => toggle(indicator.code)}>
            <strong>{indicator.label}</strong>
            <span>IMF code: {indicator.code}</span>
            <span>{indicator.category}</span>
            <p>{indicator.description}</p>
            <p>{indicator.typical_country_risk_interpretation}</p>
            <small>Expected relationship to bond yields: {indicator.expected_relationship_to_bond_yield}</small>
          </button>
        ))}
      </div>
    </section>
  );
}

