import type { ModelReadinessResponse } from "../types/dataset";

function statusLabel(status: ModelReadinessResponse["status"]): string {
  if (status === "blocked") return "Changes needed";
  if (status === "warning") return "Runnable with cautions";
  return "Ready to run";
}

function coverageLabel(firstDate?: string | null, lastDate?: string | null): string {
  if (firstDate && lastDate) return `${firstDate} to ${lastDate}`;
  return "No observations";
}

export function ModelReadinessPanel({ readiness }: { readiness?: ModelReadinessResponse | null }) {
  if (!readiness) {
    return <p className="note">Checking dataset readiness...</p>;
  }

  const selectedCoverage = readiness.variable_coverage.filter((item) => item.selected);

  return (
    <section className={`readiness-panel ${readiness.status}`}>
      <div className="readiness-header">
        <h3>Coverage & Readiness</h3>
        <span className={`status-pill ${readiness.status}`}>{statusLabel(readiness.status)}</span>
      </div>
      <div className="readiness-metrics">
        <div>
          <span>Complete rows</span>
          <strong>{readiness.complete_case_count.toLocaleString()}</strong>
        </div>
        <div>
          <span>Needed</span>
          <strong>{readiness.required_observations.toLocaleString()}</strong>
        </div>
      </div>
      {readiness.suggested_date_start && readiness.suggested_date_end && (
        <p className="note">Best complete-data window: {readiness.suggested_date_start} to {readiness.suggested_date_end}.</p>
      )}
      {!!readiness.blocking_issues.length && (
        <div className="readiness-list">
          <strong>Change before running</strong>
          {readiness.blocking_issues.map((issue) => <p key={issue}>{issue}</p>)}
        </div>
      )}
      {!!readiness.recommendations.length && (
        <div className="readiness-list">
          <strong>Suggestions</strong>
          {readiness.recommendations.map((item) => <p key={item}>{item}</p>)}
        </div>
      )}
      {!!selectedCoverage.length && (
        <div className="readiness-list">
          <strong>Selected variable coverage</strong>
          {selectedCoverage.map((item) => (
            <p key={item.variable}>
              {item.variable}: {item.exists ? `${item.non_null_count.toLocaleString()} rows, ${coverageLabel(item.first_date, item.last_date)}` : "not in dataset"}
            </p>
          ))}
        </div>
      )}
    </section>
  );
}
