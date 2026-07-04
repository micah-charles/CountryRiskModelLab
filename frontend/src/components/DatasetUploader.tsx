import { useState } from "react";
import { api } from "../api/client";
import type { DatasetPreview } from "../types/dataset";

export function DatasetUploader({ onUploaded }: { onUploaded: (preview: DatasetPreview) => void }) {
  const [error, setError] = useState("");
  async function upload(file?: File) {
    if (!file) return;
    setError("");
    try {
      onUploaded(await api.uploadDataset(file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    }
  }
  return (
    <section className="panel">
      <h3>Upload CSV</h3>
      <input type="file" accept=".csv" onChange={(event) => upload(event.target.files?.[0])} />
      {error && <p className="error">{error}</p>}
      <p className="muted">MVP uploads require `country` and `date` columns.</p>
    </section>
  );
}

