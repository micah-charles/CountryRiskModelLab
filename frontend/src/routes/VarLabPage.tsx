import { useEffect, useState } from "react";
import { api } from "../api/client";
import { LearningCoachPanel } from "../components/LearningCoachPanel";
import { ModelConfigPanel } from "../components/ModelConfigPanel";
import { ModelReadinessPanel } from "../components/ModelReadinessPanel";
import { PythonCodePanel } from "../components/PythonCodePanel";
import { ResultSummaryCard } from "../components/ResultSummaryCard";
import { VariableSelector } from "../components/VariableSelector";
import type { DatasetMetadata, DatasetPreview, ModelReadinessResponse } from "../types/dataset";
import { keepValidSelection, pickCountry, pickManyAvailable, VAR_VARIABLE_PREFERENCES } from "../utils/modelDefaults";

export function VarLabPage({ activeDatasetId, setLastModelResult }: { activeDatasetId: string; setLastModelResult: (result: Record<string, unknown>) => void }) {
  const [datasets, setDatasets] = useState<DatasetMetadata[]>([]);
  const [datasetId, setDatasetId] = useState(activeDatasetId || "sample_country_risk_quarterly");
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [country, setCountry] = useState("Indonesia");
  const [variables, setVariables] = useState<string[]>(["inflation_yoy", "policy_rate", "bond_yield_10y", "fx_depreciation_yoy"]);
  const [lagOrder, setLagOrder] = useState(1);
  const [dateStart, setDateStart] = useState("");
  const [dateEnd, setDateEnd] = useState("");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [readiness, setReadiness] = useState<ModelReadinessResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.datasets().then(setDatasets).catch(() => setDatasets([]));
    api.previewDataset(datasetId).then((p) => {
      const numeric = p.numeric_columns;
      const validVariables = keepValidSelection(variables, numeric);
      setPreview(p);
      setCountry(pickCountry(p.countries, country));
      setVariables(validVariables.length >= 2 ? validVariables : pickManyAvailable(numeric, VAR_VARIABLE_PREFERENCES, [], 3));
      setDateStart("");
      setDateEnd("");
    }).catch((err) => setError(String(err)));
  }, [datasetId]);

  useEffect(() => {
    if (!preview) return;
    let cancelled = false;
    setReadiness(null);
    api.modelReadiness({
      dataset_id: datasetId,
      lab_type: "var",
      country,
      date_start: dateStart || null,
      date_end: dateEnd || null,
      variables,
      lag_order: lagOrder,
    }).then((response) => {
      if (!cancelled) setReadiness(response);
    }).catch(() => {
      if (!cancelled) setReadiness(null);
    });
    return () => { cancelled = true; };
  }, [preview, datasetId, country, dateStart, dateEnd, variables.join("|"), lagOrder]);

  async function run() {
    try {
      setError("");
      if (!readiness?.run_enabled) {
        setError("Update the Coverage & Readiness issues before running this VAR model.");
        return;
      }
      const response = await api.runVar({ dataset_id: datasetId, country, date_start: dateStart || null, date_end: dateEnd || null, variables, lag_order: lagOrder, forecast_horizon: 8 });
      setResult(response);
      setLastModelResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "VAR failed.");
    }
  }

  return (
    <div className="lab-layout">
      <ModelConfigPanel title="VAR Lab">
        <label className="field"><span>Dataset</span><select value={datasetId} onChange={(event) => setDatasetId(event.target.value)}>{datasets.map((item) => <option key={item.dataset_id} value={item.dataset_id}>{item.name}</option>)}</select></label>
        <label className="field"><span>Country</span><select value={country} onChange={(event) => setCountry(event.target.value)}>{preview?.countries.map((item) => <option key={item}>{item}</option>)}</select></label>
        <label className="field"><span>Date start</span><input placeholder={preview?.date_range?.split(" to ")[0] || "optional"} value={dateStart} onChange={(event) => setDateStart(event.target.value)} /></label>
        <label className="field"><span>Date end</span><input placeholder={preview?.date_range?.split(" to ")[1] || "optional"} value={dateEnd} onChange={(event) => setDateEnd(event.target.value)} /></label>
        <VariableSelector label="Variables" values={readiness?.model_numeric_columns || preview?.numeric_columns || []} selected={variables} onChange={(value) => setVariables(value as string[])} multiple />
        <label className="field"><span>Lag order</span><select value={lagOrder} onChange={(event) => setLagOrder(Number(event.target.value))}><option value={1}>1</option><option value={2}>2</option><option value={4}>4</option></select></label>
        {preview?.frequency === "annual" && <p className="warning">VAR models require enough observations. With annual data, use fewer variables or a longer sample period.</p>}
        <ModelReadinessPanel readiness={readiness} />
        <button onClick={run} disabled={!readiness?.run_enabled}>Run VAR</button>
        {error && <p className="error">{error}</p>}
        <p className="note">VECM is useful when non-stationary variables share a long-run equilibrium relationship. Future phase: stationarity test, Johansen cointegration test, VECM estimation, and long-run equilibrium interpretation.</p>
      </ModelConfigPanel>
      <section className="results">
        <ResultSummaryCard result={result} />
        {Array.isArray(result?.forecast) && <section className="panel table-wrap"><h3>Forecast</h3><pre>{JSON.stringify(result.forecast, null, 2)}</pre></section>}
        <PythonCodePanel code={result?.python_code} />
      </section>
      <LearningCoachPanel mode="var" />
    </div>
  );
}
