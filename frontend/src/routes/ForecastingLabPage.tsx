import { useEffect, useState } from "react";
import { api } from "../api/client";
import { ForecastChart } from "../components/ForecastChart";
import { LearningCoachPanel } from "../components/LearningCoachPanel";
import { ModelConfigPanel } from "../components/ModelConfigPanel";
import { ModelReadinessPanel } from "../components/ModelReadinessPanel";
import { PythonCodePanel } from "../components/PythonCodePanel";
import { ResidualChart } from "../components/ResidualChart";
import { ResultSummaryCard } from "../components/ResultSummaryCard";
import { VariableSelector } from "../components/VariableSelector";
import type { DatasetMetadata, DatasetPreview, ModelReadinessResponse } from "../types/dataset";
import { FORECAST_EXTERNAL_PREFERENCES, FORECAST_TARGET_PREFERENCES, keepValidSelection, pickCountry, pickFirstAvailable, pickManyAvailable } from "../utils/modelDefaults";

export function ForecastingLabPage({ activeDatasetId, setLastModelResult }: { activeDatasetId: string; setLastModelResult: (result: Record<string, unknown>) => void }) {
  const [datasets, setDatasets] = useState<DatasetMetadata[]>([]);
  const [datasetId, setDatasetId] = useState(activeDatasetId || "sample_country_risk_monthly");
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [country, setCountry] = useState("Indonesia");
  const [target, setTarget] = useState("bond_yield_10y");
  const [modelType, setModelType] = useState("ARIMA");
  const [external, setExternal] = useState<string[]>(["policy_rate", "inflation_yoy", "global_risk_index"]);
  const [dateStart, setDateStart] = useState("");
  const [dateEnd, setDateEnd] = useState("");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [readiness, setReadiness] = useState<ModelReadinessResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.datasets().then(setDatasets).catch(() => setDatasets([]));
    api.previewDataset(datasetId).then((p) => {
      const numeric = p.numeric_columns;
      const nextTarget = numeric.includes(target) ? target : pickFirstAvailable(numeric, FORECAST_TARGET_PREFERENCES);
      const validExternal = keepValidSelection(external, numeric).filter((item) => item !== nextTarget);
      setPreview(p);
      setCountry(pickCountry(p.countries, country));
      setTarget(nextTarget);
      setExternal(validExternal.length ? validExternal : pickManyAvailable(numeric, FORECAST_EXTERNAL_PREFERENCES, [nextTarget], 3));
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
      lab_type: "forecast",
      country,
      date_start: dateStart || null,
      date_end: dateEnd || null,
      target_variable: target,
      model_type: modelType,
      external_variables: modelType === "SARIMAX" ? external : [],
    }).then((response) => {
      if (!cancelled) setReadiness(response);
    }).catch(() => {
      if (!cancelled) setReadiness(null);
    });
    return () => { cancelled = true; };
  }, [preview, datasetId, country, dateStart, dateEnd, target, modelType, external.join("|")]);

  async function run() {
    try {
      setError("");
      if (!readiness?.run_enabled) {
        setError("Update the Coverage & Readiness issues before running this forecast.");
        return;
      }
      const response = await api.runForecast({
        dataset_id: datasetId,
        country,
        date_start: dateStart || null,
        date_end: dateEnd || null,
        target_variable: target,
        model_type: modelType,
        order: [1, 1, 1],
        seasonal_order: modelType === "ARIMA" ? [0, 0, 0, 0] : [1, 0, 1, preview?.frequency === "monthly" ? 12 : 4],
        external_variables: modelType === "SARIMAX" ? external : [],
        forecast_horizon: 12,
        validation: { train_test_split: true, test_size: 0.2 }
      });
      setResult(response);
      setLastModelResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Forecast failed.");
    }
  }

  const numeric = readiness?.model_numeric_columns || preview?.numeric_columns || [];
  return (
    <div className="lab-layout">
      <ModelConfigPanel title="Forecasting Lab">
        <label className="field"><span>Dataset</span><select value={datasetId} onChange={(event) => setDatasetId(event.target.value)}>{datasets.map((item) => <option key={item.dataset_id} value={item.dataset_id}>{item.name}</option>)}</select></label>
        <label className="field"><span>Country</span><select value={country} onChange={(event) => setCountry(event.target.value)}>{preview?.countries.map((item) => <option key={item}>{item}</option>)}</select></label>
        <label className="field"><span>Date start</span><input placeholder={preview?.date_range?.split(" to ")[0] || "optional"} value={dateStart} onChange={(event) => setDateStart(event.target.value)} /></label>
        <label className="field"><span>Date end</span><input placeholder={preview?.date_range?.split(" to ")[1] || "optional"} value={dateEnd} onChange={(event) => setDateEnd(event.target.value)} /></label>
        <VariableSelector label="Target variable" values={numeric} selected={target} onChange={(value) => setTarget(String(value))} />
        <label className="field"><span>Model type</span><select value={modelType} onChange={(event) => setModelType(event.target.value)}><option>ARIMA</option><option>SARIMA</option><option>SARIMAX</option><option value="AUTO_ARIMA">Auto ARIMA educational grid search</option></select></label>
        {modelType === "SARIMAX" && <VariableSelector label="External variables" values={numeric.filter((item) => item !== target)} selected={external} onChange={(value) => setExternal(value as string[])} multiple />}
        {preview?.frequency === "annual" && <p className="warning">This dataset is annual and may have limited observations. ARIMA/SARIMAX usually work better with longer monthly or quarterly time series.</p>}
        <ModelReadinessPanel readiness={readiness} />
        <button onClick={run} disabled={!readiness?.run_enabled}>Run Forecast</button>
        {error && <p className="error">{error}</p>}
      </ModelConfigPanel>
      <section className="results">
        <ResultSummaryCard result={result} />
        <ForecastChart data={result?.forecast} lines={["forecast", "lower_ci", "upper_ci"]} />
        {Array.isArray(result?.model_candidates) && result.model_candidates.length > 0 && (
          <section className="panel table-wrap">
            <h3>Auto ARIMA Candidate Models</h3>
            <table>
              <thead><tr><th>Order</th><th>Seasonal order</th><th>AIC</th><th>RMSE</th><th>Converged</th></tr></thead>
              <tbody>{(result.model_candidates as Record<string, unknown>[]).map((row, index) => <tr key={index}><td>{JSON.stringify(row.order)}</td><td>{JSON.stringify(row.seasonal_order)}</td><td>{Number(row.aic).toFixed(2)}</td><td>{row.rmse ? Number(row.rmse).toFixed(3) : "n/a"}</td><td>{String(row.converged)}</td></tr>)}</tbody>
            </table>
            <p className="warning">The model with the lowest AIC is not always the best model for country-risk analysis. Analyst judgement is still needed.</p>
          </section>
        )}
        <ResidualChart data={result?.residuals} />
        <PythonCodePanel code={result?.python_code} />
      </section>
      <LearningCoachPanel mode="forecast" />
    </div>
  );
}
