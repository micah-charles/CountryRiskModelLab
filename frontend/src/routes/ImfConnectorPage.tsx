import { useEffect, useState } from "react";
import { api } from "../api/client";
import { ImfCountrySelector } from "../components/ImfCountrySelector";
import { ImfFetchPreview } from "../components/ImfFetchPreview";
import { ImfIndicatorSelector } from "../components/ImfIndicatorSelector";
import type { PageKey } from "../components/Sidebar";
import type { DatasetMetadata, DatasetPreview, ImfCountry, ImfCountryCatalog, ImfIndicator } from "../types/dataset";

export function ImfConnectorPage({ onDatasetReady, onNavigate }: { onDatasetReady: (id: string) => void; onNavigate: (page: PageKey) => void }) {
  const [countries, setCountries] = useState<ImfCountry[]>([]);
  const [countryCatalog, setCountryCatalog] = useState<ImfCountryCatalog | null>(null);
  const [indicators, setIndicators] = useState<ImfIndicator[]>([]);
  const [selectedCountries, setSelectedCountries] = useState<string[]>(["IDN", "BRA", "ZAF", "TUR", "MEX", "IND"]);
  const [selectedIndicators, setSelectedIndicators] = useState<string[]>(["NGDP_RPCH", "PCPIPCH", "GGXWDG_NGDP", "BCA_NGDPD"]);
  const [startYear, setStartYear] = useState(2010);
  const [endYear, setEndYear] = useState(2026);
  const [progress, setProgress] = useState<string[]>([]);
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [prefetchedDatasets, setPrefetchedDatasets] = useState<DatasetMetadata[]>([]);
  const [selectedPrefetchDatasetId, setSelectedPrefetchDatasetId] = useState("");
  const [sessionTarget, setSessionTarget] = useState<PageKey>("regression");
  const [error, setError] = useState("");
  const [refreshingCountries, setRefreshingCountries] = useState(false);

  function applyCountryCatalog(catalog: ImfCountryCatalog) {
    setCountryCatalog(catalog);
    setCountries(catalog.countries);
  }

  async function refreshPrefetchedDatasets(preferredDatasetId?: string) {
    const datasets = await api.datasets();
    const prefetched = datasets
      .filter((dataset) => dataset.dataset_id.startsWith("imf_all_countries_") || dataset.notes.includes("IMF_ALL_COUNTRIES_PREFETCH"))
      .sort((left, right) => right.created_at.localeCompare(left.created_at));
    setPrefetchedDatasets(prefetched);
    setSelectedPrefetchDatasetId(preferredDatasetId || prefetched[0]?.dataset_id || "");
  }

  useEffect(() => {
    api.imfCountryCatalog().then(applyCountryCatalog).catch(() => setCountries([]));
    api.imfIndicators().then(setIndicators).catch(() => setIndicators([]));
    refreshPrefetchedDatasets().catch(() => setPrefetchedDatasets([]));
  }, []);

  async function refreshCountries() {
    setRefreshingCountries(true);
    setError("");
    try {
      applyCountryCatalog(await api.refreshImfCountryCatalog());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not refresh the IMF country catalogue.");
    } finally {
      setRefreshingCountries(false);
    }
  }

  async function fetchData() {
    setError("");
    setProgress([
      "Connecting to IMF API...",
      "Fetching country catalogue...",
      "Fetching indicator data...",
      "Transforming data into country-year panel...",
      "Checking missing values..."
    ]);
    try {
      const result = await api.fetchImf({ countries: selectedCountries, indicators: selectedIndicators, start_year: startYear, end_year: endYear });
      setProgress(result.progress_states);
      setPreview(result.preview);
      onDatasetReady(result.dataset.dataset_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not fetch IMF data at the moment. You can still continue with sample datasets or upload a CSV.");
      setProgress([]);
    }
  }

  async function prefetchAllCountries() {
    setError("");
    setProgress([
      "Reading static IMF country catalogue...",
      "Fetching selected indicators for every catalogue country...",
      "Transforming into an all-country country-year panel...",
      "Saving prefetched dataset locally..."
    ]);
    try {
      const result = await api.prefetchAllImfCountries({ indicators: selectedIndicators, start_year: startYear, end_year: endYear });
      setProgress(result.progress_states);
      setPreview(result.preview);
      onDatasetReady(result.dataset.dataset_id);
      await refreshPrefetchedDatasets(result.dataset.dataset_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not prefetch all IMF countries.");
      setProgress([]);
    }
  }

  async function createTestSession() {
    if (!selectedPrefetchDatasetId) {
      setError("Prefetch an all-country IMF dataset first, then create a test session.");
      return;
    }
    setError("");
    setProgress([
      "Reading prefetched all-country IMF dataset...",
      "Filtering selected countries, indicators, and date range...",
      "Saving test session dataset locally...",
      `Opening ${sessionTarget} lab...`
    ]);
    try {
      const result = await api.createImfPrefetchedSession({
        source_dataset_id: selectedPrefetchDatasetId,
        countries: selectedCountries,
        indicators: selectedIndicators,
        start_year: startYear,
        end_year: endYear
      });
      setProgress(result.progress_states);
      setPreview(result.preview);
      onDatasetReady(result.dataset.dataset_id);
      onNavigate(sessionTarget);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create a test session from prefetched data.");
      setProgress([]);
    }
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>IMF Data Connector</h1>
        <p>Fetch macroeconomic data from IMF DataMapper and convert it into a modelling-ready country-year panel.</p>
      </header>
      <p className="warning">Data availability differs by country and year. Annual IMF data is useful for medium-term country-risk analysis but may be weak for short-horizon forecasting.</p>
      <div className="two-column">
        <ImfCountrySelector
          countries={countries}
          lastModifiedUtc={countryCatalog?.last_modified_utc}
          refreshing={refreshingCountries}
          onRefresh={refreshCountries}
          selected={selectedCountries}
          setSelected={setSelectedCountries}
        />
        <section className="panel">
          <h3>Date Range</h3>
          <label className="field"><span>Start year</span><input type="number" value={startYear} onChange={(event) => setStartYear(Number(event.target.value))} /></label>
          <label className="field"><span>End year</span><input type="number" value={endYear} onChange={(event) => setEndYear(Number(event.target.value))} /></label>
          <div className="actions">
            <button onClick={fetchData}>Fetch Selected Countries Live</button>
            <button className="secondary" onClick={prefetchAllCountries}>Prefetch All Countries</button>
          </div>
          <p className="note">Prefetch All Countries uses every country in the static IMF catalogue and saves the result for later test sessions.</p>
        </section>
      </div>
      <section className="panel">
        <h3>Prefetched Test Session</h3>
        <div className="two-column">
          <label className="field">
            <span>Prefetched all-country dataset</span>
            <select value={selectedPrefetchDatasetId} onChange={(event) => setSelectedPrefetchDatasetId(event.target.value)}>
              <option value="">No prefetched dataset available</option>
              {prefetchedDatasets.map((dataset) => <option key={dataset.dataset_id} value={dataset.dataset_id}>{dataset.name}</option>)}
            </select>
          </label>
          <label className="field">
            <span>Open after session</span>
            <select value={sessionTarget} onChange={(event) => setSessionTarget(event.target.value as PageKey)}>
              <option value="regression">Regression Lab</option>
              <option value="forecasting">Forecasting Lab</option>
              <option value="var">VAR Lab</option>
              <option value="dataset">Dataset Admin</option>
            </select>
          </label>
        </div>
        <div className="actions">
          <button onClick={createTestSession} disabled={!selectedPrefetchDatasetId || !selectedCountries.length || !selectedIndicators.length}>Create Test Session From Prefetched Data</button>
          <button className="secondary" onClick={() => refreshPrefetchedDatasets()}>Refresh Prefetch List</button>
        </div>
        <p className="note">This does not call IMF. It filters the selected countries, indicators, and date range from the saved all-country dataset.</p>
        </section>
      <ImfIndicatorSelector indicators={indicators} selected={selectedIndicators} setSelected={setSelectedIndicators} />
      {!!progress.length && <section className="panel"><h3>Progress</h3>{progress.map((item) => <p key={item}>{item}</p>)}</section>}
      {error && <p className="error">{error}</p>}
      <ImfFetchPreview preview={preview} onUse={(lab) => onNavigate(lab)} />
    </div>
  );
}
