"use client";

import { AlertCircle, Download, FileSpreadsheet, LockKeyhole } from "lucide-react";
import Image from "next/image";
import { useEffect, useMemo, useState } from "react";
import { BOND_CHART_PRESETS, type BondChartPresetKey } from "@/lib/bond-chart-assets";
import { BOND_COUNTRIES, type CountryKey } from "@/app/data/catalog";

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

export function BondDashboard() {
  const [envelope, setEnvelope] = useState<SummaryEnvelope | null>(null);
  const [versions, setVersions] = useState<VersionOption[]>([]);
  const [versionLoading, setVersionLoading] = useState(false);
  const [status, setStatus] = useState<"loading" | "ready" | "empty" | "error">("loading");
  const [message, setMessage] = useState("");
  const [period, setPeriod] = useState<BondChartPresetKey>("last-3-years");
  const [selected, setSelected] = useState<CountryKey[]>([]);
  const snapshot = envelope?.snapshot;
  const available = useMemo(() => BOND_COUNTRIES.filter((country) => (snapshot?.seriesSummary?.[country.key]?.observationCount ?? 0) > 0), [snapshot]);

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
    const selectedPeriod = range === "full" ? "full" : period;
    return `/api/snapshots/bond-yields/export?version=${envelope.version}&period=${selectedPeriod}&format=${format}`;
  };

  const toggle = (key: CountryKey) => setSelected((current) => current.includes(key) ? current.filter((item) => item !== key) : [...current, key]);
  const imageBase = `/api/bond-charts/${period}`;

  return <div className="research-page">
    <section className="page-heading"><div><p className="eyebrow">SOVEREIGN RATES · PRESET CHARTS</p><h1>Government bond yields</h1><p>Compare stored 10-year benchmark yield charts across fixed time windows. Daily observations remain in private storage and can be downloaded from the selected snapshot version.</p></div><div className="snapshot-stamp"><span className="pulse-dot"/>{envelope ? `Version ${envelope.version} · ${new Date(snapshot!.retrievedAt).toLocaleDateString("en-GB", { dateStyle: "medium" })}` : status === "loading" ? "Loading chart status" : "Waiting for first snapshot"}</div></section>
    <div className="data-boundary-note"><strong><LockKeyhole size={14}/> Owner-only charts and data downloads</strong><span>Five prepared periods are available. CSV, JSON and Excel downloads read the selected stored snapshot and never trigger a source refresh. The chart toggle changes which prepared country images are displayed; it does not retrieve daily rows.</span></div>
    {snapshot?.operatorSelectedPurpose === "personal-interview" ? <div className="data-boundary-note"><strong>Operator-selected purpose: personal interview · owner-only Site</strong><span>This records intended use only; it is not a rights determination. Euronext and Banca d'Italia terms apply, and written permission has not been verified. Italy BMK0200 upstream vendors are not itemized. The interactive page loads prepared charts and source summaries; owner-only downloads read the selected stored snapshot.</span></div> : null}
    {snapshot?.restrictedCountries?.length ? <div className="data-boundary-note"><strong>Some markets remain outside this snapshot</strong><span>{snapshot.restrictedCountries.join(", ")} are not stored in the Site under its current purpose configuration.</span></div> : null}
    {status === "error" || status === "empty" ? <div className={`snapshot-notice ${status === "error" ? "error" : ""}`}><AlertCircle size={17}/><div><strong>{status === "error" ? "Snapshot unavailable" : "No snapshot published"}</strong><span>{message}</span></div></div> : null}
    {envelope && snapshot ? <>
      <section className="control-panel"><div className="period-toggles" aria-label="Choose a chart period">{BOND_CHART_PRESETS.map((item) => <button key={item.key} className={`quiet-button ${period === item.key ? "period-active" : ""}`} aria-pressed={period === item.key} onClick={() => setPeriod(item.key)}>{item.label}</button>)}</div>
        <div className="country-toggles" aria-label="Show country charts">{BOND_COUNTRIES.map((country) => { const details = snapshot.seriesSummary[country.key]; const isAvailable = !!details?.observationCount; const checked = selected.includes(country.key); return <button key={country.key} onClick={() => isAvailable && toggle(country.key)} disabled={!isAvailable} aria-pressed={checked} className={`country-toggle ${checked ? "is-selected" : ""} ${isAvailable ? "" : "is-unavailable"}`}><i style={{ backgroundColor: country.color }}/>{country.name}<span>{isAvailable ? snapshot.sourceStatus[country.key]?.status ?? "Available" : country.status === "local-only" ? "Local only" : "No chart"}</span></button>; })}</div>
        <label className="history-version-select">Snapshot version <select className="plain-select" value={envelope.version} disabled={versionLoading} onChange={(event) => void loadVersion(Number(event.target.value))}>{[...new Map([...versions, { version: envelope.version, createdAt: String(envelope.manifest.createdAt ?? snapshot.retrievedAt) }].map((item) => [item.version, item])).values()].sort((a, b) => b.version - a.version).map((item) => <option key={item.version} value={item.version}>Version {item.version} · {new Date(item.createdAt).toLocaleDateString("en-GB")}</option>)}</select></label>
      </section>
      <section className="chart-panel"><div className="panel-heading"><div><p className="eyebrow">STATIC SVG ARTIFACT · PERCENT PER ANNUM</p><h2>{BOND_CHART_PRESETS.find((item) => item.key === period)?.label}</h2></div><span className="unit-pill">Version {envelope.version} · retrieved {new Date(snapshot.retrievedAt).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}</span></div>
        {selected.length ? <div className="chart-image-frame"><Image className="chart-image-base" src={`${imageBase}/base.svg?v=${envelope.version}`} alt="Prepared chart axes, source notes and retrieval details" fill sizes="(max-width: 1100px) 100vw, 1100px" unoptimized/>{selected.map((country) => <Image key={country} className="chart-image-series" src={`${imageBase}/${country}.svg?v=${envelope.version}`} alt={`${country} yield series`} fill sizes="(max-width: 1100px) 100vw, 1100px" unoptimized/>)}</div> : <div className="empty-chart"><strong>Select a country</strong><span>Choose at least one available country to show its prepared chart image.</span></div>}
      </section>
      <section className="content-panel"><div className="panel-heading"><div><h2>Latest source summary</h2><p>Summary values only; the Site does not send daily observations to this page.</p></div></div><div className="bond-summary-grid">{available.map((country) => { const detail = snapshot.seriesSummary[country.key]!; const source = snapshot.sources[country.key]; const sourceStatus = snapshot.sourceStatus[country.key]; return <article key={country.key} className="bond-summary-card"><div><i style={{ backgroundColor: country.color }}/><strong>{country.name}</strong><span className={`status-chip ${sourceStatus?.status === "stale" ? "pending-chip" : "ready-chip"}`}>{sourceStatus?.status ?? "Available"}</span></div><p>{detail.latestValue === null ? "No numeric latest value" : `${detail.latestValue.toFixed(3)}%`} <small>· {detail.latestObservation}</small></p><span>{detail.observationCount.toLocaleString()} published observations since {detail.firstObservation}</span><a href={source?.sourceUrl} target="_blank" rel="noreferrer">{source?.agency ?? country.agency} · {source?.seriesId ?? "Source series"} ↗</a>{source?.reuse && <small>{source.reuse}</small>}{sourceStatus?.error && <small className="inline-error">Last attempt failed; previous successful snapshot retained.</small>}</article>; })}</div></section>
      <section className="content-panel"><div className="panel-heading"><div><h2>Download this snapshot</h2><p>These files read the selected immutable version. They do not refresh or change the current snapshot.</p></div><span className="unit-pill">Version {envelope.version}</span></div><div className="bond-download-groups"><div><strong>Selected chart period · {BOND_CHART_PRESETS.find((item) => item.key === period)?.label}</strong><div className="export-row"><a className="button button-primary" href={downloadHref("xlsx", "preset")} download><FileSpreadsheet size={15}/> Excel</a><a className="button button-secondary" href={downloadHref("csv", "preset")} download><Download size={15}/> CSV</a><a className="button button-secondary" href={downloadHref("json", "preset")} download><Download size={15}/> JSON</a></div></div><div><strong>Full history · {snapshot.periodStart} to latest available</strong><div className="export-row"><a className="button button-primary" href={downloadHref("xlsx", "full")} download><FileSpreadsheet size={15}/> Excel</a><a className="button button-secondary" href={downloadHref("csv", "full")} download><Download size={15}/> CSV</a><a className="button button-secondary" href={downloadHref("json", "full")} download><Download size={15}/> JSON</a></div></div></div></section>
    </> : null}
    <p className="footnote">{snapshot?.operatorSelectedPurpose === "personal-interview" ? "Source terms apply and written permission has not been verified. The interactive page loads prepared charts and summaries; owner-only downloads read the selected stored version without refreshing it." : snapshot?.note ?? "Country definitions differ; source gaps are never filled."} {snapshot?.missingValuePolicy ?? "Missing observations remain blank."}</p>
  </div>;
}
