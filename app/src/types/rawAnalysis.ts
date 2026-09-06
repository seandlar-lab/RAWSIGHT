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

    distribution: NumericDistribution | Record<string, unknown> | null;
    outliers: Record<string, unknown> | null;
    temporal: Record<string, unknown> | null;
};