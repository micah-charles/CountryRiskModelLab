export interface ResearchCaseSummary {
  case_id: string;
  schema_version: string;
  title: string;
  short_title: string;
  summary: string;
  countries: string[];
  start_date?: string | null;
  end_date?: string | null;
  anchor_event_date?: string | null;
  themes: string[];
  difficulty: string;
  source_count: number;
  indicator_count: number;
  prediction_count: number;
  formula_refs: string[];
  has_report: boolean;
  origin: "built_in" | "imported";
}

export interface ResearchCase {
  case_id: string;
  schema_version: string;
  title: string;
  short_title: string;
  summary: string;
  countries: string[];
  regions: string[];
  start_date?: string | null;
  end_date?: string | null;
  anchor_event_date?: string | null;
  themes: string[];
  difficulty: string;
  trigger: Record<string, unknown>;
  background: string;
  timeline: Record<string, unknown>[];
  expected_transmission: Record<string, unknown>[];
  actual_market_moves: Record<string, unknown>[];
  market_series: Record<string, unknown>[];
  predictions: PredictionQuestion[];
  consequences: { nodes?: Record<string, unknown>[]; edges?: Record<string, unknown>[]; [key: string]: unknown };
  portfolio_impacts: Record<string, unknown>[];
  formula_refs: string[];
  lessons: (string | Record<string, unknown>)[];
  sources: Record<string, unknown>[];
  datasets: Record<string, unknown>[];
  artifacts: Record<string, string>;
  evidence_policy: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export type AnalyticalSupportType = "formula" | "statistical_model" | "transmission" | "identity" | "rule_of_thumb" | "none";

export type PredictionQuestionType = "directional" | "binary" | "numeric" | "categorical" | "ranking" | "free_text";

export interface AnalyticalSupport {
  type: AnalyticalSupportType;
  reference_id?: string | null;
  title?: string;
  summary?: string;
  available_before_reveal?: boolean;
}

export interface PredictionQuestion {
  prediction_id: string;
  prompt: string;
  type: PredictionQuestionType;
  options: string[];
  expected_answer?: unknown;
  actual_direction?: string | null;
  actual_answer?: unknown;
  assessment?: string | null;
  explanation?: string;
  source_ids: string[];
  analytical_support?: AnalyticalSupport | null;
  confidence_required?: boolean;
  magnitude_label?: string;
  magnitude_placeholder?: string;
  [key: string]: unknown;
}

export interface CasePackValidation {
  valid: boolean;
  case_id?: string | null;
  schema_version?: string | null;
  imported: boolean;
  files: string[];
  file_hashes: Record<string, string>;
  errors: string[];
  warnings: string[];
  case?: ResearchCase | null;
  case_summary?: ResearchCaseSummary | null;
}

export interface IndicatorDefinition {
  indicator_id: string;
  name: string;
  family: string;
  description: string;
  unit: string;
  direction_semantics: string;
  frequency: string;
  source: string;
  source_series_id?: string | null;
  transformation: string;
  display_format: string;
}

export interface FormulaVariable {
  name: string;
  symbol: string;
  label: string;
  type: "number" | "array" | "matrix" | "text";
  unit: string;
  default: unknown;
  min?: number | null;
  max?: number | null;
  step?: number | null;
}

export interface FormulaWorkedExample {
  name: string;
  inputs: Record<string, unknown>;
  expected_outputs: Record<string, unknown>;
}

export interface FormulaDefinition {
  formula_id: string;
  name: string;
  family: string;
  business_question: string;
  support_type: "formula";
  difficulty: string;
  latex: string;
  plain_english: string;
  variables: FormulaVariable[];
  assumptions: string[];
  limitations: string[];
  calculation_method: string;
  worked_examples: FormulaWorkedExample[];
  related_formula_ids: string[];
  relevant_indicator_ids: string[];
}

export interface TransmissionChannel {
  label: string;
  description: string;
  direction: string;
}

export interface TransmissionDefinition {
  transmission_id: string;
  title: string;
  summary: string;
  trigger: string;
  channels: TransmissionChannel[];
  countervailing_channels: TransmissionChannel[];
  expected_relationship: string;
  limitations: string[];
  evidence_refs: string[];
}

export interface AnalyticalSupportDefinition {
  support_type: AnalyticalSupportType;
  reference_id?: string | null;
  title: string;
  summary: string;
  available_before_reveal: boolean;
  formula?: FormulaDefinition | null;
  transmission?: TransmissionDefinition | null;
  model?: Record<string, unknown> | null;
  identity?: Record<string, unknown> | null;
  rule_of_thumb?: Record<string, unknown> | null;
}

export interface FormulaStep {
  label: string;
  expression: string;
  result: unknown;
}

export interface FormulaCalculation {
  formula_id: string;
  input_origin: string;
  parameters: Record<string, unknown>;
  outputs: Record<string, unknown>;
  headline: string;
  steps: FormulaStep[];
  assumptions: string[];
  limitations: string[];
}
