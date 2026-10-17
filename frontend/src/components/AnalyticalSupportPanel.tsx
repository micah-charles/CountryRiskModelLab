import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { AnalyticalSupport, AnalyticalSupportDefinition, TransmissionChannel } from "../types/research";
import { formatFormula } from "../utils/formulaDisplay";

function listValue(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String) : [];
}

function FormulaExpression({ value }: { value: string }) {
  return <div className="formula-box analytical-formula" aria-label="Mathematical expression">{formatFormula(value)}</div>;
}

function ChannelList({ title, channels }: { title: string; channels: TransmissionChannel[] }) {
  if (!channels.length) return null;
  return <div className="support-channel-group"><h4>{title}</h4><div className="support-channel-list">{channels.map((channel) => <div className="support-channel" key={`${title}-${channel.label}`}><div><strong>{channel.label}</strong><span>{channel.description}</span></div><small>{channel.direction}</small></div>)}</div></div>;
}

export function AnalyticalSupportPanel({ support, onTryCalculation }: { support: AnalyticalSupport; onTryCalculation?: (formulaId: string) => void }) {
  const [definition, setDefinition] = useState<AnalyticalSupportDefinition | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    if (!support.reference_id || support.type === "none") {
      setLoading(false);
      setDefinition(null);
      return () => { cancelled = true; };
    }
    setLoading(true);
    setError("");
    api.analyticalSupport(support.type, support.reference_id).then((result) => {
      if (!cancelled) setDefinition(result);
    }).catch((err) => {
      if (!cancelled) setError(err instanceof Error ? err.message : "Could not load analytical support.");
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, [support.reference_id, support.type]);

  if (loading) return <div className="analytical-support-panel"><p className="muted">Loading analytical support...</p></div>;
  if (error) return <div className="analytical-support-panel"><p className="error">{error}</p></div>;
  if (!definition) return null;

  const title = support.title || definition.title;
  const summary = support.summary || definition.summary;
  const formula = definition.formula;
  const transmission = definition.transmission;
  const model = definition.model;
  const identity = definition.identity;
  const rule = definition.rule_of_thumb;

  return (
    <div className="analytical-support-panel">
      <div className="support-heading"><div><span className="eyebrow">{definition.support_type.split("_").join(" ")}</span><h4>{title}</h4><p>{summary}</p></div><span className="status-pill ready">Before reveal</span></div>

      {formula && <div className="support-content"><div><h4>Intuition</h4><p>{formula.plain_english}</p></div><div><h4>Formula</h4><FormulaExpression value={formula.latex} /></div><div><h4>Symbols and units</h4><dl className="symbol-list">{formula.variables.map((variable) => <div key={variable.name}><dt>{variable.symbol}</dt><dd><strong>{variable.label}</strong><span>{variable.unit || "unit not specified"}</span></dd></div>)}</dl></div><div className="support-explain"><h4>Why use this formula?</h4><p>{formula.business_question}. It is a defensible relationship for the selected exposure, but it remains an approximation under the assumptions below.</p></div><details><summary>Assumptions and limitations</summary><div className="two-column support-lists"><div><strong>Assumptions</strong><ul>{formula.assumptions.map((item) => <li key={item}>{item}</li>)}</ul></div><div><strong>Limitations</strong><ul>{formula.limitations.map((item) => <li key={item}>{item}</li>)}</ul></div></div></details>{onTryCalculation && definition.reference_id && <div className="actions compact"><button onClick={() => onTryCalculation(definition.reference_id || "")}>Try calculation</button></div>}</div>}

      {transmission && <div className="support-content"><div><h4>Trigger</h4><p>{transmission.trigger}</p></div><ChannelList title="Transmission channels" channels={transmission.channels} /><ChannelList title="Competing or countervailing drivers" channels={transmission.countervailing_channels} /><div className="support-explain"><h4>Expected directional effect</h4><p>{transmission.expected_relationship}</p></div><details><summary>Limitations</summary><ul>{transmission.limitations.map((item) => <li key={item}>{item}</li>)}</ul></details></div>}

      {model && <div className="support-content"><div><h4>Model</h4><FormulaExpression value={String(model.model || "Statistical model")}/></div><div><h4>Inputs</h4><ul>{listValue(model.inputs).map((item) => <li key={item}>{item}</li>)}</ul></div><div><h4>Assumptions</h4><ul>{listValue(model.assumptions).map((item) => <li key={item}>{item}</li>)}</ul></div><details><summary>Limitations</summary><ul>{listValue(model.limitations).map((item) => <li key={item}>{item}</li>)}</ul></details><p className="note">This is a statistical/model-based estimate, not a deterministic fact.</p></div>}

      {identity && <div className="support-content"><h4>Conceptual relationship</h4><p>{String(identity.summary || "")}</p><FormulaExpression value={String(identity.formula || "")}/><details><summary>Limitations</summary><ul>{listValue(identity.limitations).map((item) => <li key={item}>{item}</li>)}</ul></details></div>}

      {rule && <div className="support-content"><h4>Rule and units</h4><p>{String(rule.summary || "")}</p><FormulaExpression value={String(rule.rule || "")}/><details><summary>Limitations</summary><ul>{listValue(rule.limitations).map((item) => <li key={item}>{item}</li>)}</ul></details></div>}
    </div>
  );
}
