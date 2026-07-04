export function ResultSummaryCard({ result }: { result?: Record<string, unknown> | null }) {
  if (!result) return <div className="empty">Run a model to see results.</div>;
  return (
    <section className="panel">
      <h3>{String(result.model_type || "Model Result")}</h3>
      <div className="metric-grid">
        {"r_squared" in result && <div><span>R²</span><strong>{Number(result.r_squared).toFixed(3)}</strong></div>}
        {"adjusted_r_squared" in result && <div><span>Adjusted R²</span><strong>{Number(result.adjusted_r_squared).toFixed(3)}</strong></div>}
        {"aic" in result && <div><span>AIC</span><strong>{Number(result.aic).toFixed(2)}</strong></div>}
        {"bic" in result && <div><span>BIC</span><strong>{Number(result.bic).toFixed(2)}</strong></div>}
        {"rmse" in result && <div><span>RMSE</span><strong>{Number(result.rmse).toFixed(3)}</strong></div>}
      </div>
    </section>
  );
}

