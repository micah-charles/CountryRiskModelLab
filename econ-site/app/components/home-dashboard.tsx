"use client";

import { ArrowDownRight, ArrowRight, ArrowUpRight, ChartNoAxesCombined, Clock3, Database, FileChartColumn, LockKeyhole, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

type CatalogItem = { datasetKey: string; version: number; createdAt: string; summary: Record<string, unknown>; sourceStatus: Record<string, { status: string; message?: string }> };

export function HomeDashboard() {
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    fetch("/api/snapshots", { cache: "no-store" }).then(async (response) => {
      const data = await response.json().catch(() => ({})) as Record<string, unknown>;
      if (!response.ok) throw new Error(typeof data.error === "string" ? data.error : "Snapshot catalog unavailable");
      setItems(Array.isArray(data.snapshots) ? data.snapshots as CatalogItem[] : []);
    }).catch(() => setItems([])).finally(() => setLoading(false));
  }, []);
  const byKey = new Map(items.map((item) => [item.datasetKey, item]));
  const latest = items.map((item) => item.createdAt).sort().at(-1);
  const readyCount = items.length;
  return <div className="dashboard-page">
    <section className="hero-panel">
      <div className="hero-copy">
        <p className="eyebrow"><span className="eyebrow-rule"/> ECONOMY &amp; RISK</p>
        <h1>Research, with the<br/><em>evidence in view.</em></h1>
        <p className="hero-intro">A private workspace for sovereign rates, country-risk indicators and market-event research. Every view carries its source and snapshot date.</p>
        <div className="hero-actions"><a className="button button-primary" href="/bonds">Explore bond yields <ArrowRight size={16}/></a><a className="text-link" href="/cases">Open research cases <ArrowUpRight size={16}/></a></div>
      </div>
      <div className="hero-illustration" aria-hidden="true">
        <div className="orb orb-one"/><div className="orb orb-two"/>
        <svg viewBox="0 0 360 226" className="hero-chart">
          <path d="M22 182H340M22 132H340M22 82H340M22 32H340" stroke="#ffffff22" strokeWidth="1"/>
          <path d="M24 167 C52 155 59 152 81 155 S117 168 141 142 S181 124 199 130 S228 112 247 102 S276 88 290 76 S321 65 338 34" fill="none" stroke="#e8b47a" strokeWidth="3.4" strokeLinecap="round"/>
          <path d="M24 126 C48 133 64 117 82 120 S109 95 130 106 S160 126 181 101 S213 97 230 84 S260 100 280 68 S318 62 338 54" fill="none" stroke="#93b7aa" strokeWidth="2.4" strokeLinecap="round"/>
          <path d="M24 197 C60 188 84 181 102 185 S140 177 162 184 S207 162 229 167 S273 144 291 146 S320 130 338 116" fill="none" stroke="#f3eee6aa" strokeWidth="1.6" strokeLinecap="round"/>
          <circle cx="338" cy="34" r="5" fill="#e8b47a" stroke="#152a30" strokeWidth="3"/><circle cx="338" cy="54" r="4" fill="#93b7aa" stroke="#152a30" strokeWidth="2"/>
          <text x="23" y="218" fill="#ffffff7a" fontSize="10">2020</text><text x="158" y="218" fill="#ffffff7a" fontSize="10">2023</text><text x="306" y="218" fill="#ffffff7a" fontSize="10">2026</text>
        </svg>
        <div className="hero-legend"><span><i className="legend-dot dot-amber"/> Yield snapshots</span><span><i className="legend-dot dot-green"/> Research signals</span></div>
        <div className="hero-stamp"><Sparkles size={14}/><span>Curated, versioned, sourced</span></div>
      </div>
    </section>
    <div className="section-kicker-row"><div><p className="eyebrow">YOUR WORKSPACE</p><h2>Research modules</h2></div><a className="text-link" href="/history">Version history <ArrowRight size={15}/></a></div>
    <section className="module-grid">
      <ModuleCard href="/bonds" icon={<ChartNoAxesCombined size={18}/>} eyebrow="RATES · DAILY" title="Government bond yields" text="Compare 10-year yields from six markets, with local-only import for data pending hosting permission." item={byKey.get("bond-yields")} loading={loading} accent="amber"/>
      <ModuleCard href="/country-risk" icon={<Database size={18}/>} eyebrow="COUNTRY RISK · SNAPSHOTS" title="Country-risk dashboard" text="Read versioned macro snapshots with source dates and missing values clearly marked." item={byKey.get("country-risk")} loading={loading} accent="green"/>
      <ModuleCard href="/cases" icon={<BookOpenIcon/>} eyebrow="MARKET EVENTS · CASE LIBRARY" title="Research cases" text="Follow source-linked event timelines, prediction reviews and consequence maps." item={byKey.get("research-cases")} loading={loading} accent="blue"/>
      <ModuleCard href="/demand" icon={<ArrowDownRight size={18}/>} eyebrow="HONG KONG · CHINA" title="Demand monitor" text="Explore company and industry evidence from the local analysis workflow." item={byKey.get("hk-demand")} loading={loading} accent="rose"/>
      <ModuleCard href="/indicators" icon={<Database size={18}/>} eyebrow="REFERENCE · CATALOG" title="Indicators & formulas" text="Browse the shared indicator library and trusted calculations." item={byKey.get("catalog")} loading={loading} accent="violet"/>
      <a href="/models" className="module-card pending-card"><div className="module-card-top"><span className="module-icon accent-slate"><LockKeyhole size={18}/></span><span className="status-chip pending-chip">Connection pending</span></div><p className="module-eyebrow">REGRESSION · FORECAST · VAR</p><h3>Model workspace</h3><p className="module-description">Python models remain in the local app. This Site is read-only for model results until a connection is approved.</p><div className="module-meta"><span>Local models</span><ArrowRight size={15}/></div></a>
    </section>
    <section className="bottom-strip"><div className="strip-icon"><Clock3 size={18}/></div><div><strong>{latest ? `Latest snapshot ${new Date(latest).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}` : "Waiting for the first snapshot"}</strong><p>{readyCount ? `${readyCount} versioned data ${readyCount === 1 ? "module" : "modules"} available` : "Run the private local updater to publish a reviewed snapshot. No source data is bundled with the Site code."}</p></div><div className="strip-right"><span className="strip-lock"><LockKeyhole size={14}/> Private cloud history</span><a href="/history" className="button button-secondary">Open history <ArrowRight size={14}/></a></div></section>
  </div>;
}

function ModuleCard({ href, icon, eyebrow, title, text, item, loading, accent }: { href: string; icon: React.ReactNode; eyebrow: string; title: string; text: string; item?: CatalogItem; loading: boolean; accent: string }) {
  const sourceCount = Object.keys((item?.summary.sourceCounts as Record<string, number>) ?? {}).length;
  return <a href={href} className="module-card">
    <div className="module-card-top"><span className={`module-icon accent-${accent}`}>{icon}</span>{item ? <span className="status-chip ready-chip"><i/> Version {item.version}</span> : <span className={`status-chip ${loading ? "loading-chip" : "pending-chip"}`}>{loading ? "Loading" : "No snapshot yet"}</span>}</div>
    <p className="module-eyebrow">{eyebrow}</p><h3>{title}</h3><p className="module-description">{text}</p>
    <div className="module-meta"><span>{item ? `Updated ${new Date(item.createdAt).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}${sourceCount ? ` · ${sourceCount} series` : ""}` : "View module details"}</span><ArrowRight size={15}/></div>
  </a>;
}

function BookOpenIcon() {
  return <FileChartColumn size={18}/>;
}
