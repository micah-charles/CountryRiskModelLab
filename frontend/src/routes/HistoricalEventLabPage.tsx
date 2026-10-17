import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { AnalyticalSupportPanel } from "../components/AnalyticalSupportPanel";
import type { PageKey } from "../components/Sidebar";
import type { AnalyticalSupport, PredictionQuestion, PredictionQuestionType, ResearchCase, ResearchCaseSummary } from "../types/research";

type Stage = "context" | "prediction" | "reveal" | "decision";
type PredictionAnswer = { direction?: string; magnitude?: string; confidence?: number; reasoning?: string; answer?: string; estimate?: string; rangeLow?: string; rangeHigh?: string; ranking?: string; freeText?: string };

const directionOptions = ["up", "down", "flat", "uncertain"];
const supportedQuestionTypes: PredictionQuestionType[] = ["directional", "binary", "numeric", "categorical", "ranking", "free_text"];

function text(value: unknown, fallback = "") {
  return value === undefined || value === null ? fallback : String(value);
}

function questionType(prediction: PredictionQuestion): PredictionQuestionType {
  const candidate = text(prediction.type, "directional") as PredictionQuestionType;
  return supportedQuestionTypes.includes(candidate) ? candidate : "directional";
}

function initialAnswer(type: PredictionQuestionType): PredictionAnswer {
  if (type === "directional") return { direction: "uncertain", magnitude: "", confidence: 50, reasoning: "" };
  if (type === "binary" || type === "categorical") return { answer: "", confidence: 50, reasoning: "" };
  if (type === "numeric") return { estimate: "", rangeLow: "", rangeHigh: "", confidence: 50, reasoning: "" };
  if (type === "ranking") return { ranking: "", confidence: 50, reasoning: "" };
  return { freeText: "" };
}

function formatValue(value: unknown, unit: unknown) {
  if (value === null || value === undefined || value === "") return "Unavailable";
  return `${text(value)}${unit ? ` ${text(unit)}` : ""}`;
}

function eventWindowLabel(date: string, anchor?: string | null) {
  if (!anchor || !date) return date || "n/a";
  const current = new Date(`${date}T00:00:00Z`);
  const event = new Date(`${anchor}T00:00:00Z`);
  if (Number.isNaN(current.getTime()) || Number.isNaN(event.getTime())) return date;
  let offset = 0;
  const cursor = new Date(event);
  const direction = current >= event ? 1 : -1;
  while (cursor.toISOString().slice(0, 10) !== date && Math.abs(offset) < 30) {
    cursor.setUTCDate(cursor.getUTCDate() + direction);
    const day = cursor.getUTCDay();
    if (day !== 0 && day !== 6) offset += direction;
  }
  const standardWindow = [20, 5, 1, 0];
  return standardWindow.includes(Math.abs(offset)) ? `T${offset > 0 ? "+" : ""}${offset}` : date;
}

function assessmentLabel(value: unknown) {
  const labels: Record<string, string> = {
    correct: "Correct direction",
    correct_first_order: "Correct first-order effect",
    missed_second_order_if_yes: "Second-order effect to investigate",
    directionally_supported: "Directionally supported",
    correct_magnitude: "Correct direction and magnitude",
    wrong_magnitude: "Correct direction, wrong magnitude"
  };
  return labels[text(value)] || text(value, "Case interpretation").split("_").join(" ");
}

function actualSeries(caseData: ResearchCase) {
  const grouped = new Map<string, { label: string; unit: string; rows: Record<string, unknown>[] }>();
  for (const row of [...caseData.actual_market_moves, ...caseData.market_series]) {
    const id = text(row.indicator_id, "unknown");
    const current = grouped.get(id) || { label: text(row.label, id), unit: text(row.unit), rows: [] };
    current.rows.push(row);
    grouped.set(id, current);
  }
  return [...grouped.entries()].map(([indicatorId, value]) => ({ indicatorId, ...value }));
}

function supportLabel(support: AnalyticalSupport) {
  if (support.type === "formula") return "View formula";
  if (support.type === "statistical_model") return "View model";
  if (support.type === "transmission") return "View theory";
  if (support.type === "identity") return "View relationship";
  if (support.type === "rule_of_thumb") return "View rule";
  return "Learn more";
}

function answerSummary(type: PredictionQuestionType, answer: PredictionAnswer) {
  if (type === "directional") return `${answer.direction || "not recorded"}${answer.magnitude ? ` · ${answer.magnitude}` : ""}`;
  if (type === "binary" || type === "categorical") return answer.answer || "not recorded";
  if (type === "numeric") return `${answer.estimate || "not recorded"}${answer.rangeLow || answer.rangeHigh ? ` (${answer.rangeLow || "?"} to ${answer.rangeHigh || "?"})` : ""}`;
  if (type === "ranking") return answer.ranking || "not recorded";
  return answer.freeText || "not recorded";
}

function ProvenanceBadge({ value }: { value: string }) {
  return <span className="provenance-badge">{value.replace(/_/g, " ")}</span>;
}

function ConfidenceField({ answer, update }: { answer: PredictionAnswer; update: (value: number) => void }) {
  return <label className="field"><span>Confidence: {answer.confidence ?? 50}% <ProvenanceBadge value="USER_INPUT" /></span><input type="range" min="0" max="100" value={answer.confidence ?? 50} onChange={(event) => update(Number(event.target.value))} /></label>;
}


function PortfolioImpact({ portfolio, onOpenFormula }: { portfolio: Record<string, unknown>; onOpenFormula: (formulaId: string) => void }) {
  const example = (portfolio.example || portfolio.default_parameters || {}) as Record<string, unknown>;
  const hasFxPortfolio = example.entry_usdjpy !== undefined;

  if (hasFxPortfolio) {
    const entry = Number(example.entry_usdjpy || 0);
    const exit = Number(example.exit_usdjpy || 0);
    const holdingDays = Number(example.holding_days || 0);
    const assetRate = Number(example.usd_asset_yield_annual || 0);
    const fundingRate = Number(example.jpy_funding_rate_annual || 0);
    const leverage = Number(example.leverage || 0);
    const holdingFraction = holdingDays / 365;
    const fundingGrowth = 1 + fundingRate * holdingFraction;
    const spotReturn = entry ? exit / entry - 1 : 0;
    const unleveredReturn = entry && exit && fundingGrowth ? ((1 + assetRate * holdingFraction) * exit / entry) / fundingGrowth - 1 : 0;
    const leveragedReturn = unleveredReturn * leverage;

    return (
      <section className="panel synthetic-panel">
        <span className="eyebrow">Portfolio impact</span>
        <h2>Quantify a hypothetical carry position</h2>
        <p>{text(portfolio.warning, "This carry position is synthetic and is not an historical trade.")} <ProvenanceBadge value="SYNTHETIC_CASE" /></p>
        <div className="metric-grid">
          <div><span>Entry USD/JPY <ProvenanceBadge value="SYNTHETIC_CASE" /></span><strong>{entry.toLocaleString()}</strong></div>
          <div><span>Exit USD/JPY <ProvenanceBadge value="OBSERVED" /></span><strong>{exit.toLocaleString()}</strong></div>
          <div><span>Spot move <ProvenanceBadge value="CALCULATED" /></span><strong>{(spotReturn * 100).toFixed(2)}%</strong></div>
          <div><span>Holding period <ProvenanceBadge value="SYNTHETIC_CASE" /></span><strong>{holdingDays.toLocaleString()} days</strong></div>
          <div><span>Leverage <ProvenanceBadge value="SYNTHETIC_CASE" /></span><strong>{leverage.toLocaleString()}x</strong></div>
          <div><span>Leveraged return <ProvenanceBadge value="CALCULATED" /></span><strong>{(leveragedReturn * 100).toFixed(2)}%</strong></div>
        </div>
        <details className="calculation-explainer" open>
          <summary>How is this calculated?</summary>
          <div className="calculation-detail">
            <p><strong>Method:</strong> simple unhedged carry approximation</p>
            <p><strong>Units:</strong> returns are decimals shown as percentages; USD/JPY is JPY per USD.</p>
            <div className="formula-box">Spot return = {exit.toLocaleString()} / {entry.toLocaleString()} - 1 = {(spotReturn * 100).toFixed(2)}%</div>
            <div className="formula-box">Unlevered carry return = ((1 + {assetRate.toFixed(2)} x {holdingFraction.toFixed(6)}) x {exit.toLocaleString()} / {entry.toLocaleString()}) / (1 + {fundingRate.toFixed(2)} x {holdingFraction.toFixed(6)}) - 1 = {(unleveredReturn * 100).toFixed(2)}%</div>
            <div className="formula-box">Simplified leveraged return = {(unleveredReturn * 100).toFixed(2)}% x {leverage.toLocaleString()} = {(leveragedReturn * 100).toFixed(2)}%</div>
            <p className="note">This is a teaching approximation. It does not capture transaction costs, margining, cross-currency basis, compounding, path dependence or liquidation mechanics.</p>
          </div>
        </details>
        <div className="actions"><button onClick={() => onOpenFormula("FX_UNHEDGED_CARRY_RETURN")}>Try carry calculation</button></div>
      </section>
    );
  }

  const positionValue = Number(example.market_value_gbp ?? example.position_usd ?? 0);
  const positionCurrency = example.position_usd !== undefined ? "USD" : "GBP";
  const duration = Number(example.modified_duration ?? 0);
  const dv01 = Number(example.dv01_gbp_per_bp ?? (positionValue && duration ? duration * positionValue * 0.0001 : 0));
  const teachingShock = Number(example.shock_bp ?? example.yield_shock_bp ?? 0);
  const estimatedPnl = Number(example.linear_pnl_estimate_gbp ?? example.estimated_pnl_usd ?? (-dv01 * teachingShock));

  return (
    <section className="panel synthetic-panel">
      <span className="eyebrow">Portfolio impact</span>
      <h2>Quantify a hypothetical exposure</h2>
      <p>{text(portfolio.warning, "This learning portfolio is synthetic and is not an historical position.")} <ProvenanceBadge value="SYNTHETIC_CASE" /></p>
      <div className="metric-grid">
        <div><span>Position <ProvenanceBadge value="SYNTHETIC_CASE" /></span><strong>{positionValue.toLocaleString()} {positionCurrency}</strong></div>
        <div><span>Modified duration <ProvenanceBadge value="DERIVED" /></span><strong>{duration.toLocaleString(undefined, { maximumFractionDigits: 2 })} years</strong></div>
        <div><span>DV01 <ProvenanceBadge value="CALCULATED" /></span><strong>{dv01.toLocaleString()} / bp</strong></div>
        <div><span>Teaching shock <ProvenanceBadge value="SYNTHETIC_CASE" /></span><strong>{teachingShock.toLocaleString()} bp</strong></div>
        <div><span>Estimated P&amp;L <ProvenanceBadge value="CALCULATED" /></span><strong>{estimatedPnl.toLocaleString()} {positionCurrency}</strong></div>
      </div>
      <details className="calculation-explainer" open>
        <summary>How is this calculated?</summary>
        <div className="calculation-detail">
          <p><strong>Method:</strong> first-order duration / DV01 approximation</p>
          <p><strong>Units:</strong> DV01 is {positionCurrency} per basis point; the shock is in basis points.</p>
          <div className="formula-box">DV01 approx {duration.toLocaleString(undefined, { maximumFractionDigits: 2 })} x {positionValue.toLocaleString()} x 0.0001 = {dv01.toLocaleString()} {positionCurrency}/bp</div>
          <div className="formula-box">Estimated P&amp;L approx -{dv01.toLocaleString()} x {teachingShock.toLocaleString()} = {estimatedPnl.toLocaleString()} {positionCurrency}</div>
          <p className="note">This calculation does not capture convexity, changing duration, leverage, liquidity, forced sales, basis risk or optionality.</p>
        </div>
      </details>
      <div className="actions"><button onClick={() => onOpenFormula("RATE_DV01")}>Try different assumptions</button><button className="secondary" onClick={() => onOpenFormula("RATE_DV01")}>Open DV01 formula</button></div>
    </section>
  );
}

export function HistoricalEventLabPage({ activeCaseId, setActiveCaseId, onNavigate, onOpenFormula }: { activeCaseId: string; setActiveCaseId: (id: string) => void; onNavigate: (page: PageKey) => void; onOpenFormula?: (formulaId: string) => void }) {
  const [cases, setCases] = useState<ResearchCaseSummary[]>([]);
  const [caseData, setCaseData] = useState<ResearchCase | null>(null);
  const [stage, setStage] = useState<Stage>("context");
  const [answers, setAnswers] = useState<Record<string, PredictionAnswer>>({});
  const [selectedEvidence, setSelectedEvidence] = useState<Record<string, unknown> | null>(null);
  const [openSupportId, setOpenSupportId] = useState<string | null>(null);
  const [decisionActions, setDecisionActions] = useState<string[]>([]);
  const [decisionReasoning, setDecisionReasoning] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.researchCases().then((result) => {
      setCases(result);
      if (!activeCaseId && result[0]) setActiveCaseId(result[0].case_id);
    }).catch((err) => setError(err instanceof Error ? err.message : "Could not load cases."));
  }, []);

  useEffect(() => {
    if (!activeCaseId) return;
    setSelectedEvidence(null);
    setOpenSupportId(null);
    const storedStage = sessionStorage.getItem(`risk-research-event-stage:${activeCaseId}`) as Stage | null;
    api.researchCase(activeCaseId).then((result) => {
      setCaseData(result);
      const stored = sessionStorage.getItem(`risk-research-predictions:${activeCaseId}`);
      let parsed: Record<string, PredictionAnswer> = {};
      if (stored) {
        try { parsed = JSON.parse(stored) as Record<string, PredictionAnswer>; } catch { parsed = {}; }
      }
      const initial: Record<string, PredictionAnswer> = {};
      result.predictions.forEach((item) => {
        const id = text(item.prediction_id);
        initial[id] = { ...initialAnswer(questionType(item)), ...(parsed[id] || {}) };
      });
      setAnswers(initial);
      setStage(storedStage && ["context", "prediction", "reveal", "decision"].includes(storedStage) ? storedStage : "context");
    }).catch((err) => setError(err instanceof Error ? err.message : "Could not load the selected case."));
  }, [activeCaseId]);

  useEffect(() => {
    if (activeCaseId) sessionStorage.setItem(`risk-research-event-stage:${activeCaseId}`, stage);
  }, [activeCaseId, stage]);

  useEffect(() => {
    if (activeCaseId && Object.keys(answers).length) sessionStorage.setItem(`risk-research-predictions:${activeCaseId}`, JSON.stringify(answers));
  }, [activeCaseId, answers]);

  const visibleTimeline = useMemo(() => {
    if (!caseData) return [];
    return caseData.timeline.filter((item) => !caseData.anchor_event_date || text(item.date) <= caseData.anchor_event_date);
  }, [caseData]);

  if (!caseData) {
    return <div className="page"><header className="page-header"><h1>Historical Event Lab</h1><p>Loading the selected Research Case...</p></header>{error && <p className="error">{error}</p>}</div>;
  }

  const series = actualSeries(caseData);
  const portfolio = caseData.portfolio_impacts[0] || {};
  const actions = ["Reduce exposure", "Hedge duration", "Investigate a limit breach", "Run additional stress", "Examine liquidity", "Escalate through governance"];

  function updateAnswer(predictionId: string, field: keyof PredictionAnswer, value: string | number) {
    setAnswers((current) => ({ ...current, [predictionId]: { ...(current[predictionId] || initialAnswer("directional")), [field]: value } }));
  }

  function submitPredictions() {
    sessionStorage.setItem(`risk-research-predictions:${activeCaseId}`, JSON.stringify(answers));
    setStage("reveal");
  }

  function openFormula(formulaId: string) {
    if (onOpenFormula) onOpenFormula(formulaId);
    else onNavigate("formulas");
  }

  function renderPredictionFields(prediction: PredictionQuestion, answer: PredictionAnswer, type: PredictionQuestionType, id: string) {
      if (type === "directional") return <><div className="prediction-fields"><label className="field"><span>Direction</span><select value={answer.direction || "uncertain"} onChange={(event) => updateAnswer(id, "direction", event.target.value)}>{directionOptions.map((option) => <option key={option} value={option}>{option}</option>)}</select></label><label className="field"><span>{prediction.magnitude_label || "Expected magnitude / range"}</span><input value={answer.magnitude || ""} placeholder={prediction.magnitude_placeholder || "e.g. +25 to +50bp"} onChange={(event) => updateAnswer(id, "magnitude", event.target.value)} /></label><ConfidenceField answer={answer} update={(value) => updateAnswer(id, "confidence", value)} /></div><label className="field"><span>Reasoning</span><textarea value={answer.reasoning || ""} placeholder="What mechanism are you relying on?" onChange={(event) => updateAnswer(id, "reasoning", event.target.value)} /></label></>;
    if (type === "binary" || type === "categorical") return <><div className="prediction-fields compact-fields"><label className="field"><span>{type === "binary" ? "Answer" : "Category"}</span><select value={answer.answer || ""} onChange={(event) => updateAnswer(id, "answer", event.target.value)}><option value="">Select an answer</option>{(prediction.options.length ? prediction.options : ["uncertain"]).map((option) => <option key={option} value={option}>{option}</option>)}</select></label><ConfidenceField answer={answer} update={(value) => updateAnswer(id, "confidence", value)} /></div><label className="field"><span>Reasoning</span><textarea value={answer.reasoning || ""} placeholder="Explain the judgement and competing drivers." onChange={(event) => updateAnswer(id, "reasoning", event.target.value)} /></label></>;
    if (type === "numeric") return <><div className="prediction-fields"><label className="field"><span>Estimate</span><input type="number" value={answer.estimate || ""} onChange={(event) => updateAnswer(id, "estimate", event.target.value)} /></label><label className="field"><span>Range low</span><input type="number" value={answer.rangeLow || ""} onChange={(event) => updateAnswer(id, "rangeLow", event.target.value)} /></label><label className="field"><span>Range high</span><input type="number" value={answer.rangeHigh || ""} onChange={(event) => updateAnswer(id, "rangeHigh", event.target.value)} /></label></div><div className="prediction-fields compact-fields"><ConfidenceField answer={answer} update={(value) => updateAnswer(id, "confidence", value)} /></div><label className="field"><span>Reasoning</span><textarea value={answer.reasoning || ""} placeholder="Explain the estimate and its uncertainty." onChange={(event) => updateAnswer(id, "reasoning", event.target.value)} /></label></>;
    if (type === "ranking") return <><label className="field"><span>Ranking / order</span><input value={answer.ranking || ""} placeholder="e.g. rates > FX > equity" onChange={(event) => updateAnswer(id, "ranking", event.target.value)} /></label><ConfidenceField answer={answer} update={(value) => updateAnswer(id, "confidence", value)} /><label className="field"><span>Reasoning</span><textarea value={answer.reasoning || ""} placeholder="Explain the ordering." onChange={(event) => updateAnswer(id, "reasoning", event.target.value)} /></label></>;
    return <label className="field"><span>Answer</span><textarea value={answer.freeText || ""} placeholder="Write your analytical response." onChange={(event) => updateAnswer(id, "freeText", event.target.value)} /></label>;
  }

  return (
    <div className="page event-lab">
      <header className="page-header">
        <div className="section-title-row"><div><span className="eyebrow">Historical Event Lab</span><h1>{caseData.title}</h1><p>{caseData.summary}</p></div><label className="case-switcher"><span>Case</span><select value={caseData.case_id} onChange={(event) => setActiveCaseId(event.target.value)}>{cases.map((item) => <option key={item.case_id} value={item.case_id}>{item.short_title}</option>)}</select></label></div>
        <div className="stage-nav">{(["context", "prediction", "reveal", "decision"] as Stage[]).map((item, index) => <span className={stage === item ? "stage active" : "stage"} key={item}><strong>{index + 1}</strong>{item === "context" ? "Context" : item === "prediction" ? "Predict" : item === "reveal" ? "Reveal & Explain" : "Decide"}</span>)}</div>
      </header>

      {error && <p className="error">{error}</p>}

      {stage === "context" && <div className="event-grid"><section className="panel context-panel"><span className="eyebrow">Stage A · Information available at the event point</span><h2>What is happening?</h2><p>{text(caseData.trigger.description, caseData.summary)}</p><div className="chips">{caseData.themes.map((theme) => <span className="chip" key={theme}>{theme}</span>)}</div><div className="callout"><strong>Anchor date</strong><span>{caseData.anchor_event_date || "Not specified"}</span><small>Future market outcomes stay hidden until you submit your predictions.</small></div><h3>Context timeline</h3><div className="timeline">{visibleTimeline.map((item, index) => { const eventText = text(item.description, text(item.event, text(item.title, "Event"))); return <div className="timeline-item" key={`${text(item.date)}-${index}`}><time>{text(item.date)}</time><div><strong>{eventText}</strong><p>{eventText}</p></div></div>; })}</div></section><aside className="panel learning-panel"><h3>Learning objectives</h3><ul>{caseData.lessons.map((item, index) => <li key={index}>{typeof item === "string" ? item : text(item.title, JSON.stringify(item))}</li>)}</ul><div className="source-badge"><strong>Evidence policy</strong><span>Historical facts, calculated values and synthetic learning values are kept separate.</span></div><button onClick={() => setStage("prediction")}>Make predictions</button></aside></div>}

      {stage === "prediction" && <div className="event-grid"><section className="panel prediction-panel"><span className="eyebrow">Stage B · Commit before reveal</span><h2>What do you expect?</h2><p className="muted">Make a market-risk judgement first. Theory explains the mechanism without giving away the realized outcome.</p>{caseData.predictions.map((prediction, index) => { const id = text(prediction.prediction_id, `prediction-${index}`); const type = questionType(prediction); const answer = answers[id] || initialAnswer(type); const support = prediction.analytical_support; return <article className="prediction-card" key={id}><div className="case-card-heading"><span className="eyebrow">Question {index + 1} · {type.replace(/_/g, " ")}</span>{support && support.type !== "none" && <span className="status-pill ready">Analytical support</span>}</div><h3>{text(prediction.prompt, id)}</h3>{renderPredictionFields(prediction, answer, type, id)}{support && support.type !== "none" && <div className="analytical-actions"><span>Learn before answering</span><button className="secondary" onClick={() => setOpenSupportId(openSupportId === id ? null : id)}>{supportLabel(support)}</button>{support.type === "formula" && onOpenFormula && support.reference_id && <button className="secondary" onClick={() => openFormula(support.reference_id || "")}>Try calculation</button>}</div>}{support && support.type !== "none" && openSupportId === id && <AnalyticalSupportPanel support={support} onTryCalculation={(formulaId) => openFormula(formulaId)} />}</article>; })}<div className="actions"><button className="secondary" onClick={() => setStage("context")}>Back to context</button><button onClick={submitPredictions}>Submit predictions and reveal data</button></div></section><aside className="panel learning-panel"><h3>Analyst habit</h3><p>Separate a first-order economic view from second-order effects such as leverage, collateral, liquidity, forced selling and policy intervention.</p><p className="note">Your answers are kept in this browser session and are not written into the canonical case pack.</p></aside></div>}

      {stage === "reveal" && <div className="stack"><section className="panel"><span className="eyebrow">Stage C · Actual evidence</span><h2>What actually happened?</h2><p className="muted">Observed, calculated and synthetic values remain visibly distinct.</p><div className="event-series-grid">{series.map((item) => <article className="event-series" key={item.indicatorId}><div className="series-heading"><div><h3>{item.label}</h3><p className="muted">{item.indicatorId} · {item.unit || "unit not specified"}</p></div><span className="status-pill ready">Observed</span></div>{item.rows.map((row, index) => { const status = text(row.data_status, text(row.evidence_type, "OBSERVED")).toUpperCase(); return <div className="series-row" key={`${text(row.date)}-${index}`}><time>{eventWindowLabel(text(row.date), caseData.anchor_event_date)}</time><strong>{formatValue(row.value, row.unit)}</strong><span className={text(row.direction) === "down" ? "move down" : "move"}>{text(row.direction, "n/a")}</span><ProvenanceBadge value={status} /></div>; })}</article>)}</div></section><section className="panel"><span className="eyebrow">Prediction review</span><h2>Compare expected with actual</h2><div className="comparison-grid">{caseData.predictions.map((prediction, index) => { const id = text(prediction.prediction_id, `prediction-${index}`); const type = questionType(prediction); const answer = answers[id] || initialAnswer(type); return <article className="comparison-card" key={id}><div className="case-card-heading"><strong>{text(prediction.prediction_id)}</strong><span className="status-pill warning">{assessmentLabel(prediction.assessment)}</span></div><h3>{text(prediction.prompt)}</h3><p><strong>Your judgement:</strong> {answerSummary(type, answer)} {answer.confidence !== undefined && `· ${answer.confidence}% confidence`} <ProvenanceBadge value="USER_INPUT" /></p><p><strong>Realized market view:</strong> {text(prediction.actual_answer, text(prediction.actual_direction, "Not available"))} <ProvenanceBadge value="OBSERVED" /></p><p className="muted">{text(prediction.explanation)}</p></article>; })}</div></section><section className="panel"><div className="section-title-row"><div><span className="eyebrow">Why?</span><h2>Consequence graph</h2><p className="muted">Click an edge or node to inspect its relationship and supporting evidence.</p></div></div><div className="consequence-layout"><div className="consequence-graph">{(caseData.consequences.edges || []).map((edge, index) => <button className="graph-edge" key={text(edge.edge_id, `${text(edge.from)}-${text(edge.to)}-${index}`)} onClick={() => setSelectedEvidence(edge)}><strong>{text(edge.from)} → {text(edge.to)}</strong><span>{text(edge.relation)}</span><small>{text(edge.confidence, "unknown")} confidence</small></button>)}</div><div className="evidence-detail">{selectedEvidence ? <><h3>Selected relationship</h3><pre>{JSON.stringify(selectedEvidence, null, 2)}</pre><strong>Supporting sources</strong><div className="chips">{(Array.isArray(selectedEvidence.source_ids) ? selectedEvidence.source_ids : []).map((sourceId) => { const source = caseData.sources.find((item) => text(item.source_id) === text(sourceId)); return <a className="chip" href={text(source?.url, "#")} target="_blank" rel="noreferrer" key={text(sourceId)}>{text(source?.title, text(sourceId))}</a>; })}</div></> : <p className="empty">Select a relationship to inspect its evidence metadata.</p>}</div></div><div className="graph-nodes">{(caseData.consequences.nodes || []).map((node) => <button className="chip" key={text(node.id)} onClick={() => setSelectedEvidence(node)}>{text(node.label, text(node.id))}</button>)}</div></section><section className="panel sources-panel"><div className="section-title-row"><div><span className="eyebrow">Provenance</span><h2>Supporting sources</h2></div><span className="status-pill ready">{caseData.sources.length} sources</span></div><div className="source-list">{caseData.sources.map((source) => <a className="source-row" href={text(source.url, "#")} target="_blank" rel="noreferrer" key={text(source.source_id)}><strong>{text(source.title, text(source.source_id))}</strong><span>{text(source.publisher)} · {text(source.confidence, "confidence not specified")}</span></a>)}</div></section><PortfolioImpact portfolio={portfolio} onOpenFormula={openFormula} /></div>}

      {stage === "decision" && <section className="panel decision-panel"><span className="eyebrow">Stage D · Risk decision</span><h2>What would you do next?</h2><p className="muted">There is no universal “always hedge” answer. Consider mandate, limits, liquidity, cost, business purpose and risk appetite.</p><div className="decision-options">{actions.map((action) => <label key={action}><input type="checkbox" checked={decisionActions.includes(action)} onChange={() => setDecisionActions((current) => current.includes(action) ? current.filter((item) => item !== action) : [...current, action])} /><span>{action}</span></label>)}</div><label className="field"><span>Decision reasoning</span><textarea value={decisionReasoning} placeholder="What would you investigate, escalate, hedge or monitor, and why?" onChange={(event) => setDecisionReasoning(event.target.value)} /></label><div className="decision-summary"><h3>Your risk response</h3><p>{decisionActions.length ? decisionActions.join(" · ") : "No action selected yet."}</p>{decisionReasoning && <p className="muted">{decisionReasoning}</p>}</div><div className="actions"><button className="secondary" onClick={() => setStage("reveal")}>Back to evidence</button><button onClick={() => onNavigate("cases")}>Return to Case Library</button></div></section>}
    </div>
  );
}


