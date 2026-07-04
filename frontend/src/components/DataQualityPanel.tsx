import type { DatasetPreview } from "../types/dataset";

export function DataQualityPanel({ preview }: { preview?: DatasetPreview | null }) {
  if (!preview) return <div className="empty">No dataset selected.</div>;
  const missingEntries = Object.entries(preview.missing_values);
  const totalMissingValues = missingEntries.reduce((total, [, count]) => total + count, 0);

  return (
    <section className="panel">
      <h3>Data Quality</h3>
      <p className="muted">{preview.frequency} dataset from {preview.source_name}. Date range: {preview.date_range || "unknown"}.</p>
      <div className="metric-grid">
        <div>
          <span>Rows</span>
          <strong>{preview.row_count.toLocaleString()}</strong>
        </div>
        <div>
          <span>Columns</span>
          <strong>{preview.column_count.toLocaleString()}</strong>
        </div>
        <div>
          <span>Missing Values</span>
          <strong>{totalMissingValues.toLocaleString()}</strong>
        </div>
        <div>
          <span>Rows Loaded</span>
          <strong>{preview.rows.length.toLocaleString()}</strong>
        </div>
      </div>
      <p className={totalMissingValues ? "warning" : "note"}>
        {totalMissingValues
          ? "Some variables have missing observations. Review the highlighted counts before modelling."
          : "No missing values detected in this dataset. The zeros below are expected for the built-in clean sample data."}
      </p>
      <h4>Missing Values by Column</h4>
      <div className="chips">
        {missingEntries.map(([column, count]) => (
          <span className={count ? "chip warn" : "chip"} key={column}>{column}: {count}</span>
        ))}
      </div>
      {preview.notes.map((note) => <p className="note" key={note}>{note}</p>)}
    </section>
  );
}
