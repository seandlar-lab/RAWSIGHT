export type NumericHistogramBin = {
    lower_bound: number;
    upper_bound: number;
    count: number;
};

export type NumericDistribution = {
    column: string;
    technical_type: string;

    total_rows: number;
    non_null_count: number;
    null_count: number;
    distinct_count: number;

    minimum: number | null;
    p05: number | null;
    q1: number | null;
    median: number | null;
    q3: number | null;
    p95: number | null;
    maximum: number | null;

    mean: number | null;
    standard_deviation: number | null;
    iqr: number | null;

    zero_count: number;
    negative_count: number;

    histogram_bins: NumericHistogramBin[];
};

export type CategoricalValueFrequency = {
    value: string;
    count: number;
    percent_of_non_null: number;
};

export type CategoricalDistribution = {
    column: string;
    technical_type: string;

    total_rows: number;
    non_null_count: number;
    null_count: number;
    distinct_count: number;

    dominant_value: CategoricalValueFrequency | null;
    top_values: CategoricalValueFrequency[];
};

export type TemporalAxisAnalysis = {
    column: string;
    format_hint: string | null;
    excluded_values: string[];

    candidate_count: number;
    valid_count: number;
    invalid_count: number;

    distinct_time_points: number;
    duplicate_timestamp_rows: number;

    first_observation: string | null;
    last_observation: string | null;
};

export type TemporalCadenceAnalysis = {
    column: string;
    format_hint: string | null;

    interval_count: number;

    minimum_interval_seconds: number | null;
    median_interval_seconds: number | null;
    mean_interval_seconds: number | null;
    maximum_interval_seconds: number | null;
};

export type TemporalGap = {
    from: string;
    to: string;
    interval_seconds: number;
    multiple_of_median: number;
};

export type TemporalGapsAnalysis = {
    column: string;
    status: "ok" | "insufficient_data";

    gap_factor: number;

    median_interval_seconds: number | null;
    gap_threshold_seconds: number | null;

    gap_count: number;
    gaps: TemporalGap[];
};

export type TemporalAnalysis = {
    axis: TemporalAxisAnalysis;
    cadence: TemporalCadenceAnalysis;
    gaps: TemporalGapsAnalysis;
};

export type RawAnalysisColumnResult = {
    column: string;
    technical_type: string;
    semantic_type: string | null;
    role: string | null;
    included: boolean;

    routing:
    | "numeric"
    | "categorical"
    | "temporal"
    | "identifier"
    | "provenance"
    | "excluded"
    | "unsupported";

    distribution:
    | NumericDistribution
    | CategoricalDistribution
    | Record<string, unknown>
    | null;
    outliers: Record<string, unknown> | null;
    temporal: TemporalAnalysis | null;
};