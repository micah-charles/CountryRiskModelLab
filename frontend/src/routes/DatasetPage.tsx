import { useEffect, useState } from "react";
import { api } from "../api/client";
import { DataQualityPanel } from "../components/DataQualityPanel";
import { DatasetUploader } from "../components/DatasetUploader";
import type { DatasetMetadata, DatasetPreview } from "../types/dataset";

export function DatasetPage({ activeDatasetId, setActiveDatasetId }: { activeDatasetId: string; setActiveDatasetId: (id: string) => void }) {
  const [datasets, setDatasets] = useState<DatasetMetadata[]>([]);
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [showAllRows, setShowAllRows] = useState(false);
  const [error, setError] = useState("");

  async function refresh(datasetId = activeDatasetId, allRows = showAllRows) {
    try {
      setError("");
      const items = await api.datasets();
      setDatasets(items);
      const target = datasetId || items[0]?.dataset_id;
      if (target) {
        setActiveDatasetId(target);
        const initialPreview = await api.previewDataset(target);
        if (allRows && initialPreview.row_count > initialPreview.rows.length) {
          setPreview(await api.previewDataset(target, initialPreview.row_count));
        } else {
          setPreview(initialPreview);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load datasets.");
    }
  }

  async function updateRowMode(allRows: boolean) {
    setShowAllRows(allRows);
    await refresh(activeDatasetId, allRows);
  }

  useEffect(() => { refresh(); }, []);

  return (
    <div className="page">
      <header className="page-header"><h1>Dataset Admin</h1><p>Manage sample, uploaded, and IMF-fetched datasets through one registry.</p></header>
      {error && <p className="error">{error}</p>}
      <div className="two-column">
        <section className="panel">
          <h3>Dataset Source</h3>
          <select value={activeDatasetId} onChange={(event) => { setShowAllRows(false); refresh(event.target.value, false); }}>
            {datasets.map((dataset) => <option key={dataset.dataset_id} value={dataset.dataset_id}>{dataset.name}</option>)}
          </select>
          <p className="muted">Source: {preview?.source_type || "none"}</p>
        </section>
        <DatasetUploader onUploaded={(uploaded) => { setPreview(uploaded); setActiveDatasetId(uploaded.dataset_id); refresh(uploaded.dataset_id); }} />
      </div>
      <DataQualityPanel preview={preview} />
      {preview && (
        <section className="panel table-wrap">
          <div className="section-title-row">
            <div>
              <h3>{showAllRows ? "Full Dataset" : "Preview"}</h3>
              <p className="muted">Showing {preview.rows.length.toLocaleString()} of {preview.row_count.toLocaleString()} rows.</p>
            </div>
            <div className="actions compact">
              <button className={!showAllRows ? "secondary selected-action" : "secondary"} onClick={() => updateRowMode(false)} disabled={!showAllRows}>First 20 Rows</button>
              <button onClick={() => updateRowMode(true)} disabled={showAllRows || preview.rows.length >= preview.row_count}>Show All Rows</button>
              <a className="button secondary" href={`/api/datasets/${preview.dataset_id}/csv`}>Download CSV</a>
            </div>
          </div>
          <table>
            <thead><tr>{preview.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
            <tbody>{preview.rows.map((row, index) => <tr key={index}>{preview.columns.map((column) => <td key={column}>{String(row[column] ?? "")}</td>)}</tr>)}</tbody>
          </table>
        </section>
      )}
    </div>
  );
}
