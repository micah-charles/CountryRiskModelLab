"use client";

import { AlertCircle, LockKeyhole } from "lucide-react";
import Image from "next/image";
import { useEffect, useMemo, useState } from "react";
import { BOND_CHART_PRESETS, type BondChartPresetKey } from "@/lib/bond-chart-assets";
import { BOND_COUNTRIES, type CountryKey } from "@/app/data/catalog";

type BondSummary = {
  datasetKey: "bond-yields";
  periodStart: string;
  retrievedAt: string;
  missingValuePolicy: string;
  restrictedCountries: string[];
  note?: string;
  sources: Partial<Record<CountryKey, { country?: string; agency?: string; seriesId?: string; definition?: string; sourceUrl?: string; reuse?: string }>>;
  sourceStatus: Partial<Record<CountryKey, { status?: string; lastSuccessAt?: string; latestObservation?: string; observationCount?: number; error?: string }>>;
  seriesSummary: Partial<Record<CountryKey, { observationCount: number; firstObservation: string; latestObservation: string; latestValue: number | null }>>;
};

type SummaryEnvelope = { datasetKey: string; version: number; manifest: Record<string, unknown>; snapshot: BondSummary };

export function BondDashboard() {
  const [envelope, setEnvelope] = useState<SummaryEnvelope | null>(null);
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

  const toggle = (key: CountryKey) => setSelected((current) => current.includes(key) ? current.filter((item) => item !== key) : [...current, key]);
  const imageBase = `/api/bond-charts/${period}`;

  return <div className="research-page">
    <section className="page-heading"><div><p className="eyebrow">SOVEREIGN RATES · PRESET CHARTS</p><h1>Government bond yields</h1><p>Compare stored 10-year benchmark yield charts across fixed time windows. The hosted page receives chart images and source summaries only; daily observations stay in private storage.</p></div><div className="snapshot-stamp"><span className="pulse-dot"/>{envelope ? `Version ${envelope.version} · ${new Date(snapshot!.retrievedAt).toLocaleDateString("en-GB", { dateStyle: "medium" })}` : status === "loading" ? "Loading chart status" : "Waiting for first snapshot"}</div></section>
    <div className="data-boundary-note"><strong><LockKeyhole size={14}/> Hosted chart view · no dataset or workbook download</strong><span>Five prepared periods are available. Full daily data, arbitrary date ranges and Excel exports remain available only from the local workspace. The chart toggle changes which prepared country images are displayed; it does not retrieve daily rows.</span></div>
    {snapshot?.restrictedCountries?.length ? <div className="data-boundary-note"><strong>Some markets remain local-only</strong><span>{snapshot.restrictedCountries.join(", ")} are not stored in the Site while their hosted-reuse scope is unconfirmed. Adding an image does not resolve source redistribution terms.</span></div> : null}
    {status === "error" || status === "empty" ? <div className={`snapshot-notice ${status === "error" ? "error" : ""}`}><AlertCircle size={17}/><div><strong>{status === "error" ? "Snapshot unavailable" : "No snapshot published"}</strong><span>{message}</span></div></div> : null}
    {envelope && snapshot ? <>
      <section className="control-panel"><div className="period-toggles" aria-label="Choose a chart period">{BOND_CHART_PRESETS.map((item) => <button key={item.key} className={`quiet-button ${period === item.key ? "period-active" : ""}`} aria-pressed={period === item.key} onClick={() => setPeriod(item.key)}>{item.label}</button>)}</div>
        <div className="country-toggles" aria-label="Show country charts">{BOND_COUNTRIES.map((country) => { const details = snapshot.seriesSummary[country.key]; const isAvailable = !!details?.observationCount; const checked = selected.includes(country.key); return <button key={country.key} onClick={() => isAvailable && toggle(country.key)} disabled={!isAvailable} aria-pressed={checked} className={`country-toggle ${checked ? "is-selected" : ""} ${isAvailable ? "" : "is-unavailable"}`}><i style={{ backgroundColor: country.color }}/>{country.name}<span>{isAvailable ? snapshot.sourceStatus[country.key]?.status ?? "Available" : country.status === "local-only" ? "Local only" : "No chart"}</span></button>; })}</div>
      </section>
      <section className="chart-panel"><div className="panel-heading"><div><p className="eyebrow">STATIC SVG ARTIFACT · PERCENT PER ANNUM</p><h2>{BOND_CHART_PRESETS.find((item) => item.key === period)?.label}</h2></div><span className="unit-pill">Version {envelope.version} · retrieved {new Date(snapshot.retrievedAt).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}</span></div>
        {selected.length ? <div className="chart-image-frame"><Image className="chart-image-base" src={`${imageBase}/base.svg?v=${envelope.version}`} alt="Prepared chart axes, source notes and retrieval details" fill sizes="(max-width: 1100px) 100vw, 1100px" unoptimized/>{selected.map((country) => <Image key={country} className="chart-image-series" src={`${imageBase}/${country}.svg?v=${envelope.version}`} alt={`${country} yield series`} fill sizes="(max-width: 1100px) 100vw, 1100px" unoptimized/>)}</div> : <div className="empty-chart"><strong>Select a country</strong><span>Choose at least one available country to show its prepared chart image.</span></div>}
      </section>
      <section className="content-panel"><div className="panel-heading"><div><h2>Latest source summary</h2><p>Summary values only; the Site does not send daily observations to this page.</p></div></div><div className="bond-summary-grid">{available.map((country) => { const detail = snapshot.seriesSummary[country.key]!; const source = snapshot.sources[country.key]; const sourceStatus = snapshot.sourceStatus[country.key]; return <article key={country.key} className="bond-summary-card"><div><i style={{ backgroundColor: country.color }}/><strong>{country.name}</strong><span className={`status-chip ${sourceStatus?.status === "stale" ? "pending-chip" : "ready-chip"}`}>{sourceStatus?.status ?? "Available"}</span></div><p>{detail.latestValue === null ? "No numeric latest value" : `${detail.latestValue.toFixed(3)}%`} <small>· {detail.latestObservation}</small></p><span>{detail.observationCount.toLocaleString()} published observations since {detail.firstObservation}</span><a href={source?.sourceUrl} target="_blank" rel="noreferrer">{source?.agency ?? country.agency} · {source?.seriesId ?? "Source series"} ↗</a>{sourceStatus?.error && <small className="inline-error">Last attempt failed; previous successful snapshot retained.</small>}</article>; })}</div></section>
    </> : null}
    <p className="footnote">{snapshot?.note ?? "Country definitions differ; source gaps are never filled."} {snapshot?.missingValuePolicy ?? "Missing observations remain blank."}</p>
  </div>;
}
