import type { DatasetMetadata, DatasetPreview, ImfCountry, ImfCountryCatalog, ImfFetchResponse, ImfIndicator, ModelReadinessRequest, ModelReadinessResponse } from "../types/dataset";
import type { Lesson } from "../types/lesson";
import type { AnalyticalSupportDefinition, CasePackValidation, FormulaCalculation, FormulaDefinition, IndicatorDefinition, ResearchCase, ResearchCaseSummary } from "../types/research";

const API_BASE = "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: options?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...options
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload.detail;
    throw new Error(typeof detail === "string" ? detail : detail ? JSON.stringify(detail) : "The request failed. Please try again.");
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/api/health"),
  datasets: () => request<DatasetMetadata[]>("/api/datasets"),
  sampleDatasets: () => request<DatasetMetadata[]>("/api/datasets/samples"),
  previewDataset: (datasetId: string, limit?: number) => request<DatasetPreview>(`/api/datasets/${datasetId}/preview${limit ? `?limit=${limit}` : ""}`),
  uploadDataset: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<DatasetPreview>("/api/datasets/upload", { method: "POST", body });
  },
  imfCountryCatalog: () => request<ImfCountryCatalog>("/api/imf/country-catalog"),
  imfCountries: () => request<ImfCountry[]>("/api/imf/countries"),
  refreshImfCountryCatalog: () => request<ImfCountryCatalog>("/api/imf/countries/refresh", { method: "POST" }),
  imfIndicators: () => request<ImfIndicator[]>("/api/imf/indicators"),
  fetchImf: (body: unknown) => request<ImfFetchResponse>("/api/imf/fetch", { method: "POST", body: JSON.stringify(body) }),
  prefetchAllImfCountries: (body: unknown) => request<ImfFetchResponse>("/api/imf/prefetch-all-countries", { method: "POST", body: JSON.stringify(body) }),
  createImfPrefetchedSession: (body: unknown) => request<ImfFetchResponse>("/api/imf/prefetched-session", { method: "POST", body: JSON.stringify(body) }),
  modelReadiness: (body: ModelReadinessRequest) => request<ModelReadinessResponse>("/api/models/readiness", { method: "POST", body: JSON.stringify(body) }),
  runRegression: (body: unknown) => request<Record<string, unknown>>("/api/models/regression/run", { method: "POST", body: JSON.stringify(body) }),
  runForecast: (body: unknown) => request<Record<string, unknown>>("/api/models/forecast/run", { method: "POST", body: JSON.stringify(body) }),
  runVar: (body: unknown) => request<Record<string, unknown>>("/api/models/var/run", { method: "POST", body: JSON.stringify(body) }),
  generateMemo: (body: unknown) => request<{ markdown: string }>("/api/memo/generate", { method: "POST", body: JSON.stringify(body) }),
  lessons: () => request<Lesson[]>("/api/lessons"),
  researchCases: () => request<ResearchCaseSummary[]>("/api/research-cases"),
  researchCase: (caseId: string) => request<ResearchCase>(`/api/research-cases/${caseId}`),
  analyticalSupport: (supportType: string, referenceId: string) => request<AnalyticalSupportDefinition>(`/api/analytical-support/${encodeURIComponent(supportType)}/${encodeURIComponent(referenceId)}`),
  importResearchCase: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<CasePackValidation>("/api/research-cases/import", { method: "POST", body });
  },
  indicators: () => request<IndicatorDefinition[]>("/api/indicators"),
  formulas: () => request<FormulaDefinition[]>("/api/formulas"),
  formula: (formulaId: string) => request<FormulaDefinition>(`/api/formulas/${formulaId}`),
  calculateFormula: (body: { formula_id: string; parameters: Record<string, unknown>; input_origin: "formula_example" | "case_values" | "user_modified" }) => request<FormulaCalculation>("/api/formulas/calculate", { method: "POST", body: JSON.stringify(body) })
};
