export interface DatasetMetadata {
  dataset_id: string;
  name: string;
  source_type: "sample" | "upload" | "imf_api";
  source_name: string;
  created_at: string;
  frequency: "monthly" | "quarterly" | "annual" | "unknown";
  country_column: string;
  date_column: string;
  columns: string[];
  file_path: string;
  metadata_path?: string | null;
  countries: string[];
  date_range?: string | null;
  notes: string[];
}

export interface DatasetPreview {
  dataset_id: string;
  name: string;
  source_type: string;
  source_name: string;
  frequency: string;
  columns: string[];
  row_count: number;
  column_count: number;
  rows: Record<string, unknown>[];
  numeric_columns: string[];
  date_column: string;
  country_column: string;
  missing_values: Record<string, number>;
  countries: string[];
  date_range?: string | null;
  notes: string[];
}

export interface ImfIndicator {
  code: string;
  platform_variable: string;
  label: string;
  category: string;
  frequency: string;
  description: string;
  typical_country_risk_interpretation: string;
  expected_relationship_to_bond_yield: string;
}

export interface ImfCountry {
  code: string;
  name: string;
}

export interface ImfCountryCatalog {
  source_url: string;
  last_modified_utc?: string | null;
  country_count: number;
  countries: ImfCountry[];
}

export interface ImfFetchResponse {
  dataset: DatasetMetadata;
  preview: DatasetPreview;
  progress_states: string[];
}

export type LabType = "regression" | "forecast" | "var";

export interface VariableCoverage {
  variable: string;
  exists: boolean;
  selected: boolean;
  non_null_count: number;
  first_date?: string | null;
  last_date?: string | null;
  all_missing: boolean;
}

export interface ModelReadinessRequest {
  dataset_id: string;
  lab_type: LabType;
  country?: string | null;
  date_start?: string | null;
  date_end?: string | null;
  dependent_variable?: string | null;
  independent_variables?: string[];
  target_variable?: string | null;
  external_variables?: string[];
  variables?: string[];
  model_type?: string | null;
  lag_order?: number;
}

export interface ModelReadinessResponse {
  dataset_id: string;
  lab_type: LabType;
  status: "ready" | "warning" | "blocked";
  run_enabled: boolean;
  country?: string | null;
  frequency: string;
  date_range?: string | null;
  model_numeric_columns: string[];
  selected_variables: string[];
  missing_columns: string[];
  variable_coverage: VariableCoverage[];
  complete_case_count: number;
  required_observations: number;
  suggested_date_start?: string | null;
  suggested_date_end?: string | null;
  blocking_issues: string[];
  recommendations: string[];
}
