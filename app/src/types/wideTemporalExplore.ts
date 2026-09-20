export type WideTemporalDescriptor = {
  column_index: number;
  column_name: string;
  value: string | number | boolean | null;
};

export type WideTemporalSeriesSummary = {
  series_index: number;
  descriptors: WideTemporalDescriptor[];
  classification: string;
  temporal_value_count: number;
  numeric_value_count: number;
  missing_value_count: number;
  non_numeric_value_count: number;
  positive_transition_count: number;
  negative_transition_count: number;
  unchanged_transition_count: number;
  largest_positive_change: number | null;
  largest_negative_change: number | null;
};

export type WideTemporalSeriesPage = {
  status: string;
  execution_mode: string;
  classification_filter: string | null;
  offset: number;
  limit: number;
  returned_count: number;
  next_offset: number | null;
  has_more: boolean;
  rows_scanned: number;
  series: WideTemporalSeriesSummary[];
};

export type WideTemporalTemporalPoint = {
  axis_index: number;
  column_index: number;
  label: string;
  value: string | number | boolean | null;
};

export type WideTemporalNegativeTransition = {
  from_index: number;
  to_index: number;
  previous_value: number;
  current_value: number;
  change: number;
  from_column_index: number;
  to_column_index: number;
  from_label: string;
  to_label: string;
};

export type WideTemporalSeriesDetail =
  WideTemporalSeriesSummary & {
    temporal_points: WideTemporalTemporalPoint[];
    negative_transitions: WideTemporalNegativeTransition[];
  };
