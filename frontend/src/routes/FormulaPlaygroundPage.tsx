import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { FormulaCalculation, FormulaDefinition, ResearchCase } from "../types/research";
import { formatFormula } from "../utils/formulaDisplay";

function display(value: unknown) {
  if (typeof value === "number") return Math.abs(value) >= 1000 ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : value.toLocaleString(undefined, { maximumFractionDigits: 6 });
  return typeof value === "string" ? value : JSON.stringify(value);
}

function ProvenanceBadge({ value }: { value: string }) {
  return <span className="provenance-badge">{value.replace(/_/g, " ")}</span>;
}

const rateCaseFormulaIds = ["RATE_DV01", "RATE_BOND_PRICE_SENSITIVITY", "RATE_DURATION_PRICE"];
const fxCaseFormulaIds = ["FX_MOVE_PERCENT", "FX_UNHEDGED_CARRY_RETURN", "LEVERAGED_RETURN"];

export function FormulaPlaygroundPage({ activeCaseId, requestedFormulaId, onReturnToEvent }: { activeCaseId?: string; requestedFormulaId?: string; onReturnToEvent?: () => void }) {
  const [formulas, setFormulas] = useState<FormulaDefinition[]>([]);
  const [selectedId, setSelectedId] = useState("RATE_DV01");
  const [definition, setDefinition] = useState<FormulaDefinition | null>(null);
  const [parameters, setParameters] = useState<Record<string, unknown>>({});
  const [exampleParameters, setExampleParameters] = useState<Record<string, unknown>>({});
  const [caseParameters, setCaseParameters] = useState<Record<string, unknown> | null>(null);
  const [origin, setOrigin] = useState<"formula_example" | "case_values" | "user_modified">("formula_example");
  const [calculation, setCalculation] = useState<FormulaCalculation | null>(null);
  const [error, setError] = useState("");
  const [caseData, setCaseData] = useState<ResearchCase | null>(null);
  const activePortfolio = (caseData?.portfolio_impacts[0] || {}) as Record<string, unknown>;
  const activePortfolioExample = (activePortfolio.example || activePortfolio.default_parameters || {}) as Record<string, unknown>;
  const activeCaseFormulaIds = activePortfolioExample.entry_usdjpy !== undefined ? fxCaseFormulaIds : rateCaseFormulaIds;

  useEffect(() => {
    api.formulas().then((result) => {
      setFormulas(result);
      if (requestedFormulaId && result.some((item) => item.formula_id === requestedFormulaId)) setSelectedId(requestedFormulaId);
    }).catch((err) => setError(err instanceof Error ? err.message : "Could not load formulas."));
    if (activeCaseId) api.researchCase(activeCaseId).then(setCaseData).catch(() => undefined);
  }, [activeCaseId, requestedFormulaId]);

  const selectedDefinition = useMemo(() => formulas.find((item) => item.formula_id === selectedId) || formulas[0] || null, [formulas, selectedId]);

  useEffect(() => {
    if (!selectedDefinition) return;
    const example = selectedDefinition.worked_examples[0]?.inputs || Object.fromEntries(selectedDefinition.variables.map((item) => [item.name, item.default]));
    setDefinition(selectedDefinition);
    setExampleParameters(example);
    setParameters(example);
    setOrigin("formula_example");
  }, [selectedDefinition]);

  useEffect(() => {
    if (!caseData) return;
    const portfolio = (caseData.portfolio_impacts[0] || {}) as Record<string, unknown>;
    const example = (portfolio.example || portfolio.default_parameters || {}) as Record<string, unknown>;
    if (example.entry_usdjpy !== undefined) {
      const entry = Number(example.entry_usdjpy);
      const exit = Number(example.exit_usdjpy);
      const holdingFraction = Number(example.holding_days) / 365;
      const fundingGrowth = 1 + Number(example.jpy_funding_rate_annual) * holdingFraction;
      const unleveredReturn = entry && exit && fundingGrowth ? ((1 + Number(example.usd_asset_yield_annual) * holdingFraction) * exit / entry) / fundingGrowth - 1 : 0;
      setCaseParameters({
        entry_usdjpy: entry,
        exit_usdjpy: exit,
        holding_days: Number(example.holding_days),
        usd_asset_yield_annual: Number(example.usd_asset_yield_annual),
        jpy_funding_rate_annual: Number(example.jpy_funding_rate_annual),
        leverage: Number(example.leverage),
        unlevered_return: unleveredReturn,
      });
      return;
    }
    const positionValue = Number(example.market_value_gbp ?? example.position_usd ?? 0);
    const duration = Number(example.modified_duration ?? 0);
    const dv01 = Number(example.dv01_gbp_per_bp ?? (positionValue && duration ? duration * positionValue * 0.0001 : 0));
    setCaseParameters({ position_value: positionValue, modified_duration: duration || (positionValue ? dv01 / (positionValue * 0.0001) : 18), yield_shock_bp: Number(example.shock_bp ?? example.yield_shock_bp ?? 50) });
  }, [caseData]);

  useEffect(() => {
    if (caseParameters && activeCaseFormulaIds.includes(selectedId)) {
      setParameters(caseParameters);
      setOrigin("case_values");
    }
  }, [activeCaseFormulaIds, caseParameters, selectedId]);

  useEffect(() => {
    if (!definition || !Object.keys(parameters).length) return;
    let cancelled = false;
    setError("");
    api.calculateFormula({ formula_id: definition.formula_id, parameters, input_origin: origin }).then((result) => { if (!cancelled) setCalculation(result); }).catch((err) => { if (!cancelled) { setCalculation(null); setError(err instanceof Error ? err.message : "Calculation failed."); } });
    return () => { cancelled = true; };
  }, [definition, parameters, origin]);

  function changeParameter(name: string, raw: string, type: string) {
    if (type === "number") {
      setParameters((current) => ({ ...current, [name]: raw === "" ? "" : Number(raw) }));
    } else {
      try { setParameters((current) => ({ ...current, [name]: JSON.parse(raw) })); } catch { return; }
    }
    setOrigin("user_modified");
  }

  function resetExample() { setParameters(exampleParameters); setOrigin("formula_example"); }
  function resetCase() { if (caseParameters && activeCaseFormulaIds.includes(selectedId)) { setParameters(caseParameters); setOrigin("case_values"); } }

  return (
    <div className="page formula-page">
      <header className="page-header"><div className="section-title-row"><div><span className="eyebrow">Risk Mathematics</span><h1>Formula Playground</h1><p>Change inputs at runtime, inspect the calculation, and keep canonical case values separate from learner edits.</p></div>{onReturnToEvent && <button className="secondary" onClick={onReturnToEvent}>Return to Event</button>}</div></header>
      {error && <p className="error">{error}</p>}
      <div className="formula-layout">
        <section className="panel formula-selector"><label className="field"><span>Select formula</span><select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>{formulas.map((item) => <option value={item.formula_id} key={item.formula_id}>{item.family} · {item.name}</option>)}</select></label>{definition && <><p className="eyebrow">{definition.formula_id}</p><h2>{definition.name}</h2><p>{definition.business_question}</p><div className="formula-box">{formatFormula(definition.latex)}</div><p className="muted">{definition.plain_english}</p><div className="actions"><button className="secondary" onClick={resetExample}>Reset to formula example</button><button onClick={resetCase} disabled={!caseParameters || !activeCaseFormulaIds.includes(selectedId)}>Reset to case values</button></div>{caseParameters && activeCaseFormulaIds.includes(selectedId) && <p className="note">Case values come from the synthetic learning portfolio in {caseData?.short_title || "this case"}; they are not historical position data.</p>}</>}</section>
        <section className="panel formula-inputs"><div className="section-title-row"><div><h2>Runtime inputs</h2><p className="muted">No page reload. Edited values stay in this session only.</p></div>{calculation && <span className={`status-pill ${origin === "user_modified" ? "warning" : "ready"}`}>{origin === "case_values" ? "Case values" : origin === "formula_example" ? "Formula example" : "User modified"}</span>}</div>{definition?.variables.map((variable) => <label className="field" key={variable.name}><span>{variable.label} <small>({variable.unit})</small> <ProvenanceBadge value={origin === "case_values" ? "CASE_VALUES" : origin === "formula_example" ? "FORMULA_DEFAULT" : "USER_INPUT"} /></span>{variable.type === "number" ? <input type="number" value={parameters[variable.name] as string | number ?? ""} min={variable.min ?? undefined} max={variable.max ?? undefined} step={variable.step ?? "any"} onChange={(event) => changeParameter(variable.name, event.target.value, variable.type)} /> : <textarea value={JSON.stringify(parameters[variable.name] ?? variable.default)} onChange={(event) => changeParameter(variable.name, event.target.value, variable.type)} />}</label>)}</section>
        <section className="panel calculation-panel"><div className="section-title-row"><div><h2>Calculation</h2><p className="muted">Progressive disclosure from substitution to interpretation.</p></div></div>{calculation ? <><div className="calculation-headline">{calculation.headline} <ProvenanceBadge value="CALCULATED" /></div><div className="calculation-steps">{calculation.steps.map((step) => <div className="calculation-step" key={step.label}><span>{step.label}</span><code>{step.expression}</code><strong><ProvenanceBadge value="CALCULATED" /> {display(step.result)}</strong></div>)}</div><h3>Outputs</h3><div className="metric-grid">{Object.entries(calculation.outputs).map(([key, value]) => <div key={key}><span>{key.split("_").join(" ")}</span><strong><ProvenanceBadge value="CALCULATED" /> {display(value)}</strong></div>)}</div><details open><summary>Assumptions</summary><ul>{calculation.assumptions.map((item) => <li key={item}>{item}</li>)}</ul></details><details><summary>Limitations</summary><ul>{calculation.limitations.map((item) => <li key={item}>{item}</li>)}</ul></details></> : <p className="empty">Enter valid inputs to calculate.</p>}</section>
      </div>
      {definition && <section className="panel formula-context"><h2>Formula context</h2><div className="two-column"><div><h3>Related formulas</h3><div className="chips">{definition.related_formula_ids.length ? definition.related_formula_ids.map((item) => <span className="chip" key={item}>{item}</span>) : <span className="muted">None listed</span>}</div></div><div><h3>Relevant indicators</h3><div className="chips">{definition.relevant_indicator_ids.length ? definition.relevant_indicator_ids.map((item) => <span className="chip" key={item}>{item}</span>) : <span className="muted">None listed</span>}</div></div></div></section>}
    </div>
  );
}
