import type { DatasetPreview } from "../types/dataset";
import { DataQualityPanel } from "./DataQualityPanel";

export function ImfFetchPreview({ preview, onUse }: { preview?: DatasetPreview | null; onUse: (lab: "regression" | "forecasting" | "var") => void }) {
  if (!preview) return null;
  return (
    <section className="stack">
      <DataQualityPanel preview={preview} />
      <div className="actions">
        <button onClick={() => onUse("regression")}>Use in Regression Lab</button>
        <button onClick={() => onUse("forecasting")}>Use in Forecasting Lab</button>
        <button onClick={() => onUse("var")}>Use in VAR Lab</button>
        <a className="button secondary" href={`/api/datasets/${preview.dataset_id}/csv`}>Download CSV</a>
      </div>
    </section>
  );
}
