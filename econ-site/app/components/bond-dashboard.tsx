"use client";

import { AlertCircle, Download, FileSpreadsheet, ImageDown, LockKeyhole } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { BOND_CHART_PRESETS, type BondChartPresetKey } from "@/lib/bond-chart-logic";
import type { BondDateGrid, BondPeriodMode } from "@/lib/bond-chart-logic";
import { BondYieldChart, exportBondChart } from "@/app/components/bond-yield-chart";
import { BOND_COUNTRIES, type CountryKey, type SourceDetails, type YieldPoint } from "@/app/data/catalog";

type BondSummary = {
  datasetKey: "bond-yields";
  periodStart: string;
  retrievedAt: string;
  missingValuePolicy: string;
  operatorSelectedPurpose?: string | null;
  sourceRightsStatus?: Partial<Record<CountryKey, string>>;
  restrictedCountries: string[];
  note?: string;
  sources: Partial<Record<CountryKey, { country?: string; agency?: string; seriesId?: string; definition?: string; sourceUrl?: string; reuse?: string }>>;
  sourceStatus: Partial<Record<CountryKey, { status?: string; lastSuccessAt?: string; latestObservation?: string; observationCount?: number; error?: string }>>;
  seriesSummary: Partial<Record<CountryKey, { observationCount: number; firstObservation: string; latestObservation: string; latestValue: number | null }>>;
};

type SummaryEnvelope = { datasetKey: string; version: number; manifest: Record<string, unknown>; snapshot: BondSummary };
type VersionOption = { version: number; createdAt: string };
type ObservationEnvelope = { version: number; period: BondChartPresetKey; startDate: string; endDate: string; periodMode: BondPeriodMode | "fixed"; retrievedAt: string; sources: Partial<Record<CountryKey, SourceDetails>>; series: Partial<Record<CountryKey, YieldPoint[]>> };

export function BondDashboard() {
  const [envelope, setEnvelope] = useState<SummaryEnvelope | null>(null);
  const [versions, setVersions] = useState<VersionOption[]>([]);
  const [versionLoading, setVersionLoading] = useState(false);
  const [status, setStatus] = useState<"loading" | "ready" | "empty" | "error">("loading");
  const [message, setMessage] = useState("");
  const [period, setPeriod] = useState<BondChartPresetKey>("last-3-years");
  const [periodMode, setPeriodMode] = useState<BondPeriodMode>("rolling");
  const [dateGrid, setDateGrid] = useState<BondDateGrid>("quarterly");
  const [selected, setSelected] = useState<CountryKey[]>([]);
  const [chartData, setChartData] = useState<ObservationEnvelope | null>(null);
  const [chartError, setChartError] = useState<{ key: string; message: string } | null>(null);
  const chartRef = useRef<SVGSVGElement>(null);
  const snapshot = envelope?.snapshot;
  const available = useMemo(() => BOND_COUNTRIES.filter((country) => (snapshot?.seriesSummary?.[country.key]?.observationCount ?? 0) > 0), [snapshot]);
  const preset = BOND_CHART_PRESETS.find((item) => item.key === period)!;
  const periodDescription = preset.years === null
    ? period === "year-to-date" ? "Calendar year to date" : "Since 1 January 2020"
    : `${periodMode === "rolling" ? "Rolling" : "Calendar-year"} ${preset.years}-year window`;
  const version = envelope?.version;
  const requestKey = version ? `${version}:${period}:${periodMode}` : "";
  const chartDataMatches = !!chartData && chartData.version === version && chartData.period === period && chartData.periodMode === (preset.years === null ? "fixed" : periodMode);
  const chartLoading = !!version && !chartDataMatches && chartError?.key !== requestKey;
  const currentChartError = chartError?.key === requestKey ? chartError.message : "";

  useEffect(() => {
    let active = true;
    fetch("/api/snapshots/bond-yields", { cache: "no-store" }).then(async (response) => {
      const body = await response.json().catch(() => ({})) as Record<string, unknown>;
      if (!response.ok) {
        if (response.status === 404) return { kind: "empty" as const, message: "No bond chart snapshot has been published yet." };
        throw new Error(typeof body.error === "string" ? body.error : "Bond chart summary is unavailable.");
      }
      return { kind: "ready" as const, value: body as SummaryEnvelope };
    }).then((result) => {
      if (!active) return;
      if (result.kind === "empty") { setStatus("empty"); setMessage(result.message); return; }
      setEnvelope(result.value); setSelected(Object.keys(result.value.snapshot.seriesSummary ?? {}).filter((key): key is CountryKey => BOND_COUNTRIES.some((country) => country.key === key)));
      setStatus("ready");
    }).catch((error: unknown) => { if (active) { setStatus("error"); setMessage(error instanceof Error ? error.message : "Bond chart summary is unavailable."); } });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!version) return;
    let active = true;
    const key = `${version}:${period}:${periodMode}`;
    const params = new URLSearchParams({ version: String(version), period, mode: periodMode });
    fetch(`/api/snapshots/bond-yields/observations?${params}`, { cache: "no-store" }).then(async (response) => {
      const body = await response.json().catch(() => ({})) as ObservationEnvelope & { error?: string };
      if (!response.ok) throw new Error(body.error ?? "Daily chart observations are unavailable.");
      if (body.version !== version || body.period !== period || !body.startDate || !body.endDate || !body.series) throw new Error("The daily chart response did not match the selected snapshot.");
      return body;
    }).then((body) => { if (active) setChartData(body); }).catch((error: unknown) => {
      if (active) setChartError({ key, message: error instanceof Error ? error.message : "Daily chart observations are unavailable." });
    });
    return () => { active = false; };
  }, [version, period, periodMode]);

  useEffect(() => {
    fetch("/api/snapshots/bond-yields/versions?limit=100", { cache: "no-store" }).then(async (response) => {
      if (!response.ok) return [];
      const body = await response.json() as { versions?: VersionOption[] };
      return Array.isArray(body.versions) ? body.versions : [];
    }).then(setVersions).catch(() => setVersions([]));
  }, []);

  async function loadVersion(version: number) {
    setVersionLoading(true);
    try {
      const response = await fetch(`/api/snapshots/bond-yields?version=${version}`, { cache: "no-store" });
      const body = await response.json() as SummaryEnvelope & { error?: string };
      if (!response.ok) throw new Error(body.error ?? "The selected snapshot version could not be loaded.");
      setEnvelope(body);
      setSelected(Object.keys(body.snapshot.seriesSummary ?? {}).filter((key): key is CountryKey => BOND_COUNTRIES.some((country) => country.key === key)));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "The selected snapshot version could not be loaded.");
    } finally {
      setVersionLoading(false);
    }
  }

  const downloadHref = (format: "xlsx" | "csv" | "json", range: "preset" | "full") => {
    if (!envelope) return "#";
    if (range === "preset" && !selected.length) return "#";
    const params = new URLSearchParams({ version: String(envelope.version), period: range === "full" ? "full" : period, format });
    if (range === "preset") {
      params.set("mode", periodMode);
      params.set("dateGrid", dateGrid);
      if (selected.length) params.set("countries", selected.join(","));
    }
    return `/api/snapshots/bond-yields/export?${params}`;
  };

  const toggle = (key: CountryKey) => setSelected((current) => current.includes(key) ? current.filter((item) => item !== key) : [...current, key]);
  const exactRange = chartDataMatches ? { startDate: chartData!.startDate, endDate: chartData!.endDate } : null;
  const periodButtonsEnabled = preset.years !== null;

  return <div className="research-page">
    <section className="page-heading"><div><p className="eyebrow">SOVEREIGN RATES · DAILY OBSERVATIONS</p><h1>Government bond yields</h1><p>Compare each market’s published 10-year benchmark. Definitions vary by source; values stay in their source units and gaps are never filled.</p></div><div className="snapshot-stamp"><span className="pulse-dot"/>{envelope ? `Version ${envelope.version} · ${new Date(snapshot!.retrievedAt).toLocaleDateString("en-GB", { dateStyle: "medium" })}` : status === "loading" ? "Loading chart status" : "Waiting for first snapshot"}</div></section>
    <div className="data-boundary-note"><strong><LockKeyhole size={14}/> Owner-only charts and data downloads</strong><span>Daily observations from the selected immutable snapshot load to this private Site to draw the interactive chart. CSV, JSON, Excel, SVG and PNG exports use the current chart settings; downloads never refresh data or change a snapshot.</span></div>
    {snapshot?.operatorSelectedPurpose === "personal-interview" ? <div className="data-boundary-note"><strong>Operator-selected purpose: personal interview · owner-only Site</strong><span>This records intended use only; it is not a rights determination. Euronext and Banca d&apos;Italia terms apply, and written permission has not been verified. Italy BMK0200 upstream vendors are not itemized. The interactive page reads daily observations from the selected stored snapshot; owner-only downloads use the same range and country selection.</span></div> : null}
    {snapshot?.restrictedCountries?.length ? <div className="data-boundary-note"><strong>Some markets remain outside this snapshot</strong><span>{snapshot.restrictedCountries.join(", ")} are not stored in the Site under its current purpose configuration.</span></div> : null}
    {status === "error" || status === "empty" ? <div className={`snapshot-notice ${status === "error" ? "error" : ""}`}><AlertCircle size={17}/><div><strong>{status === "error" ? "Snapshot unavailable" : "No snapshot published"}</strong><span>{message}</span></div></div> : null}
    {envelope && snapshot ? <>
      <section className="control-panel"><div className="period-toggles" aria-label="Choose a chart period">{BOND_CHART_PRESETS.map((item) => <button key={item.key} className={`quiet-button ${period === item.key ? "period-active" : ""}`} aria-pressed={period === item.key} onClick={() => setPeriod(item.key)}>{item.label}</button>)}</div>
        <div className="chart-options-row"><fieldset className="chart-option-set"><legend>Window definition</legend><div className="period-toggles"><button type="button" className={`quiet-button ${periodMode === "rolling" ? "period-active" : ""}`} aria-pressed={periodMode === "rolling"} disabled={!periodButtonsEnabled} onClick={() => setPeriodMode("rolling")}>Rolling dates</button><button type="button" className={`quiet-button ${periodMode === "calendar" ? "period-active" : ""}`} aria-pressed={periodMode === "calendar"} disabled={!periodButtonsEnabled} onClick={() => setPeriodMode("calendar")}>Calendar years</button></div></fieldset><fieldset className="chart-option-set"><legend>Date labels</legend><div className="period-toggles"><button type="button" className={`quiet-button ${dateGrid === "quarterly" ? "period-active" : ""}`} aria-pressed={dateGrid === "quarterly"} onClick={() => setDateGrid("quarterly")}>Quarterly</button><button type="button" className={`quiet-button ${dateGrid === "semiannual" ? "period-active" : ""}`} aria-pressed={dateGrid === "semiannual"} onClick={() => setDateGrid("semiannual")}>Semiannual</button></div></fieldset><span className="chart-range-summary">{exactRange ? `True date bounds: ${exactRange.startDate} to ${exactRange.endDate}` : chartLoading ? "Loading selected period…" : "Date bounds unavailable"}</span></div>
        <div className="country-toggles" aria-label="Show country charts">{BOND_COUNTRIES.map((country) => { const details = snapshot.seriesSummary[country.key]; const isAvailable = !!details?.observationCount; const checked = selected.includes(country.key); return <button key={country.key} onClick={() => isAvailable && toggle(country.key)} disabled={!isAvailable} aria-pressed={checked} className={`country-toggle ${checked ? "is-selected" : ""} ${isAvailable ? "" : "is-unavailable"}`}><i style={{ backgroundColor: country.color }}/>{country.name}<span>{isAvailable ? snapshot.sourceStatus[country.key]?.status ?? "Available" : country.status === "local-only" ? "Local only" : "No chart"}</span></button>; })}</div>
        <label className="history-version-select">Snapshot version <select className="plain-select" value={envelope.version} disabled={versionLoading} onChange={(event) => void loadVersion(Number(event.target.value))}>{[...new Map([...versions, { version: envelope.version, createdAt: String(envelope.manifest.createdAt ?? snapshot.retrievedAt) }].map((item) => [item.version, item])).values()].sort((a, b) => b.version - a.version).map((item) => <option key={item.version} value={item.version}>Version {item.version} · {new Date(item.createdAt).toLocaleDateString("en-GB")}</option>)}</select></label>
      </section>
      <section className="chart-panel"><div className="panel-heading"><div><p className="eyebrow">INTERACTIVE DAILY SERIES · PERCENT PER ANNUM</p><h2>{preset.label} · {periodDescription}</h2></div><div className="chart-export-tools"><span className="unit-pill">Version {envelope.version} · retrieved {new Date(snapshot.retrievedAt).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}</span><button className="button button-secondary" disabled={!chartDataMatches || !selected.length} onClick={() => chartRef.current && void exportBondChart(chartRef.current, "svg", `government-bond-yields-${period}-${periodMode}`)}><Download size={14}/> SVG</button><button className="button button-secondary" disabled={!chartDataMatches || !selected.length} onClick={() => chartRef.current && void exportBondChart(chartRef.current, "png", `government-bond-yields-${period}-${periodMode}`)}><ImageDown size={14}/> 3840 × 2160 PNG</button></div></div>
        {chartLoading ? <div className="empty-chart"><strong>Loading daily observations</strong><span>Reading version {envelope.version} for {preset.label.toLowerCase()}.</span></div> : currentChartError ? <div className="snapshot-notice error" role="alert"><AlertCircle size={17}/><div><strong>Chart data unavailable</strong><span>{currentChartError}</span></div></div> : !selected.length ? <div className="empty-chart"><strong>Select a country</strong><span>Choose at least one available country to display its daily values.</span></div> : chartDataMatches ? <div className="chart-scroll"><BondYieldChart chartRef={chartRef} series={chartData!.series} selected={selected} startDate={chartData!.startDate} endDate={chartData!.endDate} dateGrid={dateGrid} periodLabel={preset.label} periodDescription={periodDescription} versionLabel={`snapshot v${chartData!.version}`} retrievedAt={chartData!.retrievedAt} sources={chartData!.sources}/></div> : null}
      </section>
      <section className="content-panel"><div className="panel-heading"><div><h2>Latest source summary</h2><p>Daily observations load only to this owner-private page for the selected interactive chart and exports.</p></div></div><div className="bond-summary-grid">{available.map((country) => { const detail = snapshot.seriesSummary[country.key]!; const source = snapshot.sources[country.key]; const sourceStatus = snapshot.sourceStatus[country.key]; return <article key={country.key} className="bond-summary-card"><div><i style={{ backgroundColor: country.color }}/><strong>{country.name}</strong><span className={`status-chip ${sourceStatus?.status === "stale" ? "pending-chip" : "ready-chip"}`}>{sourceStatus?.status ?? "Available"}</span></div><p>{detail.latestValue === null ? "No numeric latest value" : `${detail.latestValue.toFixed(3)}%`} <small>· {detail.latestObservation}</small></p><span>{detail.observationCount.toLocaleString()} published observations since {detail.firstObservation}</span><a href={source?.sourceUrl} target="_blank" rel="noreferrer">{source?.agency ?? country.agency} · {source?.seriesId ?? "Source series"} ↗</a>{source?.reuse && <small>{source.reuse}</small>}{sourceStatus?.error && <small className="inline-error">Last attempt failed; previous successful snapshot retained.</small>}</article>; })}</div></section>
      <section className="content-panel"><div className="panel-heading"><div><h2>Download this snapshot</h2><p>Selected-period files match the chart’s date window and enabled countries. Full history remains available for all series. Downloads do not refresh or change snapshots.</p></div><span className="unit-pill">Version {envelope.version}</span></div><div className="bond-download-groups"><div><strong>Chart range · {preset.label} · {periodDescription} · {selected.length ? selected.join(", ") : "no countries selected"}</strong><div className="export-row"><a className="button button-primary" href={selected.length ? downloadHref("xlsx", "preset") : undefined} aria-disabled={!selected.length} download><FileSpreadsheet size={15}/> Excel</a><a className="button button-secondary" href={selected.length ? downloadHref("csv", "preset") : undefined} aria-disabled={!selected.length} download><Download size={15}/> CSV</a><a className="button button-secondary" href={selected.length ? downloadHref("json", "preset") : undefined} aria-disabled={!selected.length} download><Download size={15}/> JSON</a></div></div><div><strong>Full history · {snapshot.periodStart} to latest available · all available series</strong><div className="export-row"><a className="button button-primary" href={downloadHref("xlsx", "full")} download><FileSpreadsheet size={15}/> Excel</a><a className="button button-secondary" href={downloadHref("csv", "full")} download><Download size={15}/> CSV</a><a className="button button-secondary" href={downloadHref("json", "full")} download><Download size={15}/> JSON</a></div></div></div></section>
    </> : null}
    <p className="footnote">{snapshot?.operatorSelectedPurpose === "personal-interview" ? "Source terms apply and written permission has not been verified. The owner-only chart reads daily data from the selected stored version; downloads do not refresh it." : snapshot?.note ?? "Country definitions differ; source gaps are never filled."} {snapshot?.missingValuePolicy ?? "Missing observations remain blank."}</p>
  </div>;
}
