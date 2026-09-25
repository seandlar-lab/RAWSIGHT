export type WideTemporalReferenceComparisonPosition = {
  axis_index: number;
  column_index: number;
  label: string;
  selected_value_kind: "numeric" | "missing" | "non_numeric" | string;
  selected_value: number | null;
  reference_numeric_count: number;
  reference_median: number | null;
  difference_from_median: number | null;
  percentile_position: number | null;
};

export type WideTemporalReferenceComparison = {
  status: string;
  analysis_kind: string;
  percentile_position_method: string;
  temporal_position_count: number;
  evaluated_position_count: number;
  selected_missing_count: number;
  selected_non_numeric_count: number;
  reference_without_numeric_count: number;
  percentile_position_min: number | null;
  percentile_position_max: number | null;
  difference_from_median_min: number | null;
  difference_from_median_max: number | null;
  positions: WideTemporalReferenceComparisonPosition[];
};

export type WideTemporalReferenceComparisonExecution = {
  status: string;
  analysis_kind: string;
  execution_mode: string;
  series_index: number;
  reference_cache_status: string;
  reference_population_count: number | null;
  reference_statistics_mode: string | null;
  reference_percentile_method: string | null;
  selected_series_rows_scanned: number;
  temporal_column_count: number;
  comparison: WideTemporalReferenceComparison;
  limitations?: {
    series_index_is_source_row_ordinal?: boolean;
    cache_miss_builds_reference_before_selected_series_read?: boolean;
    source_and_artifact_are_not_a_transactional_snapshot?: boolean;
  };
};
