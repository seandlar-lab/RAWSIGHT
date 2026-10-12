export type LongTemporalSeriesProjectionPoint = {
  projection_index: number;
  time: string;
  value: number;
  position: number;
  roles: string[];
  break_before: boolean;
};

export type LongTemporalSeriesBucket = {
  bucket_index: number;
  bucket_start: string;
  bucket_end: string;
  count: number;
  mean: number | null;
  minimum: number | null;
  maximum: number | null;
};

export type LongTemporalSeriesGroup = {
  time: string;
  count: number;
  mean: number | null;
  minimum: number | null;
  maximum: number | null;
};

export type LongTemporalSeriesSource = {
  usable_observation_count: number;
  first_observation: string | null;
  last_observation: string | null;
};

export type LongTemporalSeriesDetailSource = {
  matching_observation_count: number;
  first_observation: string | null;
  last_observation: string | null;
};

export type LongTemporalSeriesRequestedRange = {
  start: string;
  end: string;
};

export type LongTemporalSeriesDisplayProjection = {
  mode: string;
  point_limit: number;
  point_count: number;
  bucket_count: number | null;
  bucket_width_seconds: number | null;
  points: LongTemporalSeriesProjectionPoint[];
  buckets?: LongTemporalSeriesBucket[];
  groups?: LongTemporalSeriesGroup[];
};

export type LongTemporalSeriesExecution = {
  mode: string;
  temporal_display_order: string;
  source_order_used: boolean;
  point_limit: number;
  limitations: string[];
};

export type LongTemporalSeriesResult = {
  status: string;
  result_kind: string;

  temporal_column_index: number;
  temporal_column_name: string;

  value_column_index: number;
  value_column_name: string;
  value_technical_type: string;

  source: LongTemporalSeriesSource;

  display_projection:
  LongTemporalSeriesDisplayProjection;

  execution: LongTemporalSeriesExecution;
};

export type LongTemporalSeriesDetailResult = {
  status: string;
  result_kind: string;

  temporal_column_index: number;
  temporal_column_name: string;

  value_column_index: number;
  value_column_name: string;
  value_technical_type: string;

  requested_range:
  LongTemporalSeriesRequestedRange;

  source: LongTemporalSeriesDetailSource;

  display_projection:
  LongTemporalSeriesDisplayProjection;

  execution: LongTemporalSeriesExecution;
};
