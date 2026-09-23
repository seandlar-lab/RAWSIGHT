export type WideTemporalReferencePosition = {
  axis_index: number;
  population_count: number;
  numeric_count: number;
  missing_count: number;
  non_numeric_count: number;
  sum: number | null;
  mean: number | null;
  median: number | null;
  p10: number | null;
  p25: number | null;
  p50: number | null;
  p75: number | null;
  p90: number | null;
  column_index: number;
  label: string;
};

export type WideTemporalReferenceProfile = {
  status: string;
  analysis_kind: "wide_temporal_reference" | string;
  statistics_mode: "exact" | "approximate" | string;
  percentile_method: string;
  population_count: number;
  temporal_position_count: number;
  retained_numeric_value_count: number;
  retained_numeric_payload_bytes: number;
  positions: WideTemporalReferencePosition[];
};

export type WideTemporalReferenceExecution = {
  status: string;
  analysis_kind:
    | "wide_temporal_reference_execution"
    | string;
  execution_mode: string;
  rows_processed: number;
  dataset_column_count: number;
  temporal_column_count: number;
  reference_profile: WideTemporalReferenceProfile;
};
