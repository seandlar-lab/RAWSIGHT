export type LongTemporalSeriesProjectionPoint = {
  projection_index: number;
  time: string;
  count: number;
  mean: number | null;
  minimum: number | null;
  maximum: number | null;
  bucket_start: string | null;
  bucket_end: string | null;
};

export type LongTemporalSeriesSource = {
  usable_observation_count: number;
  first_observation: string | null;
  last_observation: string | null;
};

export type LongTemporalSeriesDisplayProjection = {
  mode: string;
  point_limit: number;
  point_count: number;
  bucket_width_seconds: number | null;
  points: LongTemporalSeriesProjectionPoint[];
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
