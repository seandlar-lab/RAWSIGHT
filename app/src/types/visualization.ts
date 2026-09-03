export type VisualizationType =
    | "histogram"
    | "boxplot"
    | "scatter"
    | "line"
    | "bar"
    | "heatmap"
    | "dependency_graph";

export type VisualizationReason =
    | "numeric_distribution"
    | "numeric_outliers"
    | "numeric_relationship"
    | "temporal_series"
    | "categorical_distribution"
    | "categorical_relationship"
    | "functional_dependency";

export type VisualizationSpec = {
    chartType: VisualizationType;

    title: string;

    xColumn?: string;
    yColumn?: string;
    groupByColumn?: string;
};

export type VisualizationRecommendation = {
    reason: VisualizationReason;

    recommended: VisualizationSpec;

    alternatives?: VisualizationSpec[];

    confidence?: number;
};

export type VisualizationValue =
    | string
    | number
    | null;

export type VisualizationRow = Record<
    string,
    VisualizationValue
>;

export type VisualizationData = {
    rows: VisualizationRow[];
};