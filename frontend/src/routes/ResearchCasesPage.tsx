import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { CasePackValidation, ResearchCaseSummary } from "../types/research";
import type { PageKey } from "../components/Sidebar";

export function ResearchCasesPage({ onNavigate, activeCaseId, setActiveCaseId }: { onNavigate: (page: PageKey) => void; activeCaseId: string; setActiveCaseId: (id: string) => void }) {
  const [cases, setCases] = useState<ResearchCaseSummary[]>([]);
  const [validation, setValidation] = useState<CasePackValidation | null>(null);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  async function loadCases() {
    try {
      setError("");
      const result = await api.researchCases();
      setCases(result);
      if (!activeCaseId && result[0]) setActiveCaseId(result[0].case_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load Research Cases.");
    }
  }

  useEffect(() => { loadCases(); }, []);

  async function importPack(file: File) {
    try {
      setError("");
      const result = await api.importResearchCase(file);
      setValidation(result);
      await loadCases();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Case Pack import failed.";
      try {
        const payload = JSON.parse(message) as { validation?: CasePackValidation; message?: string };
        if (payload.validation) setValidation(payload.validation);
        setError(payload.message || "Case Pack validation failed.");
      } catch {
        setError(message);
      }
    } finally {
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  function openCase(caseId: string) {
    setActiveCaseId(caseId);
    onNavigate("event");
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Research Cases</h1>
        <p>Evidence-based Case Packs turn historical research into reusable learning experiences.</p>
      </header>

      {error && <p className="error">{error}</p>}

      <section className="panel import-panel">
        <div>
          <h2>Import a Case Pack</h2>
          <p className="muted">ZIP files are validated before they enter the case registry. Imported content cannot execute code.</p>
        </div>
        <div className="actions">
          <input ref={fileRef} type="file" accept=".zip,application/zip" onChange={(event) => { const file = event.target.files?.[0]; if (file) importPack(file); }} />
        </div>
      </section>

      {validation && (
        <section className={`panel validation-result ${validation.valid ? "valid" : "invalid"}`}>
          <div className="section-title-row">
            <div>
              <h2>{validation.valid ? "Case Pack validated" : "Case Pack needs changes"}</h2>
              <p className="muted">{validation.case_id || "Unknown case"} · schema {validation.schema_version || "unknown"}</p>
            </div>
            <span className={`status-pill ${validation.valid ? "ready" : "blocked"}`}>{validation.valid ? "Imported" : "Rejected"}</span>
          </div>
          {!!validation.errors.length && <div className="readiness-list"><strong>Errors</strong>{validation.errors.map((item) => <p key={item}>{item}</p>)}</div>}
          {!!validation.warnings.length && <div className="readiness-list"><strong>Warnings</strong>{validation.warnings.map((item) => <p key={item}>{item}</p>)}</div>}
          {validation.valid && <p className="note">The pack is available in the Case Library and can be opened in Historical Event Lab.</p>}
        </section>
      )}

      <section className="stack">
        <div className="section-title-row"><div><h2>Case Library</h2><p className="muted">New cases should add content and evidence, not a new React page.</p></div></div>
        {!cases.length && <p className="empty">No validated cases are available yet.</p>}
        <div className="case-grid">
          {cases.map((item) => (
            <article className={`case-card ${item.case_id === activeCaseId ? "selected-action" : ""}`} key={item.case_id}>
              <div className="case-card-heading"><span className="eyebrow">{item.origin === "built_in" ? "Built-in Golden Case" : "Imported Case"}</span><span className="status-pill ready">v{item.schema_version}</span></div>
              <h3>{item.title}</h3>
              <p>{item.summary}</p>
              <div className="chips">{item.themes.slice(0, 5).map((theme) => <span className="chip" key={theme}>{theme}</span>)}</div>
              <div className="case-stats"><span>{item.start_date || "?"} to {item.end_date || "?"}</span><span>{item.prediction_count} predictions</span><span>{item.source_count} sources</span></div>
              <div className="actions"><button onClick={() => openCase(item.case_id)}>Open Event Lab</button>{item.has_report && <a className="button secondary" href={`/api/research-cases/${item.case_id}/artifact/report.pdf`} target="_blank" rel="noreferrer">View report</a>}</div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
