import type { DatasetMetadata } from "./dataset";

export interface ModelResult {
  model_type: string;
  dataset?: DatasetMetadata;
  [key: string]: unknown;
}

