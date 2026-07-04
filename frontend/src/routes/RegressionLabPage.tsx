import { useEffect, useState } from "react";
import { api } from "../api/client";
import { DiagnosticsPanel } from "../components/DiagnosticsPanel";
import { ForecastChart } from "../components/ForecastChart";
import { LearningCoachPanel } from "../components/LearningCoachPanel";
import { ModelConfigPanel } from "../components/ModelConfigPanel";
import { ModelReadinessPanel } from "../components/ModelReadinessPanel";
import { PythonCodePanel } from "../components/PythonCodePanel";
import { RegressionResultTable } from "../components/RegressionResultTable";
import { ResidualChart } from "../components/ResidualChart";
import { ResultSummaryCard } from "../components/ResultSummaryCard";
import { VariableSelector } from "../components/VariableSelector";
import type { DatasetMetadata, DatasetPreview, ModelReadinessResponse } from "../types/dataset";
import { keepValidSelection, pickCountry, pickFirstAvailable, pickManyAvailable, REGRESSION_DEPENDENT_PREFERENCES, REGRESSION_INDEPENDENT_PREFERENCES } from "../utils/modelDefaults";

export function RegressionLabPage({ activeDatasetId, setLastModelResult }: { activeDatasetId: string; setLastModelResult: (result: Record<string, unknown>) => void }) {
  const [datasets, setDatasets] = useState<DatasetMetadata[]>([]);
  const [datasetId, setDatasetId] = useState(activeDatasetId || "sample_country_risk_quarterly");
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [country, setCountry] = useState("Indonesia");
  const [dependent, setDependent] = useState("bond_yield_10y");
  const [independent, setIndependent] = useState<string[]>(["inflation_yoy", "policy_rate", "debt_gdp", "current_account_gdp", "global_risk_index"]);
  const [dateStart, setDateStart] = useState("");
  const [dateEnd, setDateEnd] = useState("");
  const [lagVariables, setLagVariables] = useState("");
  const [zScoreVariables, setZScoreVariables] = useState("");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [readiness, setReadiness] = useState<ModelReadinessResponse | null>(null);
  const [error, setError] = useState("");

  async function load(id = datasetId) {
    const items = await api.datasets();
    setDatasets(items);
    const p = await api.previewDataset(id);
    setPreview(p);
    const numeric = p.numeric_columns;
    const nextCountry = pickCountry(p.countries, country);
    const nextDependent = numeric.includes(dependent) ? dependent : pickFirstAvailable(numeric, REGRESSION_DEPENDENT_PREFERENCES);
    const validIndependent = keepValidSelection(independent, numeric).filter((item) => item !== nextDependent);
    setCountry(nextCountry);
    setDependent(nextDependent);
    setIndependent(validIndependent.length ? validIndependent : pickManyAvailable(numeric, REGRESSION_INDEPENDENT_PREFERENCES, [nextDependent], 4));
    setDateStart("");
    setDateEnd("");
  }
  useEffect(() => { load(datasetId).catch((err) => setError(String(err))); }, [datasetId]);

  useEffect(() => {
    if (!preview) return;
    let cancelled = false;
    setReadiness(null);
    api.modelReadiness({
      dataset_id: datasetId,
      lab_type: "regression",
      country,
      date_start: dateStart || null,
      date_end: dateEnd || null,
      dependent_variable: dependent,
      independent_variables: independent,
    }).then((response) => {
      if (!cancelled) setReadiness(response);
    }).catch(() => {
      if (!cancelled) setReadiness(null);
    });
    return () => { cancelled = true; };
  }, [preview, datasetId, country, dateStart, dateEnd, dependent, independent.join("|")]);

  async function run() {
    try {
      setError("");
      if (!readiness?.run_enabled) {
        setError("Update the Coverage & Readiness issues before running this regression.");
        return;
      }
      const response = await api.runRegression({
        dataset_id: datasetId,
        country,
        date_start: dateStart || null,
        date_end: dateEnd || null,
        dependent_variable: dependent,
        independent_variables: independent,
        transformations: {
          lag_1: lagVariables.split(",").map((item) => item.trim()).filter(Boolean),
          z_score: zScoreVariables.split(",").map((item) => item.trim()).filter(Boolean)
        },
        validation: { train_test_split: true, test_size: 0.2 }
      });
      setResult(response);
      setLastModelResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Regression failed.");
    }
  }
  const numeric = readiness?.model_numeric_columns || preview?.numeric_columns || [];
  const charts = result?.charts as Record<string, unknown> | undefined;

  return (
    <div className="lab-layout">
      <ModelConfigPanel title="Regression Lab">
        <label className="field"><span>Dataset</span><select value={datasetId} onChange={(event) => setDatasetId(event.target.value)}>{datasets.map((item) => <option key={item.dataset_id} value={item.dataset_id}>{item.name}</option>)}</select></label>
        <label className="field"><span>Country</span><select value={country} onChange={(event) => setCountry(event.target.value)}>{preview?.countries.map((item) => <option key={item}>{item}</option>)}</select></label>
        <label className="field"><span>Date start</span><input placeholder={preview?.date_range?.split(" to ")[0] || "optional"} value={dateStart} onChange={(event) => setDateStart(event.target.value)} /></label>
        <label className="field"><span>Date end</span><input placeholder={preview?.date_range?.split(" to ")[1] || "optional"} value={dateEnd} onChange={(event) => setDateEnd(event.target.value)} /></label>
        <VariableSelector label="Dependent variable" values={numeric} selected={dependent} onChange={(value) => setDependent(String(value))} />
        <VariableSelector label="Independent variables" values={numeric.filter((item) => item !== dependent)} selected={independent} onChange={(value) => setIndependent(value as string[])} multiple />
        <label className="field"><span>Lag 1 variables</span><input placeholder="comma-separated, optional" value={lagVariables} onChange={(event) => setLagVariables(event.target.value)} /></label>
        <label className="field"><span>Z-score variables</span><input placeholder="comma-separated, optional" value={zScoreVariables} onChange={(event) => setZScoreVariables(event.target.value)} /></label>
        {preview?.source_type === "imf_api" && <p className="warning">Dataset source: IMF API. Annual data may have limited observations.</p>}
        <ModelReadinessPanel readiness={readiness} />
        <button onClick={run} disabled={!readiness?.run_enabled}>Run Regression</button>
        {error && <p className="error">{error}</p>}
      </ModelConfigPanel>
      <section className="results">
        <ResultSummaryCard result={result} />
        <RegressionResultTable coefficients={result?.coefficients} />
        <ForecastChart data={charts?.actual_vs_fitted} lines={["actual", "fitted"]} />
        <ResidualChart data={charts?.residuals} />
        <DiagnosticsPanel diagnostics={result?.diagnostics} />
        <PythonCodePanel code={result?.python_code} />
      </section>
      <LearningCoachPanel mode="regression" />
    </div>
  );
}
