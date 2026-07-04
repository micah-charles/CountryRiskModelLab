export function DiagnosticsPanel({ diagnostics }: { diagnostics?: unknown }) {
  if (!diagnostics || typeof diagnostics !== "object") return null;
  return (
    <section className="panel">
      <h3>Diagnostics</h3>
      <div className="chips">
        {Object.entries(diagnostics as Record<string, unknown>).map(([key, value]) => (
          <span className={value === true ? "chip warn" : "chip"} key={key}>{key}: {String(value)}</span>
        ))}
      </div>
    </section>
  );
}

